#!/usr/bin/env python3
"""
Build outputs/thoughtspot_export/data_dictionary.pdf — a plain-English guide
to every CSV in the ThoughtSpot export bundle.

For each file: purpose, grain (what one row represents), ideal visualizations,
and a table describing every column (name / type / description / why it
matters). For `loans.csv` columns are grouped into buckets to stay readable.

Usage:
    python src/build_data_dictionary_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF

SRC = Path(__file__).resolve().parent
PROJECT = SRC.parent
sys.path.insert(0, str(PROJECT))
import config

OUT_DIR = config.OUTPUTS_PATH / "thoughtspot_export"
OUT_PATH = OUT_DIR / "data_dictionary.pdf"

NAVY  = (20, 50, 90)
GREY  = (90, 90, 90)
LIGHT = (230, 235, 245)
BODY  = (50, 50, 50)


# ───────────────────────── content as data ──────────────────────────────────
# Each file: purpose, grain, visuals, and a list of column dicts or
# (group_header, [cols]) tuples. Columns as tuples of
# (name, type, description, value).

FILES = [
    # ─────────────────────────── loans.csv ─────────────────────────────────
    {
        "filename": "loans.csv",
        "purpose": "The master per-loan table. Every other CSV either aggregates "
                   "this one or references it by LoanGuid. Load it as your "
                   "primary fact table in ThoughtSpot.",
        "grain": "One row per active pipeline loan at snapshot_date. Active "
                 "means the loan is opened and has not yet funded, been "
                 "cancelled, denied, or withdrawn. Includes both 'live' loans "
                 "and 'dead' loans (flagged by the elimination filter but not "
                 "yet archived by ops).",
        "visuals": [
            "Overview KPI tiles (count live loans, sum expected_value)",
            "Stage funnel (group by current_stage)",
            "Watch List table (filter is_at_risk=true)",
            "Moneyball bubble chart (moneyball_difficulty × ml_probability, size=LoanAmount)",
            "Any product / channel / stage / loan-officer breakdown",
            "Drill-down from any aggregate chart — join back via LoanGuid",
        ],
        "columns_grouped": [
            ("Identity & snapshot", [
                ("snapshot_date", "date", "The pipeline 'as-of' date this row reflects.", "Lets you append multiple daily/weekly runs without overwriting history."),
                ("LoanGuid", "text", "Unique loan identifier from Encompass.", "Primary join key. Use it to link to your own loan tables."),
                ("Loan Number", "text", "Human-readable loan number (e.g. 82511086).", "Easier for ops to reference than the GUID."),
            ]),
            ("What kind of loan", [
                ("Product Type", "text", "Mortgage product family: NONCONFORMING, CONFORMING, FHA, VA, 2ND, etc.", "Primary segmentation — every analytic breaks out by this."),
                ("Loan Purpose", "text", "Purchase, Refinance, Refinance CashOut.", "Purchase loans close faster than refis — useful cut."),
                ("Branch Channel", "text", "Wholesale or Retail.", "Wholesale funds at ~42%, Retail ~10% — huge behavioural split."),
                ("LoanAmount", "number", "Loan face value in dollars.", "Revenue metric — multiply by probability to get expected dollars."),
                ("Loan Type", "text", "Conventional / FHA / VA (regulatory category).", "Related to Product Type but coarser."),
                ("Occupancy Type", "text", "Primary / Investment / Secondary.", "Investment loans have different risk profile."),
                ("Property State", "text", "State the property is in.", "Geographic segmentation."),
            ]),
            ("Where the loan is right now", [
                ("current_stage", "text", "Where the loan is in the pipeline (Opened, Submitted, Underwriting, Approved, Cond Review, Final UW, CTC, Docs, Docs Back, Fund Cond, Sched Fund).", "The single most important feature — drives almost all visuals."),
                ("stage_rank", "integer 0-12", "Numeric order of current_stage. Higher = closer to funding.", "Use for sorting stages on the funnel chart."),
                ("days_at_stage", "integer", "Days the loan has been sitting at its current stage.", "Loans stuck >30 days at a mid-pipeline stage are at high dropout risk."),
                ("status", "text", "'live' or 'dead'. Dead = elimination filter flagged it.", "Filter live loans for the 'real' pipeline view."),
                ("elimination_reason", "text", "If dead, which rule fired (opened_stale, lock_already_expired, etc.).", "Explains why ops should archive the loan."),
                ("failure_archetype", "text", "Human-readable label for the failure pattern (e.g. 'Lock Expired, Gave Up').", "Good for pie chart of dead-loan categories."),
            ]),
            ("Model outputs", [
                ("ml_probability", "decimal 0–1", "ML model's estimate of funding by month-end.", "Core prediction. Multiply by LoanAmount = expected dollars."),
                ("expected_value", "number (dollars)", "ml_probability × LoanAmount.", "Sum this across live loans = projected fundings from pipeline."),
                ("base_probability", "decimal 0–1", "Stratified baseline (stage × product × purpose) before ML refinement.", "For comparing ML uplift vs the naive baseline."),
            ]),
            ("Counterfactual recommendation (what to DO)", [
                ("is_at_risk", "bool", "True if the loan matched any of 5 watch-list criteria.", "Filter WHERE is_at_risk = TRUE to get the full Watch List table."),
                ("risk_reasons", "text (| separated)", "Plain-English reasons the loan is flagged, e.g. 'Rate lock expires within 7 days — still at Approved'.", "Tooltip / table column."),
                ("recommended_action", "text", "Best single action to take (e.g. 'Secure rate lock (30-day)').", "The 'tell me what to do' column Augie asked for."),
                ("counterfactual_probability", "decimal 0–1", "Re-scored probability if the recommended_action is taken.", "Compare to ml_probability — shows the lift."),
                ("probability_delta", "decimal 0–1", "counterfactual_probability − ml_probability.", "How much the action moves the needle."),
                ("expected_value_uplift", "number (dollars)", "probability_delta × LoanAmount.", "Dollar impact of the action. Rank by this to prioritise ops."),
            ]),
            ("Ranked-subset flags (replace separate CSVs)", [
                ("recovery_rank", "integer (1-12) or null", "Ranking among the top 12 loans by recovery gap (null for all other loans).", "Filter WHERE recovery_rank IS NOT NULL ORDER BY recovery_rank for the Revenue-at-Risk recovery table."),
                ("recovery_gap", "number (dollars) or null", "LoanAmount − expected_value for the top-12 recovery loans.", "Ranking value. Only populated for recovery_rank rows."),
                ("momentum_rank", "integer (1-15) or null", "Ranking among the top 15 slow-moving high-value loans (null for all others).", "Filter WHERE momentum_rank IS NOT NULL ORDER BY momentum_rank for the Velocity tab's Momentum Alerts list."),
            ]),
            ("Moneyball quadrant", [
                ("moneyball_difficulty", "0–100", "How hard this loan is to move forward (composite of stages-remaining, stall days, lock status, risk flags).", "X-axis of the Moneyball scatter."),
                ("moneyball_quadrant", "text", "easy_win / quick_fix / stretch / long_shot.", "The 'pick up the easy chips first' segmentation. Colour bubbles by quadrant."),
                ("moneyball_is_movable", "bool", "True if the counterfactual action would shift this loan to a better quadrant.", "Highlight these — they're the highest-leverage loans."),
                ("moneyball_cf_quadrant", "text", "Quadrant the loan would land in after the counterfactual.", "Show as an arrow from current to target quadrant."),
            ]),
            ("Velocity", [
                ("velocity", "decimal", "Stages cleared per day since loan opened.", "Raw speed metric."),
                ("velocity_band", "text", "Fast Track / On Pace / Slow / Stalled (by thresholds 0.30 / 0.15 / 0.05).", "Categorical for grouped bar charts."),
            ]),
            ("Engineered features (f_* columns — 31 of them)", [
                ("f_is_locked", "0/1", "Is the loan currently rate-locked?", "Single highest-signal feature."),
                ("f_days_until_lock_expiry", "integer", "Days until the lock expires (negative = already expired).", "Critical for 'lock expiring' alerts."),
                ("f_lock_expiring_not_progressed", "0/1", "Lock expires within 7 days AND loan hasn't reached CTC.", "Most urgent risk flag."),
                ("f_unlocked_at_late_stage", "0/1", "Past Approved without a rate lock.", "High dropout risk."),
                ("f_stale_at_approved", "0/1", "Sitting at Approved >30 days.", "Most actionable stall pattern."),
                ("f_stages_per_day", "decimal", "Pipeline velocity (used to derive velocity_band).", "Feed for the velocity chart."),
                ("f_credit_score, f_ltv, f_cltv, f_note_rate, f_loan_amount", "numeric", "Standard underwriting features, cleaned and missing-value-imputed.", "Useful if the team wants to slice by credit tier, LTV band, etc."),
                ("…plus 20 more f_* flags", "mixed", "Interaction flags like f_fresh_lock_late_stage, f_likely_lock_extended, f_lock_expiry_vs_month_end, f_approved_to_lock_speed, f_days_remaining, etc.", "Used internally by the ML model; kept in the export in case ThoughtSpot users want to drill into WHY a loan scored a certain way."),
            ]),
            ("Other raw source columns", [
                ("DecisionCreditScore, NoteRate, LTV, CLTV, Term, Lien Position…", "numeric", "Full set of raw underwriting and pricing columns carried from Encompass.", "Available if Gallus wants to build extra cuts not in the dashboard (e.g. credit-score band breakdowns)."),
                ("Internal Assigned Loan Officer Name / Processor / Underwriter / Manager", "text", "Ops team names.", "Enables per-LO or per-processor scorecards in ThoughtSpot."),
                ("Branch, Property State, Property City, Property Zip", "text", "Geographic / org columns.", "Enables map or branch-level views."),
                ("Loan Open Date, Respa App D, Submitted D, …, Funded D", "date", "Every pipeline milestone timestamp (ISO strings).", "Derive any custom stage-transition time on the SQL side."),
            ]),
        ],
    },

    # ─────────────────────── already_funded.csv ───────────────────────────
    {
        "filename": "already_funded.csv",
        "purpose": "Loans that have already funded between the first of the month "
                   "and the snapshot date. This is the 'bank' portion of the "
                   "monthly projection.",
        "grain": "One row per loan funded this month-to-date.",
        "visuals": ["Overview 'Already Funded' KPI tile", "Running total line chart by Funded D"],
        "columns": [
            ("snapshot_date", "date", "Snapshot these fundings were measured against.", "Ties the row to a point-in-time view."),
            ("LoanGuid", "text", "Loan identifier.", "Join key."),
            ("Product Type", "text", "Mortgage product family.", "Breakdown of funded volume by product."),
            ("Branch Channel", "text", "Wholesale / Retail.", "Funded volume by channel."),
            ("Loan Purpose", "text", "Purchase / Refinance.", "Funded volume by purpose."),
            ("LoanAmount", "number", "Loan face value.", "Funded dollars = sum of this column."),
            ("Funded D", "date", "When the loan funded.", "For daily/weekly breakdowns."),
        ],
    },

    # ─────────────────────── summary_kpis.csv ─────────────────────────────
    {
        "filename": "summary_kpis.csv",
        "purpose": "Single-row snapshot of the top-line numbers that headline "
                   "the Overview tab.",
        "grain": "One row per run (snapshot_date).",
        "visuals": ["KPI tile strip at the top of the Overview tab"],
        "columns": [
            ("snapshot_date", "date", "As-of date.", "Anchors all downstream numbers."),
            ("month", "text (YYYY-MM)", "Month being projected.", "For labelling the headline."),
            ("model_used", "text", "Which ML model was selected (e.g. GradientBoosting).", "Transparency / audit trail."),
            ("total_pipeline_loans", "integer", "Active loans (live + dead).", "Raw pipeline depth."),
            ("total_pipeline_value", "number", "Sum of LoanAmount across all active loans.", "Total dollar exposure."),
            ("live_pipeline_loans", "integer", "Live loans only.", "The 'real' pipeline count."),
            ("live_pipeline_value", "number", "Sum of LoanAmount for live loans.", "Live dollars at stake."),
            ("dead_pipeline_loans", "integer", "Loans flagged by elimination filter.", "How much ops cleanup is needed."),
            ("dead_pipeline_value", "number", "Sum of LoanAmount for dead loans.", "Dollars locked up in archival candidates."),
            ("already_funded_loans", "integer", "Loans funded month-to-date.", "Progress-to-month-end denominator."),
            ("already_funded_value", "number", "Dollars funded month-to-date.", "The 'bank' portion of the projection."),
            ("projected_total", "number", "already_funded_value + sum(live expected_value).", "The headline projection number."),
            ("overall_pull_through", "decimal 0-1", "Historical pipeline-entry pull-through rate.", "Baseline for scorecards."),
            ("median_cycle_days", "number", "Median open-to-funded days among historical funded loans.", "Benchmark for speed KPIs."),
            ("elimination_total", "integer", "Total loans the filter ran on.", "Context for the elimination_pct."),
            ("elimination_count", "integer", "Loans flagged as dead.", "Count of ops cleanup targets."),
            ("elimination_pct", "decimal", "% of pipeline flagged.", "Health indicator — high = pipeline hygiene problem."),
            ("elim_<rule>", "integer", "Per-rule counts (opened_stale, lock_already_expired, etc.).", "Categorised view of the dead pipeline."),
        ],
    },

    # ─────────────────────── stage_funnel.csv ─────────────────────────────
    {
        "filename": "stage_funnel.csv",
        "purpose": "Loan count and dollars at each pipeline stage right now.",
        "grain": "One row per pipeline stage (12 rows — Opened through Funded).",
        "visuals": ["Funnel chart (Overview tab)", "Stacked bar by stage"],
        "columns": [
            ("stage", "text", "Pipeline stage name.", "Axis label."),
            ("rank", "integer 0-12", "Numeric ordering of the stage.", "Sort the funnel bars correctly."),
            ("total_loans", "integer", "Loans at this stage (live + dead).", "Funnel width."),
            ("total_value", "number", "Sum of LoanAmount at this stage.", "Dollar funnel (alternative to loan count)."),
            ("live_loans", "integer", "Live loans at this stage.", "Funnel minus dead pipeline."),
            ("live_value", "number", "Dollars in live loans at this stage.", "Live dollar view."),
            ("avg_probability", "decimal 0-1", "Average ML probability for live loans at this stage.", "How likely to fund. Later stages = higher."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── channel_split.csv ────────────────────────────
    {
        "filename": "channel_split.csv",
        "purpose": "Wholesale vs Retail pipeline split.",
        "grain": "One row per channel.",
        "visuals": ["Donut chart", "Side-by-side KPI tiles"],
        "columns": [
            ("channel", "text", "Wholesale / Retail / Unknown.", "Category label."),
            ("total_loans / total_value / live_loans / live_value", "integer / number", "Same meaning as in stage_funnel.csv.", "Channel depth and dollars."),
            ("projected_value", "number", "Sum of expected_value for live loans in channel.", "Channel contribution to the projection."),
            ("avg_probability", "decimal 0-1", "Average ML probability.", "Channel quality signal."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── product_breakdown.csv ────────────────────────
    {
        "filename": "product_breakdown.csv",
        "purpose": "Pipeline split by mortgage product family.",
        "grain": "One row per Product Type.",
        "visuals": ["Horizontal bar chart", "Stacked bar of live vs dead"],
        "columns": [
            ("product", "text", "Product Type name.", "Category label."),
            ("total_loans / total_value / live_loans / live_value", "integer / number", "Same as stage_funnel.csv.", "Product depth and dollars."),
            ("avg_probability", "decimal 0-1", "Average ML probability in product.", "Product quality signal."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── pull_through_monthly.csv ─────────────────────
    {
        "filename": "pull_through_monthly.csv",
        "purpose": "Historical % of pipeline that funded, per month per product.",
        "grain": "One row per (month × product). Only months × products with "
                 "≥5 pipeline loans are included.",
        "visuals": ["Multi-line chart (one line per product, x=month)", "Stacked area chart of funded_count over time"],
        "columns": [
            ("month", "text (YYYY-MM)", "Calendar month.", "X-axis."),
            ("product", "text", "Product Type.", "Series / colour."),
            ("pull_through_rate", "decimal 0-1", "funded_count / total_count for loans active at month start.", "Key trend metric."),
            ("funded_count", "integer", "Loans in this product that funded by month-end.", "Numerator."),
            ("total_count", "integer", "Loans in this product active at the start of the month.", "Denominator."),
        ],
    },

    # ─────────────────────── cycle_times_by_product.csv ────────────────────
    {
        "filename": "cycle_times_by_product.csv",
        "purpose": "Percentile summary of open-to-funded days, per product.",
        "grain": "One row per product (plus an 'Overall' row).",
        "visuals": ["Box-and-whisker chart using p10/p25/median/p75/p90", "Bar chart of median cycle days by product", "KPI tile for above_sla_pct"],
        "columns": [
            ("product", "text", "Product Type (or 'Overall').", "Category."),
            ("count", "integer", "How many funded loans fed the distribution.", "Sample size — trust percentiles less if count is small."),
            ("median", "number", "Median cycle days.", "Middle of the distribution. The headline KPI."),
            ("mean / std", "number", "Mean and standard deviation.", "For detecting skew or variance."),
            ("p10 / p25 / p75 / p90", "number", "Distribution percentiles.", "Box-plot inputs — p25-p75 is the IQR box."),
            ("above_sla", "integer", "Loans that took longer than the SLA threshold (45 days).", "Problem-case count."),
            ("above_sla_pct", "number %", "Share that breached SLA.", "Operational KPI."),
            ("sla_threshold_days", "integer", "SLA threshold used (45).", "Reference constant."),
        ],
    },

    # ─────────────────────── cycle_times_per_loan.csv ──────────────────────
    {
        "filename": "cycle_times_per_loan.csv",
        "purpose": "One row per historical funded loan with its actual cycle "
                   "time. Use for ThoughtSpot-native histograms / box plots "
                   "rather than pre-binned percentiles.",
        "grain": "One row per funded loan (~5,660 rows).",
        "visuals": ["Histogram of cycle_days", "Box plot of cycle_days by product / channel / purpose", "Scatter of cycle_days vs LoanAmount"],
        "columns": [
            ("LoanGuid", "text", "Loan identifier.", "Join key."),
            ("Product Type / Branch Channel / Loan Purpose", "text", "Standard segmentation fields.", "Break histograms out by any of these."),
            ("LoanAmount", "number", "Loan face value.", "Weighted histograms."),
            ("Funded D", "date", "When the loan funded.", "Time-based trending."),
            ("cycle_days", "integer", "Days from application to funded.", "The metric to plot."),
        ],
    },

    # ─────────────────────── backtest_monthly.csv ─────────────────────────
    {
        "filename": "backtest_monthly.csv",
        "purpose": "Model validation — per-month backtest results (ML method, "
                   "rolling training, day-15 mid-month snapshots).",
        "grain": "One row per month the model was backtested (24 months).",
        "visuals": ["Line chart of projected vs actual by month", "Bar chart of |error_pct| by month", "Summary KPI: MAPE across all months"],
        "columns": [
            ("year, month", "integer", "The month being predicted.", "X-axis."),
            ("month (merged)", "text (YYYY-MM)", "Pre-formatted month label.", "Use directly as chart axis."),
            ("snapshot_day", "integer", "Day of month the snapshot was taken (always 15 in this file).", "Mid-month is the main test point."),
            ("method", "text", "'ML' (the model we're shipping).", "Filter constant."),
            ("training_mode", "text", "'rolling' means the model was retrained on data up to each snapshot.", "Prevents look-ahead leakage."),
            ("already_funded", "number", "Dollars funded between month-start and snapshot.", "Bank portion of the projection."),
            ("projected_pipeline", "number", "Dollars projected from live pipeline.", "ML portion."),
            ("projected", "number", "Total projection = already_funded + projected_pipeline.", "Compare to actual."),
            ("actual", "number", "Actual month-end fundings.", "Ground truth."),
            ("error_pct", "number %", "(projected − actual) / actual × 100.", "Accuracy metric. MAPE = mean of |error_pct|."),
            ("direction", "text", "over/under/on — which way the miss went.", "Bias detection."),
        ],
    },

    # ─────────────────────── revenue_at_risk_buckets.csv ──────────────────
    {
        "filename": "revenue_at_risk_buckets.csv",
        "purpose": "Five risk categories that segment live dollars by failure mode.",
        "grain": "Five rows — one per risk bucket.",
        "visuals": ["Horizontal bar chart of value_at_risk per bucket", "Action cards per bucket showing recommended action + dollars"],
        "columns": [
            ("id / label", "text", "Internal id and display label for the bucket.", "Use label as the card title."),
            ("description", "text", "What this bucket means in plain English.", "Card subtitle."),
            ("action", "text", "Recommended ops response.", "The 'do this' callout."),
            ("loan_count", "integer", "How many loans match.", "Card KPI."),
            ("total_value", "number", "Sum of LoanAmount in bucket.", "Face value at stake."),
            ("expected_value", "number", "Sum of expected_value in bucket.", "What we'll collect today with no action."),
            ("value_at_risk", "number", "total_value − expected_value.", "Headline dollar risk if nothing changes."),
            ("avg_probability", "decimal 0-1", "Average ML probability in bucket.", "Bucket quality."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
            ("_total_*", "number", "Bundle totals carried on every row for easy SQL access.", "Convenience."),
        ],
    },

    # ─────────────────────── moneyball_quadrant_summary.csv ───────────────
    {
        "filename": "moneyball_quadrant_summary.csv",
        "purpose": "Aggregated headline numbers per Moneyball quadrant — the "
                   "labels / totals that sit above the scatter plot.",
        "grain": "Four rows — easy_win / quick_fix / stretch / long_shot.",
        "visuals": ["Four KPI cards above the Moneyball scatter", "Quadrant legend with counts and dollars"],
        "columns": [
            ("quadrant", "text", "Quadrant name.", "Card title."),
            ("count", "integer", "Loans in this quadrant.", "Headline number."),
            ("total_value", "number", "Sum of LoanAmount.", "Face dollars at stake."),
            ("total_ev", "number", "Sum of expected_value.", "Projected dollars."),
            ("avg_prob", "decimal 0-1", "Average ML probability.", "Quadrant health."),
            ("movable_count / total_loans", "integer", "Totals carried for convenience.", "Shown in the tab header."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── bottleneck_heatmap.csv ────────────────────────
    {
        "filename": "bottleneck_heatmap.csv",
        "purpose": "Historical median transition time from one stage to the "
                   "next, with IQR and industry benchmarks. Long format so a "
                   "single worksheet powers both the overall view and the "
                   "product filter on the Pipeline Health tab.",
        "grain": "One row per (transition × product), plus one row per "
                 "transition with product='Overall'.",
        "visuals": ["Heatmap (transitions × products, colour by median_days)", "Bar chart of vs_benchmark — negative = faster than industry"],
        "columns": [
            ("transition", "text", "e.g. 'Approved → CTC'.", "Row label in the heatmap."),
            ("product", "text", "Product Type or 'Overall'.", "Column label."),
            ("median_days", "number", "Median days historical funded loans took for this transition.", "Heatmap colour value."),
            ("p25_days / p75_days", "number", "Interquartile range (the Domino's pizza variance Augie asked for).", "Show as tooltip or whisker bands."),
            ("std_days", "number", "Standard deviation (only for Overall).", "Variance indicator."),
            ("benchmark_median / benchmark_fast / benchmark_slow", "number", "Industry reference from ICE/Ellie Mae/LendingTree 2024.", "Comparison line in the heatmap cell."),
            ("vs_benchmark", "number", "median_days − benchmark_median. Negative = faster than industry.", "The 'we beat the industry' indicator."),
        ],
    },

    # ─────────────────────── stage_conversion_rates.csv ───────────────────
    {
        "filename": "stage_conversion_rates.csv",
        "purpose": "% of loans that reach each stage that go on to fund. Long "
                   "format, one row per (product × stage).",
        "grain": "Stage × product, including product='Overall'.",
        "visuals": ["Conversion funnel (one per product)", "Line chart of conversion_rate vs stage"],
        "columns": [
            ("product", "text", "Product Type or 'Overall'.", "Filter / series."),
            ("stage", "text", "Pipeline stage name.", "Funnel step."),
            ("reached_count", "integer", "Loans that reached this stage.", "Funnel denominator."),
            ("funded_count", "integer", "Of those, how many eventually funded.", "Funnel numerator."),
            ("conversion_rate", "decimal 0-1", "funded_count / reached_count.", "The percentage that survives this step."),
        ],
    },

    # ─────────────────────── current_bottlenecks.csv ──────────────────────
    {
        "filename": "current_bottlenecks.csv",
        "purpose": "Where loans are piling up right now — live pipeline by "
                   "current stage with days-at-stage variance.",
        "grain": "Current stage × product (long, with product='Overall').",
        "visuals": ["Bar chart of loan_count by stage", "Heatmap of median_days_at_stage by (stage × product)", "KPI tile: pct_over_30d for the worst stage"],
        "columns": [
            ("product", "text", "Product Type or 'Overall'.", "Filter."),
            ("stage", "text", "Current pipeline stage.", "Axis label."),
            ("rank", "integer", "Numeric stage order.", "Sort correctly."),
            ("loan_count", "integer", "Live loans at this stage right now.", "Pileup size."),
            ("total_value", "number", "Sum of LoanAmount.", "Dollars stuck at stage."),
            ("avg_days_at_stage / median_days_at_stage", "number", "How long loans have been sitting.", "Bottleneck severity."),
            ("p25_days_at_stage / p75_days_at_stage", "number", "IQR variance.", "Some loans flying through, others stuck?"),
            ("avg_probability", "decimal 0-1", "Average ML probability at this stage.", "How likely the stuck loans fund."),
            ("pct_over_30d", "number %", "Share of loans sitting 30+ days.", "'How stuck' KPI."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── velocity_distribution.csv ────────────────────
    {
        "filename": "velocity_distribution.csv",
        "purpose": "How live loans split across the four velocity bands.",
        "grain": "Band × product (long, with product='Overall').",
        "visuals": ["Stacked bar chart (bands as segments)", "Donut chart of loan_count per band"],
        "columns": [
            ("product", "text", "Product Type or 'Overall'.", "Filter."),
            ("band", "text", "Fast Track / On Pace / Slow / Stalled.", "Category."),
            ("loan_count", "integer", "Live loans in band.", "Size."),
            ("total_value", "number", "Sum of LoanAmount.", "Dollars in each speed."),
            ("expected_value", "number", "Sum of expected_value.", "Projected dollars by speed (Overall only)."),
            ("avg_probability", "decimal 0-1", "Average ML probability.", "Band quality."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── velocity_by_stage.csv ────────────────────────
    {
        "filename": "velocity_by_stage.csv",
        "purpose": "Per-stage velocity stats — are loans faster or slower at "
                   "specific stages?",
        "grain": "One row per current_stage.",
        "visuals": ["Bar chart of median_velocity by stage", "Line chart with p25/p75 as whiskers"],
        "columns": [
            ("stage", "text", "Current stage.", "Axis."),
            ("loan_count", "integer", "Live loans at stage.", "Sample size."),
            ("avg_velocity / median_velocity / p25_velocity / p75_velocity", "decimal", "Speed percentiles (stages per day).", "Box-plot inputs."),
            ("avg_days_at_stage", "number", "Average time sitting at stage.", "Pileup indicator."),
            ("avg_probability", "decimal 0-1", "Average ML probability at stage.", "Expected outcome."),
            ("pct_stalled", "number %", "% of loans in 'Stalled' band.", "Stage-specific problem KPI."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── what_if_scenarios.csv ────────────────────────
    {
        "filename": "what_if_scenarios.csv",
        "purpose": "Four operational levers with estimated dollar impact if "
                   "pulled, plus confidence + caveats (the 'red-team' section "
                   "from the dashboard).",
        "grain": "One row per scenario (4 rows).",
        "visuals": ["Scenario cards with current → improved bar + delta label", "Confidence badges (medium/low)", "Aggregate tile showing adjusted_potential_delta"],
        "columns": [
            ("id / lever / description", "text", "Scenario identity and plain-English explanation.", "Card headline + body."),
            ("current_state / target_state", "text", "Baseline and goal, both in human-readable form.", "Narrative framing for the card."),
            ("current_value / improved_value / delta", "number", "Dollars before and after, and the delta.", "Bar chart values."),
            ("pct_improvement", "number %", "Relative uplift.", "Alternative framing."),
            ("affected_loans / affected_value", "integer / number", "How many loans and how much value the scenario touches.", "Scope of the action."),
            ("methodology", "text", "How the estimate was computed.", "Tooltip / audit trail."),
            ("confidence", "text", "medium / low / low-medium.", "Badge / colour."),
            ("confidence_note", "text", "One-sentence explanation of the confidence level.", "Tooltip."),
            ("caveats", "text (| separated)", "Specific reasons the number could be wrong.", "Required reading — surface next to the card."),
            ("_totals_*", "number", "Bundle totals carried on every row (current_projected, adjusted_potential_delta, overlap_discount, etc.).", "So a single query can pull headline numbers without a separate summary CSV."),
        ],
    },

    # ─────────────────────── scorecards.csv ───────────────────────────────
    {
        "filename": "scorecards.csv",
        "purpose": "Per-product and per-channel composite scorecards (the "
                   "'single number' Augie asked for).",
        "grain": "One row per (product or channel). dimension='product' or 'channel'.",
        "visuals": ["Comparative table with composite_score colour scale", "Side-by-side bar chart for each sub-score", "Scorecard tile with trend arrow"],
        "columns": [
            ("name", "text", "Product Type or Channel name.", "Row label."),
            ("dimension", "text", "'product' or 'channel'.", "Split the table in ThoughtSpot."),
            ("pull_through_rate / pt_recent_3m / pt_prior_3m", "decimal 0-1", "Overall and rolling pull-through.", "Trend calculation inputs."),
            ("pt_trend_delta", "decimal", "recent_3m − prior_3m.", "Arrow metric."),
            ("pt_trend", "text", "up / down / flat.", "Arrow display."),
            ("median_cycle_days", "number", "Median open-to-funded days.", "Speed KPI."),
            ("avg_loan_amount", "number", "Average loan size in segment.", "Revenue density."),
            ("funded_volume_6m / pipeline_volume_6m", "number", "Recent 6-month actuals.", "Revenue efficiency inputs."),
            ("revenue_efficiency", "decimal 0-1", "funded_volume / pipeline_volume.", "Dollars-in / dollars-out."),
            ("current_active_loans / current_projected_value", "integer / number", "Today's live pipeline in the segment.", "Current-state KPIs."),
            ("avg_pipeline_probability", "decimal 0-1", "Average ML probability today.", "Pipeline quality."),
            ("efficiency_score", "number", "pull_through_rate × avg_loan_amount.", "Legacy ranking metric."),
            ("composite_score", "0-100", "Weighted blend of pull-through (30%), cycle time (20%), revenue efficiency (20%), trend (15%), pipeline probability (15%).", "The headline single number."),
            ("sub_pull_through / sub_cycle_time / sub_revenue_efficiency / sub_trend / sub_pipeline_probability", "0-100", "Individual component scores that feed composite_score.", "So users can see WHY a product scored well or poorly."),
            ("rank", "integer (or null for channels)", "Product rank by composite_score (1 = best).", "Sort / ranking strip. NULL for channel rows."),
            ("tier", "text (or null for channels)", "top / mid / bottom tier based on rank.", "Colour code on the ranking strip."),
            ("industry_benchmark_pt / industry_benchmark_cycle", "number", "Reference industry values.", "Comparison line."),
            ("benchmark_note", "text", "Caveat about the industry benchmark definition.", "Footer."),
        ],
    },

    # ─────────────────────── optimization_recommendations.csv ─────────────
    {
        "filename": "optimization_recommendations.csv",
        "purpose": "Priority-ranked ops action list for the week — what the "
                   "team should actually DO.",
        "grain": "One row per recommendation (6-8 rows).",
        "visuals": ["Ranked action list at the top of the Overview tab", "KPI tile of total estimated_impact"],
        "columns": [
            ("priority", "integer", "1-N ranking.", "Row order."),
            ("title", "text", "One-line action headline.", "Card title."),
            ("description", "text", "Plain-English explanation.", "Card body."),
            ("estimated_impact", "number", "Dollars unlocked if the action is taken.", "Headline number per card."),
            ("effort", "text", "low / medium / high.", "Balances impact vs cost."),
            ("loan_count", "integer", "How many loans the action touches.", "Scope."),
            ("category", "text", "lock_management / pipeline_acceleration / borrower_engagement / resource_reallocation.", "Grouping."),
            ("urgency", "text", "immediate / this_week / this_month.", "Time colour-code."),
            ("confidence_caveat", "text", "When present, flags why the number could be wrong.", "Required reading for low-confidence actions."),
            ("_total_estimated_impact_all", "number", "Sum across all recommendations.", "Header KPI."),
            ("snapshot_date", "date", "As-of date.", "For appending."),
        ],
    },

    # ─────────────────────── industry_benchmarks_transitions.csv ──────────
    {
        "filename": "industry_benchmarks_transitions.csv",
        "purpose": "Reference table of industry transition-time benchmarks "
                   "(ICE / Ellie Mae / LendingTree 2024) by product.",
        "grain": "One row per (transition × product).",
        "visuals": ["Overlay line on the bottleneck heatmap", "Tooltip in any stage-time chart"],
        "columns": [
            ("transition", "text", "Stage-to-stage transition name.", "Row label."),
            ("product", "text", "Product Type.", "Column."),
            ("benchmark_fast / benchmark_median / benchmark_slow", "number", "Industry day counts for fast / typical / slow lenders.", "Comparison ranges."),
            ("source", "text", "Citation.", "Credibility / audit trail."),
        ],
    },

    # ─────────────────────── feature_importance.csv ───────────────────────
    {
        "filename": "feature_importance.csv",
        "purpose": "Which features the ML model relies on most.",
        "grain": "One row per feature.",
        "visuals": ["Horizontal bar chart of top 15 features", "Model-accuracy tooltip"],
        "columns": [
            ("feature", "text", "Feature name (matches an f_* column in loans.csv).", "Label."),
            ("importance", "decimal 0-1", "Share of the model's splitting decisions explained by this feature.", "Bar value. Sum across all features = 1."),
        ],
    },
]


# ───────────────────────── rendering helpers ────────────────────────────────

_UNICODE_TO_ASCII = {
    "—": "--", "–": "-", "−": "-",
    "→": "->", "←": "<-", "×": "x",
    "•": "-", "·": "-", "…": "...",
    "≤": "<=", "≥": ">=",
    "“": '"', "”": '"', "‘": "'", "’": "'",
}

def _clean(text):
    if text is None:
        return ""
    s = str(text)
    for k, v in _UNICODE_TO_ASCII.items():
        s = s.replace(k, v)
    # Strip any remaining non-Latin-1 characters
    return s.encode("latin-1", "replace").decode("latin-1")


class DictPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=22)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, _clean(
            f"FlexPoint  ·  Data Dictionary  ·  Page {self.page_no() - 1}"),
            align="C")

    # ---- primitives ----
    def h1(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*NAVY)
        self.cell(0, 10, _clean(text), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*NAVY)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def h2(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*NAVY)
        self.cell(0, 8, _clean(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h3(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.cell(0, 6, _clean(text), new_x="LMARGIN", new_y="NEXT")

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BODY)
        self.multi_cell(0, 5, _clean(text))
        self.ln(1)

    def small(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GREY)
        self.multi_cell(0, 5, _clean(text))
        self.ln(1)

    def kv(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.cell(26, 6, _clean(key), new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BODY)
        self.multi_cell(0, 6, _clean(value))

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*BODY)
        self.set_x(self.l_margin + 4)
        self.multi_cell(0, 5, "- " + _clean(text))

    def column_table(self, rows):
        """Render a column-docs table. rows = list of (name, type, desc, value)."""
        page_w = self.w - self.l_margin - self.r_margin
        widths = [42, 22, 60, page_w - (42 + 22 + 60)]
        headers = ["Column", "Type", "What it is", "Why it matters / how to use"]

        # Header row
        self.set_fill_color(*LIGHT)
        self.set_text_color(*NAVY)
        self.set_font("Helvetica", "B", 9)
        for w, h in zip(widths, headers):
            self.cell(w, 7, _clean(h), border=1, fill=True)
        self.ln(7)

        # Body rows
        self.set_text_color(*BODY)
        self.set_font("Helvetica", "", 9)
        for row in rows:
            self._wrapped_row([_clean(c) for c in row], widths)

    def _wrapped_row(self, cells, widths):
        """Draw a row where every cell can wrap. Lines are measured at the
        exact inner width we render at so the row height is always sufficient
        to contain every line — no bleed into the next row."""
        line_h = 4.5
        pad_x = 1.5
        pad_y = 1.0
        inner_widths = [max(w - 2 * pad_x, 1) for w in widths]

        # Measure how many lines each cell wraps to at the inner width we'll
        # actually render with. Use fpdf2's dry_run + LINES output.
        self.set_font("Helvetica", "", 9)
        wraps = []
        for text, iw in zip(cells, inner_widths):
            lines = self.multi_cell(iw, line_h, text, border=0, align="L",
                                    dry_run=True, output="LINES")
            if not lines:
                lines = [""]
            wraps.append(list(lines))

        max_lines = max(len(w) for w in wraps)
        row_h = max_lines * line_h + 2 * pad_y

        # Page-break guard (keep row intact)
        if self.get_y() + row_h > self.h - self.b_margin:
            self.add_page()

        x0 = self.get_x()
        y0 = self.get_y()

        # Draw each cell: rect border + each wrapped line placed explicitly
        # via set_xy + cell so the renderer can't re-wrap and overflow.
        for i, (lines, w, iw) in enumerate(zip(wraps, widths, inner_widths)):
            x = x0 + sum(widths[:i])
            self.rect(x, y0, w, row_h)
            for li, line in enumerate(lines):
                self.set_xy(x + pad_x, y0 + pad_y + li * line_h)
                self.cell(iw, line_h, line, border=0, align="L")

        self.set_xy(x0, y0 + row_h)


# ───────────────────────── page builders ────────────────────────────────────

def cover_page(pdf):
    pdf.add_page()
    pdf.ln(55)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 14, _clean("FlexPoint ThoughtSpot Export"), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 20)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 12, _clean("Data Dictionary"), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.6)
    pdf.line(60, pdf.get_y(), pdf.w - 60, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 6, _clean(
        "A plain-English guide to every CSV in the export bundle: purpose, "
        "grain (what one row represents), ideal visualisations, and "
        "column-by-column meaning."),
        align="C")
    pdf.ln(16)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, _clean("Audience"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 6, _clean("Gallus Insights SQL / ThoughtSpot team"),
        align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, _clean("Bundle location"), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 6, _clean("outputs/thoughtspot_export/"),
        align="C", new_x="LMARGIN", new_y="NEXT")


def overview_page(pdf):
    pdf.add_page()
    pdf.h1("How to use this bundle")

    pdf.h2("What's in the box")
    pdf.body(
        "26 CSVs plus this PDF. The export was produced by running the FlexPoint "
        "v3 pipeline model against a point-in-time pipeline snapshot. Each CSV "
        "is pre-aggregated at the grain its dashboard visual needs — you can "
        "load them into ThoughtSpot as worksheets without further SQL work. "
        "If you want per-loan drill-downs, join anything back to loans.csv on "
        "LoanGuid.")

    pdf.h2("The one file that matters most")
    pdf.body(
        "loans.csv — one row per active loan with raw pipeline state, 31 "
        "engineered features (f_* prefix), the ML prediction, counterfactual "
        "recommendations, Moneyball quadrant assignment, and velocity band. "
        "Treat it as the primary fact table; use the aggregate CSVs as "
        "worksheets that reference it.")

    pdf.h2("Join key")
    pdf.body(
        "LoanGuid is unique and present in every per-loan CSV. It matches the "
        "LoanGuid column you already have from Encompass.")

    pdf.h2("Column-name conventions")
    pdf.bullet("Raw source columns keep their original names (LoanGuid, LoanAmount, "
               "Product Type, Branch Channel, Rate Lock D). This preserves joinability "
               "to your existing Encompass tables.")
    pdf.bullet("Derived columns use snake_case (current_stage, days_at_stage, "
               "ml_probability, expected_value).")
    pdf.bullet("Engineered model features are prefixed f_ (f_is_locked, "
               "f_lock_expiring_not_progressed, f_stages_per_day, etc.).")
    pdf.bullet("Nested lists (risk_reasons, caveats, risk_factors) are flattened "
               "to pipe-separated text columns: 'reason A | reason B'.")
    pdf.bullet("All dates are ISO strings (YYYY-MM-DD).")

    pdf.h2("Snapshot vs time-series")
    pdf.body(
        "Every file carries a snapshot_date column. A single run produces one "
        "snapshot. Rerun the export on fresh data and append to build a "
        "time-series without schema change (one row per (LoanGuid, snapshot_date) "
        "in loans.csv, one row per (stage, snapshot_date) in stage_funnel.csv, "
        "and so on).")

    pdf.h2("Ideal display methods (quick reference)")
    pdf.bullet("KPI tiles → summary_kpis.csv columns, total_* rows in buckets")
    pdf.bullet("Funnel → stage_funnel.csv, stage_conversion_rates.csv")
    pdf.bullet("Heatmap → bottleneck_heatmap.csv (transition × product)")
    pdf.bullet("Bubble scatter → loans.csv (moneyball_difficulty × ml_probability, bubble=LoanAmount)")
    pdf.bullet("Line chart over time → pull_through_monthly.csv, backtest_monthly.csv")
    pdf.bullet("Box/whisker → cycle_times_by_product.csv (p10/p25/median/p75/p90), or cycle_times_raw.csv for native")
    pdf.bullet("Ranked bar → scorecard_rankings.csv, optimization_recommendations.csv")
    pdf.bullet("Tables with action columns → at_risk_loans.csv, top_recovery_opportunities.csv")


def file_to_visual_map_page(pdf):
    pdf.add_page()
    pdf.h1("CSV → Dashboard visual map")
    pdf.body("Shortcut for which file powers which tab on the existing FlexPoint "
             "dashboard. Use this when deciding which CSVs to load first.")

    # One CSV per line (joined with \n) so the row height stays predictable
    # and the SQL team can scan-read instead of parsing a 170-char comma blob.
    mapping = [
        ("Overview",
         "summary_kpis\nstage_funnel\nchannel_split\nproduct_breakdown\n"
         "backtest_monthly\noptimization_recommendations\nalready_funded"),
        ("Watch List",
         "loans  (filter WHERE is_at_risk = TRUE)"),
        ("Revenue at Risk",
         "revenue_at_risk_buckets\nmoneyball_quadrant_summary\n"
         "loans  (filter WHERE recovery_rank IS NOT NULL for the recovery table)\n"
         "loans  (use moneyball_* columns for the scatter bubbles)"),
        ("Pipeline Health",
         "bottleneck_heatmap\nstage_conversion_rates\n"
         "current_bottlenecks\nindustry_benchmarks_transitions"),
        ("Trends",
         "pull_through_monthly\ncycle_times_by_product\ncycle_times_per_loan"),
        ("Velocity / Momentum",
         "velocity_distribution\nvelocity_by_stage\n"
         "loans  (filter WHERE momentum_rank IS NOT NULL for momentum alerts)"),
        ("What-If", "what_if_scenarios"),
        ("Scorecards", "scorecards  (includes rank + tier columns)"),
        ("Model transparency", "feature_importance"),
    ]

    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    widths = [40, page_w - 40]
    # header
    pdf.set_fill_color(*LIGHT)
    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 10)
    for w, h in zip(widths, ["Tab", "CSVs that power it"]):
        pdf.cell(w, 8, _clean(h), border=1, fill=True)
    pdf.ln(8)
    pdf.set_text_color(*BODY)
    pdf.set_font("Helvetica", "", 10)
    for tab, files in mapping:
        pdf._wrapped_row((_clean(tab), _clean(files)), widths)


def file_detail_page(pdf, file_def):
    pdf.add_page()
    pdf.h1(file_def["filename"])

    pdf.h3("What it is")
    pdf.body(file_def["purpose"])

    pdf.h3("Grain (what one row represents)")
    pdf.body(file_def["grain"])

    pdf.h3("Best ways to visualise")
    for v in file_def["visuals"]:
        pdf.bullet(v)

    pdf.ln(1)
    pdf.h3("Columns")

    if "columns_grouped" in file_def:
        for group_name, cols in file_def["columns_grouped"]:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*NAVY)
            pdf.cell(0, 6, _clean(group_name), new_x="LMARGIN", new_y="NEXT")
            pdf.column_table(cols)
    else:
        pdf.column_table(file_def["columns"])


# ───────────────────────────────── main ─────────────────────────────────────

def main():
    pdf = DictPDF()
    cover_page(pdf)
    overview_page(pdf)
    file_to_visual_map_page(pdf)
    for file_def in FILES:
        file_detail_page(pdf, file_def)

    pdf.output(str(OUT_PATH))
    print(f"Wrote → {OUT_PATH}")
    print(f"  {len(FILES)} files documented · {pdf.page_no()} pages")


if __name__ == "__main__":
    main()
