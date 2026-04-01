"""
Comprehensive analysis pass — runs every module, captures all output,
writes outputs/results/full_findings.md.

Loads data and trains models ONCE, then runs:
  1. Full backtest (all months × all snapshot days × both methods)
  2. Scorer on 3 most recent complete months
  3. Full model comparison, all feature importances, calibration assessment
  4. Full EDA (correlations, categorical spreads, time-at-stage)
  5. Full transition table dump
"""
import sys
import io
from pathlib import Path
from datetime import date

import pandas as pd
import numpy as np
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

from data_prep import load_and_clean
from transition_tables import build_transition_tables
from feature_engineering import (
    build_training_set, encode_categoricals, fill_missing_numeric,
    get_feature_columns,
)
from models import train_and_select, _predict_proba, evaluate_models, feature_importance
from backtest import run_backtest, print_backtest_summary, save_comparison_figure
from scorer import score_pipeline, print_dashboard
from eda import numeric_correlations, categorical_spreads, time_at_stage_analysis

# ─── Tee: capture printed output AND show on terminal ────────────────────────

class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()
    def flush(self):
        for s in self.streams:
            s.flush()

capture = io.StringIO()
sys.stdout = Tee(sys.__stdout__, capture)


# =============================================================================
# SETUP — Load once, train once
# =============================================================================

print("=" * 80)
print("COMPREHENSIVE ANALYSIS — LOADING DATA & TRAINING")
print("=" * 80)

df = load_and_clean()
print(f"\nDataset: {len(df):,} rows x {len(df.columns)} columns")
print(f"Outcomes: {df['Outcome'].value_counts().to_dict()}")
print(f"Date range: {df['Funded D'].min()} → {df['Funded D'].max()}")

print("\nBuilding transition tables...")
tables = build_transition_tables(df)
obs = tables["observations"]
print(f"  Observations: {len(obs):,} loan-month records across {obs['snapshot_month'].nunique()} months")

print("\nBuilding training set...")
training = build_training_set(df, tables)
print(f"  Training set: {training.shape[0]:,} rows x {training.shape[1]} columns")
print(f"  Positive rate: {training['fund_by_end'].mean():.1%}")

encoded, encoders = encode_categoricals(training, fit=True)
encoded, medians = fill_missing_numeric(encoded, fit=True)
feature_cols = get_feature_columns(encoders)
print(f"  Features after encoding: {len(feature_cols)}")

print("\nTraining models...")
bundle = train_and_select(encoded, feature_cols)
best_model = bundle["best_model"]
best_name = bundle["best_model_name"]
all_models = bundle["models"]
X_test = bundle["X_test"]
y_test = bundle["y_test"]


# =============================================================================
# 1. FULL BACKTEST — every month, every snapshot day, both methods
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 1. FULL BACKTEST — ALL MONTHS × ALL SNAPSHOT DAYS × BOTH METHODS")
print(f"{'#' * 80}")

bt = run_backtest(df, tables, best_model, feature_cols, encoders, medians)

# Save CSV
csv_path = config.OUTPUTS_PATH / "results" / "backtest_results.csv"
csv_path.parent.mkdir(parents=True, exist_ok=True)
bt.to_csv(csv_path, index=False)
print(f"\nSaved → {csv_path}")

# Print the COMPLETE table — every row
print(f"\n{'─' * 120}")
print("COMPLETE BACKTEST TABLE")
print(f"{'─' * 120}")
print(f"{'Month':<10s} {'Day':>3s} {'Method':<20s} {'Already':>14s} {'Pipeline':>14s} "
      f"{'Projected':>14s} {'Actual':>14s} {'Error%':>8s} {'Dir':<5s}")
print(f"{'─' * 120}")

for _, r in bt.sort_values(["year", "month", "snapshot_day", "method"]).iterrows():
    label = f"{int(r['year'])}-{int(r['month']):02d}"
    print(f"{label:<10s} {int(r['snapshot_day']):>3d} {r['method']:<20s} "
          f"${r['already_funded']:>13,.0f} ${r['projected_pipeline']:>13,.0f} "
          f"${r['projected']:>13,.0f} ${r['actual']:>13,.0f} "
          f"{r['error_pct']:>+7.1f}% {r['direction']:<5s}")

