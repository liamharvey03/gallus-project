"""
FlexPoint Loan Funding Forecasting — Monthly Backtest

Runs the full projection pipeline across every (month, snapshot_day) in
BACKTEST_MONTHS × SNAPSHOT_DAYS.  For each snapshot, scores with both
transition tables (baseline) and the ML model, compares to actual monthly
funding, and records the results.

Outputs:
  - outputs/results/backtest_results.csv
  - outputs/figures/backtest_comparison.png
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

from pipeline_snapshot import build_snapshot


# ─── Compute actual monthly funding ─────────────────────────────────────────

def _actual_monthly_funding(df):
    """
    Return a dict mapping (year, month) -> actual funded dollar amount.
    """
    funded = df[df["Funded D"].notna()].copy()
    funded["_year"] = funded["Funded D"].dt.year
    funded["_month"] = funded["Funded D"].dt.month
    return (
        funded.groupby(["_year", "_month"])["LoanAmount"]
        .sum()
        .to_dict()
    )


# ─── Run full backtest ───────────────────────────────────────────────────────

def run_backtest(df, transition_tables, model=None, feature_columns=None,
                 encoders=None, medians=None, training_mode="fixed"):
    """
    Run projections for every (month, day) and compare to actuals.

    Parameters
    ----------
    training_mode : str
        "fixed"   — use the passed-in model/encoders/medians for all months.
        "rolling" — retrain on prior 12 months for each test month.

    Returns a DataFrame with columns:
        year, month, snapshot_day, method, projected, actual,
        error_pct, direction, already_funded, projected_pipeline
    """
    actuals = _actual_monthly_funding(df)

    # Imports needed for rolling mode
    if training_mode == "rolling":
        from feature_engineering import (
            build_training_set, encode_categoricals,
            fill_missing_numeric, get_feature_columns,
        )
        from models import train_models

    rows = []
    total = len(config.BACKTEST_MONTHS) * len(config.SNAPSHOT_DAYS)
    done = 0

    for year, month in config.BACKTEST_MONTHS:
        actual = actuals.get((year, month), 0)
        if actual == 0:
            continue  # no funded loans — skip month

        # ── Rolling: retrain on prior 12 months ───────────────────────
        if training_mode == "rolling":
            train_months = []
            for offset in range(1, 13):
                m = month - offset
                y = year
                while m <= 0:
                    m += 12
                    y -= 1
                train_months.append((y, m))
            train_months.sort()

            training = build_training_set(df, transition_tables,
                                          months=train_months)
            if len(training) < 100:
                done += len(config.SNAPSHOT_DAYS)
                print(f"    Skipping {year}-{month:02d} — only {len(training)} "
                      f"training rows", flush=True)
                continue

            enc_df, r_encoders = encode_categoricals(training, fit=True)
            enc_df, r_medians = fill_missing_numeric(enc_df, fit=True)
            r_feat_cols = get_feature_columns(r_encoders)

            X_all = enc_df[r_feat_cols].values.astype(np.float32)
            y_all = enc_df["fund_by_end"].values.astype(int)
            trained = train_models(X_all, y_all, r_feat_cols)
            # Use GradientBoosting consistently
            r_model = trained.get("GradientBoosting",
                                  list(trained.values())[0])
            use_model = r_model
            use_fc = r_feat_cols
            use_enc = r_encoders
            use_med = r_medians
        else:
            use_model = model
            use_fc = feature_columns
            use_enc = encoders
            use_med = medians

        for day in config.SNAPSHOT_DAYS:
            done += 1
            try:
                if day == 0:
                    as_of = pd.Timestamp(year, month, 1) - pd.Timedelta(days=1)
                    month_end = (pd.Timestamp(year, month, 1)
                                 + pd.offsets.MonthEnd(0))
                else:
                    as_of = pd.Timestamp(year, month, day)
                    month_end = as_of.replace(day=1) + pd.offsets.MonthEnd(0)
            except ValueError:
                continue  # e.g. Feb 30

            target_month_start = pd.Timestamp(year, month, 1)

            result = build_snapshot(
                df, as_of, month_end=month_end,
                month_start=target_month_start if day == 0 else None,
                transition_tables=transition_tables,
                model=use_model, feature_columns=use_fc,
                encoders=use_enc, medians=use_med,
            )
            s = result["summary"]
            already = s["already_funded_dollars"]

            # Transition tables projection
            tt_total = s.get("projected_total", already)
            tt_pipeline = s.get("projected_pipeline", 0)
            tt_error = (tt_total - actual) / actual if actual else 0
            rows.append({
                "year": year, "month": month, "snapshot_day": day,
                "method": "Transition Tables",
                "already_funded": already,
                "projected_pipeline": tt_pipeline,
                "projected": tt_total,
                "actual": actual,
                "error_pct": tt_error * 100,
                "direction": "over" if tt_error > 0 else "under",
            })

            # ML projection
            ml_total = s.get("ml_projected_total", already)
            ml_pipeline = s.get("ml_projected_pipeline", 0)
            ml_error = (ml_total - actual) / actual if actual else 0
            rows.append({
                "year": year, "month": month, "snapshot_day": day,
                "method": "ML",
                "already_funded": already,
                "projected_pipeline": ml_pipeline,
                "projected": ml_total,
                "actual": actual,
                "error_pct": ml_error * 100,
                "direction": "over" if ml_error > 0 else "under",
            })

            if done % 10 == 0:
                print(f"    [{training_mode}] {done}/{total} snapshots...",
                      flush=True)

    return pd.DataFrame(rows)


# ─── Summary statistics ──────────────────────────────────────────────────────

def print_backtest_summary(results):
    """Print comprehensive backtest summary."""
    print(f"\n{'═' * 80}")
    print("BACKTEST RESULTS SUMMARY")
    print(f"{'═' * 80}")

    # ── Overall MAPE by method × snapshot day ─────────────────────────
    print(f"\n  MAPE by Method × Snapshot Day:")
    print(f"  {'Method':<22s}", end="")
    for day in config.SNAPSHOT_DAYS:
        print(f"  Day {day:>2d}", end="")
    print(f"  {'Overall':>8s}")
    print(f"  {'─' * 62}")

    for method in ["Transition Tables", "ML"]:
        sub = results[results["method"] == method]
        print(f"  {method:<22s}", end="")
        for day in config.SNAPSHOT_DAYS:
            day_sub = sub[sub["snapshot_day"] == day]
            mape = day_sub["error_pct"].abs().mean()
            print(f"  {mape:>5.1f}%", end="")
        overall_mape = sub["error_pct"].abs().mean()
        print(f"  {overall_mape:>6.1f}%")

    # ── Day-15 month-by-month comparison ──────────────────────────────
    day15 = results[results["snapshot_day"] == 15].copy()
    if len(day15) == 0:
        return

    print(f"\n{'═' * 80}")
    print("MONTH-BY-MONTH COMPARISON (Day 15 Snapshots)")
    print(f"{'═' * 80}")
    print(f"  {'Month':<10s} {'Actual':>12s}  │ {'TT Proj':>12s} {'TT Err':>8s}  │ "
          f"{'ML Proj':>12s} {'ML Err':>8s}")
    print(f"  {'─' * 76}")

    months = sorted(day15[["year", "month"]].drop_duplicates().values.tolist())
    for year, month in months:
        mask = (day15["year"] == year) & (day15["month"] == month)
        tt = day15[mask & (day15["method"] == "Transition Tables")]
        ml = day15[mask & (day15["method"] == "ML")]

        if len(tt) == 0 or len(ml) == 0:
            continue

        actual = tt.iloc[0]["actual"]
        tt_proj = tt.iloc[0]["projected"]
        tt_err = tt.iloc[0]["error_pct"]
        ml_proj = ml.iloc[0]["projected"]
        ml_err = ml.iloc[0]["error_pct"]

        label = f"{year}-{month:02d}"
        print(f"  {label:<10s} ${actual:>11,.0f}  │ ${tt_proj:>11,.0f} {tt_err:>+7.1f}%  │ "
              f"${ml_proj:>11,.0f} {ml_err:>+7.1f}%")

    # ── Months within 10% error at day 15 ─────────────────────────────
    print(f"\n{'─' * 80}")
    for method in ["Transition Tables", "ML"]:
        sub15 = day15[day15["method"] == method]
        within_10 = (sub15["error_pct"].abs() <= 10).sum()
        total_months = len(sub15)
        print(f"  {method}: {within_10}/{total_months} months within 10% error at day 15")

    # ── Best and worst months ─────────────────────────────────────────
    print(f"\n{'─' * 80}")
    for method in ["Transition Tables", "ML"]:
        sub15 = day15[day15["method"] == method]
        abs_err = sub15["error_pct"].abs()
        best_idx = abs_err.idxmin()
        worst_idx = abs_err.idxmax()
        best = sub15.loc[best_idx]
        worst = sub15.loc[worst_idx]
        print(f"  {method}:")
        print(f"    Best:  {int(best['year'])}-{int(best['month']):02d}  "
              f"error {best['error_pct']:>+.1f}%")
        print(f"    Worst: {int(worst['year'])}-{int(worst['month']):02d}  "
              f"error {worst['error_pct']:>+.1f}%")


# ─── Comparison figure ───────────────────────────────────────────────────────

def save_comparison_figure(results, save_path):
    """
    Plot projected vs actual over time for day-15 snapshots, both methods.
    """
    day15 = results[results["snapshot_day"] == 15].copy()
    if len(day15) == 0:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

    # Build time axis
    months_order = sorted(
        day15[["year", "month"]].drop_duplicates().values.tolist()
    )
    labels = [f"{y}-{m:02d}" for y, m in months_order]
    x = np.arange(len(labels))

    actuals = []
    tt_proj = []
    ml_proj = []
    tt_err = []
    ml_err = []

    for year, month in months_order:
        mask = (day15["year"] == year) & (day15["month"] == month)
        tt = day15[mask & (day15["method"] == "Transition Tables")]
        ml = day15[mask & (day15["method"] == "ML")]

        actuals.append(tt.iloc[0]["actual"] / 1e6 if len(tt) else 0)
        tt_proj.append(tt.iloc[0]["projected"] / 1e6 if len(tt) else 0)
        ml_proj.append(ml.iloc[0]["projected"] / 1e6 if len(ml) else 0)
        tt_err.append(tt.iloc[0]["error_pct"] if len(tt) else 0)
        ml_err.append(ml.iloc[0]["error_pct"] if len(ml) else 0)

    # Top panel: projected vs actual
    ax1.plot(x, actuals, "ko-", label="Actual", linewidth=2, markersize=5)
    ax1.plot(x, tt_proj, "s--", color="tab:blue", label="Transition Tables",
             linewidth=1.5, markersize=4)
    ax1.plot(x, ml_proj, "^--", color="tab:orange", label="ML (GradientBoosting)",
             linewidth=1.5, markersize=4)
    ax1.set_ylabel("Monthly Funding ($M)")
    ax1.set_title("Day-15 Projections vs Actual Monthly Funding")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Bottom panel: error %
    ax2.bar(x - 0.15, tt_err, 0.3, label="Transition Tables", color="tab:blue",
            alpha=0.7)
    ax2.bar(x + 0.15, ml_err, 0.3, label="ML", color="tab:orange", alpha=0.7)
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.axhline(10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax2.axhline(-10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax2.set_ylabel("Error (%)")
    ax2.set_xlabel("Month")
    ax2.set_title("Projection Error by Month (Day 15)")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3, axis="y")

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha="right")

    fig.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150)
    print(f"\n  Saved → {save_path}")
    plt.close(fig)


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

    print("\nTraining ML model...")
    bundle = train_and_select(encoded, feature_cols)
    best_model = bundle["best_model"]
    print(f"  Selected: {bundle['best_model_name']}")

    print(f"\n{'═' * 80}")
    print("RUNNING FULL BACKTEST")
    print(f"{'═' * 80}")
    print(f"  Months: {len(config.BACKTEST_MONTHS)}  "
          f"Snapshot days: {config.SNAPSHOT_DAYS}  "
          f"Total snapshots: {len(config.BACKTEST_MONTHS) * len(config.SNAPSHOT_DAYS)}")

    results = run_backtest(df, tables, best_model, feature_cols,
                           encoders, medians)

    # Save CSV
    csv_path = config.OUTPUTS_PATH / "results" / "backtest_results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(csv_path, index=False)
    print(f"\n  Saved → {csv_path}")

    # Print summary
    print_backtest_summary(results)

    # Save figure
    fig_path = config.OUTPUTS_PATH / "figures" / "backtest_comparison.png"
    save_comparison_figure(results, fig_path)
