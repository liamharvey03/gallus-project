"""
Generate 7 figures for v2 presentation deck.
Run from project root: python generate_v2_figures.py
"""
import sys
import shutil
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# ─── Style constants ──────────────────────────────────────────────────────────
NAVY    = "#1E2761"
BLUE    = "#3B82F6"
GREEN   = "#10B981"
ORANGE  = "#F59E0B"
RED     = "#EF4444"
BLACK   = "#111111"
WHITE   = "#FFFFFF"
GRAY    = "#9CA3AF"

FIG_W, FIG_H = 10, 5.625  # 16:9
DPI = 150
FONT_FAMILY = "Calibri"

FIGURES_DIR = Path("outputs/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Try Calibri, fall back to sans-serif
try:
    from matplotlib.font_manager import FontProperties
    fp = FontProperties(family="Calibri")
    fp.get_name()
    plt.rcParams["font.family"] = "Calibri"
except Exception:
    plt.rcParams["font.family"] = "sans-serif"

plt.rcParams.update({
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "axes.edgecolor": GRAY,
    "axes.labelcolor": NAVY,
    "xtick.color": NAVY,
    "ytick.color": NAVY,
    "text.color": NAVY,
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": DPI,
})

# ─── Load data ────────────────────────────────────────────────────────────────
v2 = pd.read_csv("outputs/results/backtest_results_v2.csv")
v1 = pd.read_csv("outputs/results/backtest_results.csv")
fi = pd.read_csv("outputs/results/feature_importance_v2.csv")

# Helper: month label
def month_label(year, month):
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{months[int(month)-1]} {str(int(year))[-2:]}"

# Build ordered month list from v2 data
all_months = sorted(v2[["year","month"]].drop_duplicates().values.tolist())
month_labels = [month_label(y, m) for y, m in all_months]
x = np.arange(len(all_months))


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1: Day-15 Projections vs Actual Monthly Funding
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 1: Projected vs Actual...")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

actuals = []
v2_fixed_proj = []
v1_proj = []

for yr, mo in all_months:
    # Actual (from v2 fixed, day 15)
    row = v2[(v2["year"]==yr) & (v2["month"]==mo) &
             (v2["snapshot_day"]==15) & (v2["method"]=="ML") &
             (v2["training_mode"]=="fixed")]
    actuals.append(row.iloc[0]["actual"] / 1e6 if len(row) else np.nan)
    v2_fixed_proj.append(row.iloc[0]["projected"] / 1e6 if len(row) else np.nan)

    # v1 ML day 15
    row_v1 = v1[(v1["year"]==yr) & (v1["month"]==mo) &
                (v1["snapshot_day"]==15) & (v1["method"]=="ML")]
    v1_proj.append(row_v1.iloc[0]["projected"] / 1e6 if len(row_v1) else np.nan)

ax.plot(x, actuals, "o-", color=BLACK, linewidth=2.2, markersize=5,
        label="Actual", zorder=3)
ax.plot(x, v1_proj, "o--", color=NAVY, linewidth=1.5, markersize=4,
        label="v1 ML", alpha=0.8)
ax.plot(x, v2_fixed_proj, "o--", color=ORANGE, linewidth=1.5, markersize=4,
        label="v2 ML (Fixed)")

ax.set_xticks(x)
ax.set_xticklabels(month_labels, rotation=45, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}M"))
ax.set_ylabel("Monthly Funding ($M)", fontsize=10, fontweight="bold")
ax.set_title("Day-15 Projections vs Actual Monthly Funding",
             fontsize=13, fontweight="bold", pad=12)
ax.legend(loc="upper left", fontsize=9, frameon=True, facecolor=WHITE,
          edgecolor=GRAY)

# Subtle horizontal reference lines
for tick in ax.get_yticks():
    ax.axhline(tick, color="#E5E7EB", linewidth=0.5, zorder=0)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_backtest_projected_vs_actual.png", dpi=DPI,
            facecolor=WHITE)
