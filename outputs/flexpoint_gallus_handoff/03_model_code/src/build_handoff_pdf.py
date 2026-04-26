#!/usr/bin/env python3
"""
Build outputs/flexpoint_gallus_handoff/02_csv_exports/data_dictionary.pdf

Short bridge doc for the Gallus handoff. For each CSV it answers:
    1. What does this CSV contain? (one sentence)
    2. Which dashboard chart does it feed? (tab + visual)
    3. How do I build that chart in ThoughtSpot? (one-line recipe)

Usage:
    python src/build_handoff_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF

SRC = Path(__file__).resolve().parent
PROJECT = SRC.parent
sys.path.insert(0, str(PROJECT))

OUT_DIR = PROJECT / "outputs" / "flexpoint_gallus_handoff" / "02_csv_exports"
OUT_PATH = OUT_DIR / "data_dictionary.pdf"

NAVY = (20, 50, 90)
ACCENT = (30, 110, 170)
GREY = (95, 95, 95)
LIGHT = (235, 240, 248)
BODY = (45, 45, 45)

_UNICODE_TO_ASCII = {
    "—": "-", "–": "-", "−": "-",
    "→": "->", "←": "<-",
    "×": "x", "·": "-", "•": "-",
    "…": "...", "≤": "<=", "≥": ">=",
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    " ": " ",
}


def _clean(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    for k, v in _UNICODE_TO_ASCII.items():
        s = s.replace(k, v)
    return s


# ──────────────────────────────────────────────────────────────────────────
# Content. Column lists are written to match the actual CSV headers
# produced by export_for_thoughtspot.py — keep these in sync if you
# rename anything there.
# ──────────────────────────────────────────────────────────────────────────

FILES = [
    {
        "filename": "loans.csv",
        "star": True,
        "purpose": "Master per-loan table. Every other CSV aggregates this one or references it by LoanGuid.",
        "grain": "One row per active pipeline loan at snapshot_date (2025-12-15).",
        "dashboard": [
            ("Overview", "KPI tiles - count live loans, sum expected_value"),
            ("Overview", "Stage funnel - group by current_stage"),
            ("Watch List", "Loan table - filter is_at_risk = TRUE"),
            ("Revenue at Risk", "Moneyball bubble - moneyball_difficulty x ml_probability, size=LoanAmount"),
            ("Revenue at Risk", "Top recovery table - filter recovery_rank IS NOT NULL ORDER BY recovery_rank"),
            ("Any tab", "Drill-down target - join other CSVs back via LoanGuid"),
        ],
        "recipe": "Load as the base worksheet. Every other worksheet joins back to this on LoanGuid. Most dashboard charts are this table filtered + grouped.",
        "key_columns": [
            ("LoanGuid", "join key (used by every other CSV)"),
            ("LoanAmount, ml_probability, expected_value, base_probability", "core revenue metrics"),
            ("current_stage, stage_rank, days_at_stage", "where the loan is and how long it's been there"),
            ("Product Type, Branch Channel, Loan Purpose", "primary slicing dimensions"),
            ("status, is_at_risk, elimination_reason, failure_archetype, risk_reasons", "live/dead + risk filter flags"),
            ("recommended_action, counterfactual_probability, probability_delta, expected_value_uplift", "counterfactual recommendation"),
            ("moneyball_quadrant, moneyball_difficulty, moneyball_is_movable, moneyball_cf_quadrant", "Moneyball chart axes"),
            ("recovery_rank, recovery_gap, momentum_rank", "ranked subsets - filter NOT NULL for top-N tables"),
            ("velocity, velocity_band", "pipeline velocity classification"),
            ("f_* (31 columns)", "engineered features fed to the ML model (audit / debug)"),
            ("Loan Number, Loan Status, IsFunded, DecisionCreditScore, LTV, CLTV, NoteRate, Lock Period (days), ...", "raw passthrough columns from sectG (~150 fields)"),
        ],
    },
    {
        "filename": "already_funded.csv",
        "purpose": "Loans that funded earlier this month before the snapshot date - the 'already booked' part of the monthly total.",
        "grain": "One row per loan funded between Dec 1 and Dec 15, 2025.",
        "dashboard": [
            ("Overview", "Monthly total KPI - $68M already funded + $32.4M projected = ~$100M"),
            ("Overview", "Channel split for realized fundings"),
        ],
        "recipe": "Sum LoanAmount. Display next to sum(expected_value) from loans.csv to get the full monthly projection.",
        "key_columns": [
            ("snapshot_date, LoanGuid, Funded D", "identity + fund date"),
            ("LoanAmount", "amount to sum"),
            ("Product Type, Branch Channel, Loan Purpose", "breakdown dimensions"),
        ],
    },
    {
        "filename": "summary_kpis.csv",
        "purpose": "Single-row snapshot of every top-of-dashboard KPI value (pipeline counts, $ totals, pull-through, elimination breakdown).",
        "grain": "ONE row total. Wide format - each column is a different KPI value.",
        "dashboard": [("Overview", "KPI tile row (top of dashboard)")],
        "recipe": "Use as a one-row lookup table. Pin individual columns as KPI tiles - no aggregation needed.",
        "key_columns": [
            ("snapshot_date, month, model_used", "context"),
            ("total_pipeline_loans, total_pipeline_value, live_pipeline_loans, live_pipeline_value, dead_pipeline_loans, dead_pipeline_value", "pipeline counts + $"),
            ("already_funded_loans, already_funded_value, projected_total", "monthly projection"),
            ("overall_pull_through, median_cycle_days", "headline metrics"),
            ("elimination_total, elimination_count, elimination_pct, elim_opened_stale, elim_underwriting_unlocked_stale, elim_approved_expired_lock, elim_submitted_unlocked_stale, elim_application_stale", "elimination filter breakdown"),
        ],
    },
    {
        "filename": "stage_funnel.csv",
        "purpose": "Loan count and dollar volume at each pipeline stage.",
        "grain": "One row per pipeline stage.",
        "dashboard": [("Overview", "Pipeline funnel chart")],
        "recipe": "Column or funnel chart. X = stage (sorted by rank). Y = loan_count or total_value. Add live_loans / live_value as overlay.",
        "key_columns": [
            ("stage, rank", "X axis (rank = stage ordering)"),
            ("loan_count, total_value", "Y axis options"),
            ("live_loans, live_value, avg_probability", "live-pipeline subset"),
            ("snapshot_date", "as-of date"),
        ],
    },
    {
        "filename": "channel_split.csv",
        "purpose": "Wholesale vs Retail breakdown of pipeline volume.",
        "grain": "One row per Branch Channel.",
        "dashboard": [("Overview", "Channel split donut / bar")],
        "recipe": "Donut or bar. Category = Branch Channel. Value = loan_count or projected_value.",
        "key_columns": [
            ("Branch Channel", "category"),
            ("loan_count, total_value, projected_value, avg_probability", "metrics"),
            ("live_loans, live_value", "live-only subset"),
            ("snapshot_date", "as-of date"),
        ],
    },
    {
        "filename": "product_breakdown.csv",
        "purpose": "Pipeline volume by Product Type.",
        "grain": "One row per Product Type.",
        "dashboard": [("Overview", "Product mix bar chart")],
        "recipe": "Bar: X = Product Type, Y = loan_count or projected_value.",
        "key_columns": [
            ("Product Type", "category"),
            ("loan_count, total_value, projected_value, avg_probability", "metrics"),
            ("live_loans, live_value", "live-only subset"),
            ("snapshot_date", "as-of date"),
        ],
    },
    {
        "filename": "pull_through_monthly.csv",
        "purpose": "Historical monthly pull-through rate by product (% of loans opened in a month that eventually funded).",
        "grain": "One row per (month x Product Type).",
        "dashboard": [("Trends", "Monthly pull-through line chart")],
        "recipe": "Line. X = month. Y = pull_through_rate. Color by Product Type. Filter Product Type='Overall' for the headline line.",
        "key_columns": [
            ("month, Product Type", "axes (Product Type = 'Overall' = aggregate line)"),
            ("pull_through_rate, funded_count, total_count", "rate + counts"),
        ],
    },
    {
        "filename": "cycle_times_by_product.csv",
        "purpose": "Distribution stats (median, mean, percentiles) of total funded cycle time by product, with SLA-breach rate.",
        "grain": "One row per Product Type.",
        "dashboard": [("Trends", "Cycle time distributions with IQR bands")],
        "recipe": "Box-style bar. X = Product Type. Y = median. Error bars = p25 to p75 (or p10 to p90).",
        "key_columns": [
            ("Product Type, loan_count", "category + sample size"),
            ("median, mean, std, p10, p25, p75, p90", "distribution"),
            ("above_sla, above_sla_pct, sla_threshold_days", "SLA-breach stats"),
        ],
    },
    {
        "filename": "cycle_times_per_loan.csv",
        "purpose": "Per-loan total cycle time - the raw data behind the cycle-time charts.",
        "grain": "One row per funded loan.",
        "dashboard": [("Trends", "Histogram / scatter - raw distribution of cycle times")],
        "recipe": "Histogram of cycle_days. Or scatter: X = Funded D, Y = cycle_days, color = Product Type.",
        "key_columns": [
            ("LoanGuid", "join to loans.csv"),
            ("Product Type, Branch Channel, Loan Purpose", "slicing dimensions"),
            ("LoanAmount, Funded D, cycle_days", "main metrics"),
        ],
    },
    {
        "filename": "backtest_monthly.csv",
        "purpose": "Model accuracy vs actuals across 24 backtested months (Jan 2024 - Dec 2025).",
        "grain": "One row per (month x snapshot_day x method x training_mode).",
        "dashboard": [("Overview", "Backtest accuracy chart - projected vs actual")],
        "recipe": "Two-line chart. Filter method='ML' AND training_mode='rolling' AND snapshot_day=15. X = year-month. Y1 = projected, Y2 = actual. Secondary axis = error_pct.",
        "key_columns": [
            ("year, month, snapshot_day, method, training_mode", "filter to one series"),
            ("already_funded, projected_pipeline, projected, actual", "$ values"),
            ("error_pct, direction", "accuracy"),
        ],
    },
    {
        "filename": "revenue_at_risk_buckets.csv",
        "purpose": "Dollars at risk bucketed by failure archetype (lock expired, stuck, etc.).",
        "grain": "One row per risk bucket.",
        "dashboard": [("Revenue at Risk", "Risk bucket bar chart ($145M total)")],
        "recipe": "Horizontal bar. Category = label. Value = value_at_risk. Sort descending. Tooltip = description + action.",
        "key_columns": [
            ("id, label, description, action", "bucket identity + recommended action"),
            ("loan_count, total_value, expected_value, value_at_risk, avg_probability", "metrics (value_at_risk = bar height)"),
            ("_total_at_risk, _total_recovery_potential, _live_pipeline_value", "row-constant grand totals"),
        ],
    },
    {
        "filename": "moneyball_quadrant_summary.csv",
        "purpose": "Count and dollar value of loans in each Moneyball quadrant (easy_win / quick_fix / stretch / long_shot).",
        "grain": "One row per quadrant.",
        "dashboard": [("Revenue at Risk", "Moneyball quadrant legend / summary tiles")],
        "recipe": "4 KPI tiles, one per quadrant. Value = loan_count or total_value. Pair with the bubble chart from loans.csv.",
        "key_columns": [
            ("quadrant", "category"),
            ("loan_count, total_value, total_expected_value, avg_probability", "per-quadrant metrics"),
            ("movable_count, total_loans_all_quadrants, snapshot_date", "row-constant grand totals + as-of"),
        ],
    },
    {
        "filename": "bottleneck_heatmap.csv",
        "purpose": "Stage transition times by product with industry benchmarks - the Pipeline Health heatmap.",
        "grain": "One row per (transition x Product Type) cell.",
        "dashboard": [("Pipeline Health", "Main heatmap: transitions x products, colored by vs_benchmark")],
        "recipe": "Heatmap. Rows = transition. Columns = Product Type. Color cell = vs_benchmark (green=faster than industry, red=slower). Tooltip: median_days + p25/p75 + benchmark_median.",
        "key_columns": [
            ("transition, Product Type", "heatmap axes"),
            ("median_days, p25_days, p75_days, std_days", "FlexPoint cell + IQR"),
            ("benchmark_median, benchmark_fast, benchmark_slow, vs_benchmark", "industry comparison (vs_benchmark = days faster/slower)"),
        ],
    },
    {
        "filename": "stage_conversion_rates.csv",
        "purpose": "What % of loans that reach a stage actually fund (per product).",
        "grain": "One row per (Product Type x stage).",
        "dashboard": [("Pipeline Health", "Conversion funnel")],
        "recipe": "Funnel chart. Filter Product Type='Overall'. X = stage (ordered). Y = conversion_rate.",
        "key_columns": [
            ("Product Type, stage", "axes"),
            ("reached_count, funded_count, conversion_rate", "metrics"),
        ],
    },
    {
        "filename": "current_bottlenecks.csv",
        "purpose": "Where live loans are piling up right now (count of loans stuck per stage, with $ stuck).",
        "grain": "One row per (Product Type x stage). Top-ranked stages have rank populated.",
        "dashboard": [("Pipeline Health", "Current bottleneck pileup bar chart")],
        "recipe": "Bar. Filter Product Type='Overall'. X = stage. Y = loan_count. Color by pct_over_30d.",
        "key_columns": [
            ("Product Type, stage, rank", "axes (rank = bottleneck-severity rank)"),
            ("loan_count, total_value", "size of pileup"),
            ("avg_days_at_stage, median_days_at_stage, p25_days_at_stage, p75_days_at_stage", "how long they have been stuck"),
            ("avg_probability, pct_over_30d", "severity"),
            ("snapshot_date", "as-of"),
        ],
    },
    {
        "filename": "velocity_distribution.csv",
        "purpose": "Distribution of pipeline velocity bands (Fast / Normal / Slow / Stalled) by product.",
        "grain": "One row per (Product Type x band).",
        "dashboard": [("Pipeline Health", "Velocity distribution donut")],
        "recipe": "Donut. Filter Product Type='Overall'. Category = band. Value = loan_count or expected_value.",
        "key_columns": [
            ("Product Type, band", "axes"),
            ("loan_count, total_value, expected_value, avg_probability", "metrics"),
            ("snapshot_date", "as-of"),
        ],
    },
    {
        "filename": "velocity_by_stage.csv",
        "purpose": "Median velocity (and IQR) for live loans at each pipeline stage.",
        "grain": "One row per stage.",
        "dashboard": [("Pipeline Health", "Velocity by stage bar chart with IQR")],
        "recipe": "Bar. X = stage. Y = median_velocity. Error bars = p25_velocity to p75_velocity. Annotate avg_days_at_stage.",
        "key_columns": [
            ("stage, loan_count", "axes + sample size"),
            ("avg_velocity, median_velocity, p25_velocity, p75_velocity", "velocity distribution"),
            ("avg_days_at_stage, avg_probability, pct_stalled", "severity"),
        ],
    },
    {
        "filename": "what_if_scenarios.csv",
        "purpose": "Impact of 4 operational levers (lock improvements, channel-mix shifts, etc.) on projected fundings.",
        "grain": "One row per scenario.",
        "dashboard": [("What-If", "Scenario cards with raw vs overlap-adjusted values")],
        "recipe": "Card layout. Each card shows lever, description, current_state -> target_state, delta ($), pct_improvement, confidence. Footer = caveats.",
        "key_columns": [
            ("id, lever, description", "scenario identity"),
            ("current_state, target_state, current_value, improved_value", "scenario definition"),
            ("delta, pct_improvement, affected_loans, affected_value", "raw impact"),
            ("methodology, confidence, confidence_note, caveats", "trustworthiness"),
            ("_totals_* (8 columns)", "row-constant grand totals (raw + overlap-adjusted upside)"),
        ],
    },
    {
        "filename": "scorecards.csv",
        "purpose": "Balanced composite score (0-100) per product / channel with five sub-scores.",
        "grain": "One row per scorecard entity (product or channel).",
        "dashboard": [("Scorecards", "Product / channel scorecard grid")],
        "recipe": "Sortable table. Sort by rank (or composite_score desc). Color composite_score on a gradient. Tier = Elite/Strong/Average/Weak. Filter by dimension to split product vs channel boards.",
        "key_columns": [
            ("name, dimension, rank, tier, composite_score", "ranking"),
            ("sub_pull_through, sub_cycle_time, sub_revenue_efficiency, sub_trend, sub_pipeline_probability", "5 weighted sub-scores"),
            ("pull_through_rate, pt_recent_3m, pt_prior_3m, pt_trend_delta, pt_trend, median_cycle_days, avg_loan_amount, funded_volume_6m, pipeline_volume_6m, revenue_efficiency, current_active_loans, current_projected_value, avg_pipeline_probability, efficiency_score", "underlying raw values"),
            ("industry_benchmark_pt, industry_benchmark_cycle, benchmark_note", "industry comparison"),
        ],
    },
    {
        "filename": "optimization_recommendations.csv",
        "purpose": "Top ranked actions with estimated dollar impact (the 'tell me what to do' list).",
        "grain": "One row per recommendation.",
        "dashboard": [("Overview", "Recommendations panel at top of dashboard")],
        "recipe": "Ordered list / table. Sort by priority. Display: priority, title, description, estimated_impact, urgency, confidence_caveat.",
        "key_columns": [
            ("priority, title, description", "the action"),
            ("estimated_impact, effort, loan_count, category, urgency", "impact + effort"),
            ("confidence_caveat", "trust note"),
            ("_total_estimated_impact_all, snapshot_date", "row-constant grand total + as-of"),
        ],
    },
    {
        "filename": "industry_benchmarks_transitions.csv",
        "purpose": "ICE Mortgage Technology 2024 industry benchmarks for stage transitions by product.",
        "grain": "One row per (transition x Product Type).",
        "dashboard": [("Pipeline Health", "Reference data for heatmap overlay")],
        "recipe": "Lookup table. Already pre-joined into bottleneck_heatmap.csv as benchmark_median/fast/slow. Show standalone as a small reference table on the methodology page.",
        "key_columns": [
            ("transition, Product Type", "lookup keys"),
            ("benchmark_fast, benchmark_median, benchmark_slow", "industry stats"),
            ("source", "citation"),
        ],
    },
    {
        "filename": "feature_importance.csv",
        "purpose": "Model feature importance ranking - which features drive the predictions.",
        "grain": "One row per feature.",
        "dashboard": [("Not on dashboard", "Reference only - for model audit / explainability")],
        "recipe": "Horizontal bar chart sorted by importance desc. Top 10 typically shown.",
        "key_columns": [("feature, importance", "")],
    },
]

# ──────────────────────────────────────────────────────────────────────────
# PDF
# ──────────────────────────────────────────────────────────────────────────


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, "FlexPoint Pipeline Intelligence - CSV Data Dictionary",
                  ln=0, align="L")
        self.cell(0, 6, f"Page {self.page_no()}", ln=1, align="R")
        self.ln(2)

    def section_title(self, text, size=13, color=NAVY):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*color)
        self.cell(0, 8, _clean(text), ln=1)
        self.ln(1)

    def label_value(self, label, value):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.cell(28, 5, _clean(label), ln=0)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BODY)
        w = self.w - self.r_margin - self.get_x()
        self.multi_cell(w, 5, _clean(value))


def build_cover(pdf):
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 12, "FlexPoint Pipeline Intelligence", ln=1, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, "CSV Data Dictionary for Gallus Insights", ln=1, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + 15)
    pdf.multi_cell(
        pdf.w - 2 * pdf.l_margin - 30, 6,
        _clean(
            "This doc is a short bridge between the 22 CSVs in this folder "
            "and the FlexPoint dashboard (01_dashboard_reference.html). "
            "For each CSV you get: what it contains, which dashboard visual "
            "it feeds, and a one-line recipe for recreating that visual in "
            "ThoughtSpot. Open the HTML side-by-side with this PDF to see "
            "the target while you read."
        ),
        align="C",
    )

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "How to use the handoff bundle", ln=1, align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BODY)
    steps = [
        "1. Open 01_dashboard_reference.html in any browser - this is the visual target.",
        "2. Skim this PDF's CSV index on the next page.",
        "3. For each chart in ThoughtSpot, find the matching CSV entry, follow the recipe.",
        "4. loans.csv is the master fact table - everything else joins to it on LoanGuid.",
        "5. If you want to regenerate on fresh data, see 03_model_code/RUNBOOK.md.",
    ]
    for s in steps:
        pdf.set_x(pdf.l_margin + 15)
        pdf.multi_cell(pdf.w - 2 * pdf.l_margin - 30, 6, _clean(s))

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "Naming conventions across CSVs", ln=1, align="C")
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + 15)
    pdf.multi_cell(pdf.w - 2 * pdf.l_margin - 30, 5, _clean(
        "Same concept = same column name across every CSV. 'Branch Channel', "
        "'Product Type', 'LoanAmount', 'LoanGuid' use the raw sectG spelling "
        "(spaces, capitalization preserved) so they join cleanly. Counts use "
        "'loan_count'. Probabilities use 'avg_probability'. $ totals use "
        "'total_value' (overall) or 'expected_value' (probability-weighted)."
    ))

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, _clean("Snapshot date: 2025-12-15    |    Model: GradientBoosting v3 (5.8% MAPE backtest)"), ln=1, align="C")


def build_index(pdf):
    pdf.add_page()
    pdf.section_title("CSV Index - What Each File Is For", size=14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*BODY)

    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(55, 7, "CSV", border=0, fill=True)
    pdf.cell(40, 7, "Dashboard Tab", border=0, fill=True)
    pdf.cell(0, 7, "One-line purpose", ln=1, border=0, fill=True)
    pdf.ln(1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*BODY)
    col1, col2 = 55, 40
    col3 = pdf.w - pdf.l_margin - pdf.r_margin - col1 - col2
    for f in FILES:
        name = f["filename"] + ("  *" if f.get("star") else "")
        tab = f["dashboard"][0][0] if f["dashboard"] else "Reference"
        purpose_short = f["purpose"].split(".")[0] + "."

        if pdf.get_y() > pdf.h - 20:
            pdf.add_page()

        x0 = pdf.l_margin
        y0 = pdf.get_y()
        pdf.set_xy(x0, y0)
        pdf.set_font("Helvetica", "B" if f.get("star") else "", 8.5)
        pdf.cell(col1, 5, _clean(name), ln=0)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(col2, 5, _clean(tab), ln=0)
        pdf.multi_cell(col3, 5, _clean(purpose_short))

    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, _clean(
        "* = master fact table. All per-loan drill-down queries start here."
    ))


def build_file_entry(pdf, f):
    block_estimate = 80 + 5 * len(f["dashboard"]) + 5 * len(f["key_columns"])
    if pdf.get_y() + block_estimate > pdf.h - pdf.b_margin:
        pdf.add_page()

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    title = f["filename"]
    if f.get("star"):
        title += "   [MASTER TABLE]"
    pdf.cell(0, 7, _clean(title), ln=1)

    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(2)

    pdf.label_value("What it is:", f["purpose"])
    pdf.label_value("Grain:", f["grain"])

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "Dashboard chart(s) it feeds:", ln=1)
    for tab, chart in f["dashboard"]:
        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*ACCENT)
        pdf.cell(35, 5, _clean("[" + tab + "]"), ln=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*BODY)
        remain = pdf.w - pdf.r_margin - pdf.get_x()
        pdf.multi_cell(remain, 5, _clean(chart))

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "ThoughtSpot recipe:", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + 5)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 5, _clean(f["recipe"]))

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "Key columns:", ln=1)
    for col, note in f["key_columns"]:
        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*BODY)
        text = _clean(col)
        if note:
            text += " - " + _clean(note)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 5, text)

    pdf.ln(4)


def build_pdf():
    pdf = PDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=15, right=15)

    build_cover(pdf)
    build_index(pdf)

    pdf.add_page()
    pdf.section_title("CSV Details", size=14)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, _clean(
        "One entry per CSV. Open the HTML dashboard alongside this - the "
        "tab + chart name in each entry points to the visual you're trying "
        "to reproduce."
    ))
    pdf.ln(3)

    for f in FILES:
        build_file_entry(pdf, f)

    pdf.add_page()
    pdf.section_title("Quick reference: where does each dashboard tab's data come from?", size=12)
    tab_map = [
        ("Overview", "summary_kpis, stage_funnel, channel_split, product_breakdown, backtest_monthly, optimization_recommendations, already_funded + loans"),
        ("Watch List", "loans (filter is_at_risk = TRUE)"),
        ("Revenue at Risk", "revenue_at_risk_buckets, moneyball_quadrant_summary, loans (recovery_rank, moneyball_*)"),
        ("Pipeline Health", "bottleneck_heatmap, stage_conversion_rates, current_bottlenecks, velocity_distribution, velocity_by_stage, industry_benchmarks_transitions"),
        ("Trends", "pull_through_monthly, cycle_times_by_product, cycle_times_per_loan"),
        ("What-If", "what_if_scenarios"),
        ("Scorecards", "scorecards"),
    ]
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    for tab, csvs in tab_map:
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT)
        pdf.cell(38, 5, _clean(tab), ln=0)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 38, 5, _clean(csvs))
        pdf.ln(0.5)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "Questions while building?", ln=1)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5, _clean(
        "Reach out to Ajer (ajersher61@gmail.com). The most common questions "
        "are about the model column definitions (the f_* features in "
        "loans.csv) and the counterfactual recommendation logic - both are "
        "documented in 03_model_code/src/feature_engineering_v3.py and "
        "scorer.py if you want to dig in."
    ))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_PATH))
    print(f"Wrote {OUT_PATH} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    build_pdf()
