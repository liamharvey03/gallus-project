"""
FlexPoint v2 Model Analysis — Full Evaluation

Changes from v1:
  1. stage_only_probability replaces base_probability (product/purpose independent)
  2. 5 lock date features added
  3. Day-0 (prior month-end) snapshot added
  4. Rolling 12-month training window option

Outputs:
  - outputs/results/backtest_results_v2.csv
  - outputs/results/model_v1_vs_v2.md
  - outputs/results/feature_importance_v2.csv
  - outputs/figures/backtest_comparison_v2.png
  - outputs/figures/error_by_month_v2.png
"""
import sys
import time
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

from data_prep import load_and_clean
from transition_tables import build_transition_tables
from feature_engineering import (
    build_training_set, encode_categoricals, fill_missing_numeric,
    get_feature_columns, NUMERIC_FEATURES, CATEGORICAL_FEATURES,
)
from models import (
    train_and_select, feature_importance, evaluate_models,
    calibration_plot, _predict_proba,
)
from backtest import (
    run_backtest, print_backtest_summary, save_comparison_figure,
)

RESULTS_DIR = config.OUTPUTS_PATH / "results"
FIGURES_DIR = config.OUTPUTS_PATH / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SETUP — Load once
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("V2 MODEL ANALYSIS — LOADING DATA & TRAINING")
print("=" * 80)

df = load_and_clean()
print(f"\nDataset: {len(df):,} rows x {len(df.columns)} columns")

print("\nBuilding transition tables...")
tables = build_transition_tables(df)

print("Building v2 training set (with day-0 + lock features)...")
t0 = time.time()
training = build_training_set(df, tables)
print(f"  Training set: {training.shape[0]:,} rows x {training.shape[1]} cols"
      f"  ({time.time() - t0:.1f}s)")
print(f"  Positive rate: {training['fund_by_end'].mean():.1%}")

# Encode and train
encoded, encoders = encode_categoricals(training, fit=True)
encoded, medians = fill_missing_numeric(encoded, fit=True)
feature_cols = get_feature_columns(encoders)
print(f"  Features after encoding: {len(feature_cols)}")

print("\nTraining v2 models (fixed split: 2024 train / 2025 test)...")
bundle = train_and_select(encoded, feature_cols)
best_model = bundle["best_model"]
best_name = bundle["best_model_name"]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MODEL COMPARISON & FEATURE IMPORTANCE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("V2 MODEL COMPARISON")
print(f"{'═' * 80}")

results_table = bundle["results"]
print(f"\n  {'Model':<25s} {'Brier':>10s} {'AUC':>10s} {'LogLoss':>10s}")
print(f"  {'─' * 58}")
for _, row in results_table.iterrows():
    marker = " <<<" if row["model"] == best_name else ""
    print(f"  {row['model']:<25s} {row['brier_score']:>10.6f} "
          f"{row['auc']:>10.6f} {row['log_loss']:>10.6f}{marker}")

print(f"\n  Selected: {best_name}")

# Feature importance
fi = feature_importance(best_model, feature_cols)
fi.to_csv(RESULTS_DIR / "feature_importance_v2.csv", index=False)

print(f"\n{'═' * 80}")
print(f"V2 FEATURE IMPORTANCE — {best_name} (top 20)")
print(f"{'═' * 80}")
print(f"  {'Rank':>4s} {'Feature':<40s} {'Importance':>10s} {'Cumul%':>8s}")
print(f"  {'─' * 65}")
cumul = 0.0
for i, (_, row) in enumerate(fi.head(20).iterrows()):
    cumul += row["importance"]
    print(f"  {i+1:>4d} {row['feature']:<40s} "
          f"{row['importance']:>10.6f} {cumul:>7.1%}")

