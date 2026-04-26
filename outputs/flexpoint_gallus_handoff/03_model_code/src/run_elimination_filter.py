"""
FlexPoint Step 3 — Elimination Filter Backtest

Runs the full 24-month backtest with and without the dead-loan elimination
filter applied to ML projections.  Measures:
  1. MAPE improvement by snapshot day
  2. False negative rate (eliminated loans that actually fund)
  3. Filter statistics (how many loans eliminated, by rule)
  4. Dollar impact (how much projected volume is removed)

Uses v3 features (module swap) so the filter runs on top of the best model.

Outputs:
  - outputs/results/elimination_filter_results.csv
  - outputs/results/elimination_filter_summary.md
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
from transition_tables import build_transition_tables, vectorized_current_stage  # noqa: E402
from feature_engineering_v3 import (  # noqa: E402
    build_training_set, encode_categoricals, fill_missing_numeric,
    get_feature_columns,
)
from models import (  # noqa: E402
    train_and_select, _predict_proba, train_models,
)
from pipeline_snapshot import build_snapshot  # noqa: E402
from elimination_filter import (  # noqa: E402
    apply_elimination_filter, print_filter_stats,
)

RESULTS_DIR = config.OUTPUTS_PATH / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _actual_monthly_funding(df):
    """Return dict (year, month) -> actual funded dollars."""
    funded = df[df["Funded D"].notna()].copy()
    funded["_year"] = funded["Funded D"].dt.year
    funded["_month"] = funded["Funded D"].dt.month
    return funded.groupby(["_year", "_month"])["LoanAmount"].sum().to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SETUP
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("STEP 3 — ELIMINATION FILTER BACKTEST")
print("=" * 80)

t0 = time.time()
df = load_and_clean()
print(f"\nDataset: {len(df):,} rows")

print("\nBuilding transition tables...")
tables = build_transition_tables(df)

print("Building v3 training set (2024 fixed split)...")
training = build_training_set(df, tables)
print(f"  Training rows: {len(training):,}")

enc_train, encoders = encode_categoricals(training, fit=True)
enc_train, medians = fill_missing_numeric(enc_train, fit=True)
feat_cols = get_feature_columns(encoders)

print("\nTraining fixed-split model...")
bundle = train_and_select(enc_train, feat_cols)
best_model = bundle["best_model"]
best_name = bundle["best_model_name"]
print(f"  Selected: {best_name}")

actuals = _actual_monthly_funding(df)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BACKTEST WITH ELIMINATION FILTER
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("RUNNING 24-MONTH BACKTEST — FIXED SPLIT + ELIMINATION FILTER")
print(f"{'=' * 80}")
print(f"  Months: {len(config.BACKTEST_MONTHS)}  "
      f"Snapshot days: {config.SNAPSHOT_DAYS}")
print(f"  Training mode: fixed (2024 train → 2025 test)")

rows = []
filter_stats_all = []
false_neg_details = []

total = len(config.BACKTEST_MONTHS) * len(config.SNAPSHOT_DAYS)
done = 0

for year, month in config.BACKTEST_MONTHS:
    actual = actuals.get((year, month), 0)
    if actual == 0:
        done += len(config.SNAPSHOT_DAYS)
        continue

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
            continue

        target_month_start = pd.Timestamp(year, month, 1)

        # ── Build snapshot with ML scoring ────────────────────────────
        result = build_snapshot(
            df, as_of, month_end=month_end,
            month_start=target_month_start if day == 0 else None,
            transition_tables=tables,
            model=best_model, feature_columns=feat_cols,
            encoders=encoders, medians=medians,
        )
        s = result["summary"]
        active = result["active_pipeline"]
        already = s["already_funded_dollars"]

        # ── ML projection WITHOUT filter (baseline) ───────────────────
        if "ml_expected_funding" in active.columns:
            ml_pipeline_raw = active["ml_expected_funding"].sum()
            ml_total_raw = already + ml_pipeline_raw
        else:
            ml_pipeline_raw = 0
            ml_total_raw = already

        ml_error_raw = ((ml_total_raw - actual) / actual * 100
                        if actual else 0)

        # ── Apply elimination filter ──────────────────────────────────
        # The filter needs stage_rank, days_at_stage, and lock info.
        # active already has stage_rank and days_at_stage from build_snapshot.
        # We pass active as both scored_df and active_df since it has
        # the raw columns too.
        filtered, fstats = apply_elimination_filter(
            active, as_of, active_df=active, conservative=True,
            month_end=month_end,
        )

        # Zero out eliminated loans' ML probability
        if "ml_probability" in filtered.columns:
            filtered.loc[filtered["eliminated"], "ml_expected_funding"] = 0.0

        ml_pipeline_filt = filtered["ml_expected_funding"].sum() \
            if "ml_expected_funding" in filtered.columns else 0
        ml_total_filt = already + ml_pipeline_filt
        ml_error_filt = ((ml_total_filt - actual) / actual * 100
                         if actual else 0)

        # ── False negatives: eliminated loans that actually fund ──────
        # Check: of the eliminated loans, how many have Funded D within
        # the month?
        if filtered["eliminated"].any():
            elim_mask = filtered["eliminated"]
            elim_loans = filtered.loc[elim_mask]
            # Match back to raw df to check Funded D
            elim_guids = active.loc[elim_loans.index, "LoanGuid"] \
                if "LoanGuid" in active.columns else pd.Series(dtype=str)

            # Check actual funding
            if len(elim_guids) > 0 and "LoanGuid" in df.columns:
                funded_check = df[df["LoanGuid"].isin(elim_guids.values)]
                fn = funded_check[
                    funded_check["Funded D"].notna()
                    & (funded_check["Funded D"] >= target_month_start)
                    & (funded_check["Funded D"] <= month_end)
                ]
                n_false_neg = len(fn)
                fn_dollars = fn["LoanAmount"].sum() if len(fn) > 0 else 0
            else:
                n_false_neg = 0
                fn_dollars = 0
        else:
            n_false_neg = 0
            fn_dollars = 0

        # Total loans that actually fund this month (for false neg rate)
        total_funded_month = df[
            df["Funded D"].notna()
            & (df["Funded D"] >= target_month_start)
            & (df["Funded D"] <= month_end)
        ]
        n_total_funded = len(total_funded_month)

        fn_rate = (n_false_neg / n_total_funded * 100
                   if n_total_funded > 0 else 0)

        # ── Record results ────────────────────────────────────────────
        base_row = {
            "year": year, "month": month, "snapshot_day": day,
            "actual": actual,
            "already_funded": already,
            "active_loans": len(active),
        }

        # Without filter
        rows.append({
            **base_row,
            "method": "ML_no_filter",
            "projected_pipeline": ml_pipeline_raw,
            "projected": ml_total_raw,
            "error_pct": ml_error_raw,
        })

        # With filter
        rows.append({
            **base_row,
            "method": "ML_with_filter",
            "projected_pipeline": ml_pipeline_filt,
            "projected": ml_total_filt,
            "error_pct": ml_error_filt,
            "eliminated": fstats["eliminated"],
            "pct_eliminated": fstats["pct_eliminated"],
            "false_negatives": n_false_neg,
            "false_neg_dollars": fn_dollars,
            "false_neg_rate": fn_rate,
        })

        # Filter stats for aggregation
        filter_stats_all.append({
            "year": year, "month": month, "day": day,
            **fstats,
            "false_negatives": n_false_neg,
            "false_neg_dollars": fn_dollars,
            "false_neg_rate": fn_rate,
        })

        if done % 20 == 0 or done == total:
            print(f"    {done}/{total} snapshots...", flush=True)

results = pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SAVE RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

csv_path = RESULTS_DIR / "elimination_filter_results.csv"
results.to_csv(csv_path, index=False)
print(f"\n  Saved results → {csv_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ANALYSIS & SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 80}")
print("ELIMINATION FILTER RESULTS")
print(f"{'=' * 80}")

# ── MAPE comparison by snapshot day ───────────────────────────────────────
print(f"\n  MAPE by Snapshot Day:")
print(f"  {'Method':<22s}", end="")
for day in config.SNAPSHOT_DAYS:
    print(f"  Day {day:>2d}", end="")
print(f"  {'Overall':>8s}")
print(f"  {'─' * 62}")

for method in ["ML_no_filter", "ML_with_filter"]:
    sub = results[results["method"] == method]
    label = "ML (no filter)" if method == "ML_no_filter" else "ML + Filter"
    print(f"  {label:<22s}", end="")
    for day in config.SNAPSHOT_DAYS:
        day_sub = sub[sub["snapshot_day"] == day]
        mape = day_sub["error_pct"].abs().mean()
        print(f"  {mape:>5.1f}%", end="")
    overall = sub["error_pct"].abs().mean()
    print(f"  {overall:>6.1f}%")

# ── Improvement ───────────────────────────────────────────────────────────
print(f"\n  MAPE Improvement (no filter → with filter):")
print(f"  {'':22s}", end="")
for day in config.SNAPSHOT_DAYS:
    no_f = results[(results["method"] == "ML_no_filter") &
                   (results["snapshot_day"] == day)]["error_pct"].abs().mean()
    w_f = results[(results["method"] == "ML_with_filter") &
                  (results["snapshot_day"] == day)]["error_pct"].abs().mean()
    delta = no_f - w_f
    print(f"  {delta:>+5.1f}", end="")
no_f_all = results[results["method"] == "ML_no_filter"]["error_pct"].abs().mean()
w_f_all = results[results["method"] == "ML_with_filter"]["error_pct"].abs().mean()
print(f"  {no_f_all - w_f_all:>+6.1f}")

# ── False negative analysis ───────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  FALSE NEGATIVE ANALYSIS")
print(f"{'─' * 80}")

filt_rows = results[results["method"] == "ML_with_filter"]
total_fn = filt_rows["false_negatives"].sum()
total_fn_dollars = filt_rows["false_neg_dollars"].sum()

# Overall false negative rate across all snapshots
fs_df = pd.DataFrame(filter_stats_all)
avg_fn_rate = fs_df["false_neg_rate"].mean()
max_fn_rate = fs_df["false_neg_rate"].max()

print(f"  Total false negatives across all snapshots: {total_fn}")
print(f"  Total false negative dollars:               ${total_fn_dollars:,.0f}")
print(f"  Average false negative rate:                {avg_fn_rate:.2f}%")
print(f"  Maximum false negative rate (any snapshot): {max_fn_rate:.2f}%")
print(f"  Target: < 1.0%                              "
      f"{'PASS' if max_fn_rate < 1.0 else 'FAIL'}")

# By snapshot day
print(f"\n  False Negative Rate by Snapshot Day:")
for day in config.SNAPSHOT_DAYS:
    day_fs = fs_df[fs_df["day"] == day]
    avg = day_fs["false_neg_rate"].mean()
    mx = day_fs["false_neg_rate"].max()
    total = int(day_fs["false_negatives"].sum())
    print(f"    Day {day:>2d}:  avg {avg:.2f}%  max {mx:.2f}%  "
          f"total FN: {total}")

# ── Filter statistics ─────────────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  FILTER STATISTICS")
print(f"{'─' * 80}")

avg_elim = filt_rows["eliminated"].mean()
avg_pct = filt_rows["pct_eliminated"].mean()
print(f"  Average loans eliminated per snapshot: {avg_elim:.0f}")
print(f"  Average % of pipeline eliminated:      {avg_pct:.1f}%")

# By snapshot day
print(f"\n  Eliminated by Snapshot Day:")
for day in config.SNAPSHOT_DAYS:
    day_sub = filt_rows[filt_rows["snapshot_day"] == day]
    avg_e = day_sub["eliminated"].mean()
    avg_p = day_sub["pct_eliminated"].mean()
    print(f"    Day {day:>2d}:  avg {avg_e:.0f} loans eliminated  ({avg_p:.1f}%)")

# ── Months within 10% ────────────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  MONTHS WITHIN 10% ERROR (Day 15):")

day15 = results[results["snapshot_day"] == 15]
for method in ["ML_no_filter", "ML_with_filter"]:
    sub = day15[day15["method"] == method]
    within = (sub["error_pct"].abs() <= 10).sum()
    total_m = len(sub)
    label = "ML (no filter)" if method == "ML_no_filter" else "ML + Filter"
    print(f"    {label}: {within}/{total_m}")

# ── Day-15 month-by-month comparison ─────────────────────────────────────
print(f"\n{'=' * 80}")
print("  DAY-15 MONTH-BY-MONTH COMPARISON")
print(f"{'=' * 80}")
print(f"  {'Month':<10s} {'Actual':>12s} │ {'No Filter':>12s} {'Err':>8s} │ "
      f"{'Filtered':>12s} {'Err':>8s} │ {'FN':>3s} {'Elim':>5s}")
print(f"  {'─' * 82}")

months = sorted(day15[["year", "month"]].drop_duplicates().values.tolist())
for yr, mo in months:
    mask = (day15["year"] == yr) & (day15["month"] == mo)
    nf = day15[mask & (day15["method"] == "ML_no_filter")]
    wf = day15[mask & (day15["method"] == "ML_with_filter")]

    if len(nf) == 0 or len(wf) == 0:
        continue

    act = nf.iloc[0]["actual"]
    nf_proj = nf.iloc[0]["projected"]
    nf_err = nf.iloc[0]["error_pct"]
    wf_proj = wf.iloc[0]["projected"]
    wf_err = wf.iloc[0]["error_pct"]
    fn = int(wf.iloc[0].get("false_negatives", 0))
    elim = int(wf.iloc[0].get("eliminated", 0))

    label = f"{yr}-{mo:02d}"
    print(f"  {label:<10s} ${act:>11,.0f} │ ${nf_proj:>11,.0f} {nf_err:>+7.1f}% │ "
          f"${wf_proj:>11,.0f} {wf_err:>+7.1f}% │ {fn:>3d} {elim:>5d}")

# ── Directional bias check ───────────────────────────────────────────────
print(f"\n{'─' * 80}")
print("  DIRECTIONAL BIAS CHECK (Day 15):")
for method in ["ML_no_filter", "ML_with_filter"]:
    sub = day15[day15["method"] == method]
    avg_err = sub["error_pct"].mean()
    n_over = (sub["error_pct"] > 0).sum()
    n_under = (sub["error_pct"] < 0).sum()
    label = "ML (no filter)" if method == "ML_no_filter" else "ML + Filter"
    print(f"    {label}:  mean error {avg_err:>+.1f}%  "
          f"(over: {n_over}, under: {n_under})")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GENERATE SUMMARY MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════════

md_lines = [
    "# FlexPoint Step 3 — Elimination Filter Results",
    f"",
    f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
    f"",
    "## What Is the Elimination Filter?",
    "",
    "A conservative rule-based pre-filter that identifies \"dead\" loans in the",
    "pipeline — loans with <2% historical probability of funding — and removes",
    "them from the dollar projection before aggregation.",
    "",
    "## Rules Applied (Conservative / Tier 1)",
    "",
    "| # | Rule | Description | Hist. Funding Rate | Sample Size |",
    "|---|---|---|---|---|",
    "| 1 | opened_stale | Opened stage, 30+ days | 0.006% | 16,325 |",
    "| 2 | application_stale | Application stage, 30+ days | 0.0% | 302 |",
    "| 3 | submitted_unlocked_stale | Submitted + unlocked, 22+ days | 0.1% | 5,553 |",
    "| 4 | underwriting_unlocked_stale | Underwriting + unlocked, 22+ days | 0.1% | 15,883 |",
    "| 5 | approved_expired_lock | Approved + expired lock | 0.0% | 1,141 |",
    "",
    "## MAPE Comparison",
    "",
    "| Method | Day 0 | Day 1 | Day 8 | Day 15 | Day 22 | Overall |",
    "|---|---|---|---|---|---|---|",
]

for method, label in [("ML_no_filter", "ML (no filter)"),
                       ("ML_with_filter", "ML + Filter")]:
    sub = results[results["method"] == method]
    vals = []
    for day in config.SNAPSHOT_DAYS:
        mape = sub[sub["snapshot_day"] == day]["error_pct"].abs().mean()
        vals.append(f"{mape:.1f}%")
    overall = sub["error_pct"].abs().mean()
    vals.append(f"{overall:.1f}%")
    md_lines.append(f"| {label} | {' | '.join(vals)} |")

md_lines += [
    "",
    "## False Negative Analysis",
    "",
    f"- Average false negative rate: {avg_fn_rate:.2f}%",
    f"- Maximum false negative rate: {max_fn_rate:.2f}%",
    f"- Target: < 1.0% — **{'PASS' if max_fn_rate < 1.0 else 'FAIL'}**",
    f"- Total false negatives across all snapshots: {total_fn}",
    f"- Total false negative dollars: ${total_fn_dollars:,.0f}",
    "",
    "## Filter Statistics",
    "",
    f"- Average loans eliminated per snapshot: {avg_elim:.0f}",
    f"- Average % of pipeline eliminated: {avg_pct:.1f}%",
    "",
    "## Day-15 Month-by-Month",
    "",
    "| Month | Actual | No Filter | Err | Filtered | Err | FN | Elim |",
    "|---|---|---|---|---|---|---|---|",
]

for yr, mo in months:
    mask = (day15["year"] == yr) & (day15["month"] == mo)
    nf = day15[mask & (day15["method"] == "ML_no_filter")]
    wf = day15[mask & (day15["method"] == "ML_with_filter")]
    if len(nf) == 0 or len(wf) == 0:
        continue
    act = nf.iloc[0]["actual"]
    nf_err = nf.iloc[0]["error_pct"]
    wf_proj = wf.iloc[0]["projected"]
    wf_err = wf.iloc[0]["error_pct"]
    fn = int(wf.iloc[0].get("false_negatives", 0))
    elim = int(wf.iloc[0].get("eliminated", 0))
    md_lines.append(
        f"| {yr}-{mo:02d} | ${act:,.0f} | ${nf.iloc[0]['projected']:,.0f} | "
        f"{nf_err:+.1f}% | ${wf_proj:,.0f} | {wf_err:+.1f}% | {fn} | {elim} |"
    )

md_path = RESULTS_DIR / "elimination_filter_summary.md"
md_path.write_text("\n".join(md_lines))
print(f"\n  Saved summary → {md_path}")

elapsed = time.time() - t0
print(f"\n{'=' * 80}")
print(f"COMPLETE — {elapsed:.0f}s elapsed")
print(f"{'=' * 80}")
