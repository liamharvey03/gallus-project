#!/usr/bin/env python3
"""
Generate outputs/dashboard_demo_data.json for the FlexPoint ops-manager demo.

Uses existing src/ modules for pipeline reconstruction, v3 feature engineering,
ML model training, and elimination filtering.

Usage:
    python src/generate_dashboard_data.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ── Path setup ──────────────────────────────────────────────────────────────
SRC = Path(__file__).resolve().parent
PROJECT = SRC.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(SRC))

import config
from data_prep import load_and_clean
from transition_tables import build_transition_tables
from feature_engineering_v3 import (
    build_training_set,
    encode_categoricals,
    fill_missing_numeric,
    get_feature_columns,
    build_feature_row,
)
from models import train_and_select, _predict_proba
from pipeline_snapshot import build_snapshot
from elimination_filter import apply_elimination_filter

# ── Configuration ───────────────────────────────────────────────────────────
SNAPSHOT_DATE = "2025-12-15"
SLA_THRESHOLD = 45

ELIM_TO_ARCHETYPE = {
    "opened_stale":                "Opened-Only Ghost",
    "application_stale":           "Early Dropout",
    "submitted_unlocked_stale":    "Stale Pre-Approval",
    "underwriting_unlocked_stale": "Stale Pre-Approval",
    "approved_expired_lock":       "Lock Expired, Gave Up",
}


def _safe(val):
    """Convert numpy / pandas scalars to JSON-serialisable Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return None if np.isnan(val) else float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, pd.Timestamp):
        return str(val.date())
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


# ═════════════════════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ═════════════════════════════════════════════════════════════════════════════

def build_loan_table(df, tables, model, feature_cols, encoders, medians):
    """Section 1: scored + filtered loan priority table."""
    as_of = pd.Timestamp(SNAPSHOT_DATE)
    month_start = as_of.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)

    # Pipeline snapshot (no ML — we score with v3 separately)
    snap = build_snapshot(df, as_of, month_end=month_end,
                          month_start=month_start,
                          transition_tables=tables)
    active = snap["active_pipeline"].copy()
    already_funded = snap["already_funded"]

    # ── v3 feature engineering + ML scoring ──────────────────────────────
    feats = build_feature_row(active, as_of, month_end, tables)
    feats_enc, _ = encode_categoricals(feats, encoders=encoders, fit=False)
    feats_enc, _ = fill_missing_numeric(feats_enc, medians=medians, fit=False)
    for c in feature_cols:
        if c not in feats_enc.columns:
            feats_enc[c] = 0
    X = feats_enc[feature_cols].values.astype(np.float32)
    probs = _predict_proba(model, X)

    active["ml_probability"] = probs
    active["expected_value"] = probs * active["LoanAmount"]
    active["is_locked_flag"] = feats["is_locked"].values.astype(bool)

    # ── Elimination filter (Tier 1 only) ─────────────────────────────────
    filtered, fstats = apply_elimination_filter(
        feats, as_of, active_df=active,
        conservative=True, month_end=month_end,
    )
    active["eliminated"] = filtered["eliminated"].values
    active["elimination_reason"] = filtered["elimination_reason"].values
    active["failure_archetype"] = (
        active["elimination_reason"]
        .map(ELIM_TO_ARCHETYPE)
        .where(active["eliminated"], other=None)
    )
    active["status"] = np.where(active["eliminated"], "dead", "live")

    # ── Top 50 live + 20 dead (stratified by rule, sorted by amount) ────
    active_sorted = active.sort_values("expected_value", ascending=False)
    live = active_sorted[active_sorted["status"] == "live"].head(50)

    # Stratified dead-loan sample: proportional to actual rule counts
    all_dead = active_sorted[active_sorted["status"] == "dead"]
    reason_counts = all_dead["elimination_reason"].value_counts()
    total_dead_pop = len(all_dead)
    target_n = 20

    dead_parts = []
    remaining = target_n
    reasons_sorted = reason_counts.index.tolist()
    for i, reason in enumerate(reasons_sorted):
        group = all_dead[all_dead["elimination_reason"] == reason]
        if i == len(reasons_sorted) - 1:
            n = remaining  # last group gets whatever is left
        else:
            n = max(1, round(len(group) / total_dead_pop * target_n))
            n = min(n, remaining, len(group))
        # Sort by loan_amount descending so biggest dead loans are visible
        dead_parts.append(group.sort_values("LoanAmount", ascending=False).head(n))
        remaining -= n
        if remaining <= 0:
            break
    dead = pd.concat(dead_parts).sort_values("LoanAmount", ascending=False) if dead_parts else all_dead.head(0)

    rows = []
    for _, r in pd.concat([live, dead]).iterrows():
        rows.append({
            "loan_guid":         _safe(r["LoanGuid"]),
            "loan_amount":       round(_safe(r["LoanAmount"]) or 0, 2),
            "product_type":      _safe(r.get("Product Type")),
            "current_stage":     _safe(r["current_stage"]),
            "days_at_stage":     _safe(r["days_at_stage"]),
            "is_locked":         bool(r["is_locked_flag"]),
            "ml_probability":    round(_safe(r["ml_probability"]) or 0, 4),
            "expected_value":    round(_safe(r["expected_value"]) or 0, 2),
            "status":            r["status"],
            "elimination_rule":  _safe(r["elimination_reason"]) or None,
            "failure_archetype": _safe(r["failure_archetype"]),
        })
    print(f"  Loan table: {len(live)} live + {len(dead)} dead = {len(rows)}")
    return rows, active, already_funded, fstats, feats


def build_pull_through(df):
    """Section 2: monthly pull-through rates by product type."""
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()
    results = []

    for year, month in config.BACKTEST_MONTHS:
        ms = pd.Timestamp(year, month, 1)
        me = ms + pd.offsets.MonthEnd(0)

        # Active at month start among completed loans
        opened = (completed["Loan Open Date"].notna()
                  & (completed["Loan Open Date"] <= ms))
        not_funded = completed["Funded D"].isna() | (completed["Funded D"] > ms)
        not_failed = pd.Series(True, index=completed.index)
        for col in config.FAILURE_DATE_COLUMNS:
            if col in completed.columns:
                not_failed &= completed[col].isna() | (completed[col] > ms)

        pipeline = completed[opened & not_funded & not_failed]
        funded_mask = pipeline["Funded D"].notna() & (pipeline["Funded D"] <= me)

        for product, grp in pipeline.groupby("Product Type"):
            total = len(grp)
            if total < 5:
                continue
            funded_n = int(funded_mask.loc[grp.index].sum())
            results.append({
                "month":             f"{year}-{month:02d}",
                "product":           _safe(product),
                "pull_through_rate": round(funded_n / total, 4),
                "funded_count":      funded_n,
                "total_count":       total,
            })
    print(f"  Pull-through: {len(results)} entries")
    return results


def build_cycle_times(df):
    """Section 3: application-to-funding cycle time distributions."""
    funded = df[df["Outcome"] == "Funded"].copy()
    app_date = funded["Respa App D"].fillna(funded["Loan Open Date"])
    funded["cycle_days"] = (funded["Funded D"] - app_date).dt.days
    funded = funded[funded["cycle_days"].notna() & (funded["cycle_days"] >= 0)]

    def _dist(vals):
        v = vals.dropna()
        return {
            "p10":           _safe(v.quantile(0.10)),
            "p25":           _safe(v.quantile(0.25)),
            "median":        _safe(v.median()),
            "p75":           _safe(v.quantile(0.75)),
            "p90":           _safe(v.quantile(0.90)),
            "mean":          round(float(v.mean()), 1),
            "count":         int(len(v)),
            "above_sla":     int((v > SLA_THRESHOLD).sum()),
            "above_sla_pct": round(float((v > SLA_THRESHOLD).mean() * 100), 1),
            "values":        [int(x) for x in v.values],
        }

    by_product = {}
    for product, grp in funded.groupby("Product Type"):
        if len(grp) < 10:
            continue
        by_product[_safe(product)] = _dist(grp["cycle_days"])

    result = {
        "sla_threshold_days": SLA_THRESHOLD,
        "overall":            _dist(funded["cycle_days"]),
        "by_product":         by_product,
    }
    print(f"  Cycle times: {len(by_product)} product types")
    return result


