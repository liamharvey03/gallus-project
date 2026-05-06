"""Smoke-test db.read_table — confirms typed coercion works on real tables.

Run from repo root:

    python scripts/test_read_table.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from db import read_table  # noqa: E402


def _is_numeric(dtype) -> bool:
    return pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype)


def _is_datetime(dtype) -> bool:
    return pd.api.types.is_datetime64_any_dtype(dtype)


def main() -> int:
    failures: list[str] = []

    print("=" * 60)
    print("read_table('loans', limit=10)")
    print("=" * 60)
    loans = read_table("loans", limit=10)
    print(f"Shape: {loans.shape}")
    print()
    print("Spot-check dtypes:")
    spot_loans = [
        ("DecisionCreditScore", "numeric"),
        ("Funded D", "datetime"),
        ("Approved D", "datetime"),
        ("DaysApprovedToCTC", "numeric"),
        ("PurchasePrice", "numeric"),
        ("LoanAmount", "numeric"),  # already float in source — should stay numeric
        ("LoanGuid", "string"),     # NOT in dtype registry — should stay string-ish
        ("recovery_rank", "numeric"),
        ("recovery_gap", "numeric"),
        ("momentum_rank", "numeric"),
        ("moneyball_difficulty", "numeric"),
    ]
    for col, expected in spot_loans:
        if col not in loans.columns:
            print(f"  ! {col}: column not in result")
            failures.append(f"{col} missing from loans")
            continue
        dtype = loans[col].dtype
        if expected == "numeric":
            ok = _is_numeric(dtype)
        elif expected == "datetime":
            ok = _is_datetime(dtype)
        else:
            ok = pd.api.types.is_string_dtype(dtype) or str(dtype) == "object"
        status = "OK" if ok else "FAIL"
        if not ok:
            failures.append(f"loans.{col}: expected {expected}, got {dtype}")
        print(f"  [{status}] {col}: {dtype} (expected {expected})")

    print()
    print("Full dtype list (loans, first 30 cols):")
    print(loans.dtypes.head(30).to_string())

    print()
    print("=" * 60)
    print("read_table('backtest_monthly')")
    print("=" * 60)
    bt = read_table("backtest_monthly")
    print(f"Shape: {bt.shape}")
    print()
    print("Spot-check dtypes:")
    spot_bt = [
        ("projected", "numeric"),
        ("projected_pipeline", "numeric"),
        ("actual", "numeric"),
        ("error_pct", "numeric"),
    ]
    for col, expected in spot_bt:
        if col not in bt.columns:
            print(f"  ! {col}: column not in result")
            failures.append(f"{col} missing from backtest_monthly")
            continue
        dtype = bt[col].dtype
        ok = _is_numeric(dtype) if expected == "numeric" else _is_datetime(dtype)
        status = "OK" if ok else "FAIL"
        if not ok:
            failures.append(f"backtest_monthly.{col}: expected {expected}, got {dtype}")
        print(f"  [{status}] {col}: {dtype} (expected {expected})")

    print()
    print("Full dtype list (backtest_monthly):")
    print(bt.dtypes.to_string())

    print()
    print("=" * 60)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