plt.close(fig)
print("  Saved v2_backtest_projected_vs_actual.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2: Projection Error by Month (Day 15)
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 2: Error by Month...")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

width = 0.25
v1_errs = []
v2f_errs = []
v2r_errs = []

for yr, mo in all_months:
    # v1
    r = v1[(v1["year"]==yr) & (v1["month"]==mo) &
           (v1["snapshot_day"]==15) & (v1["method"]=="ML")]
    v1_errs.append(r.iloc[0]["error_pct"] if len(r) else 0)
    # v2 fixed
    r = v2[(v2["year"]==yr) & (v2["month"]==mo) &
           (v2["snapshot_day"]==15) & (v2["method"]=="ML") &
           (v2["training_mode"]=="fixed")]
    v2f_errs.append(r.iloc[0]["error_pct"] if len(r) else 0)
    # v2 rolling
    r = v2[(v2["year"]==yr) & (v2["month"]==mo) &
           (v2["snapshot_day"]==15) & (v2["method"]=="ML") &
           (v2["training_mode"]=="rolling")]
    v2r_errs.append(r.iloc[0]["error_pct"] if len(r) else 0)

ax.bar(x - width, v1_errs, width, label="v1 ML", color=NAVY, alpha=0.85)
ax.bar(x,         v2f_errs, width, label="v2 Fixed ML", color=BLUE, alpha=0.85)
ax.bar(x + width, v2r_errs, width, label="v2 Rolling ML", color=GREEN, alpha=0.85)

ax.axhline(10, color=RED, linewidth=1.2, linestyle="--", alpha=0.7, zorder=4)
ax.axhline(-10, color=RED, linewidth=1.2, linestyle="--", alpha=0.7, zorder=4)
ax.axhline(0, color=NAVY, linewidth=0.6, alpha=0.4)

# Label the target lines
ax.text(len(all_months) - 0.5, 11.2, "+10% target", color=RED,
        fontsize=7, ha="right", alpha=0.8)
ax.text(len(all_months) - 0.5, -12.5, "−10% target", color=RED,
        fontsize=7, ha="right", alpha=0.8)

ax.set_xticks(x)
ax.set_xticklabels(month_labels, rotation=45, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v:+.0f}%"))
ax.set_ylabel("Error (%)", fontsize=10, fontweight="bold")
ax.set_title("Projection Error by Month (Day 15)",
             fontsize=13, fontweight="bold", pad=12)
ax.legend(loc="upper left", fontsize=9, frameon=True, facecolor=WHITE,
          edgecolor=GRAY)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_error_by_month.png", dpi=DPI, facecolor=WHITE)
plt.close(fig)
print("  Saved v2_error_by_month.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3: Average Error by Snapshot Day
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 3: MAPE by Snapshot Day...")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

snap_days = [0, 1, 8, 15, 22]
width = 0.22

v1_mapes = []
v2f_mapes = []
v2r_mapes = []

for day in snap_days:
    # v1 (no day 0)
    if day == 0:
        v1_mapes.append(np.nan)
    else:
        sub = v1[(v1["method"]=="ML") & (v1["snapshot_day"]==day)]
        v1_mapes.append(sub["error_pct"].abs().mean() if len(sub) else np.nan)
    # v2 fixed
    sub = v2[(v2["method"]=="ML") & (v2["snapshot_day"]==day) &
             (v2["training_mode"]=="fixed")]
    v2f_mapes.append(sub["error_pct"].abs().mean() if len(sub) else np.nan)
    # v2 rolling
    sub = v2[(v2["method"]=="ML") & (v2["snapshot_day"]==day) &
             (v2["training_mode"]=="rolling")]
    v2r_mapes.append(sub["error_pct"].abs().mean() if len(sub) else np.nan)

xd = np.arange(len(snap_days))
day_labels = [f"Day {d}" for d in snap_days]

bars1 = ax.bar(xd - width, v1_mapes, width, label="v1 ML", color=NAVY,
               alpha=0.85)
bars2 = ax.bar(xd,         v2f_mapes, width, label="v2 Fixed ML", color=BLUE,
               alpha=0.85)
bars3 = ax.bar(xd + width, v2r_mapes, width, label="v2 Rolling ML",
               color=GREEN, alpha=0.85)

# Value labels on top
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        if np.isnan(h) or h == 0:
            continue
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                f"{h:.1f}%", ha="center", va="bottom", fontsize=8,
                fontweight="bold", color=NAVY)

ax.set_xticks(xd)
ax.set_xticklabels(day_labels, fontsize=10)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v:.0f}%"))
ax.set_ylabel("MAPE (%)", fontsize=10, fontweight="bold")
ax.set_title("Average Error by Snapshot Day",
             fontsize=13, fontweight="bold", pad=12)
