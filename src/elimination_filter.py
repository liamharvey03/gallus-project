"""
FlexPoint Loan Funding Forecasting — Elimination Filter (Dead Loan Detection)

Conservative rule-based filter that identifies loans with <2% historical
funding probability and sets their predicted probability to zero before
dollar-volume aggregation.

Rules are derived from empirical analysis across 24 months of snapshots
(Jan 2024 – Dec 2025).  Each rule cites the historical funding rate and
sample size that justifies it.

Usage:
    from elimination_filter import apply_elimination_filter
    scored_df = apply_elimination_filter(scored_df, as_of)

The filter adds two columns:
    - `eliminated` (bool):  True if the loan is flagged as dead
    - `elimination_reason` (str):  Human-readable rule that triggered it
"""

import numpy as np
import pandas as pd

# ─── Rule definitions ─────────────────────────────────────────────────────────
#
# Each rule is a dict with:
#   name        — short label for reporting
#   description — human-readable explanation for Augie
#   hist_rate   — historical funding rate (%) from Part A analysis
#   hist_n      — sample size backing the rate
#   condition   — callable(row_dict) → bool, evaluated per-loan
#
# Rules are evaluated in order; the FIRST matching rule wins.
# All rules target loans with historical funding rate < 2%.

RULES = [
    # ── Tier 1: Essentially zero funding rate ────────────────────────────
    {
        "name": "opened_stale",
        "description": "Opened stage, 30+ days — loan never progressed past intake",
        "hist_rate": 0.006,
        "hist_n": 16325,
    },
    {
        "name": "application_stale",
        "description": "Application stage, 30+ days — stalled at application",
        "hist_rate": 0.0,
        "hist_n": 302,
    },
    {
        "name": "submitted_unlocked_stale",
        "description": "Submitted + unlocked, 22+ days — no lock, no progression",
        "hist_rate": 0.1,
        "hist_n": 5553,
    },
    {
        "name": "underwriting_unlocked_stale",
        "description": "Underwriting + unlocked, 22+ days — stuck in UW without lock",
        "hist_rate": 0.1,
        "hist_n": 15883,
    },
    {
        "name": "approved_expired_lock",
        "description": "Approved stage + lock expired — lock expired without CTC",
        "hist_rate": 0.0,
        "hist_n": 1141,
    },

    # ── Tier 2: Very low but nonzero ─────────────────────────────────────
    {
        "name": "submitted_any_22d",
        "description": "Submitted stage, 22+ days (regardless of lock)",
        "hist_rate": 0.1,
        "hist_n": 5587,
    },
    {
        "name": "underwriting_unlocked_8d",
        "description": "Underwriting + unlocked, 8+ days",
        "hist_rate": 0.2,
        "hist_n": 16500,
    },
]


def _compute_lock_fields(df, as_of):
    """Compute is_locked and lock_expired for a DataFrame of active loans."""
    as_of = pd.Timestamp(as_of)

    rate_lock_d = df.get("Rate Lock D")
    rate_lock_exp = df.get("Rate Lock Expiration D")
    has_rate_lock = df.get("HasRateLock")

    # is_locked
    if rate_lock_d is not None and has_rate_lock is not None:
        is_locked = (
            (has_rate_lock == 1)
            & rate_lock_d.notna()
            & (rate_lock_d <= as_of)
        ).astype(int)
    else:
        is_locked = pd.Series(0, index=df.index)

    # lock_expired
    if rate_lock_exp is not None:
        lock_expired = (
            rate_lock_exp.notna() & (rate_lock_exp < as_of)
        ).astype(int)
    else:
        lock_expired = pd.Series(0, index=df.index)

    return is_locked, lock_expired