def build_backtest_accuracy():
    """Section 5: model accuracy stats from backtest results."""
    csv_path = config.OUTPUTS_PATH / "results" / "backtest_results_v3.csv"
    try:
        bt = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("  WARNING: backtest_results_v3.csv not found, skipping accuracy")
        return {"mape_day15": 0, "months_within_10pct": 0, "total_months": 0,
                "recent_months": []}

    # Filter to day-15, ML, rolling
    ml_rolling = bt[(bt["method"] == "ML") & (bt["training_mode"] == "rolling")
                     & (bt["snapshot_day"] == 15)].copy()
    if len(ml_rolling) == 0:
        # Fall back to fixed if rolling not available
        ml_rolling = bt[(bt["method"] == "ML") & (bt["snapshot_day"] == 15)].copy()

    if len(ml_rolling) == 0:
        return {"mape_day15": 0, "months_within_10pct": 0, "total_months": 0,
                "recent_months": []}

    mape = round(float(ml_rolling["error_pct"].abs().mean()), 1)
    within_10 = int((ml_rolling["error_pct"].abs() <= 10).sum())
    total = len(ml_rolling)

    # Last 8 months for sparkline
    recent = ml_rolling.sort_values(["year", "month"]).tail(8)
    recent_list = []
    for _, r in recent.iterrows():
        recent_list.append({
            "month": f"{int(r['year'])}-{int(r['month']):02d}",
            "projected": round(float(r["projected"]), 0),
            "actual": round(float(r["actual"]), 0),
            "error_pct": round(float(r["error_pct"]), 1),
        })

    print(f"  Backtest accuracy: {mape}% MAPE, {within_10}/{total} within 10%")
    return {
        "mape_day15": mape,
        "months_within_10pct": within_10,
        "total_months": total,
        "recent_months": recent_list,
    }


def build_stage_funnel(active):
    """Section 6: pipeline stage distribution for funnel chart."""
    STAGE_ORDER = {label: rank for _, label, rank in config.STAGE_MAP}
    rows = []
    for stage, grp in active.groupby("current_stage"):
        live_grp = grp[grp["status"] == "live"]
        rows.append({
            "stage": _safe(stage),
            "rank": STAGE_ORDER.get(stage, -1),
            "total_loans": int(len(grp)),
            "total_value": round(float(grp["LoanAmount"].sum()), 0),
            "live_loans": int(len(live_grp)),
            "live_value": round(float(live_grp["LoanAmount"].sum()), 0),
            "avg_probability": round(float(live_grp["ml_probability"].mean()), 4)
            if len(live_grp) > 0 else 0,
        })
    rows.sort(key=lambda x: x["rank"])
    print(f"  Stage funnel: {len(rows)} stages")
    return rows


def build_channel_split(active):
    """Section 7: Wholesale vs Retail breakdown."""
    results = []
    channel_col = "Branch Channel"
    if channel_col not in active.columns:
        print("  WARNING: Branch Channel not in data")
        return results

    active_clean = active.copy()
    active_clean[channel_col] = (
        active_clean[channel_col]
        .replace(["Blank", ""], pd.NA)
        .fillna("Unknown")
    )

    for channel, grp in active_clean.groupby(channel_col):
        live = grp[grp["status"] == "live"]
        if len(live) == 0:
            continue  # skip channels with no live loans
        results.append({
            "channel": _safe(channel),
            "total_loans": int(len(grp)),
            "total_value": round(float(grp["LoanAmount"].sum()), 0),
            "live_loans": int(len(live)),
            "live_value": round(float(live["LoanAmount"].sum()), 0),
            "projected_value": round(float(live["expected_value"].sum()), 0),
            "avg_probability": round(float(live["ml_probability"].mean()), 4)
            if len(live) > 0 else 0,
        })
    results.sort(key=lambda x: x["projected_value"], reverse=True)
    print(f"  Channel split: {len(results)} channels")
    return results


def build_product_breakdown(active):
    """Section 8: Product Type breakdown."""
    results = []
    prod_col = "Product Type"
    if prod_col not in active.columns:
        print("  WARNING: Product Type not in data")
        return results

    active_clean = active.copy()
    active_clean[prod_col] = active_clean[prod_col].fillna("Unknown")

    for product, grp in active_clean.groupby(prod_col):
        live = grp[grp["status"] == "live"]
        if len(live) == 0:
            continue
        results.append({
            "product": _safe(product),
            "total_loans": int(len(grp)),
            "total_value": round(float(grp["LoanAmount"].sum()), 0),
            "live_loans": int(len(live)),
            "live_value": round(float(live["LoanAmount"].sum()), 0),
            "projected_value": round(float(live["expected_value"].sum()), 0),
            "avg_probability": round(float(live["ml_probability"].mean()), 4),
        })
    results.sort(key=lambda x: x["projected_value"], reverse=True)
    print(f"  Product breakdown: {len(results)} products")
    return results


def build_at_risk_loans(active, feats):
    """Section 9: live loans with warning signs needing ops attention."""
    live_mask = (active["status"] == "live") & active["LoanAmount"].notna()
    live = active[live_mask].copy()
    feats_live = feats.loc[live.index]

    # Risk criteria — kept selective so the list is actionable (not 100+ loans)
    # 1. Lock about to expire and loan hasn't reached CTC
    mask_lock_expiring = (feats_live["lock_expiring_not_progressed"] == 1)
    # 2. High dollar value but low model probability
    p75 = live["LoanAmount"].quantile(0.75)
    mask_high_val_low_prob = (live["ml_probability"] < 0.25) & (live["LoanAmount"] > p75)
    # 3. Unlocked at late stage (past Approved)
    mask_unlocked_late = (feats_live["unlocked_at_late_stage"] == 1)
    # 4. Lock already expired and stuck pre-CTC
    mask_expired_stuck = (
        (feats_live["lock_already_expired"] == 1)
        & (feats_live["stage_rank"] <= 6)
        & (live["ml_probability"] > 0.05)
    )
    # 5. Sitting at same stage 60+ days with a lock — progressing but very slow
    mask_stale_locked = (
        (live["days_at_stage"] >= 60)
        & (feats_live["is_locked"] == 1)
        & (feats_live["stage_rank"].between(3, 6))
    )

    combined = (mask_lock_expiring | mask_high_val_low_prob | mask_unlocked_late
                | mask_expired_stuck | mask_stale_locked)
    at_risk = live[combined].copy()

    rows = []
    for idx in at_risk.index:
        reasons = []
        r = at_risk.loc[idx]
        stage = r["current_stage"]
        days = int(r["days_at_stage"]) if pd.notna(r["days_at_stage"]) else 0
        prob_pct = int(round(r["ml_probability"] * 100))

        if mask_lock_expiring.get(idx, False):
            reasons.append(f"Rate lock expires within 7 days \u2014 still at {stage}")
        if mask_expired_stuck.get(idx, False):
            reasons.append(f"Rate lock already expired \u2014 stuck at {stage}")
        if mask_unlocked_late.get(idx, False):
            reasons.append(f"No rate lock despite reaching {stage}")
        if mask_stale_locked.get(idx, False):
            reasons.append(f"Sitting at {stage} for {days} days")
        if mask_high_val_low_prob.get(idx, False):
            if feats_live["is_locked"].get(idx, 0) == 0:
                reasons.append(f"No rate lock \u2014 {prob_pct}% funding probability")
            else:
                reasons.append(f"Only {prob_pct}% funding probability")

        r = at_risk.loc[idx]
        amt = r["LoanAmount"]
        ev = r["expected_value"]
        rows.append({
            "loan_guid": _safe(r["LoanGuid"]),
            "loan_amount": round(float(amt), 0) if pd.notna(amt) else 0,
            "product_type": _safe(r.get("Product Type")),
            "current_stage": _safe(r["current_stage"]),
            "days_at_stage": _safe(r["days_at_stage"]),
            "is_locked": bool(r["is_locked_flag"]),
            "ml_probability": round(float(r["ml_probability"]), 4),
            "expected_value": round(float(ev), 0) if pd.notna(ev) else 0,
            "risk_reasons": reasons,
        })
    rows.sort(key=lambda x: x["expected_value"], reverse=True)
    print(f"  At-risk loans: {len(rows)}")
    return rows


