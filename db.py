"""SQLAlchemy engine factory for the Gallus SQL Server database."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv(override=True)

ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


def _build_connection_url() -> str:
    host = os.environ["HOST"]
    port = os.environ.get("PORT", "1433")
    user = os.environ["USER"]
    password = os.environ["PASS"]
    database = os.environ.get("DATABASE", "")

    odbc_parts = [
        f"DRIVER={{{ODBC_DRIVER}}}",
        f"SERVER={host},{port}",
        f"UID={user}",
        f"PWD={password}",
        "Encrypt=yes",
        "TrustServerCertificate=yes",
    ]
    if database:
        odbc_parts.append(f"DATABASE={database}")

    odbc_str = ";".join(odbc_parts)
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(_build_connection_url(), pool_pre_ping=True, future=True)


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)
