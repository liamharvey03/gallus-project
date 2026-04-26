#!/usr/bin/env python3
"""
Export v3 model outputs + every dashboard data section as CSVs for the
Gallus team to join in SQL and replicate the FlexPoint dashboard inside
ThoughtSpot.

Writes a bundle to `outputs/thoughtspot_export/`:
  - loans.csv                          (one row per active pipeline loan, wide)
  - already_funded.csv                 (month-to-date funded loans)
  - summary_kpis.csv                   (single-row snapshot KPIs)
  - stage_funnel.csv                   (pipeline stage distribution)
  - channel_split.csv                  (Wholesale vs Retail)
  - product_breakdown.csv              (per Product Type)
  - pull_through_monthly.csv           (month x product historical pull-through)
  - cycle_times_by_product.csv         (percentiles per product)
  - cycle_times_raw.csv                (one row per funded loan + cycle_days)
  - backtest_monthly.csv               (per-month ML rolling backtest)
  - revenue_at_risk_buckets.csv
  - top_recovery_opportunities.csv
  - at_risk_loans.csv                  (Watch List: rich per-loan with counterfactuals)
  - moneyball_quadrant_summary.csv
  - bottleneck_heatmap.csv             (transition x product x metric - long)
  - stage_conversion_rates.csv         (overall + per product - long)
  - current_bottlenecks.csv            (active pipeline by stage - long)
  - velocity_distribution.csv          (bands + per product - long)
  - velocity_by_stage.csv
  - momentum_alerts.csv
  - what_if_scenarios.csv
  - scorecards.csv                     (products + channels with composite sub-scores)
  - scorecard_rankings.csv
  - optimization_recommendations.csv
  - industry_benchmarks_transitions.csv
  - feature_importance.csv
  - README.md                          (CSV-to-visual map + grain notes)

All CSVs carry a `snapshot_date` column where applicable so historical snapshots
can be appended (one-row-per-loan-per-snapshot) later without schema change.

Usage:
    python src/export_for_thoughtspot.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent
PROJECT = SRC.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(SRC))

import config
from data_prep import load_and_clean
from transition_tables import build_transition_tables
from feature_engineering_v3 import (
    build_training_set,
    encode_categoricals,
    fill_missing_numeric,
    get_feature_columns,
    build_feature_row,
)
from models import train_and_select, _predict_proba
from pipeline_snapshot import build_snapshot
from elimination_filter import apply_elimination_filter

import generate_dashboard_data as gdd


SNAPSHOT_DATE = gdd.SNAPSHOT_DATE
OUT_DIR = config.OUTPUTS_PATH / "thoughtspot_export"


# ───────────────────────────────── helpers ──────────────────────────────────

def _flatten_list_col(series: pd.Series, sep: str = " | ") -> pd.Series:
    """JSON list → pipe-joined string so SQL-side it's a simple TEXT column."""
    def _to_str(v):
        if isinstance(v, (list, tuple)):
            return sep.join(str(x) for x in v if x is not None and str(x) != "")
        return v
    return series.map(_to_str)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write(df: pd.DataFrame, name: str) -> None:
    path = OUT_DIR / name
    df.to_csv(path, index=False)
    print(f"  → {name:45s} {len(df):>6d} rows × {df.shape[1]:>3d} cols")


# ─────────────────────────────── loans.csv ──────────────────────────────────