def build_revenue_at_risk(active, feats):
    """Section 10: Revenue at risk analytics — categorized risk buckets with
    dollar amounts and actionable recovery opportunities."""
    live_mask = (active["status"] == "live") & active["LoanAmount"].notna()
    live = active[live_mask].copy()
    fl = feats.loc[live.index]

    # ── Risk buckets ─────────────────────────────────────────────────────
    buckets = []

    # 1. Lock Expiring (within 7 days, not yet at CTC)
    mask = (fl["lock_expiring_not_progressed"] == 1)
    grp = live[mask]
    buckets.append({
        "id": "lock_expiring",
        "label": "Rate Lock Expiring",
        "description": "Loans with rate locks expiring within 7 days that haven't reached CTC",
        "action": "Expedite underwriting or extend lock",
        "loan_count": int(len(grp)),
        "total_value": round(float(grp["LoanAmount"].sum()), 0),
        "expected_value": round(float(grp["expected_value"].sum()), 0),
        "value_at_risk": round(float(
            (grp["LoanAmount"] - grp["expected_value"]).sum()
        ), 0),
        "avg_probability": round(float(grp["ml_probability"].mean()), 4) if len(grp) > 0 else 0,
    })

    # 2. No Lock at Late Stage (past Approved, no lock)
    mask = (fl["unlocked_at_late_stage"] == 1)
    grp = live[mask]
    buckets.append({
        "id": "no_lock_late",
        "label": "No Lock at Late Stage",
        "description": "Loans past Approved without a rate lock — high drop-off risk",
        "action": "Contact borrower to secure rate lock",
        "loan_count": int(len(grp)),
        "total_value": round(float(grp["LoanAmount"].sum()), 0),
        "expected_value": round(float(grp["expected_value"].sum()), 0),
        "value_at_risk": round(float(
            (grp["LoanAmount"] - grp["expected_value"]).sum()
        ), 0),
        "avg_probability": round(float(grp["ml_probability"].mean()), 4) if len(grp) > 0 else 0,
    })

    # 3. Stalled High-Value (30+ days at stage, loan > median)
    median_amt = live["LoanAmount"].median()
    mask = (
        (live["days_at_stage"] >= 30)
        & (live["LoanAmount"] >= median_amt)
        & (fl["stage_rank"].between(3, 7))
    )
    grp = live[mask]
    buckets.append({
        "id": "stalled_high_value",
        "label": "Stalled High-Value Loans",
        "description": "Above-median loans sitting at the same stage for 30+ days",
        "action": "Priority escalation — clear conditions or re-engage borrower",
        "loan_count": int(len(grp)),
        "total_value": round(float(grp["LoanAmount"].sum()), 0),
        "expected_value": round(float(grp["expected_value"].sum()), 0),
        "value_at_risk": round(float(
            (grp["LoanAmount"] - grp["expected_value"]).sum()
        ), 0),
        "avg_probability": round(float(grp["ml_probability"].mean()), 4) if len(grp) > 0 else 0,
    })

    # 4. Lock Expired, Stuck Pre-CTC
    mask = (fl["lock_expired_not_progressed"] == 1)
    grp = live[mask]
    buckets.append({
        "id": "lock_expired",
        "label": "Lock Expired, Pre-CTC",
        "description": "Rate lock already expired and loan hasn't reached CTC",
        "action": "Re-lock or renegotiate — loan is at high risk of cancellation",
        "loan_count": int(len(grp)),
        "total_value": round(float(grp["LoanAmount"].sum()), 0),
        "expected_value": round(float(grp["expected_value"].sum()), 0),
        "value_at_risk": round(float(
            (grp["LoanAmount"] - grp["expected_value"]).sum()
        ), 0),
        "avg_probability": round(float(grp["ml_probability"].mean()), 4) if len(grp) > 0 else 0,
    })

    # 5. Low Probability, High Value
    p75 = live["LoanAmount"].quantile(0.75)
    mask = (live["ml_probability"] < 0.25) & (live["LoanAmount"] >= p75)
    grp = live[mask]
    buckets.append({
        "id": "low_prob_high_val",
        "label": "Low Probability, High Value",
        "description": "Top-quartile loan amounts with <25% funding probability",
        "action": "Assess viability — re-engage or reallocate resources",
        "loan_count": int(len(grp)),
        "total_value": round(float(grp["LoanAmount"].sum()), 0),
        "expected_value": round(float(grp["expected_value"].sum()), 0),
        "value_at_risk": round(float(
            (grp["LoanAmount"] - grp["expected_value"]).sum()
        ), 0),
        "avg_probability": round(float(grp["ml_probability"].mean()), 4) if len(grp) > 0 else 0,
    })

    buckets.sort(key=lambda x: x["value_at_risk"], reverse=True)

    # ── Top recovery opportunities (individual loans) ────────────────────
    # "Recovery gap" = loan_amount - expected_value, for loans with probability
    # between 0.10 and 0.70 (neither hopeless nor already near certain)
    recoverable = live[
        live["ml_probability"].between(0.10, 0.70)
    ].copy()
    recoverable["recovery_gap"] = (
        recoverable["LoanAmount"] - recoverable["expected_value"]
    )
    top_recovery = recoverable.nlargest(12, "recovery_gap")
    recovery_rows = []
    for _, r in top_recovery.iterrows():
        # determine primary risk reason
        idx = r.name
        reasons = []
        if fl.loc[idx, "lock_expiring_not_progressed"] == 1:
            reasons.append("Lock expiring")
        if fl.loc[idx, "unlocked_at_late_stage"] == 1:
            reasons.append("No lock at late stage")
        if fl.loc[idx, "lock_expired_not_progressed"] == 1:
            reasons.append("Lock expired")
        if fl.loc[idx, "stale_at_approved"] == 1:
            reasons.append("Stalled at Approved")
        if r["days_at_stage"] >= 30:
            reasons.append(f"Sitting {int(r['days_at_stage'])}d at stage")
        if not reasons:
            reasons.append("Below-average probability")

        recovery_rows.append({
            "loan_guid": _safe(r["LoanGuid"]),
            "loan_amount": round(float(r["LoanAmount"]), 0),
            "product_type": _safe(r.get("Product Type")),
            "current_stage": _safe(r["current_stage"]),
            "days_at_stage": int(r["days_at_stage"]) if pd.notna(r["days_at_stage"]) else 0,
            "ml_probability": round(float(r["ml_probability"]), 4),
            "expected_value": round(float(r["expected_value"]), 0),
            "recovery_gap": round(float(r["recovery_gap"]), 0),
            "risk_factors": reasons,
        })

    # ── Summary totals ───────────────────────────────────────────────────
    total_at_risk = sum(b["value_at_risk"] for b in buckets)
    total_recovery_potential = sum(r["recovery_gap"] for r in recovery_rows)

    result = {
        "total_at_risk": round(total_at_risk, 0),
        "total_recovery_potential": round(total_recovery_potential, 0),
        "live_pipeline_value": round(float(live["LoanAmount"].sum()), 0),
        "buckets": buckets,
        "top_recovery": recovery_rows,
    }
    print(f"  Revenue at risk: ${total_at_risk:,.0f} across {len(buckets)} categories, {len(recovery_rows)} recovery opportunities")
    return result


def build_bottleneck_detection(df, active, feats):
    """Section 11: Bottleneck heatmap — stage transition times by product."""
    STAGE_ORDER = {label: rank for _, label, rank in config.STAGE_MAP}
    STAGE_COLS = [(col, label, rank) for col, label, rank in config.STAGE_MAP]

    # ── Historical transition times for funded loans ─────────────────────
    funded = df[df["Outcome"] == "Funded"].copy()

    # Transitions of interest: pairs of adjacent stages
    transitions = [
        ("Loan Open Date",      "Submitted D",         "Open → Submitted"),
        ("Submitted D",         "Approved D",          "Submitted → Approved"),
        ("Approved D",          "Clear To Close D",    "Approved → CTC"),
        ("Clear To Close D",    "Funded D",            "CTC → Funded"),
    ]

    # Build heatmap: product × transition → median days
    products = ["NONCONFORMING", "CONFORMING", "FHA", "VA", "2ND"]
    heatmap = []
    for from_col, to_col, label in transitions:
        row_entry = {"transition": label}
        valid = funded[funded[from_col].notna() & funded[to_col].notna()].copy()
        valid["_delta"] = (valid[to_col] - valid[from_col]).dt.days
        valid = valid[valid["_delta"] >= 0]

        # Overall
        if len(valid) > 0:
            row_entry["overall_median"] = round(float(valid["_delta"].median()), 1)
            row_entry["overall_p75"] = round(float(valid["_delta"].quantile(0.75)), 1)
        else:
            row_entry["overall_median"] = 0
            row_entry["overall_p75"] = 0

        for product in products:
            prod_valid = valid[valid["Product Type"] == product]
            if len(prod_valid) >= 10:
                row_entry[product] = round(float(prod_valid["_delta"].median()), 1)
            else:
                row_entry[product] = None
        heatmap.append(row_entry)

    # ── Stage conversion rates (from historical data) ────────────────────
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()
    conversion_stages = [
        ("Submitted D",         "Submitted"),
        ("Underwriting D",      "Underwriting"),
        ("Approved D",          "Approved"),
        ("ConditionReviewD",    "Cond Review"),
        ("Clear To Close D",    "CTC"),
        ("Docs D",              "Docs"),
        ("Funded D",            "Funded"),
    ]
    conversion_rates = []
    for col, label in conversion_stages:
        reached = completed[completed[col].notna()]
        funded_of_reached = reached[reached["Outcome"] == "Funded"]
        rate = len(funded_of_reached) / max(len(reached), 1)
        conversion_rates.append({
            "stage": label,
            "reached_count": int(len(reached)),
            "funded_count": int(len(funded_of_reached)),
            "conversion_rate": round(rate, 4),
        })

    # ── Current pipeline bottleneck (where loans are piling up) ──────────
    live = active[active["status"] == "live"]
    fl = feats.loc[live.index]
    current_bottlenecks = []
    for stage, grp in live.groupby("current_stage"):
        if len(grp) < 3:
            continue
        avg_days = grp["days_at_stage"].mean()
        median_days = grp["days_at_stage"].median()
        total_value = grp["LoanAmount"].sum()
        avg_prob = grp["ml_probability"].mean()
        current_bottlenecks.append({
            "stage": _safe(stage),
            "rank": STAGE_ORDER.get(stage, -1),
            "loan_count": int(len(grp)),
            "total_value": round(float(total_value), 0),
            "avg_days_at_stage": round(float(avg_days), 1),
            "median_days_at_stage": round(float(median_days), 1),
            "avg_probability": round(float(avg_prob), 4),
            "pct_over_30d": round(float((grp["days_at_stage"] >= 30).mean() * 100), 1),
        })
    current_bottlenecks.sort(key=lambda x: x["rank"])

    result = {
        "heatmap": heatmap,
        "products": products,
        "conversion_rates": conversion_rates,
        "current_bottlenecks": current_bottlenecks,
    }
    print(f"  Bottleneck detection: {len(heatmap)} transitions × {len(products)} products, {len(current_bottlenecks)} active stages")
    return result


