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
