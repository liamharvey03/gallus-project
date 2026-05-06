"""Smoke-test the Gallus SQL Server connection.

Run from the repo root:

    python scripts/test_connection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

from db import get_engine


def _diagnose(err: Exception) -> str:
    msg = str(err).lower()
    if any(s in msg for s in ("timeout", "could not open a connection", "tcp provider", "network-related")):
        return (
            "Looks like a network / IP-whitelist issue (the host is unreachable from this machine). "
            "Check the RDS security group inbound rule on port 1433 — your current public IP probably "
            "isn't whitelisted."
        )
    if any(s in msg for s in ("login failed", "cannot open server", "password did not match", "18456")):
        return (
            "Looks like an auth failure (username/password rejected, or the user has no access to the "
            "default database). Verify the credentials with the data owner."
        )
    if "ssl" in msg or "certificate" in msg:
        return "Looks like a TLS / certificate issue. Check Encrypt / TrustServerCertificate settings."
    return "Unrecognized error pattern — full traceback below."


def main() -> int:
    print(">> Building engine and connecting...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT @@VERSION")).scalar_one()
            print(">> Connected.")
            print("\n--- @@VERSION ---")
            print(version)

            print("\n--- Tables ---")
            rows = conn.execute(
                text(
                    "SELECT TABLE_SCHEMA, TABLE_NAME "
                    "FROM INFORMATION_SCHEMA.TABLES "
                    "ORDER BY TABLE_SCHEMA, TABLE_NAME"
                )
            ).all()

        if not rows:
            print("(no tables visible to this user)")
        else:
            current_schema = None
            for schema, name in rows:
                if schema != current_schema:
                    print(f"\n[{schema}]")
                    current_schema = schema
                print(f"  {name}")
            print(f"\n>> {len(rows)} table(s) total")
        return 0

    except (OperationalError, DBAPIError) as err:
        print(">> CONNECTION FAILED", file=sys.stderr)
        print(_diagnose(err), file=sys.stderr)
        print("\n--- Full error ---", file=sys.stderr)
        print(repr(err), file=sys.stderr)
        return 1
    except Exception as err:
        print(">> UNEXPECTED ERROR", file=sys.stderr)
        print(_diagnose(err), file=sys.stderr)
        print("\n--- Full error ---", file=sys.stderr)
        print(repr(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