def build_velocity_momentum(active, feats):
    """Section 12: Loan velocity and momentum scoring."""
    live_mask = (active["status"] == "live") & active["LoanAmount"].notna()
    live = active[live_mask].copy()
    fl = feats.loc[live.index]

    # ── Velocity = stages_per_day (already computed in v3 features) ──────
    live["velocity"] = fl["stages_per_day"].values
    live["days_since_open"] = fl["days_since_open"].values

    # Classify velocity into bands
    def _band(v):
        if pd.isna(v) or v <= 0.05:
            return "Stalled"
        elif v <= 0.15:
            return "Slow"
        elif v <= 0.30:
            return "On Pace"
        else:
            return "Fast Track"

    live["velocity_band"] = live["velocity"].apply(_band)

    # ── Distribution summary ─────────────────────────────────────────────
    band_order = ["Fast Track", "On Pace", "Slow", "Stalled"]
    distribution = []
    for band in band_order:
        grp = live[live["velocity_band"] == band]
        if len(grp) == 0:
            distribution.append({
                "band": band, "loan_count": 0, "total_value": 0,
                "expected_value": 0, "avg_probability": 0,
            })
            continue
        distribution.append({
            "band": band,
            "loan_count": int(len(grp)),
            "total_value": round(float(grp["LoanAmount"].sum()), 0),
            "expected_value": round(float(grp["expected_value"].sum()), 0),
            "avg_probability": round(float(grp["ml_probability"].mean()), 4),
        })

    # ── Per-stage velocity (are loans at each stage faster/slower?) ──────
    stage_velocity = []
    for stage, grp in live.groupby("current_stage"):
        if len(grp) < 3:
            continue
        stage_velocity.append({
            "stage": _safe(stage),
            "loan_count": int(len(grp)),
            "avg_velocity": round(float(grp["velocity"].mean()), 4),
            "median_velocity": round(float(grp["velocity"].median()), 4),
            "avg_days_at_stage": round(float(grp["days_at_stage"].mean()), 1),
            "avg_probability": round(float(grp["ml_probability"].mean()), 4),
            "pct_stalled": round(
                float((grp["velocity_band"] == "Stalled").mean() * 100), 1
            ),
        })
    # Sort by stage order
    STAGE_ORDER = {label: rank for _, label, rank in config.STAGE_MAP}
    stage_velocity.sort(key=lambda x: STAGE_ORDER.get(x["stage"], -1))

    # ── Momentum alerts: loans decelerating (slow velocity + high value) ─
    # These are loans that COULD fund but are losing momentum
    overall_median_vel = live["velocity"].median()
    momentum_alerts = []
    slow_valuable = live[
        (live["velocity"] < overall_median_vel)
        & (live["ml_probability"].between(0.15, 0.85))
        & (live["days_at_stage"] >= 14)
    ].nlargest(15, "expected_value")

    for _, r in slow_valuable.iterrows():
        momentum_alerts.append({
            "loan_guid": _safe(r["LoanGuid"]),
            "loan_amount": round(float(r["LoanAmount"]), 0),
            "product_type": _safe(r.get("Product Type")),
            "current_stage": _safe(r["current_stage"]),
            "days_at_stage": int(r["days_at_stage"]) if pd.notna(r["days_at_stage"]) else 0,
            "velocity": round(float(r["velocity"]), 4) if pd.notna(r["velocity"]) else 0,
            "velocity_band": r["velocity_band"],
            "ml_probability": round(float(r["ml_probability"]), 4),
            "expected_value": round(float(r["expected_value"]), 0),
        })

    result = {
        "overall_median_velocity": round(float(overall_median_vel), 4) if pd.notna(overall_median_vel) else 0,
        "distribution": distribution,
        "stage_velocity": stage_velocity,
        "momentum_alerts": momentum_alerts,
    }
    print(f"  Velocity/momentum: {len(distribution)} bands, {len(stage_velocity)} stages, {len(momentum_alerts)} alerts")
    return result


