"""
FlexPoint Step 5 — Failure Analysis & v3 Charts
=================================================
Part A: Failure segmentation (terminal stage, failure reason, archetypes)
Part B: Funded vs unfunded comparison
Part C: Generate all v3 charts (failure + model performance)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# Use Calibri if available, fall back to sans-serif
FONT_FAMILY = "Calibri"
try:
    from matplotlib.font_manager import findfont, FontProperties
    if findfont(FontProperties(family=FONT_FAMILY)) == findfont(FontProperties()):
        FONT_FAMILY = "sans-serif"
except Exception:
    FONT_FAMILY = "sans-serif"

# ── project imports ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from data_prep import load_and_clean

# ── visual style constants ──────────────────────────────────────────────────
NAVY   = "#1E2761"
BLUE   = "#3B82F6"
GREEN  = "#10B981"
ORANGE = "#F59E0B"
RED    = "#EF4444"
GRAY   = "#6B7280"
LIGHT_GRAY = "#D1D5DB"

FIG_DIR = config.OUTPUTS_PATH / "figures" / "v3"
FIG_DIR.mkdir(parents=True, exist_ok=True)

def _style_ax(ax, title, xlabel="", ylabel=""):
    """Apply consistent styling to axes."""
    ax.set_title(title, fontsize=14, fontweight="bold", color=NAVY, pad=12,
                 fontfamily=FONT_FAMILY)
    ax.set_xlabel(xlabel, fontsize=11, color=NAVY, fontfamily=FONT_FAMILY)
    ax.set_ylabel(ylabel, fontsize=11, color=NAVY, fontfamily=FONT_FAMILY)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LIGHT_GRAY)
    ax.spines["bottom"].set_color(LIGHT_GRAY)
    ax.tick_params(colors=GRAY, labelsize=9)
    ax.set_facecolor("white")
    ax.grid(False)

def _save(fig, name):
    path = FIG_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Stage map: column → (label, rank), ordered highest first
STAGE_LIST = [(col, label, rank) for col, label, rank in config.STAGE_MAP
              if label != "Funded"]  # exclude Funded stage for failure analysis

def terminal_stage(row):
    """Return the highest pipeline stage the loan reached."""
    for col, label, rank in STAGE_LIST:
        if col in row.index and pd.notna(row[col]):
            return label, rank
    return "Unknown", -1

def days_in_pipeline(row):
    """Days from Loan Open Date to earliest terminal event or last stage date."""
    open_dt = row.get("Loan Open Date")
    if pd.isna(open_dt):
        return np.nan
    # Check terminal events
    end_dt = None
    for col in ["Loan Canceled D", "Loan Denied D", "Withdrawn D", "Loan Suspended D"]:
        if col in row.index and pd.notna(row[col]):
            if end_dt is None or row[col] < end_dt:
                end_dt = row[col]
    if end_dt is None:
        # Use latest stage date as proxy
        for col, _, _ in STAGE_LIST:
            if col in row.index and pd.notna(row[col]):
                end_dt = row[col]
                break
    if end_dt is None:
        return np.nan
    return (end_dt - open_dt).days


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("STEP 5 — FAILURE ANALYSIS & V3 CHARTS")
    print("=" * 70)

    # ── Load data ───────────────────────────────────────────────────────────
    df = load_and_clean()

    funded = df[df["Outcome"] == "Funded"].copy()
    unfunded = df[df["Outcome"] != "Funded"].copy()  # Failed + Active
    failed = df[df["Outcome"] == "Failed"].copy()
    print(f"\nFunded: {len(funded):,}  |  Unfunded: {len(unfunded):,}  |  Failed: {len(failed):,}")

    # ── Compute terminal stage for all unfunded loans ───────────────────────
    print("\nComputing terminal stages...")
    ts_results = unfunded.apply(terminal_stage, axis=1)
    unfunded["terminal_stage"] = ts_results.apply(lambda x: x[0])
    unfunded["terminal_rank"] = ts_results.apply(lambda x: x[1])

    # Also for funded loans (they all reach Funded, but track highest pre-fund stage)
    ts_funded = funded.apply(terminal_stage, axis=1)
    funded["terminal_stage"] = ts_funded.apply(lambda x: x[0])
    funded["terminal_rank"] = ts_funded.apply(lambda x: x[1])

    # ── Days in pipeline ────────────────────────────────────────────────────
    print("Computing days in pipeline...")
    unfunded["days_in_pipeline"] = unfunded.apply(days_in_pipeline, axis=1)
    funded["days_in_pipeline"] = funded.apply(
        lambda r: (r["Funded D"] - r["Loan Open Date"]).days
        if pd.notna(r.get("Funded D")) and pd.notna(r.get("Loan Open Date")) else np.nan,
        axis=1
    )

    # ── Lock status ─────────────────────────────────────────────────────────
    unfunded["had_lock"] = unfunded["Rate Lock D"].notna()
    funded["had_lock"] = funded["Rate Lock D"].notna()

    # ── Failure reason ──────────────────────────────────────────────────────
    def failure_reason(row):
        if row.get("WasDenied") == 1 or row.get("WasDenied") == "1":
            return "Denied"
        if row.get("WasWithdrawn") == 1 or row.get("WasWithdrawn") == "1":
            return "Withdrawn"
        if row.get("WasSuspended") == 1 or row.get("WasSuspended") == "1":
            return "Suspended"
        if row.get("WasOnHold") == 1 or row.get("WasOnHold") == "1":
            return "On Hold"
        if row.get("WasCanceled") == 1 or row.get("WasCanceled") == "1":
            return "Canceled"
        # Fallback to Loan Status
        status = row.get("Loan Status", "")
        if "Denied" in str(status):
            return "Denied"
        if "Withdrawn" in str(status):
            return "Withdrawn"
        if "Cancel" in str(status):
            return "Canceled"
        return "Other"

    unfunded["failure_reason"] = unfunded.apply(failure_reason, axis=1)

    # =====================================================================
    # PART A: FAILURE SEGMENTATION
    # =====================================================================
    print("\n" + "=" * 70)
    print("PART A: FAILURE SEGMENTATION")
    print("=" * 70)

    # ── A.1: By Terminal Stage ──────────────────────────────────────────────
    print("\n─── A.1: Failures by Terminal Stage ───")
    stage_order = ["Opened", "Application", "Submitted", "Underwriting",
                   "Approved", "Cond Review", "Final UW", "CTC", "Docs",
                   "Docs Back", "Fund Cond", "Sched Fund"]
    stage_counts = unfunded.groupby("terminal_stage").agg(
        count=("terminal_stage", "size"),
        median_days=("days_in_pipeline", "median"),
        median_amount=("LoanAmount", "median"),
        lock_rate=("had_lock", "mean"),
    ).reindex([s for s in stage_order if s in unfunded["terminal_stage"].values])
    stage_counts["pct"] = (stage_counts["count"] / len(unfunded) * 100).round(1)

    # Most common product type per terminal stage
    mode_product = unfunded.groupby("terminal_stage")["Product Type"].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "N/A"
    )
    mode_channel = unfunded.groupby("terminal_stage")["Branch Channel"].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "N/A"
    )
    stage_counts["top_product"] = mode_product
    stage_counts["top_channel"] = mode_channel

    print(f"\n{'Stage':<15} {'Count':>6} {'%':>6} {'Med Days':>9} {'Med $':>10} {'Lock%':>6} {'Top Product':<18} {'Channel':<12}")
    print("─" * 95)
    for stage in stage_counts.index:
        r = stage_counts.loc[stage]
        print(f"{stage:<15} {r['count']:>6.0f} {r['pct']:>5.1f}% {r['median_days']:>8.0f}d "
              f"${r['median_amount']:>9,.0f} {r['lock_rate']:>5.0%} {r['top_product']:<18} {r['top_channel']:<12}")

    # ── A.2: By Failure Reason ──────────────────────────────────────────────
    print("\n─── A.2: Failures by Reason ───")
    reason_stats = unfunded.groupby("failure_reason").agg(
        count=("failure_reason", "size"),
        median_days=("days_in_pipeline", "median"),
        median_amount=("LoanAmount", "median"),
    )
    reason_stats["pct"] = (reason_stats["count"] / len(unfunded) * 100).round(1)
    reason_stats = reason_stats.sort_values("count", ascending=False)

    print(f"\n{'Reason':<12} {'Count':>6} {'%':>6} {'Med Days':>9}")
    print("─" * 40)
    for reason in reason_stats.index:
        r = reason_stats.loc[reason]
        print(f"{reason:<12} {r['count']:>6.0f} {r['pct']:>5.1f}% {r['median_days']:>8.0f}d")

    # Failure reason by terminal stage cross-tab
    print("\n─── Failure Reason × Terminal Stage ───")
    ct = pd.crosstab(unfunded["terminal_stage"], unfunded["failure_reason"])
    ct = ct.reindex([s for s in stage_order if s in ct.index])
    ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
    print(ct_pct.round(1).to_string())

    # Denied vs Canceled speed
    print("\n─── Denied vs Canceled: Speed Comparison ───")
    for reason in ["Denied", "Canceled", "Withdrawn", "Suspended"]:
        subset = unfunded[unfunded["failure_reason"] == reason]
        if len(subset) > 10:
            med = subset["days_in_pipeline"].median()
            p25 = subset["days_in_pipeline"].quantile(0.25)
            p75 = subset["days_in_pipeline"].quantile(0.75)
            print(f"  {reason:<12}: median {med:.0f}d  (p25={p25:.0f}, p75={p75:.0f})  n={len(subset)}")

    # ── A.3: Failure Archetypes ─────────────────────────────────────────────
    print("\n─── A.3: Failure Archetypes ───")

    # Compute lock expiry status
    unfunded["lock_expired"] = (
        unfunded["Rate Lock Expiration D"].notna() &
        (unfunded["Rate Lock Expiration D"] < unfunded.apply(
            lambda r: r.get("Loan Canceled D") or r.get("Loan Denied D") or
                      r.get("Withdrawn D") or r.get("Loan Suspended D") or
                      pd.Timestamp("2026-01-01"),
            axis=1
        ))
    )

    archetypes = []

    # 1. Early Dropout — never past Submitted, gone in <21 days
    mask_early = (
        (unfunded["terminal_rank"] <= 2) &
        (unfunded["days_in_pipeline"] < 21)
    )
    archetypes.append({
        "name": "Early Dropout",
        "desc": "Never made it past Submitted, gone within 3 weeks — likely lost interest or found another lender",
        "mask": mask_early,
    })

    # 2. Stale at Underwriting — reached UW but sat 30+ days, never progressed
    mask_stale_uw = (
        (unfunded["terminal_stage"].isin(["Underwriting", "Submitted"])) &
        (unfunded["terminal_rank"] <= 3) &
        (unfunded["days_in_pipeline"] >= 30) &
        (~unfunded["had_lock"])
    )
    archetypes.append({
        "name": "Stale Pre-Approval",
        "desc": "Reached Submitted/UW but sat 30+ days unlocked — processing bottleneck or borrower disengaged",
        "mask": mask_stale_uw,
    })

    # 3. Denied at Underwriting — denied, terminal stage at or before Approved
    mask_denied = (
        (unfunded["failure_reason"] == "Denied") &
        (unfunded["terminal_rank"] <= 4)
    )
    archetypes.append({
        "name": "Underwriting Denial",
        "desc": "Denied during underwriting — didn't meet credit, income, or property requirements",
        "mask": mask_denied,
    })

    # 4. Stale at Approved — reached Approved, sat 30+ days, never locked
    mask_stale_app = (
        (unfunded["terminal_stage"] == "Approved") &
        (unfunded["days_in_pipeline"] >= 30) &
        (~unfunded["had_lock"])
    )
    archetypes.append({
        "name": "Stale at Approved",
        "desc": "Approved but never locked a rate, sat 30+ days — rate shopping or lost to competitor",
        "mask": mask_stale_app,
    })

    # 5. Lock Expired — had a lock that expired, never made it past Approved
    mask_lock_exp = (
        unfunded["lock_expired"] &
        (unfunded["terminal_rank"] <= 4)
    )
    archetypes.append({
        "name": "Lock Expired, Gave Up",
        "desc": "Locked a rate but lock expired before progressing past Approved — deal fell apart",
        "mask": mask_lock_exp,
    })

    # 6. Late-Stage Surprise — made it to CTC or beyond but then failed
    mask_late = (
        (unfunded["terminal_rank"] >= 7)  # CTC or later
    )
    archetypes.append({
        "name": "Late-Stage Surprise",
        "desc": "Reached CTC or beyond then failed — title issues, appraisal problems, or last-minute borrower withdrawal",
        "mask": mask_late,
    })

    # 7. Opened-Only Ghost — never even hit Application
    mask_ghost = (
        (unfunded["terminal_stage"] == "Opened") &
        (unfunded["terminal_rank"] == 0)
    )
    archetypes.append({
        "name": "Opened-Only Ghost",
        "desc": "File opened but never progressed to Application — lead that never converted to real loan",
        "mask": mask_ghost,
    })

    # 8. Long Pipeline, Eventually Canceled — 45+ days, reached Cond Review or Final UW
    mask_long = (
        (unfunded["terminal_stage"].isin(["Cond Review", "Final UW"])) &
        (unfunded["days_in_pipeline"] >= 45)
    )
    archetypes.append({
        "name": "Long Pipeline Dropout",
        "desc": "Made it to Cond Review/Final UW after 45+ days — conditions couldn't be cleared or borrower exhausted",
        "mask": mask_long,
    })

    # Assign archetypes (first match wins, no double-counting)
    unfunded["archetype"] = "Unclassified"
    assigned = pd.Series(False, index=unfunded.index)
    for arch in archetypes:
        new_mask = arch["mask"] & ~assigned
        unfunded.loc[new_mask, "archetype"] = arch["name"]
        assigned = assigned | new_mask

    print(f"\n{'Archetype':<25} {'Count':>6} {'%':>6} {'Med $':>10} {'Med Days':>9} Description")
    print("─" * 110)
    for arch in archetypes:
        subset = unfunded[unfunded["archetype"] == arch["name"]]
        n = len(subset)
        pct = n / len(unfunded) * 100
        med_amt = subset["LoanAmount"].median()
        med_days = subset["days_in_pipeline"].median()
        print(f"{arch['name']:<25} {n:>6} {pct:>5.1f}% ${med_amt:>9,.0f} {med_days:>8.0f}d  {arch['desc']}")

    unclass = unfunded[unfunded["archetype"] == "Unclassified"]
    print(f"{'Unclassified':<25} {len(unclass):>6} {len(unclass)/len(unfunded)*100:>5.1f}%")

    # =====================================================================
    # PART B: FUNDED vs UNFUNDED COMPARISON
    # =====================================================================
    print("\n" + "=" * 70)
    print("PART B: FUNDED vs UNFUNDED COMPARISON")
    print("=" * 70)

    # ── B.1: Days at each stage ─────────────────────────────────────────────
    print("\n─── B.1: Days-at-Stage Comparison ───")
    key_stages = [
        ("Submitted D", "Underwriting D", "Submitted → UW"),
        ("Underwriting D", "Approved D", "UW → Approved"),
        ("Approved D", "Clear To Close D", "Approved → CTC"),
        ("Clear To Close D", "Funded D", "CTC → Funded"),
    ]
    for col_start, col_end, label in key_stages:
        for group_name, group_df in [("Funded", funded), ("Failed", failed)]:
            if col_start in group_df.columns and col_end in group_df.columns:
                dur = (group_df[col_end] - group_df[col_start]).dt.days
                dur = dur.dropna()
                dur = dur[(dur >= 0) & (dur < 365)]
                if len(dur) > 10:
                    print(f"  {label:<20} {group_name:<8}: median {dur.median():>5.0f}d  "
                          f"mean {dur.mean():>5.1f}d  n={len(dur)}")

    # ── B.2: Lock rate by stage ─────────────────────────────────────────────
    print("\n─── B.2: Lock Rate by Terminal Stage ───")
    print(f"  {'Stage':<15} {'Funded Lock%':>12} {'Unfunded Lock%':>14}")
    print("  " + "─" * 45)
    for stage in stage_order:
        f_sub = funded[funded["terminal_stage"] == stage]
        u_sub = unfunded[unfunded["terminal_stage"] == stage]
        f_lock = f_sub["had_lock"].mean() if len(f_sub) > 10 else np.nan
        u_lock = u_sub["had_lock"].mean() if len(u_sub) > 10 else np.nan
        if not (np.isnan(f_lock) and np.isnan(u_lock)):
            f_str = f"{f_lock:.0%}" if not np.isnan(f_lock) else "n/a"
            u_str = f"{u_lock:.0%}" if not np.isnan(u_lock) else "n/a"
            print(f"  {stage:<15} {f_str:>12} {u_str:>14}")

    # ── B.3: Product type distribution ──────────────────────────────────────
    print("\n─── B.3: Product Type Distribution ───")
    f_prod = funded["Product Type"].value_counts(normalize=True).head(8) * 100
    u_prod = unfunded["Product Type"].value_counts(normalize=True).head(8) * 100
    all_prods = sorted(set(f_prod.index) | set(u_prod.index))
    print(f"  {'Product':<22} {'Funded%':>8} {'Unfunded%':>10}")
    print("  " + "─" * 42)
    for p in all_prods:
        f_v = f_prod.get(p, 0)
        u_v = u_prod.get(p, 0)
        print(f"  {p:<22} {f_v:>7.1f}% {u_v:>9.1f}%")

    # ── B.4: Credit score distribution ──────────────────────────────────────
    print("\n─── B.4: Credit Score Distribution ───")
    for name, grp in [("Funded", funded), ("Unfunded", unfunded)]:
        cs = grp["DecisionCreditScore"].dropna()
        print(f"  {name:<10}: median {cs.median():.0f}  mean {cs.mean():.0f}  "
              f"p25={cs.quantile(.25):.0f}  p75={cs.quantile(.75):.0f}  n={len(cs)}")

    # ── B.5: Loan amount distribution ───────────────────────────────────────
    print("\n─── B.5: Loan Amount Distribution ───")
    for name, grp in [("Funded", funded), ("Unfunded", unfunded)]:
        la = grp["LoanAmount"].dropna()
        print(f"  {name:<10}: median ${la.median():,.0f}  mean ${la.mean():,.0f}  "
              f"p25=${la.quantile(.25):,.0f}  p75=${la.quantile(.75):,.0f}")

    # =====================================================================
    # PART C: GENERATE CHARTS
    # =====================================================================
    print("\n" + "=" * 70)
    print("PART C: GENERATING CHARTS")
    print("=" * 70)

    # ── Chart 1: Failure by Terminal Stage ──────────────────────────────────
    print("\n─── Chart 1: Failure by Terminal Stage ───")
    fig, ax = plt.subplots(figsize=(16, 9))
    stage_data = stage_counts.sort_values("count", ascending=True)
    n_stages = len(stage_data)
    # Color gradient: RED for early stages (high rank) → ORANGE for later
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("red_orange", [ORANGE, RED])
    colors = [cmap(1.0 - i / max(n_stages - 1, 1)) for i in range(n_stages)]
    bars = ax.barh(range(n_stages), stage_data["count"], color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(n_stages))
    ax.set_yticklabels(stage_data.index, fontfamily=FONT_FAMILY, fontsize=11)
    for i, (cnt, pct) in enumerate(zip(stage_data["count"], stage_data["pct"])):
        ax.text(cnt + len(unfunded) * 0.008, i, f"{cnt:,.0f} ({pct:.1f}%)",
                va="center", fontsize=10, color=NAVY, fontfamily=FONT_FAMILY)
    _style_ax(ax, "Where Unfunded Loans Die: Terminal Stage Distribution",
              xlabel="Number of Unfunded Loans")
    _save(fig, "v3_failure_by_stage.png")

    # ── Chart 2: Failure Archetypes ─────────────────────────────────────────
    print("─── Chart 2: Failure Archetypes ───")
    fig, ax = plt.subplots(figsize=(16, 9))
    arch_names = [a["name"] for a in archetypes]
    arch_counts = [len(unfunded[unfunded["archetype"] == a["name"]]) for a in archetypes]
    arch_pcts = [c / len(unfunded) * 100 for c in arch_counts]
    # Sort by count descending
    sorted_idx = sorted(range(len(arch_counts)), key=lambda i: arch_counts[i], reverse=True)
    arch_names_s = [arch_names[i] for i in sorted_idx]
    arch_counts_s = [arch_counts[i] for i in sorted_idx]
    arch_pcts_s = [arch_pcts[i] for i in sorted_idx]

    arch_colors = [RED, "#DC2626", ORANGE, "#D97706", BLUE, "#6366F1", NAVY, GRAY]
    bars = ax.barh(range(len(arch_names_s)), arch_counts_s,
                   color=[arch_colors[i % len(arch_colors)] for i in range(len(arch_names_s))],
                   edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(arch_names_s)))
    ax.set_yticklabels(arch_names_s, fontfamily=FONT_FAMILY, fontsize=11)
    for i, (cnt, pct) in enumerate(zip(arch_counts_s, arch_pcts_s)):
        ax.text(cnt + len(unfunded) * 0.008, i, f"{cnt:,.0f} ({pct:.1f}%)",
                va="center", fontsize=10, color=NAVY, fontfamily=FONT_FAMILY)
    ax.invert_yaxis()
    _style_ax(ax, "Failure Archetypes: Why Loans Don't Fund",
              xlabel="Number of Unfunded Loans")
    _save(fig, "v3_failure_archetypes.png")

    # ── Chart 3: Funded vs Unfunded Days-at-Stage ───────────────────────────
    print("─── Chart 3: Funded vs Unfunded Days-at-Stage ───")
    fig, axes = plt.subplots(1, 4, figsize=(16, 9), sharey=False)
    stage_pairs = [
        ("Submitted D", "Underwriting D", "Submitted"),
        ("Underwriting D", "Approved D", "Underwriting"),
        ("Approved D", "Clear To Close D", "Approved"),
        ("Clear To Close D", "Docs D", "CTC"),
    ]
    for i, (col_s, col_e, label) in enumerate(stage_pairs):
        ax = axes[i]
        data_sets = []
        labels = []
        colors_bp = []
        for grp_name, grp_df, clr in [("Funded", funded, GREEN), ("Unfunded", unfunded, RED)]:
            if col_s in grp_df.columns and col_e in grp_df.columns:
                dur = (grp_df[col_e] - grp_df[col_s]).dt.days.dropna()
                dur = dur[(dur >= 0) & (dur < 120)]
                if len(dur) > 10:
                    data_sets.append(dur.values)
                    labels.append(grp_name)
                    colors_bp.append(clr)
        if data_sets:
            bp = ax.boxplot(data_sets, patch_artist=True, widths=0.6,
                           medianprops=dict(color=NAVY, linewidth=2),
                           whiskerprops=dict(color=GRAY),
                           capprops=dict(color=GRAY),
                           flierprops=dict(marker=".", markersize=2, color=GRAY, alpha=0.3))
            for patch, color in zip(bp["boxes"], colors_bp):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            ax.set_xticklabels(labels, fontfamily=FONT_FAMILY, fontsize=9)
        _style_ax(ax, label, ylabel="Days" if i == 0 else "")
    fig.suptitle("Days-at-Stage: Funded vs Unfunded Loans", fontsize=14,
                 fontweight="bold", color=NAVY, fontfamily=FONT_FAMILY, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, "v3_funded_vs_unfunded_days.png")

    # ── Chart 4: Failure Timeline ───────────────────────────────────────────
    print("─── Chart 4: Failure Timeline ───")
    fig, ax = plt.subplots(figsize=(16, 9))
    reason_colors = {"Canceled": RED, "Denied": ORANGE, "Withdrawn": BLUE, "Suspended": NAVY}
    max_days = 180
    x_days = np.arange(0, max_days + 1)
    for reason, color in reason_colors.items():
        subset = unfunded[unfunded["failure_reason"] == reason]["days_in_pipeline"].dropna()
        subset = subset[subset >= 0]
        if len(subset) < 10:
            continue
        cum_pct = [(subset <= d).sum() / len(subset) * 100 for d in x_days]
        ax.plot(x_days, cum_pct, color=color, linewidth=2.5, label=f"{reason} (n={len(subset):,})")
    ax.set_xlim(0, max_days)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=11, frameon=False, loc="lower right")
    ax.axhline(50, color=LIGHT_GRAY, linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axhline(90, color=LIGHT_GRAY, linestyle="--", linewidth=0.8, alpha=0.5)
    _style_ax(ax, "When Do Failures Happen? Cumulative % by Failure Reason",
              xlabel="Days in Pipeline", ylabel="Cumulative % of Failures")
    _save(fig, "v3_failure_timeline.png")

    # ── Chart 5: Lock vs No-Lock Among Unfunded ─────────────────────────────
    print("─── Chart 5: Lock vs No-Lock Among Unfunded ───")
    fig, ax = plt.subplots(figsize=(16, 9))
    lock_by_stage = unfunded.groupby("terminal_stage")["had_lock"].agg(["sum", "count"])
    lock_by_stage = lock_by_stage.reindex([s for s in stage_order if s in lock_by_stage.index])
    lock_by_stage["no_lock"] = lock_by_stage["count"] - lock_by_stage["sum"]

    x = np.arange(len(lock_by_stage))
    w = 0.6
    ax.bar(x, lock_by_stage["sum"], w, label="Had Rate Lock", color=BLUE, edgecolor="white")
    ax.bar(x, lock_by_stage["no_lock"], w, bottom=lock_by_stage["sum"],
           label="No Rate Lock", color=LIGHT_GRAY, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(lock_by_stage.index, rotation=45, ha="right",
                       fontfamily=FONT_FAMILY, fontsize=10)
    # Add lock % labels
    for i, (locked, total) in enumerate(zip(lock_by_stage["sum"], lock_by_stage["count"])):
        pct = locked / total * 100 if total > 0 else 0
        ax.text(i, total + total * 0.02, f"{pct:.0f}%",
                ha="center", va="bottom", fontsize=9, color=NAVY, fontfamily=FONT_FAMILY)
    ax.legend(fontsize=11, frameon=False, loc="upper right")
    _style_ax(ax, "Rate Lock Status Among Unfunded Loans by Terminal Stage",
              ylabel="Number of Loans")
    _save(fig, "v3_lock_vs_nofund.png")

    # ─────────────────────────────────────────────────────────────────────
    # MODEL PERFORMANCE CHARTS
    # ─────────────────────────────────────────────────────────────────────

    # ── Chart 6: Feature Importance (v3) ────────────────────────────────────
    print("─── Chart 6: Feature Importance ───")
    fi_path = config.OUTPUTS_PATH / "results" / "feature_importance_v3.csv"
    if fi_path.exists():
        fi = pd.read_csv(fi_path)
        fi = fi[fi["importance"] > 0].head(15).sort_values("importance", ascending=True)
        fig, ax = plt.subplots(figsize=(16, 9))
        colors_fi = [BLUE if imp < fi["importance"].quantile(0.75) else NAVY
                     for imp in fi["importance"]]
        ax.barh(range(len(fi)), fi["importance"], color=colors_fi, edgecolor="white")
        ax.set_yticks(range(len(fi)))
        ax.set_yticklabels([f.replace("_", " ").title() for f in fi["feature"]],
                           fontfamily=FONT_FAMILY, fontsize=10)
        for i, v in enumerate(fi["importance"]):
            ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=9,
                    color=NAVY, fontfamily=FONT_FAMILY)
        _style_ax(ax, "v3 Model: Top 15 Feature Importances (GBM)",
                  xlabel="Importance")
        _save(fig, "v3_feature_importance.png")

    # ── Chart 7: Backtest Projected vs Actual (Day 15) ──────────────────────
    print("─── Chart 7: Backtest Projected vs Actual ───")
    bt_path = config.OUTPUTS_PATH / "results" / "backtest_results_v3.csv"
    if bt_path.exists():
        bt = pd.read_csv(bt_path)
        bt_d15 = bt[(bt["snapshot_day"] == 15) & (bt["method"] == "ML")].copy()
        bt_d15["month_label"] = bt_d15.apply(
            lambda r: f"{int(r['year'])}-{int(r['month']):02d}", axis=1)

        fig, ax = plt.subplots(figsize=(16, 9))
        x = range(len(bt_d15))
        ax.plot(x, bt_d15["actual"] / 1e6, color=NAVY, linewidth=2.5,
                marker="o", markersize=6, label="Actual", zorder=3)
        ax.plot(x, bt_d15["projected"] / 1e6, color=BLUE, linewidth=2.5,
                marker="s", markersize=5, label="v3 Projected", zorder=3)
        ax.fill_between(x, bt_d15["actual"] / 1e6, bt_d15["projected"] / 1e6,
                        alpha=0.1, color=BLUE)
        ax.set_xticks(x)
        ax.set_xticklabels(bt_d15["month_label"], rotation=45, ha="right",
                           fontfamily=FONT_FAMILY, fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}M"))
        ax.legend(fontsize=11, frameon=False, loc="upper left")
        _style_ax(ax, "v3 Monthly Backtest: Projected vs Actual Fundings (Day 15)",
                  ylabel="Funding Volume ($M)")
        _save(fig, "v3_backtest_projected_vs_actual.png")

    # ── Chart 8: Elimination Filter Impact ──────────────────────────────────
    print("─── Chart 8: Elimination Filter Impact ───")
    ef_path = config.OUTPUTS_PATH / "results" / "elimination_filter_results.csv"
    if ef_path.exists():
        ef = pd.read_csv(ef_path)
        ef_d15 = ef[(ef["snapshot_day"] == 15)].copy()
        # Get ML_with_filter rows for elimination counts
        ef_filt = ef_d15[ef_d15["method"] == "ML_with_filter"].copy()
        ef_filt["month_label"] = ef_filt.apply(
            lambda r: f"{int(r['year'])}-{int(r['month']):02d}", axis=1)

        fig, ax = plt.subplots(figsize=(16, 9))
        x = np.arange(len(ef_filt))
        remaining = ef_filt["active_loans"] - ef_filt["eliminated"].fillna(0)
        ax.bar(x, remaining, label="Active (kept)", color=BLUE, edgecolor="white")
        ax.bar(x, ef_filt["eliminated"].fillna(0), bottom=remaining,
               label="Eliminated (dead)", color=RED, alpha=0.7, edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels(ef_filt["month_label"], rotation=45, ha="right",
                           fontfamily=FONT_FAMILY, fontsize=9)
        # Add % eliminated labels
        for i, (elim, total) in enumerate(zip(ef_filt["eliminated"].fillna(0), ef_filt["active_loans"])):
            if elim > 0:
                pct = elim / total * 100
                ax.text(i, total + 10, f"{pct:.0f}%", ha="center", va="bottom",
                        fontsize=8, color=RED, fontfamily=FONT_FAMILY)
        ax.legend(fontsize=11, frameon=False, loc="upper left")
        _style_ax(ax, "Elimination Filter Impact: Pipeline Composition at Day 15",
                  ylabel="Number of Loans")
        _save(fig, "v3_elimination_filter_impact.png")

    # ── Chart 9: Weekly Funding Distribution ────────────────────────────────
    print("─── Chart 9: Weekly Funding Distribution ───")
    tm_path = config.OUTPUTS_PATH / "results" / "timing_model_results.csv"
    if tm_path.exists():
        tm = pd.read_csv(tm_path)
        # Compute actual weekly distribution across all months
        actual_by_week = tm[tm["snapshot_day"] == 0].groupby("week")["actual"].sum()
        total_actual = actual_by_week.sum()
        week_pcts = (actual_by_week / total_actual * 100)
        weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
        week_pcts = week_pcts.reindex(weeks)

        fig, ax = plt.subplots(figsize=(16, 9))
        week_colors = [BLUE, BLUE, BLUE, NAVY]
        bars = ax.bar(range(4), week_pcts, color=week_colors, edgecolor="white",
                      width=0.6)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["Week 1\n(Days 1-7)", "Week 2\n(Days 8-14)",
                            "Week 3\n(Days 15-21)", "Week 4\n(Days 22-EOM)"],
                           fontfamily=FONT_FAMILY, fontsize=11)
        for i, pct in enumerate(week_pcts):
            ax.text(i, pct + 0.5, f"{pct:.1f}%", ha="center", va="bottom",
                    fontsize=14, fontweight="bold", color=NAVY, fontfamily=FONT_FAMILY)
        ax.set_ylim(0, max(week_pcts) * 1.15)
        _style_ax(ax, "Monthly Funding Distribution by Week (Actual, 2024-2025)",
                  ylabel="% of Monthly Fundings")
        # Add annotation about back-loading
        ax.annotate("Funding is heavily back-loaded:\nWeek 4 alone accounts for ~38% of volume",
                    xy=(3, week_pcts.iloc[3]), xytext=(1.5, week_pcts.iloc[3] * 0.85),
                    fontsize=10, color=GRAY, fontfamily=FONT_FAMILY,
                    arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.2))
        _save(fig, "v3_weekly_funding_distribution.png")

    # ── Chart 10: Stage-to-Funding Durations ────────────────────────────────
    print("─── Chart 10: Stage-to-Funding Durations ───")
    dur_path = config.OUTPUTS_PATH / "results" / "stage_to_funding_durations.csv"
    if dur_path.exists():
        dur = pd.read_csv(dur_path)
        dur = dur.sort_values("median", ascending=True)

        fig, ax = plt.subplots(figsize=(16, 9))
        y = range(len(dur))
        ax.barh(y, dur["median"], color=BLUE, edgecolor="white", height=0.6, zorder=3)
        # Error bars for p25-p75
        ax.errorbar(dur["median"], y,
                    xerr=[dur["median"] - dur["p25"], dur["p75"] - dur["median"]],
                    fmt="none", ecolor=NAVY, elinewidth=1.5, capsize=4, capthick=1.5,
                    zorder=4)
        ax.set_yticks(y)
        ax.set_yticklabels(dur["stage"], fontfamily=FONT_FAMILY, fontsize=11)
        for i, (med, p75) in enumerate(zip(dur["median"], dur["p75"])):
            ax.text(p75 + 1, i, f"{med:.0f}d", va="center", fontsize=10,
                    color=NAVY, fontfamily=FONT_FAMILY)
        _style_ax(ax, "Days from Stage to Funding (Median with p25-p75 Range)",
                  xlabel="Days")
        _save(fig, "v3_stage_to_funding_durations.png")

    # ── Chart 11: MAPE by Snapshot Day (v2 vs v3) ──────────────────────────
    print("─── Chart 11: MAPE by Snapshot Day ───")
    bt_v2_path = config.OUTPUTS_PATH / "results" / "backtest_results_v2.csv"
    bt_v3_path = config.OUTPUTS_PATH / "results" / "backtest_results_v3.csv"
    if bt_v2_path.exists() and bt_v3_path.exists():
        bt_v2 = pd.read_csv(bt_v2_path)
        bt_v3 = pd.read_csv(bt_v3_path)

        snap_days = [0, 1, 8, 15, 22]
        v2_mapes = []
        v3_mapes = []
        for d in snap_days:
            v2_d = bt_v2[(bt_v2["snapshot_day"] == d) & (bt_v2["method"] == "ML")]
            v3_d = bt_v3[(bt_v3["snapshot_day"] == d) & (bt_v3["method"] == "ML")]
            v2_mapes.append(v2_d["error_pct"].abs().mean())
            v3_mapes.append(v3_d["error_pct"].abs().mean())

        fig, ax = plt.subplots(figsize=(16, 9))
        x = np.arange(len(snap_days))
        w = 0.35
        ax.bar(x - w/2, v2_mapes, w, label="v2 Model", color=LIGHT_GRAY, edgecolor="white")
        ax.bar(x + w/2, v3_mapes, w, label="v3 Model", color=BLUE, edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Day {d}" for d in snap_days], fontfamily=FONT_FAMILY, fontsize=11)
        for i, (v2, v3) in enumerate(zip(v2_mapes, v3_mapes)):
            ax.text(i - w/2, v2 + 0.3, f"{v2:.1f}%", ha="center", fontsize=9,
                    color=GRAY, fontfamily=FONT_FAMILY)
            ax.text(i + w/2, v3 + 0.3, f"{v3:.1f}%", ha="center", fontsize=9,
                    color=NAVY, fontfamily=FONT_FAMILY)
        ax.legend(fontsize=11, frameon=False, loc="upper right")
        ax.axhline(10, color=GREEN, linestyle="--", linewidth=1, alpha=0.5, label="10% target")
        _style_ax(ax, "MAPE by Snapshot Day: v2 vs v3 Model",
                  xlabel="Snapshot Day", ylabel="MAPE (%)")
        _save(fig, "v3_mape_by_snapshot_day.png")

    # ── Chart 12: Timing Accuracy by Snapshot ───────────────────────────────
    print("─── Chart 12: Timing Accuracy by Snapshot ───")
    if tm_path.exists():
        tm = pd.read_csv(tm_path)
        # Compute weekly MAPE for Historical and GBM at each snapshot day
        snap_days_tm = [0, 8, 15]
        approaches = ["Historical", "GBM"]
        approach_colors = {
            "Historical": ORANGE,
            "GBM": BLUE,
        }

        fig, ax = plt.subplots(figsize=(16, 9))
        x = np.arange(len(snap_days_tm))
        w = 0.3
        for j, approach in enumerate(approaches):
            mapes = []
            for d in snap_days_tm:
                subset = tm[(tm["snapshot_day"] == d) & (tm["approach"] == approach) &
                           (tm["is_known"] == False)]
                subset = subset.dropna(subset=["projected", "actual", "error_pct"])
                if len(subset) > 0:
                    mapes.append(subset["error_pct"].abs().mean())
                else:
                    mapes.append(0)
            offset = (j - 0.5) * w
            bars = ax.bar(x + offset, mapes, w, label=approach,
                         color=approach_colors[approach], edgecolor="white")
            for i, v in enumerate(mapes):
                ax.text(i + offset, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10,
                        color=NAVY, fontfamily=FONT_FAMILY, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([f"Day {d}" for d in snap_days_tm],
                           fontfamily=FONT_FAMILY, fontsize=12)
        ax.legend(fontsize=11, frameon=False, loc="upper right")
        _style_ax(ax, "Weekly Timing MAPE: Historical vs GBM by Snapshot Day",
                  xlabel="Snapshot Day", ylabel="Mean Weekly MAPE (%)")
        # Add annotation about crossover
        ax.annotate("GBM outperforms Historical\nat later snapshots",
                    xy=(2, 5), fontsize=10, color=GRAY, fontfamily=FONT_FAMILY,
                    ha="center")
        _save(fig, "v3_timing_accuracy_by_snapshot.png")

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FILES CREATED")
    print("=" * 70)
    created = sorted(FIG_DIR.glob("*.png"))
    for f in created:
        print(f"  {f.name}")
    print(f"\nTotal: {len(created)} charts saved to {FIG_DIR}/")


if __name__ == "__main__":
    main()