def build_loans_csv(active, feats, at_risk_loans, moneyball,
                    top_recovery, momentum_alerts):
    """Wide per-loan table combining raw pipeline state, engineered features,
    ML predictions, counterfactuals, moneyball classification, risk flags,
    and rank columns for ranked-subset views (recovery / momentum)."""

    # Start from active (raw snapshot columns + ml_probability + expected_value
    # + elimination status, added by build_loan_table upstream).
    loans = active.copy()
    loans["snapshot_date"] = SNAPSHOT_DATE

    # Join engineered features. feats has the same index as active (subset).
    # Prefix engineered columns with `f_` to avoid collision with raw columns
    # that share names (e.g. days_at_stage is in both).
    f = feats.copy()
    f.columns = [
        c if c in ("LoanGuid",) else f"f_{c}" for c in f.columns
    ]
    f = f.drop(columns=["f_LoanGuid"], errors="ignore")
    loans = loans.join(f, how="left")

    # Counterfactual + risk-reason columns, keyed on LoanGuid (strings).
    cf_by_guid = {
        str(r["loan_guid"]): {
            "recommended_action":         r.get("recommended_action"),
            "counterfactual_probability": r.get("counterfactual_probability"),
            "probability_delta":          r.get("probability_delta"),
            "expected_value_uplift":      r.get("expected_value_uplift"),
            "risk_reasons":               " | ".join(r.get("risk_reasons") or []),
        }
        for r in at_risk_loans
    }
    loans["recommended_action"]         = loans["LoanGuid"].astype(str).map(
        lambda g: cf_by_guid.get(g, {}).get("recommended_action"))
    loans["counterfactual_probability"] = loans["LoanGuid"].astype(str).map(
        lambda g: cf_by_guid.get(g, {}).get("counterfactual_probability"))
    loans["probability_delta"]          = loans["LoanGuid"].astype(str).map(
        lambda g: cf_by_guid.get(g, {}).get("probability_delta"))
    loans["expected_value_uplift"]      = loans["LoanGuid"].astype(str).map(
        lambda g: cf_by_guid.get(g, {}).get("expected_value_uplift"))
    loans["risk_reasons"]               = loans["LoanGuid"].astype(str).map(
        lambda g: cf_by_guid.get(g, {}).get("risk_reasons"))
    loans["is_at_risk"] = loans["LoanGuid"].astype(str).isin(cf_by_guid.keys())

    # Recovery ranking (top 12 loans by recovery gap).
    rec_by_guid = {str(r["loan_guid"]): (i + 1, r.get("recovery_gap"))
                   for i, r in enumerate(top_recovery)}
    loans["recovery_rank"] = loans["LoanGuid"].astype(str).map(
        lambda g: rec_by_guid.get(g, (None, None))[0])
    loans["recovery_gap"] = loans["LoanGuid"].astype(str).map(
        lambda g: rec_by_guid.get(g, (None, None))[1])

    # Momentum ranking (top 15 slow high-value loans).
    mom_by_guid = {str(a["loan_guid"]): (i + 1)
                   for i, a in enumerate(momentum_alerts)}
    loans["momentum_rank"] = loans["LoanGuid"].astype(str).map(
        lambda g: mom_by_guid.get(g))

    # Moneyball fields (difficulty, quadrant, movable).
    mb_by_guid = {str(l["loan_guid"]): l for l in moneyball["loans"]}
    loans["moneyball_difficulty"] = loans["LoanGuid"].astype(str).map(
        lambda g: mb_by_guid.get(g, {}).get("difficulty"))
    loans["moneyball_quadrant"]   = loans["LoanGuid"].astype(str).map(
        lambda g: mb_by_guid.get(g, {}).get("quadrant"))
    loans["moneyball_is_movable"] = loans["LoanGuid"].astype(str).map(
        lambda g: mb_by_guid.get(g, {}).get("is_movable", False))
    loans["moneyball_cf_quadrant"] = loans["LoanGuid"].astype(str).map(
        lambda g: mb_by_guid.get(g, {}).get("cf_quadrant"))

    # Velocity band (same logic as build_velocity_momentum).
    vel = loans["f_stages_per_day"]

    def _band(v):
        if pd.isna(v) or v <= 0.05:
            return "Stalled"
        if v <= 0.15:
            return "Slow"
        if v <= 0.30:
            return "On Pace"
        return "Fast Track"

    loans["velocity"] = vel
    loans["velocity_band"] = vel.map(_band)

    # Coerce milestone date columns to ISO strings so they load cleanly in
    # Snowflake / BigQuery / whatever backs ThoughtSpot.
    for col, _, _ in config.STAGE_MAP:
        if col in loans.columns and pd.api.types.is_datetime64_any_dtype(loans[col]):
            loans[col] = loans[col].dt.strftime("%Y-%m-%d")
    for col in config.FAILURE_DATE_COLUMNS:
        if col in loans.columns and pd.api.types.is_datetime64_any_dtype(loans[col]):
            loans[col] = loans[col].dt.strftime("%Y-%m-%d")
    # Rate Lock dates referenced in counterfactual scoring
    for col in ("Rate Lock D", "Rate Lock Expiration D"):
        if col in loans.columns and pd.api.types.is_datetime64_any_dtype(loans[col]):
            loans[col] = loans[col].dt.strftime("%Y-%m-%d")

    # Order columns: keys → raw → model outputs → engineered → counterfactual → moneyball.
    key_cols = [c for c in ("snapshot_date", "LoanGuid", "Product Type",
                            "Loan Purpose", "Branch Channel", "current_stage",
                            "stage_rank", "days_at_stage", "LoanAmount",
                            "status", "elimination_reason", "failure_archetype")
                if c in loans.columns]
    model_cols = [c for c in ("ml_probability", "expected_value",
                              "base_probability") if c in loans.columns]
    cf_cols = ["is_at_risk", "risk_reasons", "recommended_action",
               "counterfactual_probability", "probability_delta",
               "expected_value_uplift",
               "recovery_rank", "recovery_gap", "momentum_rank"]
    mb_cols = ["moneyball_difficulty", "moneyball_quadrant",
               "moneyball_is_movable", "moneyball_cf_quadrant",
               "velocity", "velocity_band"]
    feat_cols = sorted([c for c in loans.columns if c.startswith("f_")])
    other = [c for c in loans.columns
             if c not in key_cols + model_cols + cf_cols + mb_cols + feat_cols]

    ordered = key_cols + model_cols + cf_cols + mb_cols + feat_cols + other
    return loans[ordered]