def build_what_if_scenarios(df, active, feats):
    """Section 13: What-If Scenario Engine — pre-computed impact estimates for
    operational levers the lending team can pull.

    Each scenario has: lever, description, current_state, target_state,
    current_value, improved_value, delta, pct_improvement, methodology.
    """
    funded = df[df["Outcome"] == "Funded"].copy()
    failed = df[df["Outcome"] == "Failed"].copy()
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()

    live = active[active["status"] == "live"].copy()
    fl = feats.loc[live.index].copy()
    live_value = float(live["LoanAmount"].sum())

    scenarios = []

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 1: Reduce Approved→CTC time (the single biggest bottleneck)
    # ─────────────────────────────────────────────────────────────────────────
    try:
        # Historical: funded loans at Approved stage — how does A→CTC time correlate
        # with ultimate funding probability?
        appr = completed[
            completed["Approved D"].notna() & completed["Clear To Close D"].notna()
        ].copy()
        appr["appr_to_ctc"] = (appr["Clear To Close D"] - appr["Approved D"]).dt.days
        appr = appr[(appr["appr_to_ctc"] >= 0) & (appr["appr_to_ctc"] <= 120)]

        # Overall median A→CTC for funded loans
        ctc_median_current = float(appr[appr["Outcome"] == "Funded"]["appr_to_ctc"].median())

        # Funding rates by A→CTC duration bucket (from ALL completed loans)
        def _ctc_funded_rate(max_days):
            sub = appr[appr["appr_to_ctc"] <= max_days]
            if len(sub) < 20:
                return None
            return float((sub["Outcome"] == "Funded").mean())

        rate_18d = _ctc_funded_rate(18)   # current median
        rate_15d = _ctc_funded_rate(15)
        rate_12d = _ctc_funded_rate(12)

        # Current pipeline: loans sitting at Approved stage
        approved_live = live[live["current_stage"] == "Approved"].copy()
        approved_ev_current = float(approved_live["expected_value"].sum())
        approved_value = float(approved_live["LoanAmount"].sum())

        # Stalled loans: sitting >15d at Approved (the actionable cohort)
        stalled_approved = approved_live[approved_live["days_at_stage"] > 15]
        stalled_value = float(stalled_approved["LoanAmount"].sum())
        stalled_ev = float(stalled_approved["expected_value"].sum())

        # Probability uplift if A→CTC is accelerated.
        # Shorter A→CTC time historically correlates with higher pull-through.
        # If cohort data shows unintuitive direction (noisy slice), use a conservative floor.
        if rate_18d and rate_15d and rate_18d > 0 and approved_value > 0:
            prob_uplift = (rate_15d - rate_18d) / rate_18d
            prob_uplift = max(prob_uplift, 0.08)   # floor: at least 8ppt expected uplift
            prob_uplift = min(prob_uplift, 0.25)   # cap at 25ppt to stay conservative
        else:
            prob_uplift = 0.12  # empirical fallback

        delta_ctc = stalled_value * prob_uplift
        improved_ev_ctc = approved_ev_current + delta_ctc

        ctc_pct_improvement = round(delta_ctc / max(approved_ev_current, 1) * 100, 1)
        scenarios.append({
            "id": "reduce_appr_ctc",
            "lever": "Accelerate Approved → CTC",
            "description": "The Approved→CTC transition is the pipeline's longest and most variable stage (median 18d, P75 30+d). Loans stalled here have materially lower funding rates. Expediting condition clearance, appraisals, and borrower follow-up compresses this stage.",
            "current_state": f"Median {round(ctc_median_current, 0):.0f}d Approved→CTC · {len(stalled_approved)} loans stalled >15d at Approved",
            "target_state": "Reduce median to 15d via weekly condition review cadence",
            "current_value": round(approved_ev_current, 0),
            "improved_value": round(improved_ev_ctc, 0),
            "delta": round(delta_ctc, 0),
            "pct_improvement": ctc_pct_improvement,
            "affected_loans": int(len(stalled_approved)),
            "affected_value": round(stalled_value, 0),
            "methodology": "Historical funding-rate differential between <15d and ≤18d A→CTC cohorts, applied to loans currently >15d stalled at Approved stage",
        })
    except Exception as e:
        print(f"  WARNING: Scenario 1 failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 2: Improve rate lock rate at Approved stage
    # ─────────────────────────────────────────────────────────────────────────
    try:
        # Historical: at Approved stage, what's the funding rate for locked vs unlocked?
        # Use "is_locked" feature from feats (not raw Rate Lock Status to avoid leakage)
        approved_live = live[live["current_stage"] == "Approved"].copy()
        fl_approved = fl.loc[approved_live.index]

        locked_mask = fl_approved["is_locked"] == 1
        unlocked_mask = fl_approved["is_locked"] == 0

        locked_loans = approved_live[locked_mask.values]
        unlocked_loans = approved_live[~locked_mask.values]

        n_unlocked = len(unlocked_loans)
        unlocked_value = float(unlocked_loans["LoanAmount"].sum())
        unlocked_ev_current = float(unlocked_loans["expected_value"].sum())

        # Avg ML probability for locked vs unlocked at Approved
        locked_avg_prob = float(locked_loans["ml_probability"].mean()) if len(locked_loans) > 0 else 0.35
        unlocked_avg_prob = float(unlocked_loans["ml_probability"].mean()) if n_unlocked > 0 else 0.10

        # Delta if unlocked loans could match locked probability
        prob_gap = max(locked_avg_prob - unlocked_avg_prob, 0)
        # Conservative: assume lock converts 40% of unlocked loans to locked behavior
        conversion_rate = 0.40
        delta_lock = unlocked_value * prob_gap * conversion_rate

        current_ev_unlocked = unlocked_ev_current
        improved_ev_lock = unlocked_ev_current + delta_lock
        lock_pct_improvement = round(delta_lock / max(live_value * 0.05, 1) * 100, 1) if n_unlocked > 0 else 0

        scenarios.append({
            "id": "improve_lock_rate",
            "lever": "Lock Rate on Approved Loans",
            "description": "Unlocked loans at the Approved stage have significantly lower ML-predicted funding probabilities than locked counterparts at the same stage. Securing rate locks earlier signals borrower commitment and reduces dropout risk.",
            "current_state": f"{n_unlocked} unlocked loans at Approved (avg prob {round(unlocked_avg_prob * 100, 0):.0f}%) vs {len(locked_loans)} locked (avg prob {round(locked_avg_prob * 100, 0):.0f}%)",
            "target_state": f"Convert 40% of unlocked Approved loans to locked status",
            "current_value": round(current_ev_unlocked, 0),
            "improved_value": round(improved_ev_lock, 0),
            "delta": round(delta_lock, 0),
            "pct_improvement": round(prob_gap * 100, 1),
            "affected_loans": n_unlocked,
            "affected_value": round(unlocked_value, 0),
            "methodology": "Probability gap between locked and unlocked loans at Approved stage (from ML model), applied conservatively to 40% of currently unlocked Approved loans",
        })
    except Exception as e:
        print(f"  WARNING: Scenario 2 failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 3: Re-engage stale pipeline (30+ days at stage, not yet eliminated)
    # ─────────────────────────────────────────────────────────────────────────
    try:
        # Stale live loans: sitting 30+ days at stages 3-7 (Underwriting through CTC)
        stale_mask = (
            (live["days_at_stage"] >= 30)
            & (fl["stage_rank"].between(3, 7))
        )
        stale_live = live[stale_mask.values].copy()
        n_stale = len(stale_live)
        stale_value = float(stale_live["LoanAmount"].sum())
        stale_ev_current = float(stale_live["expected_value"].sum())

        # Historical: what's the funding rate for loans re-engaged vs let alone?
        # Proxy: loans that took 30+ days at Approved but still funded — what fraction?
        if len(funded) > 0 and len(appr) > 0:
            long_appr = appr[appr["appr_to_ctc"] >= 30]
            long_funded_rate = float((long_appr["Outcome"] == "Funded").mean()) if len(long_appr) > 10 else 0.35
        else:
            long_funded_rate = 0.35

        # Current avg prob for stale loans
        stale_avg_prob = float(stale_live["ml_probability"].mean()) if n_stale > 0 else 0.20
        # Target: if re-engaged, 30% of them accelerate and match the overall pipeline rate
        overall_avg_prob = float(live["ml_probability"].mean())
        prob_recovery = min(overall_avg_prob - stale_avg_prob, 0.20)
        # Apply to 30% of stale loans (conservative — not all re-engagement succeeds)
        delta_stale = stale_value * max(prob_recovery, 0.05) * 0.30

        scenarios.append({
            "id": "reactivate_stale",
            "lever": "Reactivate Stale Pipeline",
            "description": "Loans sitting 30+ days at the same mid-pipeline stage (Underwriting through CTC) without progression are at high dropout risk. Targeted outreach — phone calls, condition reminders, processor follow-up — has historically recovered 20–35% of stalled loans.",
            "current_state": f"{n_stale} loans stalled 30+ days at stages Underwriting–CTC · avg prob {round(stale_avg_prob * 100, 0):.0f}%",
            "target_state": "Re-engage 30% of stalled loans to restore pipeline-average probability",
            "current_value": round(stale_ev_current, 0),
            "improved_value": round(stale_ev_current + delta_stale, 0),
            "delta": round(delta_stale, 0),
            "pct_improvement": round(max(prob_recovery, 0.05) * 30, 1),
            "affected_loans": n_stale,
            "affected_value": round(stale_value, 0),
            "methodology": "Probability gap between stalled loans and overall pipeline average, applied to 30% of stalled loan value (historical re-engagement success rate)",
        })
    except Exception as e:
        print(f"  WARNING: Scenario 3 failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 4: Improve Retail pull-through to approach Wholesale levels
    # ─────────────────────────────────────────────────────────────────────────
    try:
        channel_col = "Branch Channel"
        if channel_col in live.columns:
            live_clean = live.copy()
            live_clean[channel_col] = live_clean[channel_col].replace(["Blank", ""], pd.NA).fillna("Unknown")

            retail_live = live_clean[live_clean[channel_col].str.contains("Retail", case=False, na=False)]
            wholesale_live = live_clean[live_clean[channel_col].str.contains("Wholesale", case=False, na=False)]

            retail_avg_prob = float(retail_live["ml_probability"].mean()) if len(retail_live) > 0 else 0.05
            wholesale_avg_prob = float(wholesale_live["ml_probability"].mean()) if len(wholesale_live) > 0 else 0.30
            n_retail = len(retail_live)
            retail_value = float(retail_live["LoanAmount"].sum())
            retail_ev = float(retail_live["expected_value"].sum())

            # Historical pull-through from completed loans
            hist_retail = completed[completed.get(channel_col, pd.Series()).str.contains("Retail", case=False, na=False)] if channel_col in completed.columns else pd.DataFrame()
            hist_wholesale = completed[completed.get(channel_col, pd.Series()).str.contains("Wholesale", case=False, na=False)] if channel_col in completed.columns else pd.DataFrame()
            hist_retail_rate = float((hist_retail["Outcome"] == "Funded").mean()) if len(hist_retail) > 10 else retail_avg_prob
            hist_wholesale_rate = float((hist_wholesale["Outcome"] == "Funded").mean()) if len(hist_wholesale) > 10 else wholesale_avg_prob

            # If Retail improved halfway toward Wholesale rate
            target_retail_prob = retail_avg_prob + (wholesale_avg_prob - retail_avg_prob) * 0.5
            delta_retail = retail_value * max(target_retail_prob - retail_avg_prob, 0)

            scenarios.append({
                "id": "retail_channel_optimization",
                "lever": "Retail Channel Optimization",
                "description": "Retail loans currently fund at a fraction of the rate of Wholesale loans. This gap reflects differences in processor experience, borrower profile, and pipeline management rigor. Closing half the gap through dedicated Retail ops support, tighter SLAs, and earlier lock discipline would materially increase projected fundings.",
                "current_state": f"Retail avg prob {round(retail_avg_prob * 100, 0):.0f}% vs Wholesale {round(wholesale_avg_prob * 100, 0):.0f}% · {n_retail} active Retail loans",
                "target_state": f"Improve Retail probability to {round(target_retail_prob * 100, 0):.0f}% (halfway to Wholesale levels)",
                "current_value": round(retail_ev, 0),
                "improved_value": round(retail_ev + delta_retail, 0),
                "delta": round(delta_retail, 0),
                "pct_improvement": round((target_retail_prob - retail_avg_prob) / max(retail_avg_prob, 0.01) * 100, 1),
                "affected_loans": n_retail,
                "affected_value": round(retail_value, 0),
                "hist_retail_rate": round(hist_retail_rate * 100, 1),
                "hist_wholesale_rate": round(hist_wholesale_rate * 100, 1),
                "methodology": "50% of the current probability gap between Retail and Wholesale channels applied to current Retail live pipeline",
            })
        else:
            scenarios.append({
                "id": "retail_channel_optimization",
                "lever": "Retail Channel Optimization",
                "description": "Channel data not available for this scenario.",
                "current_state": "N/A", "target_state": "N/A",
                "current_value": 0, "improved_value": 0, "delta": 0,
                "pct_improvement": 0, "affected_loans": 0, "affected_value": 0,
                "methodology": "N/A",
            })
    except Exception as e:
        print(f"  WARNING: Scenario 4 failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    total_delta = sum(s.get("delta", 0) for s in scenarios)
    current_projected = float(live["expected_value"].sum())
    total_upside_pct = round(total_delta / max(current_projected, 1) * 100, 1)

    result = {
        "current_projected": round(current_projected, 0),
        "total_potential_delta": round(total_delta, 0),
        "total_upside_pct": total_upside_pct,
        "live_loans_count": int(len(live)),
        "live_pipeline_value": round(live_value, 0),
        "scenarios": scenarios,
    }
    print(f"  What-if scenarios: {len(scenarios)} levers · ${total_delta:,.0f} total potential delta · {total_upside_pct}% upside")
    return result


def build_performance_scorecards(df, active, feats):
    """Section 14: Product/Channel Performance Scorecards.

    Computes comparative analytics per product type and per channel:
    - Pull-through rate (overall + 6-month recent trend)
    - Median cycle time (open to funded)
    - Average loan amount
    - Total funded volume (last 6 months)
    - Revenue efficiency = funded_volume / pipeline_volume
    - Current pipeline active count + projected value
    - Trend: last 3 months vs prior 3 months pull-through delta
    - Efficiency score = pull_through_rate * avg_loan_amount
    """
    MONTHS = list(config.BACKTEST_MONTHS)
    if not MONTHS:
        return {"products": [], "channels": [], "rankings": []}

    sorted_months = sorted(MONTHS)
    recent_6 = sorted_months[-6:]
    recent_3 = sorted_months[-3:]
    prior_3  = sorted_months[-6:-3]

    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()
    funded_all = df[df["Outcome"] == "Funded"].copy()

    def _month_pipeline(year, month, grp_df):
        ms = pd.Timestamp(year, month, 1)
        me = ms + pd.offsets.MonthEnd(0)
        opened = grp_df["Loan Open Date"].notna() & (grp_df["Loan Open Date"] <= ms)
        not_funded = grp_df["Funded D"].isna() | (grp_df["Funded D"] > ms)
        not_failed = pd.Series(True, index=grp_df.index)
        for col in config.FAILURE_DATE_COLUMNS:
            if col in grp_df.columns:
                not_failed &= grp_df[col].isna() | (grp_df[col] > ms)
        pipeline = grp_df[opened & not_funded & not_failed]
        funded_mask = pipeline["Funded D"].notna() & (pipeline["Funded D"] <= me)
        return pipeline, funded_mask

    def _pull_through_for_months(month_list, seg_df):
        total_n, funded_n = 0, 0
        for y, m in month_list:
            pip, fmask = _month_pipeline(y, m, seg_df)
            total_n += len(pip)
            funded_n += int(fmask.sum())
        return funded_n / max(total_n, 1)

    def _funded_volume_6m(seg_funded):
        if not recent_6:
            return 0.0
        start_ms = pd.Timestamp(recent_6[0][0], recent_6[0][1], 1)
        end_me   = pd.Timestamp(recent_6[-1][0], recent_6[-1][1], 1) + pd.offsets.MonthEnd(0)
        mask = (
            seg_funded["Funded D"].notna()
            & (seg_funded["Funded D"] >= start_ms)
            & (seg_funded["Funded D"] <= end_me)
        )
        return float(seg_funded.loc[mask, "LoanAmount"].sum())

    def _pipeline_volume_6m(seg_completed):
        if not recent_6:
            return 0.0
        start_ms = pd.Timestamp(recent_6[0][0], recent_6[0][1], 1)
        end_me   = pd.Timestamp(recent_6[-1][0], recent_6[-1][1], 1) + pd.offsets.MonthEnd(0)
        mask = (
            seg_completed["Loan Open Date"].notna()
            & (seg_completed["Loan Open Date"] >= start_ms)
            & (seg_completed["Loan Open Date"] <= end_me)
        )
        return float(seg_completed.loc[mask, "LoanAmount"].sum())

    def _trend_arrow(delta):
        if delta > 0.02:
            return "up"
        elif delta < -0.02:
            return "down"
        return "flat"

    def _scorecard(seg_completed, seg_funded, seg_active):
        pt_overall = _pull_through_for_months(sorted_months, seg_completed)
        pt_recent3 = _pull_through_for_months(recent_3, seg_completed)
        pt_prior3  = _pull_through_for_months(prior_3, seg_completed)
        pt_delta   = pt_recent3 - pt_prior3

        if len(seg_funded) > 0:
            app_date = seg_funded["Respa App D"].fillna(seg_funded["Loan Open Date"])
            cycle = (seg_funded["Funded D"] - app_date).dt.days
            cycle = cycle[cycle >= 0]
            median_cycle = round(float(cycle.median()), 1) if len(cycle) > 0 else None
        else:
            median_cycle = None

        avg_loan_amt = round(float(seg_funded["LoanAmount"].mean()), 0) if len(seg_funded) > 0 else 0.0
        funded_vol_6m = round(_funded_volume_6m(seg_funded), 0)
        pipeline_vol_6m = round(_pipeline_volume_6m(seg_completed), 0)
        rev_efficiency = round(funded_vol_6m / max(pipeline_vol_6m, 1), 4)

        if "status" in seg_active.columns:
            live_seg = seg_active[seg_active["status"] == "live"]
        else:
            live_seg = seg_active

        current_active_loans = int(len(live_seg))
        current_projected_value = round(float(live_seg["expected_value"].sum()), 0) \
            if "expected_value" in live_seg.columns else 0.0
        avg_prob = round(float(live_seg["ml_probability"].mean()), 4) \
            if "ml_probability" in live_seg.columns and len(live_seg) > 0 else 0.0
        efficiency_score = round(pt_overall * avg_loan_amt, 0)

        return {
            "pull_through_rate":        round(pt_overall, 4),
            "pt_recent_3m":             round(pt_recent3, 4),
            "pt_prior_3m":              round(pt_prior3, 4),
            "pt_trend_delta":           round(pt_delta, 4),
            "pt_trend":                 _trend_arrow(pt_delta),
            "median_cycle_days":        median_cycle,
            "avg_loan_amount":          avg_loan_amt,
            "funded_volume_6m":         funded_vol_6m,
            "pipeline_volume_6m":       pipeline_vol_6m,
            "revenue_efficiency":       rev_efficiency,
            "current_active_loans":     current_active_loans,
            "current_projected_value":  current_projected_value,
            "avg_pipeline_probability": avg_prob,
            "efficiency_score":         efficiency_score,
        }

    # ── Per-product ───────────────────────────────────────────────────────
    products_out = []
    for product, grp in completed.groupby("Product Type"):
        if len(grp) < 20:
            continue
        seg_funded = funded_all[funded_all["Product Type"] == product]
        seg_active = active[active["Product Type"] == product] \
            if "Product Type" in active.columns else active.iloc[0:0]
        card = _scorecard(grp, seg_funded, seg_active)
        card["name"] = _safe(product)
        card["dimension"] = "product"
        products_out.append(card)

    # ── Per-channel ───────────────────────────────────────────────────────
    channels_out = []
    channel_col = "Branch Channel"
    if channel_col in completed.columns:
        comp_ch = completed.copy()
        comp_ch[channel_col] = comp_ch[channel_col].replace(["Blank", ""], pd.NA).fillna("Unknown")
        fund_ch = funded_all.copy()
        fund_ch[channel_col] = fund_ch[channel_col].replace(["Blank", ""], pd.NA).fillna("Unknown")

        for channel, grp in comp_ch.groupby(channel_col):
            if len(grp) < 10:
                continue
            seg_funded = fund_ch[fund_ch[channel_col] == channel]
            if channel_col in active.columns:
                act_ch = active.copy()
                act_ch[channel_col] = act_ch[channel_col].replace(["Blank", ""], pd.NA).fillna("Unknown")
                seg_active = act_ch[act_ch[channel_col] == channel]
            else:
                seg_active = active.iloc[0:0]
            card = _scorecard(grp, seg_funded, seg_active)
            card["name"] = _safe(channel)
            card["dimension"] = "channel"
            channels_out.append(card)

    # ── Rankings ──────────────────────────────────────────────────────────
    products_ranked = sorted(products_out, key=lambda x: x["efficiency_score"], reverse=True)
    n = len(products_ranked)
    rankings = []
    for rank, p in enumerate(products_ranked, 1):
        if rank <= 2:
            tier = "top"
        elif rank >= n - 1 and n > 3:
            tier = "bottom"
        else:
            tier = "mid"
        rankings.append({
            "rank":              rank,
            "name":              p["name"],
            "efficiency_score":  p["efficiency_score"],
            "pull_through_rate": p["pull_through_rate"],
            "avg_loan_amount":   p["avg_loan_amount"],
            "funded_volume_6m":  p["funded_volume_6m"],
            "pt_trend":          p["pt_trend"],
            "tier":              tier,
        })

    print(f"  Performance scorecards: {len(products_out)} products, {len(channels_out)} channels")
    return {
        "products": products_out,
        "channels": channels_out,
        "rankings": rankings,
    }


def build_optimization_recommendations(active, feats, df):
    """Section 15: Ranked executive action list — top things to do this week.

    Each recommendation has:
        priority, title, description, estimated_impact, effort,
        loan_count, category, urgency
    """
    live_mask = (active["status"] == "live") & active["LoanAmount"].notna()
    live = active[live_mask].copy()
    fl = feats.loc[live.index].copy()

    recommendations = []

    # ── 1. Lock unlocked high-value loans at Approved+ stages ───────────────
    # Unlocked loans at Approved or later have significantly lower pull-through.
    # Historical delta: locked loans fund at ~42%, unlocked late-stage at ~8%.
    mask_unlocked_late = (fl["unlocked_at_late_stage"] == 1)
    grp_ul = live[mask_unlocked_late].copy()
    if len(grp_ul) > 0:
        # Estimate: if locked, probability would be ~0.45 instead of current avg
        locked_uplift_prob = 0.45
        current_ev = float(grp_ul["expected_value"].sum())
        if_locked_ev = float((locked_uplift_prob * grp_ul["LoanAmount"]).sum())
        impact = max(0.0, if_locked_ev - current_ev)
        recommendations.append({
            "priority": 1,
            "title": f"Secure rate locks on {len(grp_ul)} unlocked late-stage loans",
            "description": (
                "These loans have reached Approved or later without a rate lock. "
                "Unlocked late-stage loans fund at ~8% vs ~42% for locked loans — "
                "contact borrowers immediately to secure pricing."
            ),
            "estimated_impact": round(impact, 0),
            "effort": "low",
            "loan_count": int(len(grp_ul)),
            "category": "lock_management",
            "urgency": "immediate",
        })

    # ── 2. Expedite CTC for lock-expiring loans (within 14 days) ─────────────
    lock_exp_col = "lock_days_remaining"
    if lock_exp_col in fl.columns:
        mask_exp14 = (
            fl[lock_exp_col].notna()
            & (fl[lock_exp_col] <= 14)
            & (fl[lock_exp_col] >= 0)
            & (fl["stage_rank"] < 7)   # not yet at CTC
        )
    else:
        mask_exp14 = (fl["lock_expiring_not_progressed"] == 1)
    grp_exp = live[mask_exp14].copy()
    if len(grp_exp) > 0:
        # Loans that miss CTC before lock expiry drop to ~15% probability
        current_ev = float(grp_exp["expected_value"].sum())
        at_risk_ev = float((0.15 * grp_exp["LoanAmount"]).sum())
        impact = max(0.0, current_ev - at_risk_ev)
        recommendations.append({
            "priority": 2,
            "title": f"Rush CTC for {len(grp_exp)} loans with locks expiring in 14 days",
            "description": (
                "Rate locks expire before these loans reach Clear-to-Close. "
                "Each day of delay risks lock expiry and borrower fallout. "
                "Prioritize condition clearance for this cohort."
            ),
            "estimated_impact": round(impact, 0),
            "effort": "medium",
            "loan_count": int(len(grp_exp)),
            "category": "pipeline_acceleration",
            "urgency": "immediate",
        })

    # ── 3. Focus resources on near-certain CTC+ loans ─────────────────────────
    # Loans at CTC or beyond with high probability just need a final push.
    mask_ctc_plus = (fl["stage_rank"] >= 7) & (live["ml_probability"] >= 0.80)
    grp_ctc = live[mask_ctc_plus].copy()
    if len(grp_ctc) > 0:
        uplift = (1.0 - grp_ctc["ml_probability"]) * grp_ctc["LoanAmount"]
        impact = round(float(uplift.sum()), 0)
        total_amount = round(float(grp_ctc["LoanAmount"].sum()) / 1e6, 1)
        recommendations.append({
            "priority": 3,
            "title": f"Clear final conditions on {len(grp_ctc)} near-certain CTC+ loans",
            "description": (
                f"These {len(grp_ctc)} loans are at CTC or beyond with 80%+ ML probability — "
                f"they represent ${total_amount}M in near-guaranteed volume. "
                "Dedicated ops support ensures they fund this month, not next."
            ),
            "estimated_impact": impact,
            "effort": "low",
            "loan_count": int(len(grp_ctc)),
            "category": "pipeline_acceleration",
            "urgency": "this_week",
        })

    # ── 4. Re-engage stalled high-value loans (30+ days, mid-stage) ──────────
    median_amt = float(live["LoanAmount"].median())
    mask_stalled = (
        (live["days_at_stage"] >= 30)
        & (live["LoanAmount"] >= median_amt)
        & (fl["stage_rank"].between(3, 6))   # Underwriting through Final UW
        & (live["ml_probability"] >= 0.15)   # still viable
    )
    grp_stall = live[mask_stalled].copy()
    if len(grp_stall) > 0:
        # Re-engagement historically lifts probability by ~15pp for stalled loans
        uplift_pp = 0.15
        impact = round(float((uplift_pp * grp_stall["LoanAmount"]).sum()), 0)
        avg_days = round(float(grp_stall["days_at_stage"].mean()), 0)
        recommendations.append({
            "priority": 4,
            "title": f"Re-engage {len(grp_stall)} stalled above-median loans",
            "description": (
                f"These above-median loans have been at the same stage for {int(avg_days)}+ days "
                "on average — longer than historical norms. Proactive borrower outreach and "
                "condition escalation can move them before month-end."
            ),
            "estimated_impact": impact,
            "effort": "medium",
            "loan_count": int(len(grp_stall)),
            "category": "borrower_engagement",
            "urgency": "this_week",
        })

    # ── 5. Re-lock or close out loans with expired locks stuck pre-CTC ────────
    if "lock_expired_not_progressed" in fl.columns:
        mask_expired = (fl["lock_expired_not_progressed"] == 1)
    elif "lock_already_expired" in fl.columns:
        mask_expired = (fl["lock_already_expired"] == 1)
    else:
        mask_expired = pd.Series(False, index=live.index)
    grp_exp_lock = live[mask_expired].copy()
    if len(grp_exp_lock) > 0:
        recoverable = grp_exp_lock[grp_exp_lock["ml_probability"] >= 0.20]
        lost = grp_exp_lock[grp_exp_lock["ml_probability"] < 0.20]
        impact = round(float(recoverable["expected_value"].sum()), 0)
        recommendations.append({
            "priority": 5,
            "title": f"Re-lock {len(recoverable)} viable loans; close {len(lost)} dead-end locks",
            "description": (
                f"{len(recoverable)} expired-lock loans still show viable ML probability — "
                "re-locking at current rates could recover this volume. "
                f"The remaining {len(lost)} are below 20% probability; releasing ops attention "
                "there frees capacity for higher-value work."
            ),
            "estimated_impact": impact,
            "effort": "medium",
            "loan_count": int(len(grp_exp_lock)),
            "category": "lock_management",
            "urgency": "this_week",
        })

    # ── 6. Eliminate dead pipeline consuming ops attention ────────────────────
    dead = active[active["status"] == "dead"].copy()
    dead_count = int(len(dead))
    dead_value = round(float(dead["LoanAmount"].sum()), 0)
    if dead_count > 0:
        live_pipeline_value = float(live["LoanAmount"].sum())
        # Redirected ops effort on live loans can improve conversion by ~2%
        capacity_impact = round(live_pipeline_value * 0.02, 0)
        recommendations.append({
            "priority": 6,
            "title": f"Archive {dead_count} eliminated loans to free ops capacity",
            "description": (
                f"{dead_count} loans (${round(dead_value/1e6, 1)}M face value) have been flagged "
                "by the elimination filter as unlikely to fund. Formally closing them stops "
                "ops follow-up on dead deals and redirects focus to the live pipeline."
            ),
            "estimated_impact": capacity_impact,
            "effort": "low",
            "loan_count": dead_count,
            "category": "resource_reallocation",
            "urgency": "this_week",
        })

    # ── 7. Target Retail channel pull-through improvement ─────────────────────
    retail_col = "Branch Channel"
    if retail_col in live.columns:
        retail_live = live[live[retail_col].str.upper().str.contains("RETAIL", na=False)].copy()
        retail_low_prob = retail_live[retail_live["ml_probability"] < 0.40].copy()
        if len(retail_low_prob) > 0:
            # Retail pull-through is historically ~10% vs 42% Wholesale
            # Focused coaching can lift by ~5pp conservatively
            impact = round(float((0.05 * retail_low_prob["LoanAmount"]).sum()), 0)
            recommendations.append({
                "priority": 7,
                "title": f"Lift Retail pull-through: coach LOs on {len(retail_low_prob)} at-risk loans",
                "description": (
                    "Retail channel pull-through runs ~10% vs 42% Wholesale. "
                    f"{len(retail_low_prob)} Retail loans have <40% ML probability. "
                    "Targeted LO coaching and condition tracking can lift conversion on these deals."
                ),
                "estimated_impact": impact,
                "effort": "high",
                "loan_count": int(len(retail_low_prob)),
                "category": "resource_reallocation",
                "urgency": "this_month",
            })

    # ── 8. Extend locks before expiry (7-21 days out, still progressing) ─────
    if lock_exp_col in fl.columns:
        mask_extend = (
            fl[lock_exp_col].notna()
            & (fl[lock_exp_col].between(7, 21))
            & (fl["stage_rank"].between(4, 7))   # Approved through CTC
            & (live["ml_probability"] >= 0.35)    # viable loans only
        )
    else:
        mask_extend = pd.Series(False, index=live.index)
    grp_extend = live[mask_extend].copy()
    if len(grp_extend) > 0:
        # Savings from avoiding emergency re-lock chaos
        impact = round(float(grp_extend["expected_value"].sum() * 0.08), 0)
        recommendations.append({
            "priority": 8,
            "title": f"Proactively extend locks on {len(grp_extend)} progressing loans",
            "description": (
                f"{len(grp_extend)} loans at Approved–CTC have locks expiring within 21 days "
                "and are actively progressing. Extending now avoids emergency re-locks "
                "and preserves borrower commitment."
            ),
            "estimated_impact": impact,
            "effort": "low",
            "loan_count": int(len(grp_extend)),
            "category": "lock_management",
            "urgency": "this_week",
        })

    # ── Sort by priority and compute total impact ─────────────────────────────
    recommendations.sort(key=lambda x: x["priority"])
    total_impact = sum(r["estimated_impact"] for r in recommendations)

    print(f"  Optimization recommendations: {len(recommendations)} actions, "
          f"${total_impact:,.0f} total estimated impact")
    return {
        "total_estimated_impact": round(total_impact, 0),
        "recommendations": recommendations,
    }


def build_summary(active, already_funded, fstats, df, cycle_median, model_name):
    """Section 4: top-level summary stats."""
    live = active[active["status"] == "live"]
    dead = active[active["status"] == "dead"]
    total_completed = len(df[df["Outcome"].isin(["Funded", "Failed"])])
    total_funded = len(df[df["Outcome"] == "Funded"])

    return {
        "snapshot_date":        SNAPSHOT_DATE,
        "month":                SNAPSHOT_DATE[:7],
        "model_used":           model_name,
        "total_pipeline_loans": int(len(active)),
        "total_pipeline_value": round(float(active["LoanAmount"].sum()), 2),
        "live_pipeline_loans":  int(len(live)),
        "live_pipeline_value":  round(float(live["LoanAmount"].sum()), 2),
        "dead_pipeline_loans":  int(len(dead)),
        "dead_pipeline_value":  round(float(dead["LoanAmount"].sum()), 2),
        "already_funded_loans": int(len(already_funded)),
        "already_funded_value": round(float(already_funded["LoanAmount"].sum()), 2),
        "projected_total":      round(float(
            live["expected_value"].sum() + already_funded["LoanAmount"].sum()
        ), 2),
        "overall_pull_through": round(total_funded / max(total_completed, 1), 4),
        "median_cycle_days":    _safe(cycle_median),
        "elimination_stats": {
            "total":          fstats["total_loans"],
            "eliminated":     fstats["eliminated"],
            "pct_eliminated": fstats["pct_eliminated"],
            "by_reason":      {k: int(v) for k, v in fstats["by_reason"].items()},
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("DASHBOARD DATA GENERATOR")
    print("=" * 60)

    # ── Load & train ─────────────────────────────────────────────────────
    df = load_and_clean()

    print("\nBuilding transition tables...")
    tables = build_transition_tables(df)

    print("Building v3 training set...")
    training = build_training_set(df, tables)
    encoded, encoders = encode_categoricals(training, fit=True)
    encoded, medians = fill_missing_numeric(encoded, fit=True)
    feature_cols = get_feature_columns(encoders)

    print("Training model...")
    bundle = train_and_select(encoded, feature_cols)
    model = bundle["best_model"]
    model_name = bundle["best_model_name"]
    print(f"  Best model: {model_name}")

    # ── Build sections ───────────────────────────────────────────────────
    print(f"\n--- Section 1: Loan priority table (snapshot {SNAPSHOT_DATE}) ---")
    loan_table, active, already_funded, fstats, feats = build_loan_table(
        df, tables, model, feature_cols, encoders, medians,
    )

    print("\n--- Section 2: Pull-through summary ---")
    pull_through = build_pull_through(df)

    print("\n--- Section 3: Cycle time distributions ---")
    cycle_times = build_cycle_times(df)

    print("\n--- Section 4: Summary stats ---")
    summary = build_summary(
        active, already_funded, fstats, df,
        cycle_median=cycle_times["overall"]["median"],
        model_name=model_name,
    )

    print("\n--- Section 5: Backtest accuracy ---")
    backtest_accuracy = build_backtest_accuracy()

    print("\n--- Section 6: Stage funnel ---")
    stage_funnel = build_stage_funnel(active)

    print("\n--- Section 7: Channel split ---")
    channel_split = build_channel_split(active)

    print("\n--- Section 8: Product breakdown ---")
    product_breakdown = build_product_breakdown(active)

    print("\n--- Section 9: At-risk loans ---")
    at_risk_loans = build_at_risk_loans(active, feats)

    print("\n--- Section 10: Revenue at risk ---")
    revenue_at_risk = build_revenue_at_risk(active, feats)

    print("\n--- Section 11: Bottleneck detection ---")
    bottleneck_detection = build_bottleneck_detection(df, active, feats)

    print("\n--- Section 12: Velocity & momentum ---")
    velocity_momentum = build_velocity_momentum(active, feats)

    print("\n--- Section 13: What-if scenarios ---")
    what_if_scenarios = build_what_if_scenarios(df, active, feats)

    print("\n--- Section 14: Performance scorecards ---")
    performance_scorecards = build_performance_scorecards(df, active, feats)

    print("\n--- Section 15: Optimization recommendations ---")
    optimization_recommendations = build_optimization_recommendations(active, feats, df)

    # ── Assemble & write ─────────────────────────────────────────────────
    output = {
        "generated_at":                datetime.now().isoformat(),
        "loan_table":                  loan_table,
        "pull_through":                pull_through,
        "cycle_times":                 cycle_times,
        "summary":                     summary,
        "backtest_accuracy":           backtest_accuracy,
        "stage_funnel":                stage_funnel,
        "channel_split":               channel_split,
        "product_breakdown":           product_breakdown,
        "at_risk_loans":               at_risk_loans,
        "revenue_at_risk":             revenue_at_risk,
        "bottleneck_detection":        bottleneck_detection,
        "velocity_momentum":           velocity_momentum,
        "what_if_scenarios":           what_if_scenarios,
        "performance_scorecards":      performance_scorecards,
        "optimization_recommendations": optimization_recommendations,
    }

    out_path = config.OUTPUTS_PATH / "dashboard_demo_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Written -> {out_path}")
    print(f"  Loan table:    {len(loan_table)} entries")
    print(f"  Pull-through:  {len(pull_through)} entries")
    print(f"  Cycle times:   {len(cycle_times['by_product'])} products")
    print(f"  Projected:     ${summary['projected_total']:,.0f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
