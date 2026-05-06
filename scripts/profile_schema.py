"""Profile the Forecasting database end-to-end.

Run from repo root:

    python scripts/profile_schema.py

Writes a Markdown report to reports/schema_profile.md.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402

from db import get_engine  # noqa: E402

OUT_PATH = ROOT / "reports" / "schema_profile.md"

NUMERIC_TYPES = {
    "int", "bigint", "smallint", "tinyint",
    "decimal", "numeric", "float", "real",
    "money", "smallmoney", "bit",
}
STRING_TYPES = {"varchar", "nvarchar", "char", "nchar", "text", "ntext"}
DATE_TYPES = {
    "date", "datetime", "datetime2", "smalldatetime",
    "datetimeoffset", "time",
}
NO_DISTINCT_TYPES = {"text", "ntext", "image", "xml"}

EXPECTED_HANDOFF_NAMES = [
    "Branch Channel",
    "Product Type",
    "LoanAmount",
    "LoanGuid",
    "loan_count",
    "avg_probability",
    "total_expected_value",
]
AGGREGATE_ONLY_EXPECTED = {"loan_count", "avg_probability", "total_expected_value"}

NUMERIC_NAME_KEYWORDS = (
    "amount", "count", "rate", "score", "ltv", "cltv", "days",
    "period", "term", "value", "price", "pct", "percent",
    "probability", "fee", "income", "balance", "ratio", "qty",
    "quantity", "principal", "interest", "expected_value",
)

WIDE_TABLE_THRESHOLD = 100


def q_ident(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def name_suggests_date(name: str) -> bool:
    n = name
    if re.search(r"date", n, re.IGNORECASE):
        return True
    if re.search(r"_dt$", n, re.IGNORECASE):
        return True
    if re.search(r"\bdt\b", n, re.IGNORECASE):
        return True
    if re.search(r" d$", n, re.IGNORECASE):
        return True
    # camelCase: lowercase letter followed by capital D at end (e.g. DocsBackD)
    if re.search(r"[a-z]D$", n):
        return True
    return False


def name_suggests_numeric(name: str) -> bool:
    n = name.lower()
    return any(kw in n for kw in NUMERIC_NAME_KEYWORDS)


def list_tables(conn) -> list[tuple[str, str]]:
    sql = text(
        "SELECT TABLE_SCHEMA, TABLE_NAME "
        "FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_SCHEMA, TABLE_NAME"
    )
    return [(s, t) for s, t in conn.execute(sql).all()]


def get_columns(conn, schema: str, table: str) -> list[dict]:
    sql = text(
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "
        "       IS_NULLABLE, ORDINAL_POSITION "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = :s AND TABLE_NAME = :t "
        "ORDER BY ORDINAL_POSITION"
    )
    rows = conn.execute(sql, {"s": schema, "t": table}).all()
    return [
        {
            "name": r[0],
            "type": r[1].lower(),
            "max_len": r[2],
            "nullable": r[3],
            "pos": r[4],
        }
        for r in rows
    ]


def row_count(conn, schema: str, table: str) -> int:
    sql = text(f"SELECT COUNT(*) FROM {q_ident(schema)}.{q_ident(table)}")
    return conn.execute(sql).scalar_one()


def column_profile(conn, schema: str, table: str, col: dict) -> dict:
    full = f"{q_ident(schema)}.{q_ident(table)}"
    cn = q_ident(col["name"])
    t = col["type"]

    select_parts: list[str] = [
        f"COUNT(*) - COUNT({cn}) AS nulls",
    ]
    if t not in NO_DISTINCT_TYPES:
        select_parts.append(f"COUNT(DISTINCT {cn}) AS distinct_n")
    if t in STRING_TYPES:
        select_parts.append(
            f"SUM(CASE WHEN DATALENGTH({cn}) = 0 THEN 1 ELSE 0 END) AS empty_strings"
        )
    if t in NUMERIC_TYPES:
        select_parts.extend([
            f"MIN(CAST({cn} AS FLOAT)) AS min_v",
            f"MAX(CAST({cn} AS FLOAT)) AS max_v",
            f"AVG(CAST({cn} AS FLOAT)) AS avg_v",
            f"SUM(CASE WHEN {cn} = 0 THEN 1 ELSE 0 END) AS zeros",
        ])
    if t in DATE_TYPES:
        select_parts.extend([
            f"MIN({cn}) AS date_min",
            f"MAX({cn}) AS date_max",
        ])

    sql = "SELECT " + ", ".join(select_parts) + f" FROM {full}"
    row = dict(conn.execute(text(sql)).mappings().one())

    out: dict = {"name": col["name"], "type": t}
    out["nulls"] = row.get("nulls")
    distinct_n = row.get("distinct_n")
    if distinct_n is None and t in NO_DISTINCT_TYPES:
        out["distinct"] = "(skipped)"
    elif distinct_n is not None and distinct_n > 1000:
        out["distinct"] = ">1000"
    else:
        out["distinct"] = distinct_n

    if "empty_strings" in row:
        out["empty_strings"] = row["empty_strings"]
    if "min_v" in row:
        out["min"] = row["min_v"]
        out["max"] = row["max_v"]
        out["avg"] = row["avg_v"]
        out["zeros"] = row["zeros"]
    if "date_min" in row:
        out["date_min"] = row["date_min"]
        out["date_max"] = row["date_max"]

    return out


def sample_rows(conn, schema: str, table: str) -> pd.DataFrame:
    sql = text(f"SELECT TOP 3 * FROM {q_ident(schema)}.{q_ident(table)}")
    return pd.read_sql(sql, conn)


# ----------------------------- rendering ---------------------------------


def md_cell(v) -> str:
    if v is None:
        return ""
    s = str(v)
    s = s.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    return s


def render_md_table(rows: list[dict], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(md_cell(r.get(h, "")) for h in headers) + " |")
    return "\n".join(out)


def fmt_num(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:  # NaN
            return ""
        if abs(v) >= 1e6 or (0 < abs(v) < 1e-3):
            return f"{v:.4g}"
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def render_columns_table(cols: list[dict]) -> str:
    rows = [
        {
            "#": c["pos"],
            "name": f"`{c['name']}`",
            "type": c["type"],
            "max_len": c["max_len"] if c["max_len"] is not None else "",
            "nullable": c["nullable"],
        }
        for c in cols
    ]
    return render_md_table(rows, ["#", "name", "type", "max_len", "nullable"])


def render_profile_table(profiles: list[dict]) -> str:
    rows = []
    for p in profiles:
        rows.append({
            "name": f"`{p['name']}`",
            "type": p["type"],
            "nulls": p.get("nulls", ""),
            "distinct": p.get("distinct", ""),
            "empty_str": p.get("empty_strings", ""),
            "min": fmt_num(p.get("min")),
            "max": fmt_num(p.get("max")),
            "avg": fmt_num(p.get("avg")),
            "zeros": p.get("zeros", ""),
            "date_min": p.get("date_min", ""),
            "date_max": p.get("date_max", ""),
        })
    return render_md_table(
        rows,
        ["name", "type", "nulls", "distinct", "empty_str",
         "min", "max", "avg", "zeros", "date_min", "date_max"],
    )


def render_samples(df: pd.DataFrame) -> str:
    if df.empty:
        return "_(no rows)_"
    df = df.copy()

    def _fmt(v):
        if v is None:
            return ""
        if isinstance(v, float) and v != v:
            return ""
        s = str(v)
        return s if len(s) <= 80 else s[:77] + "..."

    if len(df.columns) <= 12:
        rows = [
            {c: _fmt(df.iloc[i][c]) for c in df.columns}
            for i in range(len(df))
        ]
        return render_md_table(rows, [str(c) for c in df.columns])

    # Wide: pivot so columns become rows
    pivot_rows = []
    for col in df.columns:
        row = {"column": f"`{col}`"}
        for i in range(len(df)):
            row[f"row{i + 1}"] = _fmt(df.iloc[i][col])
        pivot_rows.append(row)
    headers = ["column"] + [f"row{i + 1}" for i in range(len(df))]
    return render_md_table(pivot_rows, headers)


def naming_audit(loan_cols: list[dict]) -> str:
    actual = {c["name"] for c in loan_cols}
    actual_lower = {c["name"].lower(): c["name"] for c in loan_cols}

    rows = []
    for exp in EXPECTED_HANDOFF_NAMES:
        note = " _(aggregate-only convention)_" if exp in AGGREGATE_ONLY_EXPECTED else ""
        if exp in actual:
            rows.append({"expected": f"`{exp}`", "actual": f"`{exp}`",
                         "status": f"OK{note}"})
            continue
        if exp.lower() in actual_lower:
            rows.append({
                "expected": f"`{exp}`",
                "actual": f"`{actual_lower[exp.lower()]}`",
                "status": f"CASE/SPACING DIFF{note}",
            })
            continue
        # try space<->underscore variants
        match = None
        for cand in (exp.replace(" ", "_"), exp.replace("_", " ")):
            if cand in actual:
                match = cand
                break
            if cand.lower() in actual_lower:
                match = actual_lower[cand.lower()]
                break
        if match:
            rows.append({"expected": f"`{exp}`", "actual": f"`{match}`",
                         "status": f"SPACE/UNDERSCORE DIFF{note}"})
        else:
            rows.append({"expected": f"`{exp}`", "actual": "_(not found)_",
                         "status": f"MISSING{note}"})
    return render_md_table(rows, ["expected", "actual", "status"])


def find_type_coercion_failures(table_cols: dict) -> list[dict]:
    flags: list[dict] = []
    for (schema, table), cols in table_cols.items():
        for c in cols:
            if c["type"] not in STRING_TYPES:
                continue
            suspicions = []
            if name_suggests_date(c["name"]):
                suspicions.append("date")
            if name_suggests_numeric(c["name"]):
                suspicions.append("numeric")
            if suspicions:
                flags.append({
                    "schema": schema,
                    "table": f"`{table}`",
                    "column": f"`{c['name']}`",
                    "type": c["type"],
                    "max_len": c["max_len"] if c["max_len"] is not None else "",
                    "looks_like": ",".join(suspicions),
                })
    return flags


# ----------------------------- main --------------------------------------


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    md: list[str] = []
    md.append("# Forecasting DB Schema Profile")
    md.append("")
    md.append(f"_Generated: {datetime.now().isoformat(timespec='seconds')}_")
    md.append("")

    with engine.connect() as conn:
        tables = list_tables(conn)
        md.append(f"**Database:** `Forecasting`  ")
        md.append(f"**Tables:** {len(tables)}")
        md.append("")

        table_cols: dict[tuple[str, str], list[dict]] = {}
        row_counts: dict[tuple[str, str], int] = {}
        for schema, table in tables:
            print(f">> inventory: {schema}.{table}")
            table_cols[(schema, table)] = get_columns(conn, schema, table)
            row_counts[(schema, table)] = row_count(conn, schema, table)

        # Top-level table-of-tables
        md.append("## Tables")
        md.append("")
        toc_rows = [
            {
                "table": f"`{t}`",
                "rows": f"{row_counts[(s, t)]:,}",
                "cols": len(table_cols[(s, t)]),
            }
            for (s, t) in tables
        ]
        md.append(render_md_table(toc_rows, ["table", "rows", "cols"]))
        md.append("")

        # Naming audit on loans
        md.append("## Naming convention audit (`loans`)")
        md.append("")
        md.append(
            "_CLAUDE.md handoff names are checked against the actual `loans` "
            "schema. The last three expected names are aggregate-only "
            "conventions and aren't expected to appear in `loans` itself — they "
            "should land in the aggregate tables._"
        )
        md.append("")
        loan_cols = table_cols.get(("dbo", "loans"), [])
        md.append(naming_audit(loan_cols))
        md.append("")

        # Cross-table check for the aggregate-only names
        md.append("### Aggregate-name presence across all tables")
        md.append("")
        agg_rows = []
        for agg in AGGREGATE_ONLY_EXPECTED:
            hits = []
            case_hits = []
            for (s, t), cols in table_cols.items():
                names = {c["name"] for c in cols}
                lowers = {c["name"].lower(): c["name"] for c in cols}
                if agg in names:
                    hits.append(t)
                elif agg.lower() in lowers:
                    case_hits.append(f"{t} (as `{lowers[agg.lower()]}`)")
            actual = ", ".join(hits) if hits else (
                ", ".join(case_hits) if case_hits else "_(not found)_"
            )
            status = "OK" if hits else ("CASE DIFF" if case_hits else "MISSING")
            agg_rows.append({"expected": f"`{agg}`", "found_in": actual, "status": status})
        md.append(render_md_table(agg_rows, ["expected", "found_in", "status"]))
        md.append("")

        # Type-coercion flags across all tables
        md.append("## Suspected type-coercion failures")
        md.append("")
        md.append(
            "_String-typed columns whose names suggest numeric or date values. "
            "These are likely CSV-load casualties that will need explicit "
            "casting before use._"
        )
        md.append("")
        flags = find_type_coercion_failures(table_cols)
        if flags:
            md.append(render_md_table(
                flags,
                ["schema", "table", "column", "type", "max_len", "looks_like"],
            ))
        else:
            md.append("_None found._")
        md.append("")

        # Per-table sections
        for schema, table in tables:
            cols = table_cols[(schema, table)]
            n = row_counts[(schema, table)]
            print(f">> profiling {schema}.{table} ({len(cols)} cols, {n:,} rows)")

            md.append("---")
            md.append("")
            md.append(f"## `{schema}.{table}`")
            md.append("")
            md.append(f"**Rows:** {n:,}  |  **Columns:** {len(cols)}")
            md.append("")

            md.append("### Columns")
            md.append("")
            md.append(render_columns_table(cols))
            md.append("")

            do_profile = (table == "loans") or (len(cols) > WIDE_TABLE_THRESHOLD)
            if do_profile and n > 0:
                md.append("### Per-column profile")
                md.append("")
                profiles = []
                for i, c in enumerate(cols, 1):
                    if i % 25 == 0:
                        print(f"   profiling col {i}/{len(cols)}")
                    try:
                        profiles.append(column_profile(conn, schema, table, c))
                    except DBAPIError as err:
                        profiles.append({
                            "name": c["name"], "type": c["type"],
                            "nulls": "ERROR",
                            "distinct": str(err)[:120],
                        })
                md.append(render_profile_table(profiles))
                md.append("")

            md.append("### Sample (TOP 3)")
            md.append("")
            try:
                sample = sample_rows(conn, schema, table)
                md.append(render_samples(sample))
            except Exception as err:
                md.append(f"_(sample failed: {err})_")
            md.append("")

    OUT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f">> Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