# ─────────────────────────── aggregate flatteners ───────────────────────────

def build_summary_csv(summary):
    # elimination_stats is a nested dict → flatten with dot notation
    row = {k: v for k, v in summary.items() if k != "elimination_stats"}
    elim = summary.get("elimination_stats", {})
    row["elimination_total"]        = elim.get("total")
    row["elimination_count"]        = elim.get("eliminated")
    row["elimination_pct"]          = elim.get("pct_eliminated")
    by_reason = elim.get("by_reason", {})
    for reason, n in by_reason.items():
        row[f"elim_{reason}"] = n
    return pd.DataFrame([row])


def build_bottleneck_heatmap_long(bn):
    """Transition × product × metric (long format — ideal for ThoughtSpot)."""
    rows = []
    for row in bn["heatmap"]:
        transition = row["transition"]
        # overall row
        rows.append({
            "transition":     transition,
            "product":        "Overall",
            "median_days":    row.get("overall_median"),
            "p25_days":       row.get("overall_p25"),
            "p75_days":       row.get("overall_p75"),
            "std_days":       row.get("overall_std"),
            "benchmark_median": row.get("benchmark_overall"),
            "benchmark_fast": row.get("benchmark_fast"),
            "benchmark_slow": row.get("benchmark_slow"),
            "vs_benchmark":   None,
        })
        for product in bn["products"]:
            rows.append({
                "transition":       transition,
                "product":          product,
                "median_days":      row.get(product),
                "p25_days":         row.get(f"{product}_p25"),
                "p75_days":         row.get(f"{product}_p75"),
                "std_days":         None,
                "benchmark_median": row.get(f"{product}_benchmark"),
                "benchmark_fast":   None,
                "benchmark_slow":   None,
                "vs_benchmark":     row.get(f"{product}_vs_benchmark"),
            })
    return pd.DataFrame(rows)