# MAPE summary tables
print(f"\n\n{'─' * 80}")
print("MAPE BY METHOD × SNAPSHOT DAY")
print(f"{'─' * 80}")
for method in ["Transition Tables", "ML"]:
    sub = bt[bt["method"] == method]
    print(f"\n  {method}:")
    print(f"    {'Day':>5s} {'MAPE':>8s} {'MeanErr':>10s} {'MedianErr':>10s} "
          f"{'N':>4s} {'Within10%':>10s}")
    print(f"    {'─' * 50}")
    for day in config.SNAPSHOT_DAYS:
        ds = sub[sub["snapshot_day"] == day]
        mape = ds["error_pct"].abs().mean()
        mean_err = ds["error_pct"].mean()
        med_err = ds["error_pct"].median()
        w10 = (ds["error_pct"].abs() <= 10).sum()
        print(f"    {day:>5d} {mape:>7.1f}% {mean_err:>+9.1f}% {med_err:>+9.1f}% "
              f"{len(ds):>4d} {w10:>5d}/{len(ds):>2d}")
    overall_mape = sub["error_pct"].abs().mean()
    overall_mean = sub["error_pct"].mean()
    w10_all = (sub["error_pct"].abs() <= 10).sum()
    print(f"    {'ALL':>5s} {overall_mape:>7.1f}% {overall_mean:>+9.1f}% "
          f"{'':>10s} {len(sub):>4d} {w10_all:>5d}/{len(sub):>2d}")

# Bias analysis
print(f"\n{'─' * 80}")
print("BIAS ANALYSIS (Day 15)")
print(f"{'─' * 80}")
d15 = bt[bt["snapshot_day"] == 15]
for method in ["Transition Tables", "ML"]:
    sub = d15[d15["method"] == method]
    over = (sub["error_pct"] > 0).sum()
    under = (sub["error_pct"] < 0).sum()
    print(f"  {method}: over-projected {over}/{len(sub)}, "
          f"under-projected {under}/{len(sub)}, "
          f"mean bias {sub['error_pct'].mean():>+.1f}%")

# Month where model broke down
print(f"\n{'─' * 80}")
print("ANOMALOUS MONTHS (|error| > 15% at day 15)")
print(f"{'─' * 80}")
for method in ["Transition Tables", "ML"]:
    sub = d15[d15["method"] == method]
    bad = sub[sub["error_pct"].abs() > 15]
    if len(bad) > 0:
        print(f"\n  {method}:")
        for _, r in bad.iterrows():
            print(f"    {int(r['year'])}-{int(r['month']):02d}: "
                  f"projected ${r['projected']:,.0f} vs actual ${r['actual']:,.0f} = "
                  f"{r['error_pct']:+.1f}%")
    else:
        print(f"\n  {method}: none")

# Save figure
fig_path = config.OUTPUTS_PATH / "figures" / "backtest_comparison.png"
save_comparison_figure(bt, fig_path)


# =============================================================================
# 2. SCORER — 3 most recent complete months
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 2. SCORER — 3 MOST RECENT COMPLETE MONTHS")
print(f"{'#' * 80}")

max_funded = df["Funded D"].max()
# Go back from latest funded date to find 3 complete months
months_to_score = []
cursor = max_funded.replace(day=1) - pd.Timedelta(days=1)  # end of prev month
for _ in range(3):
    m_start = cursor.replace(day=1)
    m_end = m_start + pd.offsets.MonthEnd(0)
    months_to_score.append((m_start, m_end))
    cursor = m_start - pd.Timedelta(days=1)  # go to prev month

months_to_score.reverse()  # chronological order

for m_start, m_end in months_to_score:
    as_of = m_start + pd.Timedelta(days=14)  # day 15
    print(f"\n{'═' * 65}")
    print(f"SCORING: {as_of.date()}")
    print(f"{'═' * 65}")

    score = score_pipeline(
        df, as_of,
        model=best_model, transition_tables=tables,
        feature_columns=feature_cols, encoders=encoders, medians=medians,
    )

    # Get actual
    actual = df[
        df["Funded D"].notna()
        & (df["Funded D"] >= m_start)
        & (df["Funded D"] <= m_end)
    ]["LoanAmount"].sum()

    print_dashboard(score, actual=actual)


# =============================================================================
# 3. MODELS — full comparison, ALL feature importances, calibration
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 3. MODEL COMPARISON — ALL MODELS, ALL FEATURES, CALIBRATION")
print(f"{'#' * 80}")

