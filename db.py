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


def read_table(
    name: str,
    where: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read a `dbo.<name>` table into a typed DataFrame.

    Numeric and date columns registered in `forecasting.dtypes` are coerced
    via `pd.to_numeric` / `pd.to_datetime` (errors='coerce' — bad values
    become NaN/NaT rather than raising).
    """
    from forecasting.dtypes import DATE_COLUMNS, NUMERIC_COLUMNS

    parts = ["SELECT"]
    if limit is not None:
        parts.append(f"TOP {int(limit)}")
    parts.append("*")
    parts.append(f"FROM [dbo].[{name}]")
    if where:
        parts.append(f"WHERE {where}")
    sql = " ".join(parts)

    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)

    for col in NUMERIC_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DATE_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
