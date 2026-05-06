"""Per-table column type registries.

Source of truth: `reports/schema_profile.md` — the "Suspected type-coercion
failures" section. The Forecasting DB CSV-load coerced ~78 columns to
nvarchar(255) that should be numeric or datetime; this module records those
so `db.read_table()` can fix the dtypes on the way out.

Some entries were flagged on a name heuristic and may turn out to be genuinely
text (e.g. "Rate Lock Status", "Property County"). `pd.to_numeric` /
`pd.to_datetime` are called with `errors="coerce"`, so misclassified columns
become all-NaN — loud, not silent.
"""

from __future__ import annotations

NUMERIC_COLUMNS: dict[str, list[str]] = {
    "loans": [
        # Model / counterfactual outputs
        "counterfactual_probability",
        "probability_delta",
        "expected_value_uplift",
        # Ranks / difficulty scores (nvarchar in source, numeric semantics)
        "recovery_rank",
        "recovery_gap",
        "momentum_rank",
        "moneyball_difficulty",
        # Engineered features
        "f_credit_score",
        "f_days_past_lock_expiry",
        "f_days_since_lock",
        "f_days_until_lock_expiry",
        # Credit scores
        "DecisionCreditScore",
        "Borrower Experian Score",
        "Borrower TransUnion Score",
        "Borrower Equifax Score",
        "Coborrower Experian Score",
        "Coborrower TransUnion Score",
        "Coborrower Equifax Score",
        "Credit Score Type 1",
        "Credit Score Type 2",
        # Property values (both spellings exist in the source)
        "Purchase Price",
        "Appraised Value",
        "PurchasePrice",
        "AppraisedValue",
        # Rate / lock / margin
        "Rate Lock Status",
        "ARM - Rate Margin",
        # Heuristic flags — may actually be text; coerce will produce NaN if so
        "Property County",
        "Internal Assigned Lender Account Executive Name",
        "Registration",
        # Fees
        "Commission - Rebate Fee Percentage of Loan Amount",
        "Commission - Rebate Fee Total",
        "Approved Fee (YSP)",
        "GFE - Loan discount (total)",
        "GFE - Appraisal fee",
        "GFE - Credit report fee",
        "GFE - Underwriting fee",
        # Cycle-time durations
        "DaysOpenToSubmitted",
        "DaysSubmittedToApproved",
        "DaysApprovedToCTC",
        "DaysCTCToFunded",
        "DaysTotalSubmitToFund",
        "DaysTotalOpenToFund",
        "LockDurationDays",
        "DaysSubmittedToUW",
        "DaysUWToApproved",
        "DaysDocsToFunded",
    ],
    "backtest_monthly": [
        "projected",
        "projected_pipeline",
    ],
}


DATE_COLUMNS: dict[str, list[str]] = {
    "loans": [
        # Pre-pipeline
        "Pre-qual Date",
        "Pre-approved Date",
        "RegistrationD",
        # Application / intake
        "Respa App D",
        "HMDA App D",
        "Loan Submitted D",
        "DocumentCheckD",
        "PreProcessingD",
        "ProcessingD",
        # Submission through approval
        "Submitted D",
        "Underwriting D",
        "ConditionReviewD",
        "FinalUnderwritingD",
        "Approved D",
        "Clear To Close D",
        # Docs / funding
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
        # Rate-lock dates
        "Rate Lock D",
        "Rate Lock Expiration D",
        # Terminal failure dates
        "Loan OnHold D",
        "Loan Canceled D",
        "Loan Denied D",
        "Loan Suspended D",
        "Withdrawn D",
        # TIL / GFE
        "TIL Disclosure / GFE Ordered Date",
        "TIL Disclosure / GFE Due Date",
        "TIL Disclosure / GFE Received Date",
    ],
}