ax.legend(loc="upper right", fontsize=9, frameon=True, facecolor=WHITE,
          edgecolor=GRAY)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_mape_by_snapshot_day.png", dpi=DPI,
            facecolor=WHITE)
plt.close(fig)
print("  Saved v2_mape_by_snapshot_day.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4: Feature Importance (v2)
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 4: Feature Importance...")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

top12 = fi.head(12).copy()
top12 = top12.iloc[::-1]  # reverse for horizontal bar (top at top)

# Plain English labels
label_map = {
    "lock_expiry_vs_month_end": "Lock expiry vs month-end",
    "days_at_stage": "Days at current stage",
    "stage_only_probability": "Pipeline stage probability",
    "days_until_lock_expiry": "Days until lock expires",
    "lock_period": "Lock period",
    "credit_score": "Credit score",
    "loan_amount": "Loan amount",
    "note_rate": "Interest rate",
    "cltv": "Combined LTV",
    "days_remaining": "Days left in month",
    "days_since_lock": "Days since lock",
    "stage_rank": "Stage rank (ordinal)",
    "ltv": "Loan-to-value",
    "is_locked": "Is rate locked",
    "lock_already_expired": "Lock already expired",
}

# Color categories
lock_features = {"lock_expiry_vs_month_end", "days_until_lock_expiry",
                 "lock_period", "is_locked", "lock_already_expired",
                 "days_since_lock"}
stage_features = {"stage_only_probability", "days_at_stage",
                  "days_remaining", "stage_rank"}
loan_features = {"credit_score", "loan_amount", "ltv", "cltv", "note_rate"}

def get_color(feat):
    if feat in lock_features:
        return ORANGE
    if feat in stage_features:
        return BLUE
    if feat in loan_features:
        return NAVY
    return GREEN  # product/purpose categoricals

def get_label(feat):
    if feat in label_map:
        return label_map[feat]
    # Clean up categorical names
    clean = feat.replace("_", " ").replace("loan purpose ", "Purpose: ") \
                .replace("product type ", "Product: ") \
                .replace("branch channel ", "Channel: ") \
                .replace("occupancy type ", "Occupancy: ")
    return clean.title() if not any(c == ":" for c in clean) else clean

labels = [get_label(f) for f in top12["feature"]]
colors = [get_color(f) for f in top12["feature"]]
values = top12["importance"].values

y_pos = np.arange(len(labels))
bars = ax.barh(y_pos, values, color=colors, height=0.65, alpha=0.9)

# Percentage labels at end of bars
for i, (bar, val) in enumerate(zip(bars, values)):
    pct = val * 100
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
            f"{pct:.1f}%", ha="left", va="center", fontsize=8.5,
            fontweight="bold", color=NAVY)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Feature Importance", fontsize=10, fontweight="bold")
ax.set_title("What Drives the Prediction (v2)",
             fontsize=13, fontweight="bold", pad=12)
ax.set_xlim(0, max(values) * 1.18)

