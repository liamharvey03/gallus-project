"""
FlexPoint Loan Funding Forecasting — Configuration & Constants
"""
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "data"
OUTPUTS_PATH = PROJECT_ROOT / "outputs"

# ─── Loan outcome definitions ────────────────────────────────────────────────
FUNDED_STATUSES = [
    "Loan Sold", "Funded", "Loan Shipped", "Recorded", "Loan Archived",
]

FAILED_STATUSES = [
    "Loan Cancelled", "Loan Denied", "Loan Withdrawn", "Lead Cancelled",
]

# ─── Pipeline stage ordering (highest → lowest for backward walk) ─────────────
# Each tuple: (date_column, stage_label, ordinal_rank)
STAGE_MAP = [
    ("Funded D",            "Funded",        12),
    ("Scheduled Funding D", "Sched Fund",    11),
    ("FundingConditionsD",  "Fund Cond",     10),
    ("DocsBackD",           "Docs Back",      9),
    ("Docs D",              "Docs",           8),
    ("Clear To Close D",    "CTC",            7),
    ("FinalUnderwritingD",  "Final UW",       6),
    ("ConditionReviewD",    "Cond Review",    5),
    ("Approved D",          "Approved",       4),
    ("Underwriting D",      "Underwriting",   3),
    ("Submitted D",         "Submitted",      2),
    ("Respa App D",         "Application",    1),
    ("Loan Open Date",      "Opened",         0),
]

# ─── Product type groupings (for thin-cell smoothing) ────────────────────────
PRODUCT_GROUPS = {
    "CONV_CONF":    ["CONFORMING", "HOMEREADY", "HOME POSSIBLE",
                     "CONVENTIONAL BOND", "CONVENTIONAL BOND STD MI"],
    "CONV_NONCONF": ["NONCONFORMING"],
    "FHA":          ["FHA", "FHA BOND"],
    "VA":           ["VA"],
    "OTHER":        ["2ND", "ZERO INTEREST PROGRAM", "HELOC",
                     "HOME EQUITY", "RURAL"],
}

# ─── Feature tiers (Section 4.5 of README) ───────────────────────────────────
TIER1_FEATURES = [
    "current_stage",       # ordinal 0-12
    "Product Type",        # categorical
    "Loan Purpose",        # categorical
    "days_at_stage",       # continuous — derived from milestone dates
]

TIER2_FEATURES = [
    "Branch Channel",      # Wholesale / Retail
    "days_remaining",      # days remaining in month (continuous)
    "LoanAmount",          # continuous
    "Rate Lock Status",    # binary — watch for leakage
    "Lock Period (days)",  # continuous
]

TIER3_FEATURES = [
    "DecisionCreditScore",
    "LTV",
    "CLTV",
    "NoteRate",
    "Occupancy Type",
    "Property State",
    "Loan Type",
]

# ─── Backtesting parameters ──────────────────────────────────────────────────
BACKTEST_MONTHS = [
    (2024, 1), (2024, 2), (2024, 3), (2024, 4),
    (2024, 5), (2024, 6), (2024, 7), (2024, 8),
    (2024, 9), (2024, 10), (2024, 11), (2024, 12),
    (2025, 1), (2025, 2), (2025, 3), (2025, 4),
    (2025, 5), (2025, 6), (2025, 7), (2025, 8),
    (2025, 9), (2025, 10), (2025, 11), (2025, 12),
]

SNAPSHOT_DAYS = [0, 1, 8, 15, 22]

MIN_CELL_SIZE = 20

# ─── Date columns in sectG.csv ───────────────────────────────────────────────
# All columns that should be parsed as datetime
DATE_COLUMNS = [
    "Lead New Date",
    "Loan Open Date",
    "Pre-qual Date",
    "Pre-approved Date",
    "Registration",
    "RegistrationD",
    "Respa App D",
    "HMDA App D",
    "Loan Submitted D",
    "DocumentCheckD",
    "PreProcessingD",
    "ProcessingD",
    "Submitted D",
    "Underwriting D",
    "ConditionReviewD",
    "FinalUnderwritingD",
    "Approved D",
    "Estimated Closing D",
    "Clear To Close D",
    "PreDocQCD",
    "Docs D",
    "DocsOrderedD",
    "DocsDrawnD",
    "DocsBackD",
    "FundingConditionsD",
    "Scheduled Funding D",
    "Funded D",
    "Loan Closed D",
    "Recorded D",
    "Purchase D",
    "Loan Shipped D",
    "Rate Lock D",
    "Rate Lock Expiration D",
    "Loan OnHold D",
    "Loan Canceled D",
    "Loan Denied D",
    "Loan Suspended D",
    "Withdrawn D",
    "TIL Disclosure / GFE Ordered Date",
    "TIL Disclosure / GFE Due Date",
    "TIL Disclosure / GFE Received Date",
]

# Terminal-event date columns (for determining if loan failed before a date)
FAILURE_DATE_COLUMNS = [
    "Loan Canceled D",
    "Loan Denied D",
    "Withdrawn D",
    "Loan Suspended D",
]

