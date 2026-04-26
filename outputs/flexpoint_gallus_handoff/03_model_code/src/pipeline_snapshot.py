"""
FlexPoint Loan Funding Forecasting — Pipeline Snapshot Reconstruction

The critical module.  Given an as-of date, reconstruct the state of the
loan pipeline: which loans are already funded this month, which are active,
what stage each active loan is at, and how long it has been there.

Optionally integrates transition tables to assign base_probability and
expected_funding to each active loan.
"""
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Import the shared vectorised stage lookup
from transition_tables import vectorized_current_stage


# ─── Row-level helpers (kept for ad-hoc use / single-loan queries) ───────────

def get_stage_at(row, as_of_date):
    """
    Return (stage_label, stage_rank, date_entered) for a loan at *as_of_date*.
    """
    as_of = pd.Timestamp(as_of_date)
    for col, label, rank in config.STAGE_MAP:
        dt = row.get(col)
        if pd.notna(dt) and dt <= as_of:
            return label, rank, dt
    return None, -1, pd.NaT


def get_days_at_stage(row, as_of_date):
    """Days the loan has been sitting at its current stage as of *as_of_date*."""
    _, _, entered = get_stage_at(row, as_of_date)
    if pd.isna(entered):
        return np.nan
    return (pd.Timestamp(as_of_date) - entered).days


def is_loan_active_at(row, as_of_date):
    """Whether a loan should be counted as active pipeline on *as_of_date*."""
    as_of = pd.Timestamp(as_of_date)
    opened = row.get("Loan Open Date")
    if pd.isna(opened) or opened > as_of:
        return False
    funded = row.get("Funded D")
    if pd.notna(funded) and funded <= as_of:
        return False
    for col in config.FAILURE_DATE_COLUMNS:
        dt = row.get(col)
        if pd.notna(dt) and dt <= as_of:
            return False
    return True


# ─── Snapshot builder ────────────────────────────────────────────────────────