# Legend for color categories
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=ORANGE, alpha=0.9, label="Rate Lock"),
    Patch(facecolor=BLUE,   alpha=0.9, label="Stage / Time"),
    Patch(facecolor=NAVY,   alpha=0.9, label="Loan Characteristics"),
    Patch(facecolor=GREEN,  alpha=0.9, label="Product / Purpose"),
]
ax.legend(handles=legend_elements, loc="lower right", fontsize=8,
          frameon=True, facecolor=WHITE, edgecolor=GRAY)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_feature_importance.png", dpi=DPI,
            facecolor=WHITE)
plt.close(fig)
print("  Saved v2_feature_importance.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5: Nov–Dec 2025 Improvement
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 5: Nov–Dec Improvement...")

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

target_months = [(2025, 11, "Nov 2025"), (2025, 12, "Dec 2025")]
width = 0.22
xnd = np.arange(len(target_months))

v1_vals = []
v2f_vals = []
v2r_vals = []

for yr, mo, _ in target_months:
    r = v1[(v1["year"]==yr) & (v1["month"]==mo) &
           (v1["snapshot_day"]==15) & (v1["method"]=="ML")]
    v1_vals.append(r.iloc[0]["error_pct"] if len(r) else 0)

    r = v2[(v2["year"]==yr) & (v2["month"]==mo) &
           (v2["snapshot_day"]==15) & (v2["method"]=="ML") &
           (v2["training_mode"]=="fixed")]
    v2f_vals.append(r.iloc[0]["error_pct"] if len(r) else 0)

    r = v2[(v2["year"]==yr) & (v2["month"]==mo) &
           (v2["snapshot_day"]==15) & (v2["method"]=="ML") &
           (v2["training_mode"]=="rolling")]
    v2r_vals.append(r.iloc[0]["error_pct"] if len(r) else 0)

bars1 = ax.bar(xnd - width, v1_vals, width, label="v1 ML", color=NAVY,
               alpha=0.85)
bars2 = ax.bar(xnd,         v2f_vals, width, label="v2 Fixed ML", color=BLUE,
               alpha=0.85)
bars3 = ax.bar(xnd + width, v2r_vals, width, label="v2 Rolling ML",
               color=GREEN, alpha=0.85)

# Value labels
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        offset = 0.5 if h >= 0 else -1.5
        ax.text(bar.get_x() + bar.get_width()/2, h + offset,
                f"{h:+.1f}%", ha="center", va="bottom", fontsize=10,
                fontweight="bold", color=NAVY)

ax.axhline(10, color=RED, linewidth=1.2, linestyle="--", alpha=0.7, zorder=4)
ax.axhline(0, color=NAVY, linewidth=0.6, alpha=0.4)
ax.text(1.45, 10.8, "10% target", color=RED, fontsize=9, ha="right",
        alpha=0.8)

ax.set_xticks(xnd)
ax.set_xticklabels([lbl for _, _, lbl in target_months], fontsize=12)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v:+.0f}%"))
ax.set_ylabel("Error (%)", fontsize=10, fontweight="bold")
ax.set_title("Nov\u2013Dec 2025: v1 vs v2 Error (Day 15)",
             fontsize=13, fontweight="bold", pad=12)
ax.legend(loc="upper left", fontsize=9, frameon=True, facecolor=WHITE,
          edgecolor=GRAY)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_nov_dec_improvement.png", dpi=DPI,
            facecolor=WHITE)
