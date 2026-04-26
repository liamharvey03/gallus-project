"""
FlexPoint Loan Funding Forecasting — Data Loading & Cleaning
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def load_and_clean(filepath=None) -> pd.DataFrame:
    """
    Load sectG.csv and return a clean DataFrame.

    Steps:
      1. Load CSV
      2. Parse all date columns to datetime
      3. Create DidFund (1 if Funded D non-null, else 0)
      4. Create Outcome (Funded / Failed / Active)
      5. Clean numeric columns — handle "NULL" strings
      6. Zeros in DecisionCreditScore and LoanAmount → NaN
    """
    if filepath is None:
        filepath = config.DATA_PATH / "sectG.csv"

    df = pd.read_csv(filepath, low_memory=False)
    print(f"Loaded: {len(df):,} rows × {len(df.columns)} columns")

    # ── 1. Replace literal "NULL" strings with NaN across the board ──────
    df.replace("NULL", np.nan, inplace=True)

    # ── 2. Parse date columns ────────────────────────────────────────────
    parsed = 0
    for col in config.DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            parsed += 1
    print(f"Parsed {parsed} date columns")

    # ── 3. DidFund — 1 if Funded D is non-null ──────────────────────────
    df["DidFund"] = df["Funded D"].notna().astype(int)

    # ── 4. Outcome ──────────────────────────────────────────────────────
    def _outcome(row):
        if pd.notna(row["Funded D"]):
            return "Funded"
        if row["Loan Status"] in config.FAILED_STATUSES:
            return "Failed"
        return "Active"

    df["Outcome"] = df.apply(_outcome, axis=1)

    # ── 5. Clean numeric columns ─────────────────────────────────────────
    numeric_cols = [
        "DecisionCreditScore",
        "LoanAmount", "Loan Amount", "Total Loan Amount",
        "LTV", "LTV_N", "CLTV", "Gross Ltv R",
        "NoteRate", "Note Rate",
        "Term",
        "Lock Period (days)",
        "Borrower Experian Score", "Borrower TransUnion Score",
        "Borrower Equifax Score",
        "Coborrower Experian Score", "Coborrower TransUnion Score",
        "Coborrower Equifax Score",
        "Purchase Price", "Appraised Value",
        "PurchasePrice", "AppraisedValue",
        "Borrower Age",
        "Loan Amount Locked",
        "DaysOpenToSubmitted", "DaysSubmittedToApproved",
        "DaysApprovedToCTC", "DaysCTCToFunded",
        "DaysTotalSubmitToFund", "DaysTotalOpenToFund",
        "LockDurationDays", "DaysSubmittedToUW", "DaysUWToApproved",
        "DaysDocsToFunded",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 6. Zeros → NaN for credit score and loan amount ──────────────────
    if "DecisionCreditScore" in df.columns:
        df.loc[df["DecisionCreditScore"] == 0, "DecisionCreditScore"] = np.nan
    if "LoanAmount" in df.columns:
        df.loc[df["LoanAmount"] == 0, "LoanAmount"] = np.nan

    return df


# ─── CLI summary ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_and_clean()

    print(f"\n{'─' * 60}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"\nOutcome distribution:")
    print(df["Outcome"].value_counts().to_string())
    print(f"\nDidFund: {df['DidFund'].sum():,} loans funded")
    print(f"\nLoan Status breakdown:")
    print(df["Loan Status"].value_counts().head(10).to_string())
    print(f"\nDecisionCreditScore (after cleaning):")
    print(df["DecisionCreditScore"].describe().to_string())
    print(f"\nLoanAmount (after cleaning):")
    print(df["LoanAmount"].describe().to_string())
    print(f"\nDate column sample — Funded D:")
    print(f"  non-null: {df['Funded D'].notna().sum():,}")
    print(f"  range: {df['Funded D'].min()} → {df['Funded D'].max()}")
