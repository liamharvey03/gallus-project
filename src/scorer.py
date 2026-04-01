"""
FlexPoint Loan Funding Forecasting — Production Scorer

Provides the `score_pipeline()` function for scoring the current active
pipeline and producing ThoughtSpot-compatible output:

    Monthly Projected Fundings: $XXM
    +-- Already funded:         $XXM
    +-- Projected remainder:    $XXM
    |   +-- Retail:             $XXM
    |   +-- Wholesale:          $XXM
    +-- Weekly breakdown:       [Week 1] [Week 2] [Week 3] [Week 4]
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

from pipeline_snapshot import build_snapshot


# ─── Weekly bucketing ────────────────────────────────────────────────────────

def _weekly_buckets(month_start, month_end):
    """
    Return a list of (week_label, start_date, end_date) tuples covering
    the month, split into ~7-day buckets.
    """
    buckets = []
    current = month_start
    week_num = 1
    while current <= month_end:
        week_end = min(current + pd.Timedelta(days=6), month_end)
        buckets.append((f"Week {week_num}", current, week_end))
        current = week_end + pd.Timedelta(days=1)
        week_num += 1
    return buckets


def _assign_weekly_funding(active_df, already_funded_df, month_start,
                           month_end, prob_col="ml_probability"):
    """
    Distribute projected funding into weekly buckets.

    Already-funded loans go to the week they actually funded.
    Active loans are distributed proportionally across remaining weeks
    weighted by days remaining in each bucket.
    """
    buckets = _weekly_buckets(month_start, month_end)
    weekly = []

    for label, ws, we in buckets:
        # Already funded in this week
        af_in_week = already_funded_df[
            (already_funded_df["Funded D"] >= ws)
            & (already_funded_df["Funded D"] <= we)
        ]["LoanAmount"].sum()

        weekly.append({
            "week": label,
            "start": str(ws.date()),
            "end": str(we.date()),
            "already_funded": af_in_week,
            "projected_new": 0.0,
            "total": af_in_week,
        })

    # Distribute active loan expected funding across future weeks
    # Simple proportional: weight by number of days in each future bucket
    as_of = pd.Timestamp(already_funded_df["Funded D"].max()) if len(already_funded_df) else month_start
    future_buckets = [(i, b) for i, b in enumerate(buckets) if pd.Timestamp(b[2]) > as_of]

    if future_buckets and prob_col in active_df.columns:
        total_future_days = sum(
            (min(pd.Timestamp(b[2]), month_end) - max(pd.Timestamp(b[1]), as_of)).days + 1
            for _, b in future_buckets
            if pd.Timestamp(b[2]) > as_of
        )
        if total_future_days > 0:
            exp_col = prob_col.replace("probability", "expected_funding")
            total_exp = active_df[exp_col].sum() if exp_col in active_df.columns else 0

            for idx, bucket_info in future_buckets:
                bs = max(pd.Timestamp(bucket_info[1]), as_of)
                be = pd.Timestamp(bucket_info[2])
                days_in_bucket = (be - bs).days + 1
                fraction = days_in_bucket / total_future_days
                proj = total_exp * fraction
                weekly[idx]["projected_new"] = proj
                weekly[idx]["total"] += proj

    return weekly


# ─── Main scoring function ──────────────────────────────────────────────────

def score_pipeline(df, as_of_date, model=None, transition_tables=None,
                   feature_columns=None, encoders=None, medians=None):
    """
    Score the active pipeline and produce a projection bundle.

    Parameters
    ----------
    df : DataFrame — output of data_prep.load_and_clean()
    as_of_date : date-like
    model : fitted model (optional — uses ML if provided, else TT only)
    transition_tables : dict from build_transition_tables()
    feature_columns, encoders, medians : ML artifacts

    Returns
    -------
    dict with keys:
        total_projected        : float
        already_funded_amount  : float
        projected_remainder    : float
        retail_projected       : float
        wholesale_projected    : float
        weekly_breakdown       : list of dicts
        loan_level_detail      : DataFrame
        method                 : str ("ML" or "Transition Tables")
        summary                : dict (from build_snapshot)
    """
    as_of = pd.Timestamp(as_of_date)
    month_start = as_of.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)

    result = build_snapshot(
        df, as_of, month_end=month_end,
        transition_tables=transition_tables,
        model=model, feature_columns=feature_columns,
        encoders=encoders, medians=medians,
    )

    active = result["active_pipeline"]
    already = result["already_funded"]
    s = result["summary"]

    # Determine which method to use for projection
    use_ml = model is not None and "ml_expected_funding" in active.columns
    if use_ml:
        method = "ML"
        prob_col = "ml_probability"
        exp_col = "ml_expected_funding"
        total_projected = s["ml_projected_total"]
        projected_remainder = s["ml_projected_pipeline"]
    else:
        method = "Transition Tables"
        prob_col = "base_probability"
        exp_col = "expected_funding"
        total_projected = s.get("projected_total", s["already_funded_dollars"])
        projected_remainder = s.get("projected_pipeline", 0)

    already_funded_amount = s["already_funded_dollars"]

    # Retail / Wholesale split
    retail_mask = active["Branch Channel"] == "Retail"
    wholesale_mask = ~retail_mask  # Wholesale + any other

    retail_projected = (
        already[already["Branch Channel"] == "Retail"]["LoanAmount"].sum()
        + (active.loc[retail_mask, exp_col].sum() if exp_col in active.columns else 0)
    )
    wholesale_projected = (
        already[already["Branch Channel"] != "Retail"]["LoanAmount"].sum()
        + (active.loc[wholesale_mask, exp_col].sum() if exp_col in active.columns else 0)
    )

    # Weekly breakdown
    weekly = _assign_weekly_funding(
        active, already, month_start, month_end, prob_col=prob_col,
    )

    # Loan-level detail
    detail_cols = ["LoanGuid", "LoanAmount", "current_stage", "stage_rank",
                   "days_at_stage", "Product Type", "Loan Purpose",
                   "Branch Channel"]
    if prob_col in active.columns:
        detail_cols.append(prob_col)
    if exp_col in active.columns:
        detail_cols.append(exp_col)
    available_cols = [c for c in detail_cols if c in active.columns]
    loan_detail = active[available_cols].copy()
    loan_detail = loan_detail.sort_values(
        exp_col if exp_col in loan_detail.columns else "LoanAmount",
        ascending=False,
    )

    return {
        "total_projected": total_projected,
        "already_funded_amount": already_funded_amount,
        "projected_remainder": projected_remainder,
        "retail_projected": retail_projected,
        "wholesale_projected": wholesale_projected,
        "weekly_breakdown": weekly,
        "loan_level_detail": loan_detail,
        "method": method,
        "summary": s,
        "as_of": str(as_of.date()),
        "month_end": str(month_end.date()),
    }


# ─── Dashboard printer ──────────────────────────────────────────────────────

def print_dashboard(score, actual=None):
    """
    Print ThoughtSpot-style dashboard output.
    """
    as_of = score["as_of"]
    month_end = score["month_end"]
    method = score["method"]

    month_label = pd.Timestamp(month_end).strftime("%B %Y")

    print(f"\n{'═' * 65}")
    print(f"  {month_label} Projected Fundings: ${score['total_projected'] / 1e6:,.1f}M")
    print(f"  (scored as of {as_of}, method: {method})")
    print(f"{'═' * 65}")

    print(f"  |")
    print(f"  +-- Already funded:       ${score['already_funded_amount'] / 1e6:>8,.1f}M")
    print(f"  +-- Projected remainder:  ${score['projected_remainder'] / 1e6:>8,.1f}M")
    print(f"  |   +-- Retail:           ${score['retail_projected'] / 1e6:>8,.1f}M")
    print(f"  |   +-- Wholesale:        ${score['wholesale_projected'] / 1e6:>8,.1f}M")
    print(f"  |")

    # Weekly breakdown
    print(f"  +-- Weekly breakdown:")
    for w in score["weekly_breakdown"]:
        print(f"  |   {w['week']} ({w['start']} – {w['end']}): "
              f"${w['total'] / 1e6:>6,.1f}M"
              f"  (funded: ${w['already_funded'] / 1e6:,.1f}M"
              f" + proj: ${w['projected_new'] / 1e6:,.1f}M)")

    if actual is not None:
        error = (score["total_projected"] - actual) / actual
        print(f"  |")
        print(f"  +-- ACTUAL (full month):  ${actual / 1e6:>8,.1f}M")
        print(f"  +-- Error:                {error:>+8.1%}")

    # Top contributing loans
    detail = score["loan_level_detail"]
    exp_col = ([c for c in detail.columns if "expected_funding" in c] or [None])[0]
    prob_col = ([c for c in detail.columns if "probability" in c] or [None])[0]

    if exp_col:
        print(f"\n{'─' * 65}")
        print(f"  Top 10 loans by expected funding contribution:")
        print(f"{'─' * 65}")
        print(f"  {'Stage':<14s} {'Product':<16s} {'Amount':>12s} "
              f"{'P(fund)':>8s} {'Expected':>12s}")
        print(f"  {'─' * 62}")
        for _, row in detail.head(10).iterrows():
            stage = str(row.get("current_stage", ""))
            prod = str(row.get("Product Type", ""))[:15]
            amt = row.get("LoanAmount", 0)
            prob = row.get(prob_col, 0) if prob_col else 0
            exp = row.get(exp_col, 0)
            print(f"  {stage:<14s} {prod:<16s} ${amt:>11,.0f} "
                  f"{prob:>7.1%} ${exp:>11,.0f}")

    # Stage summary
    s = score["summary"]
    print(f"\n{'─' * 65}")
    print(f"  Pipeline: {s['active_count']:,} active loans  "
          f"|  ${s['active_dollars'] / 1e6:,.1f}M total pipeline")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_prep import load_and_clean
    from transition_tables import build_transition_tables
    from feature_engineering import (
        build_training_set, encode_categoricals, fill_missing_numeric,
        get_feature_columns,
    )
    from models import train_and_select

    df = load_and_clean()

    print("\nBuilding transition tables...")
    tables = build_transition_tables(df)

    print("Building training set...")
    training = build_training_set(df, tables)
    encoded, encoders = encode_categoricals(training, fit=True)
    encoded, medians = fill_missing_numeric(encoded, fit=True)
    feature_cols = get_feature_columns(encoders)

    print("Training ML model...")
    bundle = train_and_select(encoded, feature_cols)
    best_model = bundle["best_model"]
    print(f"  Selected: {bundle['best_model_name']}")

    # Find the most recent complete month in the data
    max_funded = df["Funded D"].max()
    # Go back to the previous month to ensure completeness
    last_complete = (max_funded.replace(day=1) - pd.Timedelta(days=1))
    score_month_start = last_complete.replace(day=1)
    # Score at day 15 of that month
    as_of = score_month_start + pd.Timedelta(days=14)  # day 15

    print(f"\nScoring pipeline as of {as_of.date()}...")

    score = score_pipeline(
        df, as_of,
        model=best_model, transition_tables=tables,
        feature_columns=feature_cols, encoders=encoders, medians=medians,
    )

    # Get actual for comparison
    month_end = score_month_start + pd.offsets.MonthEnd(0)
    actual = df[
        df["Funded D"].notna()
        & (df["Funded D"] >= score_month_start)
        & (df["Funded D"] <= month_end)
    ]["LoanAmount"].sum()

    print_dashboard(score, actual=actual)