def build_stage_conversion_long(bn):
    rows = []
    for r in bn["conversion_rates"]:
        rows.append({"product": "Overall", **r})
    for product, items in (bn.get("conversion_by_product") or {}).items():
        for r in items:
            rows.append({"product": product, **r})
    return pd.DataFrame(rows)


def build_current_bottlenecks_long(bn):
    rows = []
    for r in bn["current_bottlenecks"]:
        rows.append({"product": "Overall", **r})
    for product, items in (bn.get("current_bottlenecks_by_product") or {}).items():
        for r in items:
            rows.append({"product": product, **r})
    return pd.DataFrame(rows)


def build_velocity_distribution_long(vm):
    rows = []
    for r in vm["distribution"]:
        rows.append({"product": "Overall", **r})
    for product, items in (vm.get("distribution_by_product") or {}).items():
        for r in items:
            rows.append({"product": product, **r})
    return pd.DataFrame(rows)


def build_cycle_times_by_product(ct):
    rows = []
    # Overall row
    overall = {k: v for k, v in ct["overall"].items() if k != "values"}
    overall["product"] = "Overall"
    overall["sla_threshold_days"] = ct["sla_threshold_days"]
    rows.append(overall)
    for product, dist in ct.get("by_product", {}).items():
        r = {k: v for k, v in dist.items() if k != "values"}
        r["product"] = product
        r["sla_threshold_days"] = ct["sla_threshold_days"]
        rows.append(r)
    df = pd.DataFrame(rows)
    cols = ["product", "count", "median", "mean", "std", "p10", "p25", "p75",
            "p90", "above_sla", "above_sla_pct", "sla_threshold_days"]
    return df[[c for c in cols if c in df.columns]]


def build_cycle_times_raw(ct, df_raw):
    """One row per funded loan with product + cycle_days. Useful for ThoughtSpot
    histograms/box plots."""
    funded = df_raw[df_raw["Outcome"] == "Funded"].copy()
    app_date = funded["Respa App D"].fillna(funded["Loan Open Date"])
    funded["cycle_days"] = (funded["Funded D"] - app_date).dt.days
    out = funded[funded["cycle_days"].notna() & (funded["cycle_days"] >= 0)].copy()
    keep = ["LoanGuid", "Product Type", "Branch Channel", "Loan Purpose",
            "LoanAmount", "Funded D", "cycle_days"]
    out = out[[c for c in keep if c in out.columns]]
    if "Funded D" in out.columns:
        out["Funded D"] = pd.to_datetime(out["Funded D"]).dt.strftime("%Y-%m-%d")
    return out


def build_what_if_csv(wi):
    scenarios = wi["scenarios"]
    rows = []
    for s in scenarios:
        row = {k: v for k, v in s.items() if not isinstance(v, (list, dict))}
        row["caveats"] = " | ".join(s.get("caveats") or [])
        rows.append(row)
    df = pd.DataFrame(rows)
    # Totals as extra header columns on every row (convenient for ThoughtSpot)
    for k in ("current_projected", "total_potential_delta",
              "adjusted_potential_delta", "overlap_discount",
              "total_upside_pct", "adjusted_upside_pct",
              "live_loans_count", "live_pipeline_value"):
        df[f"_totals_{k}"] = wi.get(k)
    return df


def build_scorecards_csv(ps):
    """Per-product + per-channel scorecards. Product rows carry rank + tier
    from the rankings; channel rows leave those null."""
    rank_by_name = {r["name"]: (r["rank"], r["tier"])
                    for r in ps.get("rankings", [])}
    rows = []
    for dim_key in ("products", "channels"):
        for card in ps.get(dim_key, []):
            row = {k: v for k, v in card.items() if not isinstance(v, dict)}
            sub = card.get("composite_sub_scores") or {}
            for sk, sv in sub.items():
                row[f"sub_{sk}"] = sv
            rnk, tier = rank_by_name.get(card.get("name"), (None, None))
            row["rank"] = rnk
            row["tier"] = tier
            rows.append(row)
    return pd.DataFrame(rows)