def build_snapshot(df, as_of_date, month_end=None, month_start=None,
                   transition_tables=None,
                   model=None, feature_columns=None, encoders=None, medians=None):
    """
    Build a pipeline snapshot at *as_of_date*.

    Parameters
    ----------
    df : DataFrame — output of data_prep.load_and_clean()
    as_of_date : date-like — the "prediction date"
    month_end : date-like, optional — last day of the target month.
    transition_tables : dict, optional — output of
        transition_tables.build_transition_tables().  When provided, each
        active loan gets a base_probability and expected_funding column.
    model : fitted sklearn model, optional — ML model for scoring.
    feature_columns : list, optional — ordered feature column names.
    encoders : dict, optional — categorical encoders from training.
    medians : dict, optional — numeric medians from training.

    Returns
    -------
    dict with keys:
        already_funded  : DataFrame
        active_pipeline : DataFrame (with current_stage, stage_rank,
                          days_at_stage, and optionally base_probability,
                          expected_funding, ml_probability, ml_expected_funding)
        summary         : dict (counts, dollars, and optionally
                          projected_pipeline, projected_total,
                          ml_projected_pipeline, ml_projected_total)
    """
    as_of = pd.Timestamp(as_of_date)
    if month_start is not None:
        month_start = pd.Timestamp(month_start)
    else:
        month_start = as_of.replace(day=1)
    if month_end is None:
        month_end = month_start + pd.offsets.MonthEnd(0)
    month_end = pd.Timestamp(month_end)

    # ── Already funded this month (month-start … as_of) ─────────────────
    already_funded = df[
        df["Funded D"].notna()
        & (df["Funded D"] >= month_start)
        & (df["Funded D"] <= as_of)
    ].copy()

    # ── Identify active loans (vectorised) ───────────────────────────────
    opened_mask = df["Loan Open Date"].notna() & (df["Loan Open Date"] <= as_of)
    not_funded_mask = df["Funded D"].isna() | (df["Funded D"] > as_of)

    not_failed_mask = pd.Series(True, index=df.index)
    for col in config.FAILURE_DATE_COLUMNS:
        if col in df.columns:
            not_failed_mask &= df[col].isna() | (df[col] > as_of)

    active = df[opened_mask & not_funded_mask & not_failed_mask].copy()

    # ── Determine current stage (vectorised) ─────────────────────────────
    sl, sr, se = vectorized_current_stage(active, as_of)
    active["current_stage"] = sl
    active["stage_rank"] = sr
    active["days_at_stage"] = (as_of - se).dt.days

    # Drop rows that haven't entered the pipeline yet
    active = active[active["current_stage"].notna()].copy()

    # ── Assign base probabilities from transition tables ─────────────────
    if transition_tables is not None:
        from transition_tables import lookup_probability

        # Use month-end tables for projection
        me_strat = transition_tables.get("me_stratified")
        me_unstrat = transition_tables.get("me_unstratified")

        if me_strat is not None and me_unstrat is not None:
            # Vectorised: merge on the stratified table first
            active = active.reset_index(drop=True)
            active["_key"] = list(zip(
                active["current_stage"],
                active["Product Type"],
                active["Loan Purpose"],
            ))

            prob_map = me_strat["p_fund"].to_dict()
            active["base_probability"] = active["_key"].map(prob_map)

            # Fall back to stage-only for unmatched rows
            stage_map = me_unstrat["p_fund"].to_dict()
            missing = active["base_probability"].isna()
            active.loc[missing, "base_probability"] = (
                active.loc[missing, "current_stage"].map(stage_map)
            )
            active["base_probability"] = active["base_probability"].fillna(0.0)
            active.drop(columns=["_key"], inplace=True)
        else:
            active["base_probability"] = 0.0

        active["expected_funding"] = active["base_probability"] * active["LoanAmount"]

    # ── ML scoring (optional) ──────────────────────────────────────────
    if model is not None and feature_columns is not None:
        from feature_engineering import (
            build_feature_row, encode_categoricals, fill_missing_numeric,
        )
        from models import _predict_proba

        features = build_feature_row(active, as_of, month_end,
                                     transition_tables or {})
        features, _ = encode_categoricals(features, encoders=encoders, fit=False)
        features, _ = fill_missing_numeric(features, medians=medians, fit=False)

        # Align columns: add missing as 0, reorder to match training
        for col in feature_columns:
            if col not in features.columns:
                features[col] = 0
        X = features[feature_columns].values.astype(np.float32)

        ml_probs = _predict_proba(model, X)
        active["ml_probability"] = ml_probs
        active["ml_expected_funding"] = ml_probs * active["LoanAmount"]

    # ── Summary ──────────────────────────────────────────────────────────
    summary = {
        "as_of_date": str(as_of.date()),
        "month_start": str(month_start.date()),
        "month_end": str(month_end.date()),
        "already_funded_count": len(already_funded),
        "already_funded_dollars": already_funded["LoanAmount"].sum(),
        "active_count": len(active),
        "active_dollars": active["LoanAmount"].sum(),
        "stage_distribution": (
            active.groupby("current_stage")["LoanAmount"]
            .agg(["count", "sum"])
            .rename(columns={"count": "loans", "sum": "dollars"})
            .sort_values("loans", ascending=False)
        ),
    }

    if transition_tables is not None and "expected_funding" in active.columns:
        summary["projected_pipeline"] = active["expected_funding"].sum()
        summary["projected_total"] = (
            summary["already_funded_dollars"] + summary["projected_pipeline"]
        )

    if "ml_expected_funding" in active.columns:
        summary["ml_projected_pipeline"] = active["ml_expected_funding"].sum()
        summary["ml_projected_total"] = (
            summary["already_funded_dollars"] + summary["ml_projected_pipeline"]
        )

    return {
        "already_funded": already_funded,
        "active_pipeline": active,
        "summary": summary,
    }


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

    # Build transition tables
    print("\nBuilding transition tables...")
    tables = build_transition_tables(df)

    # Build training set and train ML model
    print("Building training set...")
    training = build_training_set(df, tables)
    encoded, encoders = encode_categoricals(training, fit=True)
    encoded, medians = fill_missing_numeric(encoded, fit=True)
    feature_cols = get_feature_columns(encoders)

    print(f"\n{'═' * 65}")
    print("TRAINING ML MODEL")
    print(f"{'═' * 65}")
    bundle = train_and_select(encoded, feature_cols)
    best_model = bundle["best_model"]
    best_name = bundle["best_model_name"]
    print(f"\n  Using: {best_name}")

    # POC validation: Sep 15 2025 snapshot
    snap_date = date(2025, 9, 15)
    print(f"\n{'═' * 65}")
    print(f"PIPELINE SNAPSHOT — {snap_date}")
    print(f"{'═' * 65}")

    result = build_snapshot(
        df, snap_date, transition_tables=tables,
        model=best_model, feature_columns=feature_cols,
        encoders=encoders, medians=medians,
    )
    s = result["summary"]

    print(f"\nAlready funded (Sep 1-15): {s['already_funded_count']:,} loans"
          f"  |  ${s['already_funded_dollars']:,.0f}")
    print(f"Active pipeline:          {s['active_count']:,} loans"
          f"  |  ${s['active_dollars']:,.0f}")

    print(f"\nStage distribution (active):")
    print(s["stage_distribution"].to_string())

    # ── Projection vs actual ─────────────────────────────────────────────
    actual_sep = df[
        df["Funded D"].notna()
        & (df["Funded D"] >= "2025-09-01")
        & (df["Funded D"] <= "2025-09-30")
    ]["LoanAmount"].sum()

    tt_total = s["projected_total"]
    tt_pipeline = s["projected_pipeline"]
    tt_error = (tt_total - actual_sep) / actual_sep

    ml_total = s["ml_projected_total"]
    ml_pipeline = s["ml_projected_pipeline"]
    ml_error = (ml_total - actual_sep) / actual_sep

    print(f"\n{'═' * 65}")
    print(f"PROJECTION vs ACTUAL — September 2025")
    print(f"{'═' * 65}")
    print(f"  Already funded (Sep 1-15):  ${s['already_funded_dollars']:>14,.0f}")
    print(f"  ACTUAL (full month):        ${actual_sep:>14,.0f}")
    print(f"\n  {'Method':<28s} {'Pipeline':>14s} {'Total':>14s} {'Error':>8s}")
    print(f"  {'─' * 68}")
    print(f"  {'Transition Tables':<28s} ${tt_pipeline:>13,.0f} ${tt_total:>13,.0f} {tt_error:>+7.1%}")
    print(f"  {'ML (' + best_name + ')':<28s} ${ml_pipeline:>13,.0f} ${ml_total:>13,.0f} {ml_error:>+7.1%}")
    print(f"  {'Naive POC':<28s} {'':>14s} ${146_500_000:>13,.0f} {'+4.7%':>8s}")

    # ── Stage-level comparison ─────────────────────────────────────────
    active_df = result["active_pipeline"]
    by_stage = (
        active_df.groupby("current_stage")
        .agg(
            loans=("LoanAmount", "count"),
            dollars=("LoanAmount", "sum"),
            avg_tt_prob=("base_probability", "mean"),
            tt_exp=("expected_funding", "sum"),
            avg_ml_prob=("ml_probability", "mean"),
            ml_exp=("ml_expected_funding", "sum"),
        )
    )
    by_stage = by_stage.sort_values("loans", ascending=False)
    print(f"\n{'─' * 65}")
    print("Stage-level projection detail:")
    print(f"{'─' * 65}")
    print(by_stage.to_string(float_format=lambda x: f"{x:,.1f}"))
