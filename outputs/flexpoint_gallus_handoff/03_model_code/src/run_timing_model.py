"""
FlexPoint Step 4 — Timing Model (Funding Week Prediction)

Trains and backtests two approaches for predicting which week of the month
each loan will fund:
  1. Median-based: historical stage-to-funding duration lookup
  2. GBM regression: trained model predicting days-to-fund

Outputs:
  - outputs/results/timing_model_results.csv
  - outputs/results/stage_to_funding_durations.csv
"""
import sys
import time
from pathlib import Path

# ─── Module swap: v3 features ─────────────────────────────────────────────────
src_dir = str(Path(__file__).resolve().parent)
project_root = str(Path(__file__).resolve().parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import feature_engineering_v3  # noqa: E402
sys.modules["feature_engineering"] = feature_engineering_v3

import pandas as pd  # noqa: E402
import numpy as np   # noqa: E402
import matplotlib     # noqa: E402
matplotlib.use("Agg")

import config  # noqa: E402
from data_prep import load_and_clean  # noqa: E402
from transition_tables import build_transition_tables  # noqa: E402
from feature_engineering_v3 import (  # noqa: E402
    build_training_set, encode_categoricals, fill_missing_numeric,
    get_feature_columns,
)
from models import (  # noqa: E402
    train_and_select, _predict_proba,
)
from pipeline_snapshot import build_snapshot  # noqa: E402
from timing_model import (  # noqa: E402
    build_duration_table, get_median_days_to_fund,
    build_duration_distributions,
    build_timing_training_set, train_timing_model, evaluate_timing_model,
    predict_funding_week_median, predict_funding_week_gbm,
    predict_funding_week_distributional,
    build_weekly_projection, build_weekly_projection_distributional,
    build_weekly_projection_historical,
    compute_actual_weekly,
    WEEK_LABELS, day_to_week,
)

RESULTS_DIR = config.OUTPUTS_PATH / "results"
FIGURES_DIR = config.OUTPUTS_PATH / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

t0 = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SETUP
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("STEP 4 — TIMING MODEL (FUNDING WEEK PREDICTION)")
print("=" * 80)

df = load_and_clean()
print(f"\nDataset: {len(df):,} rows")

print("\nBuilding transition tables...")
tables = build_transition_tables(df)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. STAGE-TO-FUNDING DURATION TABLE (Part A.1)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("STAGE-TO-FUNDING DURATION TABLE")
print(f"{'=' * 80}")

duration_table = build_duration_table(df)
dur_path = RESULTS_DIR / "stage_to_funding_durations.csv"
duration_table.to_csv(dur_path, index=False)
print(f"  Saved → {dur_path}")

print(f"\n  {'Stage':<20} {'N':>6} {'p25':>6} {'Median':>8} {'p75':>6} "
      f"{'p90':>6} {'Mean':>8}")
print(f"  {'-' * 62}")
for _, r in duration_table.iterrows():
    print(f"  {r['stage']:<20} {int(r['n']):>6} {r['p25']:>6.0f} "
          f"{r['median']:>8.0f} {r['p75']:>6.0f} {r['p90']:>6.0f} "
          f"{r['mean']:>8.1f}")

median_lookup = get_median_days_to_fund(duration_table)
duration_dists = build_duration_distributions(df)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TRAIN CLASSIFIER (for P(fund)) + TIMING REGRESSOR
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("TRAINING MODELS")
print(f"{'=' * 80}")

# ── Classifier (same as v3 fixed-split) ──────────────────────────────────
print("\n  Building classifier training set...")
cls_training = build_training_set(df, tables)
enc_cls, cls_encoders = encode_categoricals(cls_training, fit=True)
enc_cls, cls_medians = fill_missing_numeric(enc_cls, fit=True)
cls_feat_cols = get_feature_columns(cls_encoders)

print("  Training classifier...")
cls_bundle = train_and_select(enc_cls, cls_feat_cols)
cls_model = cls_bundle["best_model"]
print(f"  Classifier: {cls_bundle['best_model_name']}")

# ── Timing regressor ─────────────────────────────────────────────────────
print("\n  Building timing training set (funded loans only)...")
timing_training = build_timing_training_set(df, tables)
print(f"  Timing training rows: {len(timing_training):,}")
print(f"  Target (days_to_fund) — mean: {timing_training['days_to_fund'].mean():.1f}, "
      f"median: {timing_training['days_to_fund'].median():.0f}")

# Encode using same encoders as classifier
enc_timing, _ = encode_categoricals(timing_training, encoders=cls_encoders,
                                      fit=False)
enc_timing, _ = fill_missing_numeric(enc_timing, medians=cls_medians,
                                       fit=False)

# Align columns
for col in cls_feat_cols:
    if col not in enc_timing.columns:
        enc_timing[col] = 0

# Temporal split: 2024 train / 2025 test
train_mask = enc_timing["snapshot_year"] == 2024
test_mask = enc_timing["snapshot_year"] == 2025

X_time_train = enc_timing.loc[train_mask, cls_feat_cols].values.astype(np.float32)
y_time_train = enc_timing.loc[train_mask, "days_to_fund"].values.astype(float)
X_time_test = enc_timing.loc[test_mask, cls_feat_cols].values.astype(np.float32)
y_time_test = enc_timing.loc[test_mask, "days_to_fund"].values.astype(float)

print(f"\n  Timing regressor split:")
print(f"    Train: {len(X_time_train):,}  Test: {len(X_time_test):,}")

print("  Training GBM regressor...")
timing_gbm = train_timing_model(X_time_train, y_time_train)

# Evaluate
train_metrics = evaluate_timing_model(timing_gbm, X_time_train, y_time_train)
test_metrics = evaluate_timing_model(timing_gbm, X_time_test, y_time_test)
print(f"\n  Timing Regressor Metrics:")
print(f"    {'':20s} {'Train':>10s} {'Test':>10s}")
print(f"    {'MAE (days)':<20s} {train_metrics['mae']:>10.1f} {test_metrics['mae']:>10.1f}")
print(f"    {'Median AE (days)':<20s} {train_metrics['median_ae']:>10.1f} {test_metrics['median_ae']:>10.1f}")
print(f"    {'RMSE (days)':<20s} {train_metrics['rmse']:>10.1f} {test_metrics['rmse']:>10.1f}")

# Feature importance for timing model
from models import feature_importance  # noqa: E402
timing_fi = feature_importance(timing_gbm, cls_feat_cols)
print(f"\n  Timing Model — Top 10 Features:")
for i, (_, r) in enumerate(timing_fi.head(10).iterrows()):
    print(f"    {i+1:>2d}. {r['feature']:<35s} {r['importance']:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ACTUAL WEEKLY FUNDING PATTERNS (Part C)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("ACTUAL WEEKLY FUNDING PATTERNS")
print(f"{'=' * 80}")

funded = df[df["Funded D"].notna()].copy()
funded["fund_week"] = funded["Funded D"].dt.day.apply(day_to_week)
funded["fund_ym"] = funded["Funded D"].dt.to_period("M")

overall = funded.groupby("fund_week")["LoanAmount"].sum()
overall_pct = overall / overall.sum() * 100
print(f"\n  Overall $ distribution:")
for wk in WEEK_LABELS:
    print(f"    {wk}: {overall_pct.get(wk, 0):.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WEEKLY BACKTEST (Parts B + C)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("WEEKLY PROJECTION BACKTEST")
print(f"{'=' * 80}")

TIMING_SNAPSHOT_DAYS = [0, 8, 15]  # Day 0 (BOM), Day 8 (W1 known), Day 15 (W1-2 known)

weekly_rows = []
total_snaps = len(config.BACKTEST_MONTHS) * len(TIMING_SNAPSHOT_DAYS)
done = 0

for year, month in config.BACKTEST_MONTHS:
    month_start = pd.Timestamp(year, month, 1)
    month_end = month_start + pd.offsets.MonthEnd(0)

    # Actual weekly funding
    actual_weekly = compute_actual_weekly(df, month_start, month_end)
    actual_total = sum(actual_weekly.values())
    if actual_total == 0:
        done += len(TIMING_SNAPSHOT_DAYS)
        continue

    for day in TIMING_SNAPSHOT_DAYS:
        done += 1
        try:
            if day == 0:
                as_of = pd.Timestamp(year, month, 1) - pd.Timedelta(days=1)
            else:
                as_of = pd.Timestamp(year, month, day)
        except ValueError:
            continue

        # ── Build snapshot ────────────────────────────────────────────
        result = build_snapshot(
            df, as_of, month_end=month_end,
            month_start=month_start if day == 0 else None,
            transition_tables=tables,
            model=cls_model, feature_columns=cls_feat_cols,
            encoders=cls_encoders, medians=cls_medians,
        )
        active = result["active_pipeline"]
        already_funded = result["already_funded"]

        if len(active) == 0:
            continue

        # Get ML probabilities
        ml_probs = active["ml_probability"].values if "ml_probability" in active.columns \
            else np.zeros(len(active))

        # ── Approach 1: Median-based week prediction ──────────────────
        median_weeks = predict_funding_week_median(
            active, as_of, month_end, median_lookup,
        )

        median_proj = build_weekly_projection(
            active, median_weeks, ml_probs,
            already_funded, month_start, month_end,
        )

        # ── Approach 2: GBM regression week prediction ────────────────
        gbm_weeks = predict_funding_week_gbm(
            active, as_of, month_end,
            timing_gbm, cls_feat_cols, cls_encoders, cls_medians,
            tables,
        )

        gbm_proj = build_weekly_projection(
            active, gbm_weeks, ml_probs,
            already_funded, month_start, month_end,
        )

        # ── Approach 3: Distributional week prediction ────────────────
        dist_week_probs = predict_funding_week_distributional(
            active, as_of, month_end, duration_dists,
        )

        dist_proj = build_weekly_projection_distributional(
            active, dist_week_probs, ml_probs,
            already_funded, month_start, month_end,
        )

        # ── Approach 4: Historical distribution ─────────────────────
        # Use the ML model's total monthly projection (sum of P(fund) × Amount)
        # and distribute across weeks using the known historical split.
        s = result["summary"]
        already_dollars = s["already_funded_dollars"]
        ml_total = s.get("ml_projected_total", already_dollars)

        hist_proj = build_weekly_projection_historical(
            ml_total, already_funded, month_start, month_end,
        )

        # ── For mid-month snapshots, weeks already past are actuals ───
        # Day 8: Week 1 is known.  Day 15: Weeks 1-2 are known.
        known_weeks = set()
        if day >= 8:
            known_weeks.add("Week 1")
        if day >= 15:
            known_weeks.add("Week 2")

        for approach, proj in [("Median", median_proj), ("GBM", gbm_proj),
                                ("Distributional", dist_proj),
                                ("Historical", hist_proj)]:
            for wk in WEEK_LABELS:
                actual_wk = actual_weekly[wk]

                # For known weeks, use actuals instead of projection
                if wk in known_weeks:
                    proj_wk = actual_wk  # perfect knowledge
                else:
                    proj_wk = proj[wk]

                error = ((proj_wk - actual_wk) / actual_wk * 100
                         if actual_wk > 0 else 0)

                weekly_rows.append({
                    "year": year,
                    "month": month,
                    "snapshot_day": day,
                    "approach": approach,
                    "week": wk,
                    "projected": proj_wk,
                    "actual": actual_wk,
                    "error_pct": error,
                    "is_known": wk in known_weeks,
                })

        if done % 20 == 0 or done == total_snaps:
            print(f"    {done}/{total_snaps} snapshots...", flush=True)

weekly_results = pd.DataFrame(weekly_rows)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SAVE RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

csv_path = RESULTS_DIR / "timing_model_results.csv"
weekly_results.to_csv(csv_path, index=False)
print(f"\n  Saved weekly results → {csv_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

ALL_APPROACHES = ["Median", "GBM", "Distributional", "Historical"]

print(f"\n{'=' * 80}")
print("WEEKLY PROJECTION ACCURACY")
print(f"{'=' * 80}")

# ── Weekly MAPE by approach × snapshot day (exclude known weeks) ──────────
print(f"\n  Weekly MAPE (unknown weeks only):")
print(f"  {'Approach':<16s}", end="")
for day in TIMING_SNAPSHOT_DAYS:
    print(f"  Day {day:>2d}", end="")
print(f"  {'Overall':>8s}")
print(f"  {'─' * 56}")

for approach in ALL_APPROACHES:
    sub = weekly_results[
        (weekly_results["approach"] == approach)
        & (~weekly_results["is_known"])
    ]
    print(f"  {approach:<16s}", end="")
    for day in TIMING_SNAPSHOT_DAYS:
        day_sub = sub[sub["snapshot_day"] == day]
        mape = day_sub["error_pct"].abs().mean()
        print(f"  {mape:>5.1f}%", end="")
    overall = sub["error_pct"].abs().mean()
    print(f"  {overall:>6.1f}%")

# ── MAPE by week ─────────────────────────────────────────────────────────
print(f"\n  Weekly MAPE by Week (Day 0 snapshot, all weeks projected):")
print(f"  {'Approach':<16s}", end="")
for wk in WEEK_LABELS:
    print(f"  {wk:>8s}", end="")
print()
print(f"  {'─' * 54}")

for approach in ALL_APPROACHES:
    sub = weekly_results[
        (weekly_results["approach"] == approach)
        & (weekly_results["snapshot_day"] == 0)
    ]
    print(f"  {approach:<16s}", end="")
    for wk in WEEK_LABELS:
        wk_sub = sub[sub["week"] == wk]
        mape = wk_sub["error_pct"].abs().mean() if len(wk_sub) > 0 else 0
        print(f"  {mape:>7.1f}%", end="")
    print()

# ── Distribution accuracy ────────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  DISTRIBUTION ACCURACY — Does the model predict the right shape?")
print(f"{'─' * 80}")

day0 = weekly_results[weekly_results["snapshot_day"] == 0]

# Average actual %
actual_by_wk = day0[day0["approach"] == "Median"].groupby("week")["actual"].sum()
actual_pct = actual_by_wk / actual_by_wk.sum() * 100

print(f"\n  Day-0 snapshot: Predicted vs Actual distribution (total across months)")
print(f"  {'':16s}", end="")
for wk in WEEK_LABELS:
    print(f"  {wk:>8s}", end="")
print()
print(f"  {'─' * 54}")

print(f"  {'Actual':<16s}", end="")
for wk in WEEK_LABELS:
    print(f"  {actual_pct.get(wk, 0):>7.1f}%", end="")
print()

for approach in ALL_APPROACHES:
    proj_by_wk = day0[day0["approach"] == approach].groupby("week")["projected"].sum()
    proj_total = proj_by_wk.sum()
    if proj_total > 0:
        proj_pct = proj_by_wk / proj_total * 100
    else:
        proj_pct = proj_by_wk * 0
    print(f"  {approach:<16s}", end="")
    for wk in WEEK_LABELS:
        print(f"  {proj_pct.get(wk, 0):>7.1f}%", end="")
    print()

# ── Biggest-week accuracy ────────────────────────────────────────────────
print(f"\n  Biggest-week accuracy (Day 0): Correctly identifies highest-$ week?")
correct = {a: 0 for a in ALL_APPROACHES}
total_months = 0

for (yr, mo), grp in day0.groupby(["year", "month"]):
    actual_grp = grp[grp["approach"] == "Median"][["week", "actual"]].set_index("week")
    if len(actual_grp) == 0 or actual_grp["actual"].isna().all():
        continue
    actual_max = actual_grp["actual"].idxmax()
    total_months += 1

    for approach in ALL_APPROACHES:
        a_grp = grp[grp["approach"] == approach][["week", "projected"]].set_index("week")
        if len(a_grp) == 0 or a_grp["projected"].isna().all() or a_grp["projected"].sum() == 0:
            continue
        try:
            pred_max = a_grp["projected"].idxmax()
            if pred_max == actual_max:
                correct[approach] += 1
        except ValueError:
            continue

for approach in ALL_APPROACHES:
    pct = correct[approach] / max(total_months, 1) * 100
    print(f"    {approach:<16s}: {correct[approach]}/{total_months} months "
          f"({pct:.0f}%)")


# ── Month-by-month: projected vs actual for each week (Distributional) ───
print(f"\n{'=' * 80}")
print("  DAY-0 MONTH-BY-MONTH WEEKLY PROJECTIONS (Historical approach)")
print(f"{'=' * 80}")

print(f"  {'Month':<8s} │", end="")
for wk in WEEK_LABELS:
    print(f" {'Proj':>9s} {'Act':>9s} │", end="")
print()
print(f"  {'─' * 90}")

months_sorted = sorted(
    day0[["year", "month"]].drop_duplicates().values.tolist()
)
for yr, mo in months_sorted:
    mask = (day0["year"] == yr) & (day0["month"] == mo) & \
           (day0["approach"] == "Historical")
    grp = day0[mask].set_index("week")
    label = f"{yr}-{mo:02d}"
    print(f"  {label:<8s} │", end="")
    for wk in WEEK_LABELS:
        if wk in grp.index:
            proj = grp.loc[wk, "projected"]
            act = grp.loc[wk, "actual"]
            print(f" ${proj/1e6:>7.1f}M ${act/1e6:>7.1f}M │", end="")
        else:
            print(f" {'n/a':>9s} {'n/a':>9s} │", end="")
    print()


# ── Directional bias ─────────────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  DIRECTIONAL BIAS — Does the model over/under-project by week?")
print(f"{'─' * 80}")

for approach in ALL_APPROACHES:
    sub = weekly_results[
        (weekly_results["approach"] == approach)
        & (weekly_results["snapshot_day"] == 0)
    ]
    print(f"\n  {approach}:")
    for wk in WEEK_LABELS:
        wk_sub = sub[sub["week"] == wk]
        mean_err = wk_sub["error_pct"].mean()
        print(f"    {wk}: mean error {mean_err:>+.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

elapsed = time.time() - t0
print(f"\n{'=' * 80}")
print(f"TIMING MODEL COMPLETE — {elapsed:.0f}s elapsed")
print(f"{'=' * 80}")

# Key takeaways
print(f"""
KEY FINDINGS:
  1. Funding is heavily back-loaded: Week 4 gets ~{actual_pct.get('Week 4',0):.0f}% of monthly dollars
  2. Stage-to-funding durations are predictable:
     - CTC → Funded: median {int(duration_table[duration_table['stage']=='CTC']['median'].iloc[0])} days
     - Approved → Funded: median {int(duration_table[duration_table['stage']=='Approved']['median'].iloc[0])} days
     - Opened → Funded: median {int(duration_table[duration_table['stage']=='Opened']['median'].iloc[0])} days
  3. Timing regressor MAE: {test_metrics['mae']:.1f} days (test set)

OUTPUT FILES:
  - {csv_path}
  - {dur_path}
""")
