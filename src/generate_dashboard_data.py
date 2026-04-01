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
    return rows, active, already_funded, fstats


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
    loan_table, active, already_funded, fstats = build_loan_table(
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

    # ── Assemble & write ─────────────────────────────────────────────────
    output = {
        "generated_at":  datetime.now().isoformat(),
        "loan_table":    loan_table,
        "pull_through":  pull_through,
        "cycle_times":   cycle_times,
        "summary":       summary,
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
