"""
FlexPoint Loan Funding Forecasting — v3 Feature Engineering

Extends v2 with 12 interaction / combination features per Augie's direction:
  - Lock × Stage interactions (4)
  - Lock × Time-at-stage interactions (3)
  - Lock extension proxies (2)
  - Velocity / momentum features (3)

All v2 features are preserved unchanged.  The new features are appended
after the existing 15 numeric features so the v2 baseline is fully intact.
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from transition_tables import vectorized_current_stage

# ─── Feature definitions ─────────────────────────────────────────────────────

# v2 features (unchanged)
V2_NUMERIC_FEATURES = [
    "stage_rank",
    "days_at_stage",
    "days_remaining",
    "loan_amount",
    "credit_score",
    "ltv",
    "cltv",
    "note_rate",
    "lock_period",
    "stage_only_probability",
    # v2: lock date features
    "is_locked",
    "days_until_lock_expiry",
    "lock_already_expired",
    "days_since_lock",
    "lock_expiry_vs_month_end",
]

# v3 interaction features
V3_INTERACTION_FEATURES = [
    # Lock × Stage (4)
    "locked_at_early_stage",
    "unlocked_at_late_stage",
    "lock_expiring_not_progressed",
    "lock_expired_not_progressed",
    # Lock × Time-at-stage (3)
    "stale_at_approved",
    "fresh_lock_late_stage",
    "long_days_expiring_lock",
    # Lock extension proxies (2)
    "likely_lock_extended",
    "days_past_lock_expiry",
    # Velocity / momentum (3)
    "stages_per_day",
    "days_since_open",
    "approved_to_lock_speed",
]

NUMERIC_FEATURES = V2_NUMERIC_FEATURES + V3_INTERACTION_FEATURES

CATEGORICAL_FEATURES = [
    "product_type",
    "loan_purpose",
    "branch_channel",
    "occupancy_type",
]

# Metadata columns carried for splitting / tracking (not used as features)
META_COLUMNS = [
    "snapshot_year",
    "snapshot_month",
    "snapshot_day",
    "loan_guid",
    "fund_by_end",
]


# ─── Shared feature construction ─────────────────────────────────────────────

def build_feature_row(active_df, as_of, month_end, transition_tables):
    """
    Construct the feature matrix for a set of active loans at a snapshot.

    This function is the SINGLE source of truth for feature engineering.
    It is called identically during training and scoring.

    v3: Adds 12 interaction features after the v2 base features.
    """
    as_of = pd.Timestamp(as_of)
    month_end = pd.Timestamp(month_end)
    days_remaining = (month_end - as_of).days

    # ── stage_only_probability: stage-only lookup (no product/purpose) ────
    me_unstrat = transition_tables.get("me_unstratified")
    if me_unstrat is not None:
        stage_map = me_unstrat["p_fund"].to_dict()
        stage_prob = active_df["current_stage"].map(stage_map).fillna(0.0)
    else:
        stage_prob = pd.Series(0.0, index=active_df.index)

    # ── v2 lock date features ─────────────────────────────────────────────
    rate_lock_d = active_df.get("Rate Lock D")
    rate_lock_exp = active_df.get("Rate Lock Expiration D")
    has_rate_lock = active_df.get("HasRateLock")

    # is_locked
    if rate_lock_d is not None and has_rate_lock is not None:
        is_locked = (
            (has_rate_lock == 1)
            & rate_lock_d.notna()
            & (rate_lock_d <= as_of)
        ).astype(int)
    else:
        is_locked = pd.Series(0, index=active_df.index)

    # days_until_lock_expiry
    if rate_lock_exp is not None:
        days_until_expiry = (rate_lock_exp - as_of).dt.days.astype(float)
        days_until_expiry = days_until_expiry.where(is_locked == 1, other=np.nan)
    else:
        days_until_expiry = pd.Series(np.nan, index=active_df.index)

    # lock_already_expired
    if rate_lock_exp is not None:
        lock_expired = (
            rate_lock_exp.notna() & (rate_lock_exp < as_of)
        ).astype(int)
    else:
        lock_expired = pd.Series(0, index=active_df.index)

    # days_since_lock
    if rate_lock_d is not None:
        days_since = (as_of - rate_lock_d).dt.days.astype(float)
        days_since = days_since.where(is_locked == 1, other=np.nan)
    else:
        days_since = pd.Series(np.nan, index=active_df.index)

    # lock_expiry_vs_month_end
    if rate_lock_exp is not None:
        expiry_vs_me = (rate_lock_exp - month_end).dt.days.astype(float)
        expiry_vs_me = expiry_vs_me.where(rate_lock_exp.notna(), other=np.nan)
    else:
        expiry_vs_me = pd.Series(np.nan, index=active_df.index)

    # ── Intermediate values used by v3 interaction features ───────────────
    stage_rank = active_df["stage_rank"].values.astype(float)
    days_at_stage = active_df["days_at_stage"].values.astype(float)
    is_locked_arr = is_locked.values.astype(float)
    lock_expired_arr = lock_expired.values.astype(float)
    days_until_expiry_arr = days_until_expiry.values.astype(float)
    days_since_arr = days_since.values.astype(float)

    # ══════════════════════════════════════════════════════════════════════
    # v3 INTERACTION FEATURES
    # ══════════════════════════════════════════════════════════════════════

    # --- Lock × Stage interactions (4) ---

    # 1. locked_at_early_stage: locked AND stage_rank <= 4 (Opened..Approved)
    locked_at_early_stage = ((is_locked_arr == 1) & (stage_rank <= 4)).astype(float)

    # 2. unlocked_at_late_stage: NOT locked AND stage_rank >= 5 (past Approved)
    unlocked_at_late_stage = ((is_locked_arr == 0) & (stage_rank >= 5)).astype(float)

    # 3. lock_expiring_not_progressed: lock expires within 7 days AND stage <= 6
    #    (hasn't reached CTC). Augie's exact scenario.
    lock_expiring_not_progressed = (
        (days_until_expiry_arr > 0)
        & (days_until_expiry_arr <= 7)
        & (stage_rank <= 6)
    ).astype(float)

    # 4. lock_expired_not_progressed: expired AND stage <= 6
    lock_expired_not_progressed = (
        (lock_expired_arr == 1) & (stage_rank <= 6)
    ).astype(float)

    # --- Lock × Time-at-stage interactions (3) ---

    # 5. stale_at_approved: at Approved stage AND days_at_stage > 30
    current_stage_arr = active_df["current_stage"].values
    stale_at_approved = (
        (current_stage_arr == "Approved") & (days_at_stage > 30)
    ).astype(float)

    # 6. fresh_lock_late_stage: locked AND locked recently (<=14 days)
    #    AND stage >= 7 (CTC or later)
    fresh_lock_late_stage = (
        (is_locked_arr == 1)
        & (days_since_arr <= 14)
        & np.isfinite(np.where(np.isnan(days_since_arr), np.inf, days_since_arr))
        & (stage_rank >= 7)
    ).astype(float)

    # 7. long_days_expiring_lock: days_at_stage > 30 AND lock expires within 14 days
    long_days_expiring_lock = (
        (days_at_stage > 30)
        & (days_until_expiry_arr > 0)
        & (days_until_expiry_arr <= 14)
    ).astype(float)

    # --- Lock extension proxies (2) ---

    # 8. likely_lock_extended: loan still active AND lock already expired.
    #    Active-at-snapshot is already guaranteed by the caller, so just check
    #    lock_already_expired == 1.
    likely_lock_extended = lock_expired_arr.copy()

    # 9. days_past_lock_expiry: for expired locks, (as_of - expiry).days
    if rate_lock_exp is not None:
        days_past_expiry = (as_of - rate_lock_exp).dt.days.astype(float)
        days_past_expiry = days_past_expiry.where(lock_expired == 1, other=np.nan)
        days_past_expiry_arr = days_past_expiry.values
    else:
        days_past_expiry_arr = np.full(len(active_df), np.nan)

    # --- Velocity / momentum features (3) ---

    # 10. days_since_open: (as_of - Loan Open Date).days
    loan_open = active_df.get("Loan Open Date")
    if loan_open is not None:
        days_since_open_arr = (as_of - loan_open).dt.days.astype(float).values
    else:
        days_since_open_arr = np.full(len(active_df), np.nan)

    # 11. stages_per_day: stage_rank / max(days_since_open, 1)
    safe_days = np.where(
        np.isnan(days_since_open_arr) | (days_since_open_arr < 1),
        1.0,
        days_since_open_arr,
    )
    stages_per_day = stage_rank / safe_days

    # 12. approved_to_lock_speed: (Rate Lock D - Approved D).days
    #     Negative = locked before approval (very committed). NaN if either missing.
    approved_d = active_df.get("Approved D")
    if approved_d is not None and rate_lock_d is not None:
        atl_speed = (rate_lock_d - approved_d).dt.days.astype(float)
        # Only meaningful when both dates exist and occurred on or before as_of
        atl_valid = (
            approved_d.notna()
            & (approved_d <= as_of)
            & rate_lock_d.notna()
            & (rate_lock_d <= as_of)
        )
        atl_speed = atl_speed.where(atl_valid, other=np.nan)
        atl_speed_arr = atl_speed.values
    else:
        atl_speed_arr = np.full(len(active_df), np.nan)

    # ── Assemble features DataFrame ──────────────────────────────────────
    features = pd.DataFrame({
        # v2 features (15)
        "stage_rank":               stage_rank,
        "days_at_stage":            days_at_stage,
        "days_remaining":           days_remaining,
        "loan_amount":              active_df["LoanAmount"].values,
        "credit_score":             active_df["DecisionCreditScore"].values,
        "ltv":                      active_df["LTV"].values,
        "cltv":                     active_df["CLTV"].values,
        "note_rate":                active_df["NoteRate"].values,
        "lock_period":              active_df["Lock Period (days)"].values,
        "stage_only_probability":   stage_prob.values,
        "is_locked":                is_locked.values,
        "days_until_lock_expiry":   days_until_expiry.values,
        "lock_already_expired":     lock_expired.values,
        "days_since_lock":          days_since.values,
        "lock_expiry_vs_month_end": expiry_vs_me.values,
        # v3 interaction features (12)
        "locked_at_early_stage":         locked_at_early_stage,
        "unlocked_at_late_stage":        unlocked_at_late_stage,
        "lock_expiring_not_progressed":  lock_expiring_not_progressed,
        "lock_expired_not_progressed":   lock_expired_not_progressed,
        "stale_at_approved":             stale_at_approved,
        "fresh_lock_late_stage":         fresh_lock_late_stage,
        "long_days_expiring_lock":       long_days_expiring_lock,
        "likely_lock_extended":          likely_lock_extended,
        "days_past_lock_expiry":         days_past_expiry_arr,
        "stages_per_day":                stages_per_day,
        "days_since_open":               days_since_open_arr,
        "approved_to_lock_speed":        atl_speed_arr,
        # Categoricals (4)
        "product_type":             active_df["Product Type"].values,
        "loan_purpose":             active_df["Loan Purpose"].values,
        "branch_channel":           active_df["Branch Channel"].values,
        "occupancy_type":           active_df["Occupancy Type"].values,
    }, index=active_df.index)

    return features


# ─── Training set builder ────────────────────────────────────────────────────

def build_training_set(df, transition_tables, months=None):
    """
    Build the full training dataset from historical pipeline snapshots.

    Identical logic to v2 — calls v3 build_feature_row for the new features.
    """
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()

    month_list = months if months is not None else config.BACKTEST_MONTHS
    chunks = []
    for year, month in month_list:
        for day in config.SNAPSHOT_DAYS:
            if day == 0:
                as_of = pd.Timestamp(year, month, 1) - pd.Timedelta(days=1)
                month_end = (pd.Timestamp(year, month, 1)
                             + pd.offsets.MonthEnd(0))
            else:
                as_of = pd.Timestamp(year, month, day)
                month_end = as_of.replace(day=1) + pd.offsets.MonthEnd(0)

            # ── Active loan identification ─────────────────────────────────
            opened = (
                completed["Loan Open Date"].notna()
                & (completed["Loan Open Date"] <= as_of)
            )
            not_funded = (
                completed["Funded D"].isna()
                | (completed["Funded D"] > as_of)
            )
            not_failed = pd.Series(True, index=completed.index)
            for col in config.FAILURE_DATE_COLUMNS:
                if col in completed.columns:
                    not_failed &= completed[col].isna() | (completed[col] > as_of)

            active = completed.loc[opened & not_funded & not_failed].copy()
            if len(active) < 50:
                continue

            # ── Stage computation ──────────────────────────────────────────
            sl, sr, se = vectorized_current_stage(active, as_of)
            active["current_stage"] = sl
            active["stage_rank"] = sr
            active["days_at_stage"] = (as_of - se).dt.days
            active = active[active["current_stage"].notna()]

            if len(active) == 0:
                continue

            # ── Target: fund by month end ──────────────────────────────────
            fund_by_end = (
                active["Funded D"].notna() & (active["Funded D"] <= month_end)
            ).astype(int)

            # ── Features ───────────────────────────────────────────────────
            features = build_feature_row(active, as_of, month_end,
                                         transition_tables)

            # ── Attach metadata + target ───────────────────────────────────
            features["snapshot_year"] = year
            features["snapshot_month"] = month
            features["snapshot_day"] = day
            features["loan_guid"] = active["LoanGuid"].values
            features["fund_by_end"] = fund_by_end.values

            chunks.append(features)

    return pd.concat(chunks, ignore_index=True)


# ─── Categorical encoding (unchanged from v2) ────────────────────────────────

def encode_categoricals(df, encoders=None, fit=True):
    """One-hot encode categorical columns."""
    df = df.copy()
    if encoders is None:
        encoders = {}

    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            continue

        df[col] = df[col].fillna("MISSING").astype(str)

        if fit:
            categories = sorted(df[col].unique().tolist())
            encoders[col] = categories
        else:
            categories = encoders.get(col, [])

        for cat in categories:
            df[f"{col}_{cat}"] = (df[col] == cat).astype(int)

        df.drop(columns=[col], inplace=True)

    return df, encoders


def fill_missing_numeric(df, medians=None, fit=True):
    """Fill NaN in numeric features with training-set medians."""
    df = df.copy()
    if medians is None:
        medians = {}

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            continue
        if fit:
            medians[col] = float(df[col].median())
        df[col] = df[col].fillna(medians.get(col, 0))

    return df, medians


def get_feature_columns(encoders):
    """Return the ordered list of feature column names after encoding."""
    cols = list(NUMERIC_FEATURES)
    for cat_col in CATEGORICAL_FEATURES:
        categories = encoders.get(cat_col, [])
        cols.extend(f"{cat_col}_{cat}" for cat in categories)
    return cols