def apply_elimination_filter(scored_df, as_of, active_df=None,
                              conservative=True, month_end=None):
    """
    Flag dead loans in a scored pipeline snapshot.

    Parameters
    ----------
    scored_df : DataFrame
        The feature / scored DataFrame produced by build_feature_row or
        build_snapshot.  Must contain at least: stage_rank, days_at_stage.
        If current_stage is missing, stage_rank is used to infer it.
    as_of : date-like
        The snapshot date (needed for lock-status computation).
    active_df : DataFrame, optional
        The raw loan DataFrame (pre-feature-engineering).  If provided,
        lock status is computed from raw columns (Rate Lock D, HasRateLock,
        Rate Lock Expiration D).  If None, the function expects is_locked
        and lock_already_expired columns in scored_df.
    conservative : bool
        If True (default), only apply Tier 1 rules (the safest).
        If False, also apply Tier 2 rules for more aggressive filtering.
    month_end : date-like, optional
        End of the target month.  When provided, staleness rules are only
        applied if days_remaining <= 20.  This prevents false negatives at
        beginning-of-month snapshots where loans still have time to progress.

    Returns
    -------
    scored_df : DataFrame
        Copy of input with two new columns: `eliminated`, `elimination_reason`.
    stats : dict
        Summary statistics: total loans, eliminated count, reason breakdown.
    """
    as_of = pd.Timestamp(as_of)
    result = scored_df.copy()
    result["eliminated"] = False
    result["elimination_reason"] = ""

    # ── Days-remaining guard ──────────────────────────────────────────────
    # At beginning-of-month snapshots (Days 0, 1), stale loans still have
    # 28-30 days to progress.  The staleness rules are only effective when
    # days_remaining <= 20, so skip them for early-month snapshots.
    if month_end is not None:
        days_remaining = (pd.Timestamp(month_end) - as_of).days
        if days_remaining > 20:
            stats = {
                "total_loans": len(result),
                "eliminated": 0,
                "kept": len(result),
                "pct_eliminated": 0.0,
                "by_reason": {},
                "skipped_days_remaining": days_remaining,
            }
            return result, stats

    # ── Gather required fields ────────────────────────────────────────────
    stage_rank = result["stage_rank"].values.astype(float)
    days_at_stage = result["days_at_stage"].values.astype(float)

    # Lock status — either from raw data or from scored features
    if active_df is not None:
        is_locked, lock_expired = _compute_lock_fields(active_df, as_of)
        is_locked = is_locked.reindex(result.index, fill_value=0).values
        lock_expired = lock_expired.reindex(result.index, fill_value=0).values
    elif "is_locked" in result.columns and "lock_already_expired" in result.columns:
        is_locked = result["is_locked"].values.astype(float)
        lock_expired = result["lock_already_expired"].values.astype(float)
    else:
        is_locked = np.zeros(len(result))
        lock_expired = np.zeros(len(result))

    # ── Apply rules ───────────────────────────────────────────────────────
    # We track which rows are still eligible for elimination (first-match wins)
    not_yet_flagged = np.ones(len(result), dtype=bool)

    # Determine which rules to apply
    tier1_rules = {
        "opened_stale", "application_stale", "submitted_unlocked_stale",
        "underwriting_unlocked_stale", "approved_expired_lock",
    }

    for rule in RULES:
        if conservative and rule["name"] not in tier1_rules:
            continue

        # Evaluate the condition vectorised
        mask = _evaluate_rule(
            rule["name"], stage_rank, days_at_stage, is_locked, lock_expired,
        )
        # Only flag loans not already flagged by a prior rule
        new_flags = mask & not_yet_flagged
        if new_flags.any():
            result.loc[result.index[new_flags], "eliminated"] = True
            result.loc[result.index[new_flags], "elimination_reason"] = rule["name"]
            not_yet_flagged &= ~new_flags

    # ── Build stats ───────────────────────────────────────────────────────
    reason_counts = (
        result.loc[result["eliminated"], "elimination_reason"]
        .value_counts()
        .to_dict()
    )
    stats = {
        "total_loans": len(result),
        "eliminated": int(result["eliminated"].sum()),
        "kept": int((~result["eliminated"]).sum()),
        "pct_eliminated": round(
            result["eliminated"].sum() / max(len(result), 1) * 100, 1
        ),
        "by_reason": reason_counts,
    }

    return result, stats


def _evaluate_rule(name, stage_rank, days_at_stage, is_locked, lock_expired):
    """Return a boolean mask for a single rule."""

    if name == "opened_stale":
        # Opened (rank 0), 30+ days
        return (stage_rank == 0) & (days_at_stage >= 30)

    elif name == "application_stale":
        # Application (rank 1), 30+ days
        return (stage_rank == 1) & (days_at_stage >= 30)

    elif name == "submitted_unlocked_stale":
        # Submitted (rank 2) + NOT locked + 22+ days
        return (stage_rank == 2) & (is_locked == 0) & (days_at_stage >= 22)

    elif name == "underwriting_unlocked_stale":
        # Underwriting (rank 3) + NOT locked + 22+ days
        return (stage_rank == 3) & (is_locked == 0) & (days_at_stage >= 22)

    elif name == "approved_expired_lock":
        # Approved (rank 4) + lock already expired
        return (stage_rank == 4) & (lock_expired == 1)

    elif name == "submitted_any_22d":
        # Submitted (rank 2), 22+ days, regardless of lock
        return (stage_rank == 2) & (days_at_stage >= 22)

    elif name == "underwriting_unlocked_8d":
        # Underwriting (rank 3) + NOT locked + 8+ days
        return (stage_rank == 3) & (is_locked == 0) & (days_at_stage >= 8)

    else:
        return np.zeros(len(stage_rank), dtype=bool)


def zero_eliminated_probabilities(scored_df, prob_column="ml_prob"):
    """
    Set predicted probability to zero for eliminated loans.

    Call this AFTER apply_elimination_filter and BEFORE dollar aggregation.
    """
    result = scored_df.copy()
    if "eliminated" in result.columns and prob_column in result.columns:
        result.loc[result["eliminated"], prob_column] = 0.0
    return result


# ─── Summary reporting ────────────────────────────────────────────────────────

def print_filter_stats(stats, label=""):
    """Pretty-print elimination filter statistics."""
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}Elimination Filter Summary")
    print(f"  Total active loans:  {stats['total_loans']:,}")
    print(f"  Eliminated:          {stats['eliminated']:,}  "
          f"({stats['pct_eliminated']:.1f}%)")
    print(f"  Kept:                {stats['kept']:,}")
    if stats["by_reason"]:
        print("  Breakdown by rule:")
        for reason, count in sorted(stats["by_reason"].items(),
                                     key=lambda x: -x[1]):
            rule_meta = next((r for r in RULES if r["name"] == reason), None)
            desc = rule_meta["description"] if rule_meta else reason
            print(f"    {reason:<35} {count:>5}  — {desc}")
