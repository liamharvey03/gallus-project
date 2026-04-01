"""
FlexPoint v3 Model Analysis — Interaction Features

Changes from v2:
  1. 12 new interaction features (lock×stage, lock×time, extension proxy, velocity)
  2. Rolling 12-month training is the primary mode (per client direction)
  3. Fixed-split backtest also run for comparison

Does NOT modify any v2 files.  Swaps sys.modules["feature_engineering"] so that
backtest.py and pipeline_snapshot.py pick up v3 features transparently.

Outputs:
  - outputs/results/backtest_results_v3.csv
  - outputs/results/feature_importance_v3.csv
"""
import sys
import time
from pathlib import Path

# ─── Module swap: make v3 features available as "feature_engineering" ────────
# This must happen BEFORE importing backtest / pipeline_snapshot, which do
# `from feature_engineering import ...` inside their functions.

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
    get_feature_columns, NUMERIC_FEATURES, V2_NUMERIC_FEATURES,
    V3_INTERACTION_FEATURES, CATEGORICAL_FEATURES,
)
from models import (  # noqa: E402
    train_and_select, feature_importance, evaluate_models,
    _predict_proba, train_models,
)
from backtest import (  # noqa: E402
    run_backtest, print_backtest_summary,
)

RESULTS_DIR = config.OUTPUTS_PATH / "results"
FIGURES_DIR = config.OUTPUTS_PATH / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def _mape(df_sub):
    """Mean absolute percentage error."""
    return df_sub["error_pct"].abs().mean()


def _months_within_10(df_sub):
    """Count of months where |error| <= 10%."""
    return (df_sub["error_pct"].abs() <= 10).sum()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SETUP — Load data, build tables, build training set
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("V3 MODEL ANALYSIS — INTERACTION FEATURES")
print("=" * 80)

df = load_and_clean()
print(f"\nDataset: {len(df):,} rows x {len(df.columns)} columns")

print("\nBuilding transition tables...")
tables = build_transition_tables(df)

print("Building v3 training set (v2 + 12 interaction features)...")
t0 = time.time()
training = build_training_set(df, tables)
print(f"  Training set: {training.shape[0]:,} rows x {training.shape[1]} cols"
      f"  ({time.time() - t0:.1f}s)")
print(f"  Positive rate: {training['fund_by_end'].mean():.1%}")

