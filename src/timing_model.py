"""
FlexPoint Loan Funding Forecasting — Timing Model (Funding Week Prediction)

Predicts WHEN in the month a loan will fund, not just whether.
Two approaches:
  1. Median-based: historical stage-to-funding duration lookup (simple, robust)
  2. GBM regression: trained model predicting days-to-fund (more features)

Weekly buckets:
  Week 1: days 1-7    Week 2: days 8-14
  Week 3: days 15-21  Week 4: days 22-end
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, median_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from transition_tables import vectorized_current_stage


# ─── Constants ────────────────────────────────────────────────────────────────

WEEK_BINS = [0, 7, 14, 21, 32]  # day-of-month boundaries
WEEK_LABELS = ["Week 1", "Week 2", "Week 3", "Week 4"]


def day_to_week(day_of_month):
    """Map day-of-month (1-31) to week label."""
    if day_of_month <= 7:
        return "Week 1"
    elif day_of_month <= 14:
        return "Week 2"
    elif day_of_month <= 21:
        return "Week 3"
    else:
        return "Week 4"


# ═══════════════════════════════════════════════════════════════════════════════
# Part A.1: Stage-to-funding duration lookup table
# ═══════════════════════════════════════════════════════════════════════════════

def build_duration_table(df):
    """
    For every funded loan, compute days from each stage entry to Funded D.
    Returns a DataFrame with percentile statistics by stage.

    This is a standalone deliverable for Augie.
    """
    funded = df[df["Funded D"].notna()].copy()

    rows = []
    for col, label, rank in reversed(config.STAGE_MAP):
        if col == "Funded D":
            continue

        valid = funded[funded[col].notna()].copy()
        days = (valid["Funded D"] - valid[col]).dt.days
        days = days[days >= 0]

        if len(days) < 10:
            continue

        rows.append({
            "stage": label,
            "stage_rank": rank,
            "n": len(days),
            "p10": days.quantile(0.10),
            "p25": days.quantile(0.25),
            "median": days.median(),
            "p75": days.quantile(0.75),
            "p90": days.quantile(0.90),
            "mean": days.mean(),
            "std": days.std(),
        })

    return pd.DataFrame(rows).sort_values("stage_rank")


def get_median_days_to_fund(duration_table):
    """Return a dict: stage_rank -> median days to fund from that stage."""
    return dict(zip(
        duration_table["stage_rank"].astype(int),
        duration_table["median"],
    ))


def build_duration_distributions(df):
    """
    Build raw duration arrays by stage for distributional week prediction.

    Returns dict: stage_rank -> numpy array of days-to-fund values.
    """
    funded = df[df["Funded D"].notna()].copy()
    distributions = {}

    for col, label, rank in config.STAGE_MAP:
        if col == "Funded D":
            continue
        valid = funded[funded[col].notna()]
        days = (valid["Funded D"] - valid[col]).dt.days
        days = days[days >= 0].values
        if len(days) >= 10:
            distributions[rank] = days

    return distributions


# ═══════════════════════════════════════════════════════════════════════════════
# Part A.2: Build timing training data
# ═══════════════════════════════════════════════════════════════════════════════

def build_timing_training_set(df, transition_tables, months=None):
    """
    Build training data for the days-to-fund regression.

    For each (month, snapshot_day), find loans that are active AND actually
    fund by month-end.  Target: days_to_fund = (Funded D - as_of).days.

    Features mirror the v3 feature set.
    """
    from feature_engineering import build_feature_row

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

            # Active loans
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

            # Stage computation
            sl, sr, se = vectorized_current_stage(active, as_of)
            active["current_stage"] = sl
            active["stage_rank"] = sr
            active["days_at_stage"] = (as_of - se).dt.days
            active = active[active["current_stage"].notna()]

            if len(active) == 0:
                continue

            # Only keep loans that actually fund by month end
            funded_mask = (
                active["Funded D"].notna()
                & (active["Funded D"] > as_of)
                & (active["Funded D"] <= month_end)
            )
            will_fund = active[funded_mask].copy()

            if len(will_fund) < 5:
                continue

            # Target: days from snapshot to actual funding
            days_to_fund = (will_fund["Funded D"] - as_of).dt.days

            # Features
            features = build_feature_row(will_fund, as_of, month_end,
                                         transition_tables)

            # Attach metadata + target
            features["snapshot_year"] = year
            features["snapshot_month"] = month
            features["snapshot_day"] = day
            features["loan_guid"] = will_fund["LoanGuid"].values
            features["days_to_fund"] = days_to_fund.values
            features["fund_day_of_month"] = will_fund["Funded D"].dt.day.values

            chunks.append(features)

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks, ignore_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Part A.3: Train timing regression model
# ═══════════════════════════════════════════════════════════════════════════════

def train_timing_model(X_train, y_train):
    """Train a GBM regressor for days-to-fund prediction."""
    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
        loss="huber",  # robust to outliers
    )
    model.fit(X_train, y_train)
    return model


def evaluate_timing_model(model, X_test, y_test):
    """Evaluate the regression model."""
    preds = model.predict(X_test)
    preds = np.clip(preds, 0, 62)  # cap at ~2 months

    mae = mean_absolute_error(y_test, preds)
    medae = median_absolute_error(y_test, preds)
    rmse = np.sqrt(np.mean((y_test - preds) ** 2))

    # Week-level accuracy: does the predicted week match actual week?
    actual_weeks = np.array([day_to_week(d) for d in y_test])
    # Convert days_to_fund to approximate day-of-month (need snapshot context)
    # This is approximate — real week accuracy is computed in the backtest

    return {
        "mae": mae,
        "median_ae": medae,
        "rmse": rmse,
        "mean_actual": y_test.mean(),
        "mean_predicted": preds.mean(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Part A.3b: Predict funding week
# ═══════════════════════════════════════════════════════════════════════════════

def predict_funding_week_median(active_df, as_of, month_end,
                                 duration_lookup):
    """
    Simple median-based approach.

    For each loan, look up median days-to-fund from its current stage.
    predicted_fund_date = as_of + median_days.
    Map to week.
    """
    as_of = pd.Timestamp(as_of)
    month_end = pd.Timestamp(month_end)
    month_start = month_end.replace(day=1)

    stage_ranks = active_df["stage_rank"].values.astype(int)
    predicted_days = np.array([
        duration_lookup.get(sr, 30) for sr in stage_ranks
    ])
    # Subtract days already spent at stage
    days_at_stage = active_df["days_at_stage"].values.astype(float)
    adjusted_days = np.maximum(predicted_days - days_at_stage, 0)

    predicted_dates = pd.Series([
        as_of + pd.Timedelta(days=int(d)) for d in adjusted_days
    ], index=active_df.index)

    # Map to week
    weeks = []
    for pdate in predicted_dates:
        if pdate < month_start:
            weeks.append("Already")  # predicted before month start
        elif pdate > month_end:
            weeks.append("Next Month")
        else:
            weeks.append(day_to_week(pdate.day))

    return pd.Series(weeks, index=active_df.index, name="predicted_week")


def predict_funding_week_gbm(active_df, as_of, month_end,
                               model, feature_columns, encoders, medians,
                               transition_tables):
    """
    GBM regression approach.

    Predict days-to-fund for each loan, convert to funding date, map to week.
    """
    from feature_engineering import (
        build_feature_row, encode_categoricals, fill_missing_numeric,
    )

    as_of = pd.Timestamp(as_of)
    month_end = pd.Timestamp(month_end)
    month_start = month_end.replace(day=1)

    # Build features
    features = build_feature_row(active_df, as_of, month_end,
                                  transition_tables)
    features, _ = encode_categoricals(features, encoders=encoders, fit=False)
    features, _ = fill_missing_numeric(features, medians=medians, fit=False)

    # Align columns
    for col in feature_columns:
        if col not in features.columns:
            features[col] = 0
    X = features[feature_columns].values.astype(np.float32)

    # Predict days to fund
    predicted_days = model.predict(X)
    predicted_days = np.clip(predicted_days, 0, 62)

    predicted_dates = pd.Series([
        as_of + pd.Timedelta(days=int(round(d))) for d in predicted_days
    ], index=active_df.index)

    # Map to week
    weeks = []
    for pdate in predicted_dates:
        if pdate < month_start:
            weeks.append("Already")
        elif pdate > month_end:
            weeks.append("Next Month")
        else:
            weeks.append(day_to_week(pdate.day))

    return pd.Series(weeks, index=active_df.index, name="predicted_week")


# ═══════════════════════════════════════════════════════════════════════════════
# Part A.3c: Distributional approach (percentile-based week allocation)
# ═══════════════════════════════════════════════════════════════════════════════

def predict_funding_week_distributional(active_df, as_of, month_end,
                                         duration_distributions):
    """
    Distributional approach: for each loan, compute P(fund in week W | fund)
    using the historical distribution of stage-to-funding durations.

    Instead of a single point estimate, this spreads each loan's expected
    contribution across weeks according to the empirical CDF.

    Returns a DataFrame with columns [Week 1, Week 2, Week 3, Week 4]
    containing the probability weight for each week (rows sum to <=1).
    """
    as_of = pd.Timestamp(as_of)
    month_end = pd.Timestamp(month_end)
    month_start = month_end.replace(day=1)

    n = len(active_df)
    week_probs = np.zeros((n, 4))  # 4 weeks

    stage_ranks = active_df["stage_rank"].values.astype(int)
    days_at_stage = active_df["days_at_stage"].values.astype(float)

    # Week boundaries in days-from-as_of
    # Day X of the month = (month_start + X-1 days) relative to as_of
    for i in range(n):
        sr = stage_ranks[i]
        das = days_at_stage[i]

        dist = duration_distributions.get(sr)
        if dist is None or len(dist) == 0:
            # Fall back: uniform across weeks
            week_probs[i, :] = 0.25
            continue

        # Adjust distribution: remaining days = full_duration - days_at_stage
        remaining = dist - das
        remaining = remaining[remaining >= 0]

        if len(remaining) == 0:
            # Loan has exceeded typical duration — it will fund very soon
            # Put all weight in the earliest possible week
            fund_day = as_of + pd.Timedelta(days=0)
            if fund_day >= month_start and fund_day <= month_end:
                wk_idx = min((fund_day.day - 1) // 7, 3)
                week_probs[i, wk_idx] = 1.0
            continue

        # Convert remaining days to predicted fund dates
        pred_dates = as_of + pd.to_timedelta(remaining, unit="D")

        # Count how many fall in each week of the target month
        in_month = (pred_dates >= month_start) & (pred_dates <= month_end)
        if in_month.sum() == 0:
            continue  # all predictions outside this month

        month_dates = pred_dates[in_month]
        days_of_month = month_dates.day

        for j, (lo, hi) in enumerate([(1, 7), (8, 14), (15, 21), (22, 32)]):
            week_probs[i, j] = ((days_of_month >= lo) & (days_of_month <= hi)).sum()

        # Normalize: these become P(fund in week W | fund in this month)
        total = week_probs[i].sum()
        if total > 0:
            week_probs[i] /= total

    return pd.DataFrame(
        week_probs,
        index=active_df.index,
        columns=WEEK_LABELS,
    )


def build_weekly_projection_distributional(active_df, week_probs_df, ml_probs,
                                            already_funded_df, month_start,
                                            month_end):
    """
    Build weekly projection using distributional week probabilities.

    For each loan: expected $ in week W = P(fund) * P(week W | fund) * LoanAmount
    """
    month_start = pd.Timestamp(month_start)
    projection = {wk: 0.0 for wk in WEEK_LABELS}

    # Already funded
    if len(already_funded_df) > 0:
        af = already_funded_df.copy()
        af["fund_week"] = af["Funded D"].dt.day.apply(day_to_week)
        for wk in WEEK_LABELS:
            mask = af["fund_week"] == wk
            projection[wk] += af.loc[mask, "LoanAmount"].sum()

    # Pipeline: distribute each loan across weeks
    loan_amounts = active_df["LoanAmount"].values
    for j, wk in enumerate(WEEK_LABELS):
        wk_weights = week_probs_df.iloc[:, j].values
        projection[wk] += np.nansum(ml_probs * wk_weights * loan_amounts)

    return projection


# ═══════════════════════════════════════════════════════════════════════════════
# Part B: Weekly projection aggregation
# ═══════════════════════════════════════════════════════════════════════════════

def build_weekly_projection(active_df, predicted_weeks, ml_probs,
                             already_funded_df, month_start, month_end):
    """
    Produce weekly dollar projections.

    For each week, sum P(fund) × LoanAmount for loans predicted to fund
    that week.  Already-funded loans are placed in their actual week.
    """
    month_start = pd.Timestamp(month_start)
    month_end = pd.Timestamp(month_end)

    projection = {wk: 0.0 for wk in WEEK_LABELS}

    # Already funded this month
    if len(already_funded_df) > 0:
        af = already_funded_df.copy()
        af["fund_week"] = af["Funded D"].dt.day.apply(day_to_week)
        for wk in WEEK_LABELS:
            mask = af["fund_week"] == wk
            projection[wk] += af.loc[mask, "LoanAmount"].sum()

    # Pipeline loans (weighted by probability)
    loan_amounts = active_df["LoanAmount"].values
    for i, (idx, wk) in enumerate(predicted_weeks.items()):
        if wk in WEEK_LABELS:
            projection[wk] += ml_probs[i] * loan_amounts[i]
        # "Already" and "Next Month" are ignored (they don't contribute
        # to this month's projection)

    return projection


def build_weekly_projection_historical(total_monthly_projection,
                                       already_funded_df, month_start,
                                       month_end, hist_pcts=None):
    """
    Historical-distribution approach: allocate the total projected pipeline
    dollars using the known historical weekly distribution.

    Default distribution: Week 1: 18%, Week 2: 21%, Week 3: 23%, Week 4: 38%
    (computed from all funded loans across 2023-2025)

    Already-funded dollars go to their actual week.  The remaining projected
    pipeline is distributed using the historical percentages, re-normalised
    to account for weeks that are already past.
    """
    if hist_pcts is None:
        hist_pcts = {
            "Week 1": 0.178,
            "Week 2": 0.203,
            "Week 3": 0.234,
            "Week 4": 0.384,
        }

    month_start = pd.Timestamp(month_start)
    projection = {wk: 0.0 for wk in WEEK_LABELS}

    # Already funded
    already_total = 0.0
    if len(already_funded_df) > 0:
        af = already_funded_df.copy()
        af["fund_week"] = af["Funded D"].dt.day.apply(day_to_week)
        for wk in WEEK_LABELS:
            mask = af["fund_week"] == wk
            amt = af.loc[mask, "LoanAmount"].sum()
            projection[wk] += amt
            already_total += amt

    # Remaining pipeline = total - already
    remaining = total_monthly_projection - already_total

    if remaining > 0:
        # Distribute using historical percentages
        for wk in WEEK_LABELS:
            projection[wk] += remaining * hist_pcts.get(wk, 0.25)

    return projection


def compute_actual_weekly(df, month_start, month_end):
    """Compute actual funded dollars by week for a given month."""
    month_start = pd.Timestamp(month_start)
    month_end = pd.Timestamp(month_end)

    funded_month = df[
        df["Funded D"].notna()
        & (df["Funded D"] >= month_start)
        & (df["Funded D"] <= month_end)
    ].copy()

    actuals = {wk: 0.0 for wk in WEEK_LABELS}
    if len(funded_month) > 0:
        funded_month["fund_week"] = funded_month["Funded D"].dt.day.apply(
            day_to_week
        )
        for wk in WEEK_LABELS:
            mask = funded_month["fund_week"] == wk
            actuals[wk] = funded_month.loc[mask, "LoanAmount"].sum()

    return actuals