# Full model comparison
results = bundle["results"]
print(f"\n{'═' * 65}")
print("MODEL COMPARISON TABLE")
print(f"{'═' * 65}")
print(f"  {'Model':<25s} {'Brier':>10s} {'AUC':>10s} {'LogLoss':>10s}")
print(f"  {'─' * 58}")
for _, row in results.iterrows():
    marker = " <<<" if row["model"] == best_name else ""
    print(f"  {row['model']:<25s} {row['brier_score']:>10.6f} "
          f"{row['auc']:>10.6f} {row['log_loss']:>10.6f}{marker}")

print(f"\n  Selected: {best_name}")
print(f"  Train: {len(bundle['X_train']):,} rows (2024), "
      f"Test: {len(X_test):,} rows (2025)")
print(f"  Train pos rate: {bundle['y_train'].mean():.1%}, "
      f"Test pos rate: {y_test.mean():.1%}")

# COMPLETE feature importance for ALL models
for model_name, model in all_models.items():
    fi = feature_importance(model, feature_cols)
    if len(fi) == 0:
        continue
    print(f"\n{'═' * 65}")
    print(f"FEATURE IMPORTANCE — {model_name} (ALL {len(fi)} features)")
    print(f"{'═' * 65}")
    print(f"  {'Rank':>4s} {'Feature':<40s} {'Importance':>10s} {'Cumul%':>8s}")
    print(f"  {'─' * 65}")
    cumul = 0.0
    for i, (_, row) in enumerate(fi.iterrows()):
        cumul += row["importance"]
        print(f"  {i+1:>4d} {row['feature']:<40s} {row['importance']:>10.6f} {cumul:>7.1%}")

# Calibration assessment — binned predicted prob vs observed rate
print(f"\n{'═' * 65}")
print("CALIBRATION ASSESSMENT — Predicted vs Observed by Decile")
print(f"{'═' * 65}")

for model_name, model in all_models.items():
    probs = _predict_proba(model, X_test)

    print(f"\n  {model_name}:")
    print(f"  {'Bin':>15s} {'MeanPred':>10s} {'ObsRate':>10s} {'N':>7s} {'Diff':>10s}")
    print(f"  {'─' * 55}")

    # Use 10 uniform bins
    fraction_pos, mean_predicted = calibration_curve(
        y_test, probs, n_bins=10, strategy="uniform"
    )
    bin_edges = np.linspace(0, 1, 11)
    for i in range(len(mean_predicted)):
        lo = bin_edges[i]
        hi = bin_edges[i + 1]
        mask = (probs >= lo) & (probs < hi)
        n_in_bin = mask.sum()
        if n_in_bin == 0:
            continue
        obs_rate = y_test[mask].mean()
        pred_rate = probs[mask].mean()
        diff = obs_rate - pred_rate
        label = f"[{lo:.1f}, {hi:.1f})"
        print(f"  {label:>15s} {pred_rate:>10.4f} {obs_rate:>10.4f} {n_in_bin:>7,d} {diff:>+10.4f}")

    # Also show custom bins for the probability ranges we actually see
    print(f"\n  Practical bins (where data lives):")
    custom_bins = [0.0, 0.01, 0.05, 0.10, 0.20, 0.50, 0.80, 0.95, 1.01]
    print(f"  {'Bin':>15s} {'MeanPred':>10s} {'ObsRate':>10s} {'N':>7s} {'Diff':>10s}")
    print(f"  {'─' * 55}")
    for j in range(len(custom_bins) - 1):
        lo, hi = custom_bins[j], custom_bins[j + 1]
        mask = (probs >= lo) & (probs < hi)
        n_in_bin = mask.sum()
        if n_in_bin == 0:
            continue
        obs_rate = y_test[mask].mean()
        pred_rate = probs[mask].mean()
        diff = obs_rate - pred_rate
        label = f"[{lo:.2f}, {hi:.2f})"
        print(f"  {label:>15s} {pred_rate:>10.4f} {obs_rate:>10.4f} {n_in_bin:>7,d} {diff:>+10.4f}")


# =============================================================================
# 4. EDA — full correlations, all categorical spreads, time-at-stage
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 4. EDA — FULL CORRELATIONS, ALL CATEGORICAL SPREADS, TIME-AT-STAGE")
print(f"{'#' * 80}")