# Encode and prepare
encoded, encoders = encode_categoricals(training, fit=True)
encoded, medians = fill_missing_numeric(encoded, fit=True)
feature_cols = get_feature_columns(encoders)
print(f"  Features after encoding: {len(feature_cols)}")
print(f"    v2 numeric: {len(V2_NUMERIC_FEATURES)}")
print(f"    v3 interaction: {len(V3_INTERACTION_FEATURES)}")
print(f"    categorical (encoded): {len(feature_cols) - len(NUMERIC_FEATURES)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FIXED-SPLIT MODEL TRAINING (2024 train / 2025 test) — for metrics
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("V3 MODEL COMPARISON (Fixed: 2024 train / 2025 test)")
print(f"{'═' * 80}")

bundle = train_and_select(encoded, feature_cols)
best_model = bundle["best_model"]
best_name = bundle["best_model_name"]

results_table = bundle["results"]
print(f"\n  {'Model':<25s} {'Brier':>10s} {'AUC':>10s} {'LogLoss':>10s}")
print(f"  {'─' * 58}")
for _, row in results_table.iterrows():
    marker = " <<<" if row["model"] == best_name else ""
    print(f"  {row['model']:<25s} {row['brier_score']:>10.6f} "
          f"{row['auc']:>10.6f} {row['log_loss']:>10.6f}{marker}")
print(f"\n  Selected: {best_name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FEATURE IMPORTANCE (from fixed-split best model)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print(f"V3 FEATURE IMPORTANCE — {best_name}")
print(f"{'═' * 80}")

fi = feature_importance(best_model, feature_cols)
fi.to_csv(RESULTS_DIR / "feature_importance_v3.csv", index=False)

print(f"\n  {'Rank':>4s} {'Feature':<42s} {'Importance':>10s} {'Cumul%':>8s} {'New?':>5s}")
print(f"  {'─' * 72}")
cumul = 0.0
for i, (_, row) in enumerate(fi.head(30).iterrows()):
    cumul += row["importance"]
    is_new = "v3" if row["feature"] in V3_INTERACTION_FEATURES else ""
    print(f"  {i+1:>4d} {row['feature']:<42s} "
          f"{row['importance']:>10.6f} {cumul:>7.1%} {is_new:>5s}")

# Show which v3 features made top 15
top15_feats = set(fi.head(15)["feature"].tolist())
v3_in_top15 = [f for f in V3_INTERACTION_FEATURES if f in top15_feats]
print(f"\n  v3 features in top 15: {len(v3_in_top15)}")
for f in v3_in_top15:
    rank = fi[fi["feature"] == f].index[0]
    imp = fi.loc[rank, "importance"]
    print(f"    #{fi.index.get_loc(rank)+1}: {f} ({imp:.6f})")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ROLLING 12-MONTH BACKTEST (primary mode — what we're shipping)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("RUNNING ROLLING 12-MONTH BACKTEST (v3 features)")
print(f"{'═' * 80}")
print(f"  Months: {len(config.BACKTEST_MONTHS)}  "
      f"Snapshot days: {config.SNAPSHOT_DAYS}  "
      f"Total: {len(config.BACKTEST_MONTHS) * len(config.SNAPSHOT_DAYS)}")
print(f"  Each month retrains on prior 12 months...")

t0 = time.time()
bt_rolling = run_backtest(
    df, tables, training_mode="rolling",
)
bt_rolling["training_mode"] = "rolling"
elapsed_rolling = time.time() - t0
print(f"  Done in {elapsed_rolling:.0f}s")

print_backtest_summary(bt_rolling)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FIXED BACKTEST (for comparison)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("RUNNING FIXED BACKTEST (v3 features, 2024 training)")
print(f"{'═' * 80}")

t0 = time.time()
bt_fixed = run_backtest(
    df, tables, best_model, feature_cols, encoders, medians,
    training_mode="fixed",
)
bt_fixed["training_mode"] = "fixed"
print(f"  Done in {time.time() - t0:.0f}s")

print_backtest_summary(bt_fixed)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SAVE RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

bt_all = pd.concat([bt_fixed, bt_rolling], ignore_index=True)
bt_all.to_csv(RESULTS_DIR / "backtest_results_v3.csv", index=False)
print(f"\n  Saved → {RESULTS_DIR / 'backtest_results_v3.csv'}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. V2 vs V3 COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("V2 vs V3 COMPARISON")
print(f"{'═' * 80}")

# Load v2 results
v2_path = RESULTS_DIR / "backtest_results_v2.csv"
if v2_path.exists():
    v2 = pd.read_csv(v2_path)
else:
    v2 = pd.DataFrame()
    print("  WARNING: v2 backtest_results_v2.csv not found")

if len(v2) > 0:
    v2_rolling_ml = v2[(v2["method"] == "ML") & (v2["training_mode"] == "rolling")]
    v2_fixed_ml = v2[(v2["method"] == "ML") & (v2["training_mode"] == "fixed")]
    v3_rolling_ml = bt_rolling[bt_rolling["method"] == "ML"]
    v3_fixed_ml = bt_fixed[bt_fixed["method"] == "ML"]

    # ── MAPE by snapshot day ──────────────────────────────────────────
    print(f"\n  ML MAPE by Snapshot Day:")
    print(f"  {'Day':>5s} {'v2 Roll':>10s} {'v3 Roll':>10s} {'Delta':>8s}  │ "
          f"{'v2 Fix':>10s} {'v3 Fix':>10s} {'Delta':>8s}")
    print(f"  {'─' * 72}")

    for day in config.SNAPSHOT_DAYS:
        v2r = v2_rolling_ml[v2_rolling_ml["snapshot_day"] == day]
        v3r = v3_rolling_ml[v3_rolling_ml["snapshot_day"] == day]
        v2f = v2_fixed_ml[v2_fixed_ml["snapshot_day"] == day]
        v3f = v3_fixed_ml[v3_fixed_ml["snapshot_day"] == day]

        v2r_m = _mape(v2r) if len(v2r) else float("nan")
        v3r_m = _mape(v3r) if len(v3r) else float("nan")
        v2f_m = _mape(v2f) if len(v2f) else float("nan")
        v3f_m = _mape(v3f) if len(v3f) else float("nan")

        dr = v3r_m - v2r_m if not (np.isnan(v3r_m) or np.isnan(v2r_m)) else float("nan")
        df_delta = v3f_m - v2f_m if not (np.isnan(v3f_m) or np.isnan(v2f_m)) else float("nan")

        def _fmt(v):
            return f"{v:>8.1f}%" if not np.isnan(v) else "     n/a"
        def _dfmt(v):
            return f"{v:>+7.1f}%" if not np.isnan(v) else "    n/a"

        print(f"  {day:>5d} {_fmt(v2r_m)} {_fmt(v3r_m)} {_dfmt(dr)}  │ "
              f"{_fmt(v2f_m)} {_fmt(v3f_m)} {_dfmt(df_delta)}")

    # Overall
    v2r_overall = _mape(v2_rolling_ml)
    v3r_overall = _mape(v3_rolling_ml)
    v2f_overall = _mape(v2_fixed_ml)
    v3f_overall = _mape(v3_fixed_ml)
    print(f"  {'ALL':>5s} {v2r_overall:>8.1f}% {v3r_overall:>8.1f}% "
          f"{v3r_overall - v2r_overall:>+7.1f}%  │ "
          f"{v2f_overall:>8.1f}% {v3f_overall:>8.1f}% "
          f"{v3f_overall - v2f_overall:>+7.1f}%")

    # ── Months within 10% ────────────────────────────────────────────
    print(f"\n  Months within 10% error (Day 15, ML):")
    for label, data in [("v2 rolling", v2_rolling_ml),
                        ("v3 rolling", v3_rolling_ml),
                        ("v2 fixed", v2_fixed_ml),
                        ("v3 fixed", v3_fixed_ml)]:
        d15 = data[data["snapshot_day"] == 15]
        within = _months_within_10(d15)
        total = len(d15)
        print(f"    {label:<15s}: {within}/{total}")

    # ── Day-15 month-by-month rolling comparison ─────────────────────
    print(f"\n{'═' * 80}")
    print("MONTH-BY-MONTH DAY-15 COMPARISON (Rolling ML)")
    print(f"{'═' * 80}")
    print(f"  {'Month':<10s} {'Actual':>12s}  │ {'v2 Roll':>10s} {'v3 Roll':>10s} "
          f"{'Delta':>8s}  │ {'v3 better?':>10s}")
    print(f"  {'─' * 72}")

    v2r_d15 = v2_rolling_ml[v2_rolling_ml["snapshot_day"] == 15]
    v3r_d15 = v3_rolling_ml[v3_rolling_ml["snapshot_day"] == 15]

    months_order = sorted(
        v3r_d15[["year", "month"]].drop_duplicates().values.tolist()
    )
    v3_wins = 0
    v2_wins = 0
    for yr, mo in months_order:
        v2_row = v2r_d15[(v2r_d15["year"] == yr) & (v2r_d15["month"] == mo)]
        v3_row = v3r_d15[(v3r_d15["year"] == yr) & (v3r_d15["month"] == mo)]

        if len(v2_row) == 0 or len(v3_row) == 0:
            continue

        actual = v3_row.iloc[0]["actual"]
        v2_err = v2_row.iloc[0]["error_pct"]
        v3_err = v3_row.iloc[0]["error_pct"]
        delta = abs(v3_err) - abs(v2_err)

        better = "YES" if abs(v3_err) < abs(v2_err) else "no"
        if abs(v3_err) < abs(v2_err):
            v3_wins += 1
        else:
            v2_wins += 1

        label = f"{int(yr)}-{int(mo):02d}"
        print(f"  {label:<10s} ${actual:>11,.0f}  │ {v2_err:>+9.1f}% {v3_err:>+9.1f}% "
              f"{delta:>+7.1f}pp  │ {better:>10s}")

    print(f"\n  v3 wins: {v3_wins}   v2 wins: {v2_wins}   "
          f"({'v3' if v3_wins > v2_wins else 'v2'} is better overall)")

    # ── Worst months spotlight ───────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("WORST MONTHS (Rolling ML, Day 15, |error| > 10%):")
    for label, data in [("v2", v2r_d15), ("v3", v3r_d15)]:
        bad = data[data["error_pct"].abs() > 10].copy()
        bad = bad.sort_values("error_pct", key=abs, ascending=False)
        months_str = ", ".join(
            f"{int(r['year'])}-{int(r['month']):02d} ({r['error_pct']:+.1f}%)"
            for _, r in bad.iterrows()
        )
        print(f"  {label}: {months_str if months_str else 'NONE'}")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. v3 INTERACTION FEATURE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("V3 INTERACTION FEATURE ANALYSIS")
print(f"{'═' * 80}")

# Show coverage: what % of training rows have non-zero/non-NaN values
print(f"\n  Feature coverage in training data:")
print(f"  {'Feature':<42s} {'Non-zero%':>10s} {'Non-NaN%':>10s} {'Mean':>10s}")
print(f"  {'─' * 75}")
for feat in V3_INTERACTION_FEATURES:
    if feat in training.columns:
        col = training[feat]
        non_nan_pct = col.notna().mean() * 100
        non_zero_pct = ((col.notna()) & (col != 0)).mean() * 100
        mean_val = col.mean() if col.notna().any() else 0
        print(f"  {feat:<42s} {non_zero_pct:>9.1f}% {non_nan_pct:>9.1f}% {mean_val:>10.3f}")

# Show importance ranking of ONLY v3 features
print(f"\n  v3 feature importance ranking:")
print(f"  {'Overall Rank':>12s} {'Feature':<42s} {'Importance':>10s}")
print(f"  {'─' * 67}")
for feat in V3_INTERACTION_FEATURES:
    match = fi[fi["feature"] == feat]
    if len(match) > 0:
        idx = match.index[0]
        rank = fi.index.get_loc(idx) + 1
        imp = match.iloc[0]["importance"]
        print(f"  {rank:>12d} {feat:<42s} {imp:>10.6f}")
    else:
        print(f"  {'n/a':>12s} {feat:<42s} {'n/a':>10s}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'#' * 80}")
print("# V3 FINAL SUMMARY")
print(f"{'#' * 80}")

v3r_ml = bt_rolling[bt_rolling["method"] == "ML"]
v3f_ml = bt_fixed[bt_fixed["method"] == "ML"]

for day in config.SNAPSHOT_DAYS:
    v3r_d = v3r_ml[v3r_ml["snapshot_day"] == day]
    v3f_d = v3f_ml[v3f_ml["snapshot_day"] == day]
    r_mape = _mape(v3r_d) if len(v3r_d) else float("nan")
    f_mape = _mape(v3f_d) if len(v3f_d) else float("nan")
    print(f"  Day {day:>2d} MAPE:  rolling={r_mape:.1f}%  fixed={f_mape:.1f}%")

# Day-15 rolling specifics
v3r_d15 = v3r_ml[v3r_ml["snapshot_day"] == 15]
v3f_d15 = v3f_ml[v3f_ml["snapshot_day"] == 15]
print(f"\n  Day-15 rolling MAPE: {_mape(v3r_d15):.1f}%")
print(f"  Day-15 fixed MAPE:   {_mape(v3f_d15):.1f}%")
print(f"  Day-15 rolling months within 10%: "
      f"{_months_within_10(v3r_d15)}/{len(v3r_d15)}")
print(f"  Day-15 fixed months within 10%:   "
      f"{_months_within_10(v3f_d15)}/{len(v3f_d15)}")

# v2 baseline comparison
print(f"\n  v2 baseline to beat: 4.8% mid-month MAPE, 23/24 within 10%")
if len(v2) > 0:
    v2f_d15 = v2[(v2["method"] == "ML") & (v2["training_mode"] == "fixed")
                 & (v2["snapshot_day"] == 15)]
    v2r_d15_data = v2[(v2["method"] == "ML") & (v2["training_mode"] == "rolling")
                      & (v2["snapshot_day"] == 15)]
    print(f"  v2 fixed day-15 MAPE:   {_mape(v2f_d15):.1f}%  "
          f"({_months_within_10(v2f_d15)}/{len(v2f_d15)} within 10%)")
    print(f"  v2 rolling day-15 MAPE: {_mape(v2r_d15_data):.1f}%  "
          f"({_months_within_10(v2r_d15_data)}/{len(v2r_d15_data)} within 10%)")
    print(f"  v3 fixed day-15 MAPE:   {_mape(v3f_d15):.1f}%  "
          f"({_months_within_10(v3f_d15)}/{len(v3f_d15)} within 10%)")
    print(f"  v3 rolling day-15 MAPE: {_mape(v3r_d15):.1f}%  "
          f"({_months_within_10(v3r_d15)}/{len(v3r_d15)} within 10%)")

# Top 10 features
print(f"\n  Top 10 features (v3 {best_name}):")
for i, (_, row) in enumerate(fi.head(10).iterrows()):
    tag = " [NEW]" if row["feature"] in V3_INTERACTION_FEATURES else ""
    print(f"    {i+1:>2d}. {row['feature']:<40s} {row['importance']:.4f}{tag}")

print(f"\n{'═' * 80}")
print("OUTPUTS:")
print(f"  {RESULTS_DIR / 'backtest_results_v3.csv'}")
print(f"  {RESULTS_DIR / 'feature_importance_v3.csv'}")
print(f"{'═' * 80}")
print("Done.")
