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

    # ── Assemble & write ─────────────────────────────────────────────────
    output = {
        "generated_at":       datetime.now().isoformat(),
        "loan_table":         loan_table,
        "pull_through":       pull_through,
        "cycle_times":        cycle_times,
        "summary":            summary,
        "backtest_accuracy":  backtest_accuracy,
        "stage_funnel":       stage_funnel,
        "channel_split":      channel_split,
        "product_breakdown":  product_breakdown,
        "at_risk_loans":      at_risk_loans,
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