plt.close(fig)
print("  Saved v2_nov_dec_improvement.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6: Rate Lock Coverage by Pipeline Stage
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 6: Lock Diagnostic (computing from raw data)...")

import config
from data_prep import load_and_clean
from transition_tables import vectorized_current_stage

df = load_and_clean()

# Build snapshot at Oct 15 2025
as_of = pd.Timestamp(2025, 10, 15)

opened_mask = df["Loan Open Date"].notna() & (df["Loan Open Date"] <= as_of)
not_funded_mask = df["Funded D"].isna() | (df["Funded D"] > as_of)
not_failed_mask = pd.Series(True, index=df.index)
for col in config.FAILURE_DATE_COLUMNS:
    if col in df.columns:
        not_failed_mask &= df[col].isna() | (df[col] > as_of)

active = df[opened_mask & not_funded_mask & not_failed_mask].copy()

sl, sr, se = vectorized_current_stage(active, as_of)
active["current_stage"] = sl
active["stage_rank"] = sr
active = active[active["current_stage"].notna()].copy()

# Compute lock rate: Rate Lock D non-null and <= as_of
active["is_locked"] = (
    active["Rate Lock D"].notna() & (active["Rate Lock D"] <= as_of)
).astype(int)

# Stages in pipeline order (exclude Funded)
stage_order = [
    ("Opened", 0), ("Application", 1), ("Submitted", 2),
    ("Underwriting", 3), ("Approved", 4), ("Cond Review", 5),
    ("Final UW", 6), ("CTC", 7), ("Docs", 8),
    ("Fund Cond", 10), ("Sched Fund", 11),
]

stage_labels = []
lock_rates = []
counts = []

for label, rank in stage_order:
    sub = active[active["stage_rank"] == rank]
    if len(sub) > 0:
        rate = sub["is_locked"].mean() * 100
    else:
        rate = 0
    stage_labels.append(label)
    lock_rates.append(rate)
    counts.append(len(sub))

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

# Gradient from light blue to deep navy
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("lock_grad", ["#93C5FD", NAVY])
norm_vals = [r / 100 for r in lock_rates]
bar_colors = [cmap(v) for v in norm_vals]

xs = np.arange(len(stage_labels))
bars = ax.bar(xs, lock_rates, color=bar_colors, width=0.65, alpha=0.9)

# Value labels on top
for bar, rate, n in zip(bars, lock_rates, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f"{rate:.0f}%", ha="center", va="bottom", fontsize=9,
            fontweight="bold", color=NAVY)

# Annotation for Approved
approved_idx = stage_labels.index("Approved")
approved_rate = lock_rates[approved_idx]
ax.annotate(
    f"{approved_rate:.0f}% locked\nKey differentiation zone",
    xy=(approved_idx, approved_rate),
    xytext=(approved_idx + 2.2, approved_rate + 12),
    fontsize=9, fontweight="bold", color=ORANGE,
    arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.8),
    ha="center",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEF3C7",
              edgecolor=ORANGE, alpha=0.9),
)

ax.set_xticks(xs)
ax.set_xticklabels(stage_labels, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("% of Active Loans with Rate Lock", fontsize=10,
              fontweight="bold")
ax.set_title("Rate Lock Coverage by Pipeline Stage",
             fontsize=13, fontweight="bold", pad=12)
ax.set_ylim(0, 110)

fig.tight_layout()
fig.savefig(FIGURES_DIR / "v2_lock_diagnostic.png", dpi=DPI, facecolor=WHITE)
plt.close(fig)
print("  Saved v2_lock_diagnostic.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 7: Copy existing stage_fund_rates_stratified.png
# ═══════════════════════════════════════════════════════════════════════════════
print("Figure 7: Copying existing figure...")

src = FIGURES_DIR / "stage_fund_rates_stratified.png"
dst = FIGURES_DIR / "v2_stage_fund_rates_stratified.png"
if src.exists():
    shutil.copy2(src, dst)
    print(f"  Copied → {dst}")
else:
    print(f"  WARNING: {src} not found, skipping copy")


# ═══════════════════════════════════════════════════════════════════════════════
# DONE — list all v2 figures
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("ALL FIGURES GENERATED")
print("=" * 60)
import os
for f in sorted(FIGURES_DIR.glob("v2_*.png")):
    size_kb = os.path.getsize(f) / 1024
    print(f"  {f.name:<45s} {size_kb:>6.0f} KB")