# 4a. Numeric correlations
print(f"\n{'═' * 70}")
print("NUMERIC FEATURE CORRELATIONS WITH DidFund")
print(f"{'═' * 70}")
corr_df = numeric_correlations(df)
print(corr_df.to_string(index=False))

# 4b. ALL categorical spreads with full detail
print(f"\n{'═' * 70}")
print("CATEGORICAL FEATURE SPREADS — FULL DETAIL")
print(f"{'═' * 70}")
spread_df, detail = categorical_spreads(df)
print("\nSummary:")
print(spread_df.to_string(index=False))

for feat, grp in detail.items():
    print(f"\n{'─' * 60}")
    print(f"  {feat} — Fund rate by value:")
    print(f"{'─' * 60}")
    grp_show = grp.copy()
    grp_show["FundRate"] = (grp_show["FundRate"] * 100).round(2)
    for val, row in grp_show.iterrows():
        marker = "" if row["Count"] >= config.MIN_CELL_SIZE else " (thin)"
        print(f"    {str(val):<35s} {int(row['Count']):>6d} loans  "
              f"{row['FundRate']:>6.1f}%{marker}")

# 4c. Time-at-stage (full stats, not just median)
print(f"\n{'═' * 70}")
print("TIME-AT-STAGE DISTRIBUTIONS")
print(f"{'═' * 70}")
time_df = time_at_stage_analysis(df)
print(f"\n  {'Duration':<25s} {'Outcome':<10s} {'Median':>8s} {'Mean':>8s} {'N':>7s}")
print(f"  {'─' * 60}")
for _, row in time_df.iterrows():
    print(f"  {row['Duration']:<25s} {row['Outcome']:<10s} "
          f"{row['Median']:>8.0f} {row['Mean']:>8.1f} {row['N']:>7,d}")


# =============================================================================
# 5. TRANSITION TABLES — full stratified dump
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 5. TRANSITION TABLES — FULL DUMP")
print(f"{'#' * 80}")

# 5a. Unstratified (both eventually-fund and month-end)
print(f"\n{'═' * 70}")
print("UNSTRATIFIED TABLE — P(fund | stage)")
print(f"{'═' * 70}")
unstrat = tables["unstratified"]
me_unstrat = tables["me_unstratified"]
combined = unstrat[["count", "funded", "p_fund"]].copy()
combined["p_fund_me"] = me_unstrat["p_fund"]
combined = combined.rename(columns={"p_fund": "P(ever)", "p_fund_me": "P(month_end)"})
print(combined.to_string(float_format=lambda x: f"{x:.4f}"))

# 5b. Full stratified tables (month-end)
print(f"\n{'═' * 70}")
print("STRATIFIED TABLE — P(fund by month end | stage x product x purpose)")
print(f"{'═' * 70}")
me_strat = tables["me_stratified"]
print(f"\n  Total cells: {len(me_strat)}")
print(f"  Cells with count >= {config.MIN_CELL_SIZE}: "
      f"{(me_strat['count'] >= config.MIN_CELL_SIZE).sum()}")

# Print all cells with enough data
print(f"\n  {'Stage':<14s} {'Product':<18s} {'Purpose':<22s} "
      f"{'N':>5s} {'Funded':>6s} {'P_raw':>7s} {'P_smooth':>8s}")
print(f"  {'─' * 85}")
for (stage, prod, purp), row in me_strat.sort_values("count", ascending=False).iterrows():
    raw = row.get("p_fund_raw", row["p_fund"])
    smooth = row["p_fund"]
    marker = "" if row["count"] >= config.MIN_CELL_SIZE else " *"
    print(f"  {stage:<14s} {str(prod):<18s} {str(purp):<22s} "
          f"{int(row['count']):>5d} {int(row['funded']):>6d} "
          f"{raw:>6.1%} {smooth:>7.1%}{marker}")
print(f"\n  (* = smoothed to stage-only because count < {config.MIN_CELL_SIZE})")

# 5c. By product type (month-end)
print(f"\n{'═' * 70}")
print("BY PRODUCT TYPE — P(fund by month end | stage x product)")
print(f"{'═' * 70}")
me_by_prod_unstrat = me_unstrat  # for baselines
# Rebuild by-product for month-end from observations
me_obs = obs.copy()
by_prod_me = (
    me_obs.groupby(["stage", "product_type"])
    .agg(count=("fund_by_end", "count"), funded=("fund_by_end", "sum"))
)
by_prod_me["p_fund"] = by_prod_me["funded"] / by_prod_me["count"]