# ─── Industry benchmarks ────────────────────────────────────────────────────
#
# SOURCING NOTES (read before citing to clients):
#
# WELL-SOURCED (primary data):
#   - Total days to close: ICE Mortgage Technology (Ellie Mae) Origination
#     Insight Reports, covers ~80% of US mortgage applications.
#     Purchase avg 42d overall (ICE 2024). Conv ~42d, FHA ~45d, VA ~49d
#     (ValuePenguin citing Ellie Mae 2019; LendingTree 2024).
#   - Closing rates (= pull-through from formal application): 76-78%
#     overall on 90-day cycle (Ellie Mae OIR, Feb-Sep 2020 reports).
#     Purchase 80.7%, Refi 76.0% (Ellie Mae Feb 2020).
#   - Industry pull-through benchmark: 75% (FundMore.ai 2021 composite;
#     corroborated by Ellie Mae 76-78% closing rate data).
#
# ESTIMATED (derived, not from a single authoritative report):
#   - Stage-by-stage transition times: No public source breaks down
#     Submitted->Approved or Approved->CTC by product type. These are
#     estimated from total cycle times and general underwriting timelines.
#   - Pull-through by product type: Not publicly available with
#     specificity. Per-product rates are directional estimates.
#   - "fast"/"slow" thresholds: Approximate top/bottom quartile.
#
# RECOMMENDATION: Validate stage-specific benchmarks with Augie before
# presenting as authoritative. He knows the industry numbers.
#
INDUSTRY_BENCHMARKS = {
    "transition_days": {
        "Open → Submitted": {
            "overall":       {"median": 1, "fast": 0, "slow": 3},
            "NONCONFORMING": {"median": 1, "fast": 0, "slow": 3},
            "CONFORMING":    {"median": 1, "fast": 0, "slow": 2},
            "FHA":           {"median": 1, "fast": 0, "slow": 3},
            "VA":            {"median": 1, "fast": 0, "slow": 3},
            "2ND":           {"median": 1, "fast": 0, "slow": 3},
        },
        "Submitted → Approved": {
            "overall":       {"median": 5, "fast": 3, "slow": 7},
            "NONCONFORMING": {"median": 6, "fast": 4, "slow": 8},
            "CONFORMING":    {"median": 4, "fast": 3, "slow": 6},
            "FHA":           {"median": 5, "fast": 3, "slow": 7},
            "VA":            {"median": 6, "fast": 4, "slow": 8},
            "2ND":           {"median": 5, "fast": 3, "slow": 7},
        },
        "Approved → CTC": {
            # Derived: total_cycle minus other stages. Most variable stage.
            # VA/jumbo longer due to appraisal complexity + documentation.
            "overall":       {"median": 20, "fast": 12, "slow": 28},
            "NONCONFORMING": {"median": 24, "fast": 14, "slow": 32},
            "CONFORMING":    {"median": 18, "fast": 10, "slow": 24},
            "FHA":           {"median": 22, "fast": 13, "slow": 28},
            "VA":            {"median": 26, "fast": 16, "slow": 34},
            "2ND":           {"median": 20, "fast": 12, "slow": 26},
        },
        "CTC → Funded": {
            "overall":       {"median": 5, "fast": 3, "slow": 7},
            "NONCONFORMING": {"median": 5, "fast": 3, "slow": 7},
            "CONFORMING":    {"median": 4, "fast": 3, "slow": 6},
            "FHA":           {"median": 5, "fast": 3, "slow": 7},
            "VA":            {"median": 6, "fast": 3, "slow": 8},
            "2ND":           {"median": 5, "fast": 3, "slow": 7},
        },
    },
    # Total app-to-funded. Sources: ICE 2024 (42d purchase overall);
    # ValuePenguin/Ellie Mae 2019 (Conv 47d, FHA 47d, VA 49d purchase);
    # LendingTree 2024 (Conv 42d, FHA 43d, VA 40-50d).
    "total_cycle_days": {
        "overall": 43,           # ICE Mortgage Technology 2024
        "NONCONFORMING": 49,     # JVM Lending: jumbos take longer
        "CONFORMING": 42,        # LendingTree 2024; ICE 2024
        "FHA": 45,               # LendingTree 43d + Ellie Mae 47d, avg
        "VA": 49,                # LendingTree 40-50d; Ellie Mae 49d
        "2ND": 42,               # No specific data; assumed ~conforming
    },
    # Closing rates. Ellie Mae measures on 90-day cycle from application.
    # NOT the same as FlexPoint's pipeline-entry pull-through.
    "closing_rates": {
        "overall": 0.77,         # Ellie Mae OIR avg Feb-Sep 2020
        "purchase": 0.81,        # Ellie Mae Feb 2020: 80.7%
        "refinance": 0.76,       # Ellie Mae Feb 2020: 76.0%
        "industry_pull_through_benchmark": 0.75,  # FundMore.ai 2021
        "note": (
            "Industry 'closing rate' is measured from formal application "
            "on a 90-day cycle (Ellie Mae/ICE, ~80% of US mortgage apps). "
            "FlexPoint's 37% pull-through is from pipeline entry — much "
            "earlier. These are NOT directly comparable."
        ),
    },
    "sources": [
        "ICE Mortgage Technology Origination Insight Report 2024 (42d purchase avg)",
        "Ellie Mae OIR press releases Feb-Sep 2020 (closing rates 76-78%)",
        "ValuePenguin citing Ellie Mae Feb 2019 (Conv 47d, FHA 47d, VA 49d)",
        "LendingTree 2024 (Conv 42d, FHA 43d, VA 40-50d)",
        "FundMore.ai 2021 (75% pull-through benchmark)",
        "Stage transitions: ESTIMATED from total cycle + industry guides",
    ],
    "source_display": "ICE Mortgage Technology 2024, Ellie Mae OIR, LendingTree",
}