# Calibration plot
calibration_plot(
    bundle["models"], bundle["X_test"], bundle["y_test"],
    save_path=FIGURES_DIR / "calibration_curves_v2.png",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FIXED BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("RUNNING FIXED BACKTEST (v2 features, 2024 training)")
print(f"{'═' * 80}")
print(f"  Months: {len(config.BACKTEST_MONTHS)}  "
      f"Snapshot days: {config.SNAPSHOT_DAYS}  "
      f"Total: {len(config.BACKTEST_MONTHS) * len(config.SNAPSHOT_DAYS)}")

t0 = time.time()
bt_fixed = run_backtest(
    df, tables, best_model, feature_cols, encoders, medians,
    training_mode="fixed",
)
bt_fixed["training_mode"] = "fixed"
print(f"  Done in {time.time() - t0:.0f}s")

print_backtest_summary(bt_fixed)

save_comparison_figure(
    bt_fixed,
    FIGURES_DIR / "backtest_comparison_v2.png",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ROLLING BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("RUNNING ROLLING 12-MONTH BACKTEST")
print(f"{'═' * 80}")
print(f"  Each month retrains on prior 12 months. This will take a while...")

t0 = time.time()
bt_rolling = run_backtest(
    df, tables, training_mode="rolling",
)
bt_rolling["training_mode"] = "rolling"
print(f"  Done in {time.time() - t0:.0f}s")

print_backtest_summary(bt_rolling)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SAVE COMBINED RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

bt_all = pd.concat([bt_fixed, bt_rolling], ignore_index=True)
bt_all.to_csv(RESULTS_DIR / "backtest_results_v2.csv", index=False)
print(f"\n  Saved → {RESULTS_DIR / 'backtest_results_v2.csv'}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. V1 vs V2 COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'═' * 80}")
print("V1 vs V2 COMPARISON")
print(f"{'═' * 80}")

# Load v1 results
v1_path = RESULTS_DIR / "backtest_results.csv"
if v1_path.exists():
    v1 = pd.read_csv(v1_path)
else:
    v1 = pd.DataFrame()
    print("  WARNING: v1 backtest_results.csv not found — skipping comparison")


def _mape(df_sub):
    """Mean absolute percentage error."""
    return df_sub["error_pct"].abs().mean()


if len(v1) > 0:
    v1_ml = v1[v1["method"] == "ML"]

    # ── MAPE by snapshot day ──────────────────────────────────────────
    print(f"\n  ML MAPE by Snapshot Day:")
    print(f"  {'Day':>5s} {'v1':>8s} {'v2 Fix':>8s} {'v2 Roll':>8s} "
          f"{'Best':>8s}")
    print(f"  {'─' * 42}")

    for day in config.SNAPSHOT_DAYS:
        v1_d = v1_ml[v1_ml["snapshot_day"] == day] if day != 0 else pd.DataFrame()
        v2f_d = bt_fixed[(bt_fixed["method"] == "ML")
                         & (bt_fixed["snapshot_day"] == day)]
        v2r_d = bt_rolling[(bt_rolling["method"] == "ML")
                           & (bt_rolling["snapshot_day"] == day)]

        v1_mape = _mape(v1_d) if len(v1_d) > 0 else float("nan")
        v2f_mape = _mape(v2f_d) if len(v2f_d) > 0 else float("nan")
        v2r_mape = _mape(v2r_d) if len(v2r_d) > 0 else float("nan")

        vals = {"v1": v1_mape, "v2_fix": v2f_mape, "v2_roll": v2r_mape}
        best_label = min((v for v in vals.items() if not np.isnan(v[1])),
                         key=lambda x: x[1], default=("—", 0))[0]

        v1_str = f"{v1_mape:>6.1f}%" if not np.isnan(v1_mape) else "   n/a"
        v2f_str = f"{v2f_mape:>6.1f}%" if not np.isnan(v2f_mape) else "   n/a"
        v2r_str = f"{v2r_mape:>6.1f}%" if not np.isnan(v2r_mape) else "   n/a"

        print(f"  {day:>5d} {v1_str:>8s} {v2f_str:>8s} {v2r_str:>8s} "
              f"{best_label:>8s}")

    # Overall
    v1_overall = _mape(v1_ml)
    v2f_overall = _mape(bt_fixed[bt_fixed["method"] == "ML"])
    v2r_overall = _mape(bt_rolling[bt_rolling["method"] == "ML"])
    print(f"  {'ALL':>5s} {v1_overall:>6.1f}% {v2f_overall:>6.1f}% "
          f"{v2r_overall:>6.1f}%")

    # ── Nov/Dec 2025 spotlight ─────────────────────────────────────────
    print(f"\n  Nov/Dec 2025 Day-15 ML Error:")
    print(f"  {'Month':<10s} {'v1':>10s} {'v2 Fix':>10s} {'v2 Roll':>10s}")
    print(f"  {'─' * 42}")

    for yr, mo in [(2025, 11), (2025, 12)]:
        v1_e = v1_ml[(v1_ml["year"] == yr) & (v1_ml["month"] == mo)
                     & (v1_ml["snapshot_day"] == 15)]
        v2f_e = bt_fixed[(bt_fixed["method"] == "ML")
                         & (bt_fixed["year"] == yr) & (bt_fixed["month"] == mo)
                         & (bt_fixed["snapshot_day"] == 15)]
        v2r_e = bt_rolling[(bt_rolling["method"] == "ML")
                           & (bt_rolling["year"] == yr)
                           & (bt_rolling["month"] == mo)
                           & (bt_rolling["snapshot_day"] == 15)]

        v1_val = f"{v1_e.iloc[0]['error_pct']:>+.1f}%" if len(v1_e) else "n/a"
        v2f_val = f"{v2f_e.iloc[0]['error_pct']:>+.1f}%" if len(v2f_e) else "n/a"
        v2r_val = f"{v2r_e.iloc[0]['error_pct']:>+.1f}%" if len(v2r_e) else "n/a"
        print(f"  {yr}-{mo:02d}    {v1_val:>10s} {v2f_val:>10s} {v2r_val:>10s}")

    # ── Rolling vs Fixed: who wins? ────────────────────────────────────
    print(f"\n  Rolling vs Fixed (ML overall MAPE):")
    print(f"    Fixed:   {v2f_overall:.1f}%")
    print(f"    Rolling: {v2r_overall:.1f}%")
    winner = "Rolling" if v2r_overall < v2f_overall else "Fixed"
    print(f"    Winner:  {winner}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ERROR BY MONTH FIGURE (v1 vs v2 fixed vs v2 rolling)
# ═══════════════════════════════════════════════════════════════════════════════

def _save_error_by_month(v1, bt_fixed, bt_rolling, save_path):
    """Bar chart: day-15 ML error by month for v1, v2 fixed, v2 rolling."""
    months_order = sorted(
        bt_fixed[bt_fixed["snapshot_day"] == 15][["year", "month"]]
        .drop_duplicates().values.tolist()
    )
    labels = [f"{int(y)}-{int(m):02d}" for y, m in months_order]
    x = np.arange(len(labels))
    width = 0.25

    v1_errs = []
    v2f_errs = []
    v2r_errs = []

    for yr, mo in months_order:
        # v1
        if len(v1) > 0:
            v1_row = v1[(v1["method"] == "ML") & (v1["year"] == yr)
                        & (v1["month"] == mo) & (v1["snapshot_day"] == 15)]
            v1_errs.append(v1_row.iloc[0]["error_pct"] if len(v1_row) else 0)
        else:
            v1_errs.append(0)

        # v2 fixed
        v2f_row = bt_fixed[(bt_fixed["method"] == "ML")
                           & (bt_fixed["year"] == yr)
                           & (bt_fixed["month"] == mo)
                           & (bt_fixed["snapshot_day"] == 15)]
        v2f_errs.append(v2f_row.iloc[0]["error_pct"] if len(v2f_row) else 0)

        # v2 rolling
        v2r_row = bt_rolling[(bt_rolling["method"] == "ML")
                             & (bt_rolling["year"] == yr)
                             & (bt_rolling["month"] == mo)
                             & (bt_rolling["snapshot_day"] == 15)]
        v2r_errs.append(v2r_row.iloc[0]["error_pct"] if len(v2r_row) else 0)

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.bar(x - width, v1_errs, width, label="v1 ML", color="tab:gray",
           alpha=0.7)
    ax.bar(x, v2f_errs, width, label="v2 Fixed ML", color="tab:blue",
           alpha=0.7)
    ax.bar(x + width, v2r_errs, width, label="v2 Rolling ML",
           color="tab:orange", alpha=0.7)

    ax.axhline(0, color="black", linewidth=0.5)
    ax.axhline(10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.axhline(-10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Error (%)")
    ax.set_title("Day-15 ML Projection Error: v1 vs v2 Fixed vs v2 Rolling")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"\n  Saved → {save_path}")


_save_error_by_month(v1, bt_fixed, bt_rolling,
                     FIGURES_DIR / "error_by_month_v2.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. WRITE v1 vs v2 MARKDOWN SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

def _write_comparison_md(v1, bt_fixed, bt_rolling, fi, results_table,
                         save_path):
    """Write a markdown comparison of v1 vs v2."""
    lines = []
    lines.append("# FlexPoint v1 vs v2 Model Comparison\n")
    lines.append(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Model metrics
    lines.append("## v2 Model Metrics (Fixed, 2024 train / 2025 test)\n")
    lines.append("| Model | Brier | AUC | LogLoss |")
    lines.append("|---|---|---|---|")
    for _, row in results_table.iterrows():
        marker = " **BEST**" if row["model"] == best_name else ""
        lines.append(f"| {row['model']}{marker} | {row['brier_score']:.6f} "
                     f"| {row['auc']:.6f} | {row['log_loss']:.6f} |")

    # Feature importance top 15
    lines.append("\n## v2 Feature Importance (Top 15)\n")
    lines.append("| Rank | Feature | Importance |")
    lines.append("|---|---|---|")
    for i, (_, row) in enumerate(fi.head(15).iterrows()):
        lines.append(f"| {i+1} | {row['feature']} | {row['importance']:.6f} |")

    # MAPE comparison
    lines.append("\n## ML MAPE by Snapshot Day\n")
    lines.append("| Day | v1 | v2 Fixed | v2 Rolling |")
    lines.append("|---|---|---|---|")

    v1_ml = v1[v1["method"] == "ML"] if len(v1) > 0 else pd.DataFrame()
    for day in config.SNAPSHOT_DAYS:
        v1_d = v1_ml[v1_ml["snapshot_day"] == day] if len(v1_ml) > 0 and day != 0 else pd.DataFrame()
        v2f_d = bt_fixed[(bt_fixed["method"] == "ML")
                         & (bt_fixed["snapshot_day"] == day)]
        v2r_d = bt_rolling[(bt_rolling["method"] == "ML")
                           & (bt_rolling["snapshot_day"] == day)]

        v1_m = f"{_mape(v1_d):.1f}%" if len(v1_d) > 0 else "n/a"
        v2f_m = f"{_mape(v2f_d):.1f}%" if len(v2f_d) > 0 else "n/a"
        v2r_m = f"{_mape(v2r_d):.1f}%" if len(v2r_d) > 0 else "n/a"
        lines.append(f"| {day} | {v1_m} | {v2f_m} | {v2r_m} |")

    # Nov/Dec spotlight
    lines.append("\n## Nov/Dec 2025 Day-15 ML Error\n")
    lines.append("| Month | v1 | v2 Fixed | v2 Rolling |")
    lines.append("|---|---|---|---|")
    for yr, mo in [(2025, 11), (2025, 12)]:
        v1_e = v1_ml[(v1_ml["year"] == yr) & (v1_ml["month"] == mo)
                     & (v1_ml["snapshot_day"] == 15)] if len(v1_ml) > 0 else pd.DataFrame()
        v2f_e = bt_fixed[(bt_fixed["method"] == "ML")
                         & (bt_fixed["year"] == yr) & (bt_fixed["month"] == mo)
                         & (bt_fixed["snapshot_day"] == 15)]
        v2r_e = bt_rolling[(bt_rolling["method"] == "ML")
                           & (bt_rolling["year"] == yr)
                           & (bt_rolling["month"] == mo)
                           & (bt_rolling["snapshot_day"] == 15)]

        v1_v = f"{v1_e.iloc[0]['error_pct']:+.1f}%" if len(v1_e) else "n/a"
        v2f_v = f"{v2f_e.iloc[0]['error_pct']:+.1f}%" if len(v2f_e) else "n/a"
        v2r_v = f"{v2r_e.iloc[0]['error_pct']:+.1f}%" if len(v2r_e) else "n/a"
        lines.append(f"| {yr}-{mo:02d} | {v1_v} | {v2f_v} | {v2r_v} |")

    # Write
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Saved → {save_path}")


_write_comparison_md(v1, bt_fixed, bt_rolling, fi, results_table,
                     RESULTS_DIR / "model_v1_vs_v2.md")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n\n{'#' * 80}")
print("# FINAL SUMMARY")
print(f"{'#' * 80}")

v2f_ml = bt_fixed[bt_fixed["method"] == "ML"]
v2r_ml = bt_rolling[bt_rolling["method"] == "ML"]
v2f_d15 = _mape(v2f_ml[v2f_ml["snapshot_day"] == 15])
v2r_d15 = _mape(v2r_ml[v2r_ml["snapshot_day"] == 15])
v2f_d0 = _mape(v2f_ml[v2f_ml["snapshot_day"] == 0])
v2r_d0 = _mape(v2r_ml[v2r_ml["snapshot_day"] == 0])

if len(v1) > 0:
    v1_ml = v1[v1["method"] == "ML"]
    v1_d15 = _mape(v1_ml[v1_ml["snapshot_day"] == 15])
    print(f"\n  v1 day-15 MAPE (ML):           {v1_d15:.1f}%")
else:
    print(f"\n  v1 day-15 MAPE (ML):           n/a")

print(f"  v2 day-15 MAPE (fixed ML):     {v2f_d15:.1f}%")
print(f"  v2 day-15 MAPE (rolling ML):   {v2r_d15:.1f}%")
print(f"  v2 day-0  MAPE (fixed ML):     {v2f_d0:.1f}%")
print(f"  v2 day-0  MAPE (rolling ML):   {v2r_d0:.1f}%")

# Nov/Dec
for yr, mo, label in [(2025, 11, "Nov"), (2025, 12, "Dec")]:
    if len(v1) > 0:
        v1_e = v1_ml[(v1_ml["year"] == yr) & (v1_ml["month"] == mo)
                     & (v1_ml["snapshot_day"] == 15)]
        v1_str = f"{v1_e.iloc[0]['error_pct']:+.1f}%" if len(v1_e) else "n/a"
    else:
        v1_str = "n/a"
    v2f_e = v2f_ml[(v2f_ml["year"] == yr) & (v2f_ml["month"] == mo)
                   & (v2f_ml["snapshot_day"] == 15)]
    v2r_e = v2r_ml[(v2r_ml["year"] == yr) & (v2r_ml["month"] == mo)
                   & (v2r_ml["snapshot_day"] == 15)]
    v2f_str = f"{v2f_e.iloc[0]['error_pct']:+.1f}%" if len(v2f_e) else "n/a"
    v2r_str = f"{v2r_e.iloc[0]['error_pct']:+.1f}%" if len(v2r_e) else "n/a"
    print(f"\n  {label} 2025 day-15 error:  v1={v1_str}  "
          f"v2_fixed={v2f_str}  v2_rolling={v2r_str}")

# Feature importance top 10
print(f"\n  Top 10 features (v2 {best_name}):")
for i, (_, row) in enumerate(fi.head(10).iterrows()):
    print(f"    {i+1:>2d}. {row['feature']:<40s} {row['importance']:.4f}")

# Winner
v2f_overall = _mape(v2f_ml)
v2r_overall = _mape(v2r_ml)
print(f"\n  Rolling vs Fixed overall MAPE: "
      f"fixed={v2f_overall:.1f}%  rolling={v2r_overall:.1f}%")
winner = "Rolling" if v2r_overall < v2f_overall else "Fixed"
print(f"  Winner: {winner}")

print(f"\n{'═' * 80}")
print("OUTPUTS:")
print(f"  {RESULTS_DIR / 'backtest_results_v2.csv'}")
print(f"  {RESULTS_DIR / 'model_v1_vs_v2.md'}")
print(f"  {RESULTS_DIR / 'feature_importance_v2.csv'}")
print(f"  {FIGURES_DIR / 'backtest_comparison_v2.png'}")
print(f"  {FIGURES_DIR / 'error_by_month_v2.png'}")
print(f"  {FIGURES_DIR / 'calibration_curves_v2.png'}")
print(f"{'═' * 80}")
print("Done.")
