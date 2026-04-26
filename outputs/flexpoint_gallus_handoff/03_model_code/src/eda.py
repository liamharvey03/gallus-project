"""
FlexPoint Loan Funding Forecasting — Exploratory Data Analysis

Produces:
  1. Numeric feature correlations with DidFund
  2. Categorical feature funding-rate spreads
  3. Time-at-stage distributions (funded vs failed)
  4. Incremental variable value test (stage-only → +product/purpose)
  5. Key figures saved to outputs/figures/
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

FIGURES_DIR = config.OUTPUTS_PATH / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ─── 1. Numeric correlations ────────────────────────────────────────────────

def numeric_correlations(df):
    """Point-biserial correlation of numeric features with DidFund."""
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()

    numeric_cols = [
        "DecisionCreditScore", "LTV", "CLTV", "LoanAmount", "NoteRate",
        "Term", "Lock Period (days)", "Borrower Age",
        "DaysOpenToSubmitted", "DaysSubmittedToApproved",
        "DaysApprovedToCTC", "DaysCTCToFunded",
        "DaysTotalOpenToFund", "LockDurationDays",
        "DaysSubmittedToUW", "DaysUWToApproved", "DaysDocsToFunded",
    ]

    results = []
    for col in numeric_cols:
        if col not in completed.columns:
            continue
        valid = completed[[col, "DidFund"]].dropna()
        if len(valid) < 100:
            continue
        corr = valid[col].corr(valid["DidFund"])
        mean_f = valid.loc[valid["DidFund"] == 1, col].mean()
        mean_nf = valid.loc[valid["DidFund"] == 0, col].mean()
        results.append({
            "Feature": col,
            "Corr": round(corr, 4),
            "|Corr|": round(abs(corr), 4),
            "N": len(valid),
            "Mean_Funded": round(mean_f, 2),
            "Mean_Failed": round(mean_nf, 2),
        })

    corr_df = pd.DataFrame(results).sort_values("|Corr|", ascending=False)

    # ── Figure ───────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#2ecc71" if c > 0 else "#e74c3c" for c in corr_df["Corr"]]
    ax.barh(corr_df["Feature"], corr_df["Corr"], color=colors)
    ax.set_xlabel("Correlation with DidFund")
    ax.set_title("Numeric Feature Correlations with Funding Outcome")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "numeric_correlations.png", dpi=150)
    plt.close(fig)

    return corr_df


# ─── 2. Categorical spreads ─────────────────────────────────────────────────

def categorical_spreads(df):
    """Fund rate spread across values of each categorical feature."""
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()

    cat_cols = [
        "Product Type", "Loan Purpose", "Branch Channel", "Loan Type",
        "Occupancy Type", "Amortization Type", "Rate Lock Status",
        "Property State", "Lien Position", "Has Prepayment Penalty",
    ]

    summaries = []
    detail = {}
    for col in cat_cols:
        if col not in completed.columns:
            continue
        valid = completed[completed[col].notna() & (completed[col].astype(str).str.strip() != "")]
        if len(valid) < 100:
            continue

        grouped = (
            valid.groupby(col)["DidFund"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "FundRate", "count": "Count"})
            .sort_values("Count", ascending=False)
        )
        sig = grouped[grouped["Count"] >= config.MIN_CELL_SIZE]
        spread = (sig["FundRate"].max() - sig["FundRate"].min()) if len(sig) > 1 else 0
        summaries.append({
            "Feature": col,
            "Spread_pp": round(spread * 100, 1),
            "Values": len(sig),
            "N": len(valid),
        })
        detail[col] = grouped

    summary_df = pd.DataFrame(summaries).sort_values("Spread_pp", ascending=False)

    # ── Figure ───────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(summary_df["Feature"], summary_df["Spread_pp"], color="#3498db")
    ax.set_xlabel("Fund Rate Spread (pp)")
    ax.set_title("Categorical Feature Predictive Spread")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "categorical_spreads.png", dpi=150)
    plt.close(fig)

    return summary_df, detail


# ─── 3. Time-at-stage distributions ─────────────────────────────────────────

def time_at_stage_analysis(df):
    """Box plots of key inter-stage durations by outcome."""
    completed = df[df["Outcome"].isin(["Funded", "Failed"])].copy()

    duration_cols = [
        ("DaysOpenToSubmitted", "Open → Submitted"),
        ("DaysSubmittedToApproved", "Submitted → Approved"),
        ("DaysApprovedToCTC", "Approved → CTC"),
        ("DaysCTCToFunded", "CTC → Funded"),
    ]

    stats = []
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, (col, label) in enumerate(duration_cols):
        if col not in completed.columns:
            continue

        data = completed[[col, "Outcome"]].dropna()
        # Clip extreme outliers for display
        p99 = data[col].quantile(0.99)
        data_clipped = data[data[col] <= p99]

        for outcome in ["Funded", "Failed"]:
            sub = data[data["Outcome"] == outcome][col]
            stats.append({
                "Duration": label,
                "Outcome": outcome,
                "Median": sub.median(),
                "Mean": round(sub.mean(), 1),
                "N": len(sub),
            })

        ax = axes[idx]
        funded_vals = data_clipped.loc[data_clipped["Outcome"] == "Funded", col]
        failed_vals = data_clipped.loc[data_clipped["Outcome"] == "Failed", col]

        bp = ax.boxplot(
            [funded_vals.dropna(), failed_vals.dropna()],
            tick_labels=["Funded", "Failed"],
            patch_artist=True,
            widths=0.6,
        )
        bp["boxes"][0].set_facecolor("#2ecc71")
        bp["boxes"][1].set_facecolor("#e74c3c")
        ax.set_title(label)
        ax.set_ylabel("Days")

    plt.suptitle("Inter-Stage Duration by Outcome", fontsize=14, y=1.01)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "time_at_stage_distributions.png", dpi=150)
    plt.close(fig)

    return pd.DataFrame(stats)


# ─── 4. Incremental variable value test ─────────────────────────────────────

def incremental_value_test(df):
    """
    Show how projection accuracy improves when adding product/purpose
    stratification to stage-only probabilities.

    Uses several historical months as test cases.
    """
    from transition_tables import build_transition_tables, vectorized_current_stage

    tables = build_transition_tables(df)
    # Use month-end tables for projection (P(fund by month end))
    me_unstrat = tables["me_unstratified"]
    me_strat = tables["me_stratified"]

    # Test months: use the last 6 months with complete data
    test_months = [(2025, 4), (2025, 5), (2025, 6), (2025, 7), (2025, 8), (2025, 9)]

    results = []
    for year, month in test_months:
        as_of = pd.Timestamp(year, month, 15)
        month_start = as_of.replace(day=1)
        month_end = month_start + pd.offsets.MonthEnd(0)

        # Already funded this month
        already = df[
            df["Funded D"].notna()
            & (df["Funded D"] >= month_start)
            & (df["Funded D"] <= as_of)
        ]
        already_dollars = already["LoanAmount"].sum()

        # Actual total for the month
        actual_month = df[
            df["Funded D"].notna()
            & (df["Funded D"] >= month_start)
            & (df["Funded D"] <= month_end)
        ]["LoanAmount"].sum()

        if actual_month == 0:
            continue

        # Active pipeline
        opened = df["Loan Open Date"].notna() & (df["Loan Open Date"] <= as_of)
        not_funded = df["Funded D"].isna() | (df["Funded D"] > as_of)
        not_failed = pd.Series(True, index=df.index)
        for col in config.FAILURE_DATE_COLUMNS:
            if col in df.columns:
                not_failed &= df[col].isna() | (df[col] > as_of)
        active = df.loc[opened & not_funded & not_failed].copy()

        sl, sr, _ = vectorized_current_stage(active, as_of)
        active["current_stage"] = sl
        active = active[active["current_stage"].notna()]

        # Stage-only projection (month-end probabilities)
        active["p_base"] = active["current_stage"].map(me_unstrat["p_fund"]).fillna(0)
        proj_base = already_dollars + (active["p_base"] * active["LoanAmount"]).sum()

        # Stratified projection (month-end probabilities)
        def _lookup_strat(row):
            key = (row["current_stage"], row.get("Product Type"), row.get("Loan Purpose"))
            if key in me_strat.index:
                return float(me_strat.loc[key, "p_fund"])
            if row["current_stage"] in me_unstrat.index:
                return float(me_unstrat.loc[row["current_stage"], "p_fund"])
            return 0.0

        active["p_strat"] = active.apply(_lookup_strat, axis=1)
        proj_strat = already_dollars + (active["p_strat"] * active["LoanAmount"]).sum()

        err_base = (proj_base - actual_month) / actual_month
        err_strat = (proj_strat - actual_month) / actual_month

        results.append({
            "Month": f"{year}-{month:02d}",
            "Actual": actual_month,
            "Proj_Base": proj_base,
            "Err_Base": err_base,
            "Proj_Strat": proj_strat,
            "Err_Strat": err_strat,
        })

    results_df = pd.DataFrame(results)

    # ── Figure ───────────────────────────────────────────────────────────
    if len(results_df) > 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(results_df))
        ax.bar([i - 0.15 for i in x], results_df["Err_Base"].abs() * 100,
               width=0.3, label="Stage only", color="#e74c3c", alpha=0.8)
        ax.bar([i + 0.15 for i in x], results_df["Err_Strat"].abs() * 100,
               width=0.3, label="+ Product/Purpose", color="#2ecc71", alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(results_df["Month"])
        ax.set_ylabel("Absolute Error (%)")
        ax.set_title("Projection Error: Stage Only vs Stratified")
        ax.legend()
        ax.axhline(10, color="gray", linestyle="--", alpha=0.5, label="10% target")
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "incremental_value_test.png", dpi=150)
        plt.close(fig)

    return results_df


# ─── 5. Stage fund rates: stratified vs baseline ────────────────────────────

def stage_fund_rate_chart(tables):
    """Bar chart comparing fund rates for key product/purpose combos."""
    unstrat = tables["unstratified"]
    strat = tables["stratified"]

    stages = ["Submitted", "Underwriting", "Approved", "Cond Review", "CTC"]
    combos = [
        ("NONCONFORMING", "Purchase"),
        ("FHA", "Purchase"),
        ("CONFORMING", "Purchase"),
    ]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(stages))
    width = 0.18

    # Baseline
    baseline_vals = [unstrat.loc[s, "p_fund"] * 100 if s in unstrat.index else 0 for s in stages]
    ax.bar(x - 1.5 * width, baseline_vals, width, label="Baseline (stage only)",
           color="#95a5a6", edgecolor="black", linewidth=0.5)

    colors = ["#3498db", "#e67e22", "#2ecc71"]
    for i, (prod, purp) in enumerate(combos):
        vals = []
        for s in stages:
            key = (s, prod, purp)
            if key in strat.index:
                vals.append(float(strat.loc[key, "p_fund"]) * 100)
            elif s in unstrat.index:
                vals.append(float(unstrat.loc[s, "p_fund"]) * 100)
            else:
                vals.append(0)
        ax.bar(x + (i - 0.5) * width, vals, width, label=f"{prod} / {purp}",
               color=colors[i], edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(stages)
    ax.set_ylabel("P(Fund) %")
    ax.set_title("Fund Probability by Stage — Baseline vs Stratified")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "stage_fund_rates_stratified.png", dpi=150)
    plt.close(fig)


# ─── Run full EDA ────────────────────────────────────────────────────────────

def run_full_eda(df):
    """Run all EDA analyses, print summaries, save figures."""

    print(f"\n{'═' * 70}")
    print("1. NUMERIC FEATURE CORRELATIONS WITH FUNDING OUTCOME")
    print(f"{'═' * 70}")
    corr_df = numeric_correlations(df)
    print(corr_df.to_string(index=False))
    print(f"\n  → Figure saved: {FIGURES_DIR / 'numeric_correlations.png'}")

    print(f"\n{'═' * 70}")
    print("2. CATEGORICAL FEATURE FUNDING-RATE SPREADS")
    print(f"{'═' * 70}")
    spread_df, detail = categorical_spreads(df)
    print(spread_df.to_string(index=False))

    # Show top 2 details
    for feat in spread_df["Feature"].head(2):
        print(f"\n  --- {feat} ---")
        sub = detail[feat]
        sub["FundRate"] = (sub["FundRate"] * 100).round(1)
        print(sub[sub["Count"] >= 20].head(10).to_string())
    print(f"\n  → Figure saved: {FIGURES_DIR / 'categorical_spreads.png'}")

    print(f"\n{'═' * 70}")
    print("3. TIME-AT-STAGE DISTRIBUTIONS (Funded vs Failed)")
    print(f"{'═' * 70}")
    time_df = time_at_stage_analysis(df)
    pivot = time_df.pivot(index="Duration", columns="Outcome", values="Median")
    print(pivot.to_string())
    print(f"\n  → Figure saved: {FIGURES_DIR / 'time_at_stage_distributions.png'}")

    print(f"\n{'═' * 70}")
    print("4. INCREMENTAL VARIABLE VALUE TEST")
    print(f"{'═' * 70}")
    incr_df = incremental_value_test(df)
    if len(incr_df) > 0:
        for _, row in incr_df.iterrows():
            print(f"  {row['Month']}  Actual: ${row['Actual']:>12,.0f}  "
                  f"Base: ${row['Proj_Base']:>12,.0f} ({row['Err_Base']:>+6.1%})  "
                  f"Strat: ${row['Proj_Strat']:>12,.0f} ({row['Err_Strat']:>+6.1%})")
        mape_base = incr_df["Err_Base"].abs().mean()
        mape_strat = incr_df["Err_Strat"].abs().mean()
        print(f"\n  MAPE (stage only):       {mape_base:.1%}")
        print(f"  MAPE (+ product/purpose): {mape_strat:.1%}")
        improvement = mape_base - mape_strat
        print(f"  Improvement:              {improvement:+.1%}")
    print(f"\n  → Figure saved: {FIGURES_DIR / 'incremental_value_test.png'}")

    # Stratified fund rate chart (needs transition tables)
    from transition_tables import build_transition_tables
    tables = build_transition_tables(df)
    stage_fund_rate_chart(tables)
    print(f"  → Figure saved: {FIGURES_DIR / 'stage_fund_rates_stratified.png'}")

    return {
        "correlations": corr_df,
        "categorical_spreads": spread_df,
        "time_at_stage": time_df,
        "incremental": incr_df,
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_prep import load_and_clean

    df = load_and_clean()
    run_full_eda(df)
    print(f"\n{'═' * 70}")
    print("EDA COMPLETE — all figures saved to outputs/figures/")
    print(f"{'═' * 70}")
