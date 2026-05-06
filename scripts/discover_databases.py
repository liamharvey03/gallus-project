"""Enumerate non-system databases visible to the connected user and probe each
for user tables.

Run from repo root:

    python scripts/discover_databases.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError

from db import ODBC_DRIVER, get_engine  # noqa: E402

TABLE_PREVIEW_LIMIT = 20


def _engine_for(database: str | None):
    """Build an engine pinned to a specific database (bypasses get_engine cache)."""
    host = os.environ["HOST"]
    port = os.environ.get("PORT", "1433")
    user = os.environ["USER"]
    password = os.environ["PASS"]

    parts = [
        f"DRIVER={{{ODBC_DRIVER}}}",
        f"SERVER={host},{port}",
        f"UID={user}",
        f"PWD={password}",
        "Encrypt=yes",
        "TrustServerCertificate=yes",
    ]
    if database:
        parts.append(f"DATABASE={database}")
    odbc_str = ";".join(parts)
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}",
        pool_pre_ping=True,
        future=True,
    )


def list_user_databases() -> list[str]:
    print(">> Listing non-system databases visible to current user...")
    sql = text(
        "SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name"
    )
    with get_engine().connect() as conn:
        return [row[0] for row in conn.execute(sql).all()]


def probe_database(db_name: str) -> tuple[int, list[tuple[str, str]], str | None]:
    """Return (table_count, first_tables, error_message)."""
    sql = text(
        "SELECT TABLE_SCHEMA, TABLE_NAME "
        "FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_SCHEMA, TABLE_NAME"
    )
    try:
        engine = _engine_for(db_name)
        with engine.connect() as conn:
            rows = conn.execute(sql).all()
        return len(rows), [(s, t) for s, t in rows[:TABLE_PREVIEW_LIMIT]], None
    except (OperationalError, DBAPIError) as err:
        return 0, [], _short_error(err)
    except Exception as err:
        return 0, [], _short_error(err)


def _short_error(err: Exception) -> str:
    msg = str(err)
    msg = msg.replace("\n", " ").strip()
    return msg[:300] + ("..." if len(msg) > 300 else "")


def main() -> int:
    try:
        dbs = list_user_databases()
    except Exception as err:
        print(">> Failed to list databases:", _short_error(err), file=sys.stderr)
        return 1

    if not dbs:
        print("(no non-system databases visible — ForecastingUser is locked to master)")
        print("Action: ask the client to grant access or share the DB name.")
        return 0

    print(f">> {len(dbs)} non-system database(s) visible:")
    for name in dbs:
        print(f"   - {name}")
    print()

    readable: list[str] = []
    blocked: list[tuple[str, str]] = []

    for name in dbs:
        print(f"=== {name} ===")
        count, preview, err = probe_database(name)
        if err is not None:
            print(f"  ! cannot read: {err}")
            blocked.append((name, err))
            print()
            continue

        print(f"  tables: {count}")
        if preview:
            current_schema = None
            for schema, tname in preview:
                if schema != current_schema:
                    print(f"  [{schema}]")
                    current_schema = schema
                print(f"    {tname}")
            if count > TABLE_PREVIEW_LIMIT:
                print(f"  ... {count - TABLE_PREVIEW_LIMIT} more")
        readable.append(name)
        print()

    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Readable databases ({len(readable)}): {readable or '(none)'}")
    if blocked:
        print(f"Blocked databases ({len(blocked)}):")
        for name, err in blocked:
            print(f"  - {name}: {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