def build_industry_benchmarks_csv():
    """Stage transitions with per-product benchmarks (for Pipeline Health)."""
    rows = []
    for transition, prods in config.INDUSTRY_BENCHMARKS["transition_days"].items():
        for prod, band in prods.items():
            rows.append({
                "transition": transition,
                "product":    prod,
                "benchmark_fast":   band.get("fast"),
                "benchmark_median": band.get("median"),
                "benchmark_slow":   band.get("slow"),
                "source":     config.INDUSTRY_BENCHMARKS["source_display"],
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────── main ───────────────────────────────────

README = """# FlexPoint ThoughtSpot Export

Generated by `src/export_for_thoughtspot.py`. Every file here covers one grain
of the FlexPoint v3 dashboard so the Gallus SQL team can reproduce any tab's
visuals via worksheets / liveboards in ThoughtSpot.

> **Start here:** `data_dictionary.pdf` — plain-English, column-by-column
> reference for every CSV, including ideal visualisations and how to use each
> column. This README is the quick index; the PDF is the full handbook.

**Snapshot:** `{snapshot_date}` (mid-month reconstruction — same logic the
dashboard uses).

---

## Primary per-loan table (join key for most visuals)

| File | Grain | Dashboard visuals it powers |
|---|---|---|
| `loans.csv` | one row per active pipeline loan at `snapshot_date` | Overview KPI tiles, Stage Funnel, Watch List, Revenue at Risk table, Moneyball scatter, Velocity/Momentum, any product/channel breakdown, any risk filter |

`loans.csv` carries raw pipeline fields, all 31 v3 engineered features
(prefixed `f_`), `ml_probability`, `expected_value`, elimination status and
reason, counterfactual action + probability delta + dollar uplift, moneyball
difficulty + quadrant + movability, and a velocity band. Join this on
`LoanGuid` to pipeline tables and you can rebuild most dashboard visuals with
SQL alone.

**Ranked-subset views are served as filters on this table** — no separate CSVs:
- Watch List: `WHERE is_at_risk = TRUE`
- Top recovery opportunities: `WHERE recovery_rank IS NOT NULL ORDER BY recovery_rank` (top 12 loans by recovery gap)
- Momentum alerts: `WHERE momentum_rank IS NOT NULL ORDER BY momentum_rank` (top 15 slow high-value loans)

---

## Already funded (this month)

| File | Grain | Visuals |
|---|---|---|
| `already_funded.csv` | one row per loan funded between month-start and snapshot | Overview "Already Funded" bucket |

## Snapshot KPIs

| File | Grain | Visuals |
|---|---|---|
| `summary_kpis.csv` | single-row snapshot totals | Overview KPI tiles, projected total |

## Aggregates for charts

| File | Grain | Visuals |
|---|---|---|
| `stage_funnel.csv` | one row per pipeline stage | Overview funnel |
| `channel_split.csv` | Wholesale / Retail rows | Overview channel split donut |
| `product_breakdown.csv` | one row per Product Type | Overview product bars |
| `pull_through_monthly.csv` | month × product | Trends — pull-through line chart |
| `cycle_times_by_product.csv` | one row per product with p10/p25/median/p75/p90 | Trends — cycle time percentiles |
| `cycle_times_per_loan.csv` | one row per funded loan | Trends — cycle time histogram / box plot |
| `backtest_monthly.csv` | per-month backtest (ML, rolling, day-15) | Overview model-accuracy strip |
| `revenue_at_risk_buckets.csv` | 5 bucket rows | Revenue at Risk — bucket cards |
| `moneyball_quadrant_summary.csv` | 4 quadrants with counts + totals | Revenue at Risk — Moneyball quadrant headers |
| `bottleneck_heatmap.csv` | transition × product (long) | Pipeline Health — transition heatmap with IQR + industry deltas |
| `stage_conversion_rates.csv` | stage × product (long, incl. `Overall`) | Pipeline Health — conversion funnel |
| `current_bottlenecks.csv` | current stage × product (long, incl. `Overall`) | Pipeline Health — bottleneck pileup |
| `velocity_distribution.csv` | band × product (long, incl. `Overall`) | Velocity bars |
| `velocity_by_stage.csv` | one row per stage | Velocity — per-stage velocity |
| `what_if_scenarios.csv` | one row per lever + embedded overlap-adjusted totals | What-If tab — 4 scenario cards + red-team footer |
| `scorecards.csv` | per-product + per-channel composite rows, with `rank` + `tier` on product rows | Scorecards — comparative table + ranking strip |
| `optimization_recommendations.csv` | priority-sorted actions | Overview — "What to do this week" |
| `industry_benchmarks_transitions.csv` | reference table | Pipeline Health — industry column |
| `feature_importance.csv` | one row per model feature | Model-accuracy tooltip |

---

## How ThoughtSpot side should treat this

1. Load `loans.csv` as the primary fact table; it is the only per-loan asset
   and carries a `snapshot_date` column so historical snapshots can be
   appended (one row per loan per snapshot) without schema churn.
2. Load each aggregate CSV as its own worksheet. They're pre-computed at the
   grain each visual needs so SQL on the ThoughtSpot side stays simple.
3. Long-format CSVs (`bottleneck_heatmap`, `stage_conversion_rates`,
   `current_bottlenecks`, `velocity_distribution`) include an `Overall`
   pseudo-product row so a single worksheet powers both the overall view and
   the product filter on the Pipeline Health tab.
4. Nested list fields (risk_reasons, caveats) are flattened to `|`-separated
   text columns.
5. All date fields are ISO (`YYYY-MM-DD`) strings.

## Regenerating

```bash
python src/export_for_thoughtspot.py
```

Rerun any time the dashboard data changes, or point it at a different
`SNAPSHOT_DATE` by editing that constant in `src/generate_dashboard_data.py`.
"""


def main():
    print("=" * 70)
    print("ThoughtSpot export — v3 model")
    print("=" * 70)

    _ensure_dir(OUT_DIR)

    as_of = pd.Timestamp(SNAPSHOT_DATE)
    month_start = as_of.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)

    print("\nLoading data + training model (same setup as dashboard generator)...")
    df = load_and_clean()
    tables = build_transition_tables(df)
    training = build_training_set(df, tables)
    encoded, encoders = encode_categoricals(training, fit=True)
    encoded, medians = fill_missing_numeric(encoded, fit=True)
    feature_cols = get_feature_columns(encoders)
    bundle = train_and_select(encoded, feature_cols)
    model = bundle["best_model"]
    model_name = bundle["best_model_name"]
    print(f"  Best model: {model_name}")

    # ── Core per-loan pipeline state + ML + elimination ─────────────────────
    print("\nReconstructing snapshot + scoring...")
    loan_table_rows, active, already_funded, fstats, feats = gdd.build_loan_table(
        df, tables, model, feature_cols, encoders, medians,
    )

    # ── Build every section (dicts / lists) ────────────────────────────────
    print("\nBuilding dashboard sections...")
    pull_through        = gdd.build_pull_through(df)
    cycle_times         = gdd.build_cycle_times(df)
    summary             = gdd.build_summary(active, already_funded, fstats, df,
                                            cycle_median=cycle_times["overall"]["median"],
                                            model_name=model_name)
    backtest_accuracy   = gdd.build_backtest_accuracy()
    stage_funnel        = gdd.build_stage_funnel(active)
    channel_split       = gdd.build_channel_split(active)
    product_breakdown   = gdd.build_product_breakdown(active)
    at_risk_loans       = gdd.build_at_risk_loans(
        active, feats, as_of, month_end, tables,
        model, feature_cols, encoders, medians,
    )
    revenue_at_risk     = gdd.build_revenue_at_risk(
        active, feats, as_of, month_end, tables,
        model, feature_cols, encoders, medians,
    )
    bottleneck_detection = gdd.build_bottleneck_detection(df, active, feats)
    velocity_momentum   = gdd.build_velocity_momentum(active, feats)
    what_if_scenarios   = gdd.build_what_if_scenarios(df, active, feats)
    performance_scorecards = gdd.build_performance_scorecards(df, active, feats)
    optimization_recs   = gdd.build_optimization_recommendations(active, feats, df)
    moneyball_matrix    = gdd.build_moneyball_matrix(active, feats,
                                                     at_risk_loans=at_risk_loans)

    # ── Write CSVs ──────────────────────────────────────────────────────────
    print("\nWriting CSV bundle → outputs/thoughtspot_export/")

    # 1. Master per-loan table (folds in at-risk flag, recovery rank + gap,
    #    and momentum rank so the 3 watchlist-subset CSVs aren't needed).
    loans_df = build_loans_csv(
        active, feats, at_risk_loans, moneyball_matrix,
        top_recovery=revenue_at_risk["top_recovery"],
        momentum_alerts=velocity_momentum["momentum_alerts"],
    )
    _write(loans_df, "loans.csv")

    # 2. Already funded this month
    af = already_funded.copy()
    af["snapshot_date"] = SNAPSHOT_DATE
    keep = ["snapshot_date", "LoanGuid", "Product Type", "Branch Channel",
            "Loan Purpose", "LoanAmount", "Funded D"]
    af_out = af[[c for c in keep if c in af.columns]].copy()
    if "Funded D" in af_out.columns and pd.api.types.is_datetime64_any_dtype(af_out["Funded D"]):
        af_out["Funded D"] = af_out["Funded D"].dt.strftime("%Y-%m-%d")
    _write(af_out, "already_funded.csv")

    # 3. Summary KPIs
    _write(build_summary_csv(summary), "summary_kpis.csv")

    # 4. Stage funnel
    _write(pd.DataFrame(stage_funnel).assign(snapshot_date=SNAPSHOT_DATE),
           "stage_funnel.csv")

    # 5. Channel split
    _write(pd.DataFrame(channel_split).assign(snapshot_date=SNAPSHOT_DATE),
           "channel_split.csv")

    # 6. Product breakdown
    _write(pd.DataFrame(product_breakdown).assign(snapshot_date=SNAPSHOT_DATE),
           "product_breakdown.csv")

    # 7. Pull-through monthly
    _write(pd.DataFrame(pull_through), "pull_through_monthly.csv")

    # 8. Cycle times — percentile summary per product
    _write(build_cycle_times_by_product(cycle_times), "cycle_times_by_product.csv")

    # 9. Cycle times — one row per funded loan
    _write(build_cycle_times_raw(cycle_times, df), "cycle_times_per_loan.csv")

    # 10. Backtest monthly
    try:
        bt = pd.read_csv(config.OUTPUTS_PATH / "results" / "backtest_results_v3.csv")
        ml_rolling = bt[(bt["method"] == "ML") & (bt["training_mode"] == "rolling")
                        & (bt["snapshot_day"] == 15)].copy()
        ml_rolling["month"] = (ml_rolling["year"].astype(int).astype(str)
                               + "-"
                               + ml_rolling["month"].astype(int).astype(str).str.zfill(2))
        _write(ml_rolling, "backtest_monthly.csv")
    except FileNotFoundError:
        print("  (backtest_results_v3.csv not found — skipping backtest_monthly.csv)")

    # 11. Revenue at risk — buckets
    rar_df = pd.DataFrame(revenue_at_risk["buckets"])
    rar_df["snapshot_date"]            = SNAPSHOT_DATE
    rar_df["_total_at_risk"]           = revenue_at_risk["total_at_risk"]
    rar_df["_total_recovery_potential"]= revenue_at_risk["total_recovery_potential"]
    rar_df["_live_pipeline_value"]     = revenue_at_risk["live_pipeline_value"]
    _write(rar_df, "revenue_at_risk_buckets.csv")

    # (Watch-list, top-recovery, and momentum-alert views are now served by
    # filtering loans.csv on `is_at_risk`, `recovery_rank`, and
    # `momentum_rank` — no separate CSVs needed.)

    # 14. Moneyball quadrant summary
    qs = moneyball_matrix["quadrant_summary"]
    qs_rows = [{"quadrant": q, **stats} for q, stats in qs.items()]
    qs_df = pd.DataFrame(qs_rows)
    qs_df["snapshot_date"] = SNAPSHOT_DATE
    qs_df["movable_count"] = moneyball_matrix["movable_count"]
    qs_df["total_loans"]   = moneyball_matrix["total_loans"]
    _write(qs_df, "moneyball_quadrant_summary.csv")

    # 15. Bottleneck heatmap (long format)
    _write(build_bottleneck_heatmap_long(bottleneck_detection),
           "bottleneck_heatmap.csv")

    # 16. Stage conversion rates (long, overall + per product)
    _write(build_stage_conversion_long(bottleneck_detection),
           "stage_conversion_rates.csv")

    # 17. Current bottlenecks (long)
    cb_df = build_current_bottlenecks_long(bottleneck_detection)
    cb_df["snapshot_date"] = SNAPSHOT_DATE
    _write(cb_df, "current_bottlenecks.csv")

    # 18. Velocity distribution (long)
    vd_df = build_velocity_distribution_long(velocity_momentum)
    vd_df["snapshot_date"] = SNAPSHOT_DATE
    _write(vd_df, "velocity_distribution.csv")

    # 19. Velocity by stage
    vs_df = pd.DataFrame(velocity_momentum["stage_velocity"])
    vs_df["snapshot_date"] = SNAPSHOT_DATE
    _write(vs_df, "velocity_by_stage.csv")

    # (Momentum alerts now live in loans.csv via momentum_rank — filter
    # WHERE momentum_rank IS NOT NULL ORDER BY momentum_rank.)

    # 20. What-if scenarios
    _write(build_what_if_csv(what_if_scenarios), "what_if_scenarios.csv")

    # 21. Scorecards (now includes rank + tier, replacing a separate rankings file)
    _write(build_scorecards_csv(performance_scorecards), "scorecards.csv")

    # 24. Optimization recommendations
    opt_rows = []
    total_impact = optimization_recs.get("total_estimated_impact", 0)
    for r in optimization_recs["recommendations"]:
        row = {k: v for k, v in r.items()}
        row["snapshot_date"] = SNAPSHOT_DATE
        row["_total_estimated_impact_all"] = total_impact
        opt_rows.append(row)
    _write(pd.DataFrame(opt_rows), "optimization_recommendations.csv")

    # 25. Industry benchmarks reference
    _write(build_industry_benchmarks_csv(), "industry_benchmarks_transitions.csv")

    # 26. Feature importance (copy of v3 results)
    fi_src = config.OUTPUTS_PATH / "results" / "feature_importance_v3.csv"
    if fi_src.exists():
        shutil.copyfile(fi_src, OUT_DIR / "feature_importance.csv")
        print(f"  → feature_importance.csv                         (copied)")

    # 27. README
    (OUT_DIR / "README.md").write_text(README.format(snapshot_date=SNAPSHOT_DATE))
    print(f"  → README.md                                     (written)")

    print("\n" + "=" * 70)
    print(f"Done. {len(list(OUT_DIR.glob('*')))} files in {OUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
