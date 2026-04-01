"""
FlexpointUC Loan Performance Analysis
=====================================
Starter script for pulling data from SQL Server and running analysis in Python.

SETUP:
------
pip install pandas pyodbc sqlalchemy scikit-learn matplotlib seaborn

CONNECTION OPTIONS:
-------------------
1. Direct SQL Server connection (requires pyodbc + ODBC driver)
2. Load from exported CSV/JSON files (simpler)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# =============================================================================
# OPTION 1: Load from JSON files (if you export from VS Code SQL extension)
# =============================================================================

def load_from_json(filepath):
    """Load a JSON file exported from VS Code SQL extension."""
    return pd.read_json(filepath)

# Example usage:
# df_status = load_from_json('profile_status.json')
# df_numeric = load_from_json('profile_numeric.json')


# =============================================================================
# OPTION 2: Direct SQL Server Connection
# =============================================================================

def get_sql_connection():
    """
    Connect directly to SQL Server.

    Requirements:
    - Install ODBC Driver: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
    - pip install pyodbc sqlalchemy

    Update the connection string with your credentials.
    """
    from sqlalchemy import create_engine
    import urllib

    # Update these values
    server = 'YOUR_SERVER_NAME'
    database = 'FlexpointUC'
    username = 'YOUR_USERNAME'  # or use Windows auth
    password = 'YOUR_PASSWORD'

    # For Windows Authentication:
    # connection_string = f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

    # For SQL Server Authentication:
    connection_string = f"mssql+pyodbc://{username}:{urllib.parse.quote(password)}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"

    engine = create_engine(connection_string)
    return engine

def pull_loan_data(engine, start_date='2023-01-01'):
    """Pull the main loan dataset for analysis."""

    query = f"""
    SELECT
        LoanGuid,
        [Loan Status],
        CASE WHEN [Loan Status] = 'Funded' THEN 1 ELSE 0 END as IsFunded,

        -- Credit/Risk
        DecisionCreditScore,
        LTV,
        CLTV,

        -- Loan Characteristics
        LoanAmount,
        NoteRate,
        Term,
        [Loan Purpose],
        [Loan Type],
        [Product Type],
        [Amortization Type],
        [Doc Type],
        [Occupancy Type],
        [Lock Period (days)] as LockPeriodDays,
        [Rate Lock Status],

        -- Geographic
        [Property State],
        [Property County],
        ProdIsSpInRuralArea,

        -- Channel/Originator
        [Branch Channel],
        Branch,
        [Internal Assigned Loan Officer Name] as LoanOfficer,
        [Internal Assigned Processor Name] as Processor,
        [Internal Assigned Underwriter Name] as Underwriter,

        -- Dates
        [Submitted D] as SubmittedDate,
        [Approved D] as ApprovedDate,
        [Underwriting D] as UnderwritingDate,
        [Clear To Close D] as ClearToCloseDate,
        [Funded D] as FundedDate,
        [Loan Canceled D] as CanceledDate,
        [Loan Denied D] as DeniedDate,
        [Rate Lock D] as RateLockDate,
        [Rate Lock Expiration D] as RateLockExpDate,

        -- Pre-calculated velocity
        DATEDIFF(day, [Submitted D], [Approved D]) as DaysToApproval,
        DATEDIFF(day, [Rate Lock D], [Rate Lock Expiration D]) as LockDuration

    FROM FlexPointFinal
    WHERE [Submitted D] >= '{start_date}'
    """

    return pd.read_sql(query, engine)


# =============================================================================
# DATA PREPROCESSING
# =============================================================================

def preprocess_loans(df):
    """Clean and engineer features for modeling."""

    df = df.copy()

    # Convert dates
    date_cols = ['SubmittedDate', 'ApprovedDate', 'UnderwritingDate',
                 'ClearToCloseDate', 'FundedDate', 'CanceledDate',
                 'DeniedDate', 'RateLockDate', 'RateLockExpDate']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Create outcome categories
    df['Outcome'] = df['Loan Status'].apply(lambda x:
        'Funded' if x == 'Funded' else
        'Denied' if x == 'Denied' else
        'Canceled' if x in ['Canceled', 'Withdrawn'] else
        'In Progress'
    )

    # Credit score bands
    df['CreditBand'] = pd.cut(df['DecisionCreditScore'],
                              bins=[0, 620, 660, 700, 740, 780, 850],
                              labels=['Subprime', 'Near Prime', 'Prime',
                                     'Prime+', 'Super Prime', 'Exceptional'])

    # LTV bands
    df['LTVBand'] = pd.cut(df['LTV'],
                           bins=[0, 60, 70, 80, 90, 95, 150],
                           labels=['0-60%', '61-70%', '71-80%',
                                  '81-90%', '91-95%', '>95%'])

    # Loan size bands
    df['LoanSizeBand'] = pd.cut(df['LoanAmount'],
                                bins=[0, 200000, 400000, 600000, 1000000, 10000000],
                                labels=['<200K', '200-400K', '400-600K',
                                       '600K-1M', '>1M'])

    # Calculate additional velocity features
    if 'SubmittedDate' in df.columns and 'ApprovedDate' in df.columns:
        df['DaysToApprovalCalc'] = (df['ApprovedDate'] - df['SubmittedDate']).dt.days

    return df


# =============================================================================
# EXPLORATORY ANALYSIS
# =============================================================================

def run_eda(df):
    """Run exploratory data analysis and print summary."""

    print("=" * 60)
    print("DATASET OVERVIEW")
    print("=" * 60)
    print(f"Total Loans: {len(df):,}")
    print(f"Date Range: {df['SubmittedDate'].min()} to {df['SubmittedDate'].max()}")
    print(f"Columns: {len(df.columns)}")

    print("\n" + "=" * 60)
    print("TARGET VARIABLE: Loan Status")
    print("=" * 60)
    print(df['Loan Status'].value_counts())
    print(f"\nFunded Rate: {df['IsFunded'].mean()*100:.1f}%")

    print("\n" + "=" * 60)
    print("NUMERIC FEATURES SUMMARY")
    print("=" * 60)
    numeric_cols = ['DecisionCreditScore', 'LTV', 'CLTV', 'LoanAmount',
                    'NoteRate', 'Term', 'LockPeriodDays']
    print(df[numeric_cols].describe())

    print("\n" + "=" * 60)
    print("MISSING VALUES")
    print("=" * 60)
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(1)
    missing_df = pd.DataFrame({'Missing': missing, 'Percent': missing_pct})
    print(missing_df[missing_df['Missing'] > 0].sort_values('Percent', ascending=False))

    print("\n" + "=" * 60)
    print("PULL-THROUGH BY KEY SEGMENTS")
    print("=" * 60)

    for col in ['Loan Purpose', 'Loan Type', 'Branch Channel', 'Property State']:
        if col in df.columns:
            pt = df.groupby(col)['IsFunded'].agg(['mean', 'count'])
            pt.columns = ['PullThrough', 'Count']
            pt = pt[pt['Count'] >= 10].sort_values('Count', ascending=False).head(10)
            pt['PullThrough'] = (pt['PullThrough'] * 100).round(1)
            print(f"\n{col}:")
            print(pt)

    return df


# =============================================================================
# FEATURE IMPORTANCE ANALYSIS
# =============================================================================

def analyze_feature_importance(df):
    """Quick feature importance using Random Forest."""

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    # Prepare features
    feature_cols = ['DecisionCreditScore', 'LTV', 'CLTV', 'LoanAmount',
                    'NoteRate', 'Term', 'LockPeriodDays', 'DaysToApproval']

    cat_cols = ['Loan Purpose', 'Loan Type', 'Product Type', 'Branch Channel',
                'Property State', 'Occupancy Type']

    # Create a copy with only complete cases for key features
    df_model = df[['IsFunded'] + feature_cols + cat_cols].dropna(subset=feature_cols)

    # Encode categoricals
    le = LabelEncoder()
    for col in cat_cols:
        df_model[col] = df_model[col].fillna('Unknown')
        df_model[col + '_enc'] = le.fit_transform(df_model[col])

    # Features for model
    X_cols = feature_cols + [c + '_enc' for c in cat_cols]
    X = df_model[X_cols].fillna(0)
    y = df_model['IsFunded']

    # Fit Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    # Feature importance
    importance = pd.DataFrame({
        'Feature': X_cols,
        'Importance': rf.feature_importances_
    }).sort_values('Importance', ascending=False)

    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE (Random Forest)")
    print("=" * 60)
    print(importance.head(20))

    return importance, rf


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":

    # Option A: Load from JSON exports
    # ---------------------------------
    # If you've run the SQL queries and saved as JSON, load them:
    #
    # df = load_from_json('loan_export.json')

    # Option B: Load from CSV export
    # ---------------------------------
    # df = pd.read_csv('loan_export.csv')

    # Option C: Direct database connection
    # ---------------------------------
    # engine = get_sql_connection()
    # df = pull_loan_data(engine, start_date='2023-01-01')

    # Once you have data loaded:
    # df = preprocess_loans(df)
    # run_eda(df)
    # importance, model = analyze_feature_importance(df)

    print("Update connection settings or load your exported data, then run analysis!")
    print("\nQuick start:")
    print("  1. Run data_profiling.sql sections in VS Code")
    print("  2. Export SECTION 13 results as CSV")
    print("  3. df = pd.read_csv('your_export.csv')")
    print("  4. df = preprocess_loans(df)")
    print("  5. run_eda(df)")