for stage in ["Approved", "Submitted", "Underwriting", "CTC", "Cond Review"]:
    baseline = me_unstrat.loc[stage, "p_fund"] if stage in me_unstrat.index else 0
    print(f"\n  Stage: {stage} (baseline P(month_end) = {baseline:.1%})")
    print(f"  {'Product':<25s} {'N':>6s} {'Funded':>6s} {'P(fund)':>8s} {'vs base':>8s}")
    print(f"  {'─' * 55}")
    if stage in by_prod_me.index.get_level_values(0):
        sub = by_prod_me.loc[stage].sort_values("count", ascending=False)
        for prod, row in sub.iterrows():
            if row["count"] < 5:
                continue
            delta = row["p_fund"] - baseline
            sign = "+" if delta >= 0 else ""
            thin = " *" if row["count"] < config.MIN_CELL_SIZE else ""
            print(f"  {str(prod):<25s} {int(row['count']):>6d} {int(row['funded']):>6d} "
                  f"{row['p_fund']:>7.1%} {sign}{delta:>7.1%}{thin}")


# =============================================================================
# 6. DATASET STATS & ANOMALIES
# =============================================================================

print(f"\n\n{'#' * 80}")
print("# 6. DATASET STATISTICS & ANOMALIES")
print(f"{'#' * 80}")

print(f"\n{'═' * 70}")
print("MONTHLY FUNDING VOLUME")
print(f"{'═' * 70}")
funded = df[df["Funded D"].notna()].copy()
funded["_ym"] = funded["Funded D"].dt.to_period("M")
monthly = funded.groupby("_ym").agg(
    loans=("LoanAmount", "count"),
    dollars=("LoanAmount", "sum")
).sort_index()
print(f"\n  {'Month':<10s} {'Loans':>7s} {'Dollars':>14s} {'Avg Loan':>12s}")
print(f"  {'─' * 50}")
for period, row in monthly.iterrows():
    avg = row["dollars"] / row["loans"] if row["loans"] > 0 else 0
    print(f"  {str(period):<10s} {int(row['loans']):>7,d} ${row['dollars']:>13,.0f} ${avg:>11,.0f}")

print(f"\n{'═' * 70}")
print("TRAINING SET CLASS BALANCE BY SNAPSHOT")
print(f"{'═' * 70}")
for (y, m, d), grp in training.groupby(["snapshot_year", "snapshot_month", "snapshot_day"]):
    pos_rate = grp["fund_by_end"].mean()
    print(f"  {y}-{m:02d} day {d:>2d}: {len(grp):>5,d} rows  pos rate {pos_rate:>5.1%}")

# Missing data in key features
print(f"\n{'═' * 70}")
print("MISSING DATA IN KEY FEATURES (active loans)")
print(f"{'═' * 70}")
key_cols = ["DecisionCreditScore", "LTV", "CLTV", "NoteRate",
            "Lock Period (days)", "LoanAmount", "Branch Channel",
            "Product Type", "Loan Purpose", "Occupancy Type"]
active_all = df[df["Outcome"] != "Active"]  # completed loans
for col in key_cols:
    if col in active_all.columns:
        n_miss = active_all[col].isna().sum()
        pct = n_miss / len(active_all) * 100
        print(f"  {col:<30s} {n_miss:>6,d} missing ({pct:>5.1f}%)")


# =============================================================================
# DONE — write findings file
# =============================================================================

sys.stdout = sys.__stdout__  # restore stdout

findings = capture.getvalue()

findings_path = config.OUTPUTS_PATH / "results" / "full_findings.md"
findings_path.parent.mkdir(parents=True, exist_ok=True)

with open(findings_path, "w") as f:
    f.write("# FlexPoint Loan Funding Forecasting — Full Findings\n\n")
    f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write("```\n")
    f.write(findings)
    f.write("```\n")

print(f"\nAll output captured → {findings_path}")
print(f"Backtest CSV → {csv_path}")
print(f"Figures → {config.OUTPUTS_PATH / 'figures' / ''}")
print("Done.")
