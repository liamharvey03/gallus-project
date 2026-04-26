# FlexPoint Pipeline Intelligence — Handoff for Gallus Insights

This bundle contains everything the Gallus team needs to reproduce the
FlexPoint dashboard inside ThoughtSpot: the visual target, the CSV data
that feeds it, the model code that produced the CSVs, and the raw loan
extract used as input.

**Snapshot date:** 2025-12-15  
**Model:** GradientBoosting v3 (5.8% MAPE across 24-month backtest)

---

## What's in here

```
flexpoint_gallus_handoff/
├── 00_README.md                    ← you are here
├── 01_dashboard_reference.html     ← open in any browser — visual target
├── 02_csv_exports/                 ← 22 CSVs + PDF data dictionary
├── 03_model_code/                  ← full Python pipeline + runbook
└── 04_source_dataset/              ← sectG.csv (the input data)
```

## Recommended reading order

1. **Open `01_dashboard_reference.html`** in any browser. This is the
   target — what the dashboard should look like once rebuilt in
   ThoughtSpot. It's fully self-contained (all data inline). It does
   pull React / Recharts from public CDNs, so you need internet.

2. **Skim `02_csv_exports/data_dictionary.pdf`** (11 pages). For each
   CSV it tells you: what's in it, which dashboard chart it feeds, and
   a one-line recipe for recreating that chart in ThoughtSpot.

3. **Open `02_csv_exports/` CSVs** and start wiring them up. Start
   with `loans.csv` — it's the master fact table. Every other CSV
   aggregates it or joins to it on `LoanGuid`.

4. **Only if you want to regenerate on fresh data:** read
   `03_model_code/RUNBOOK.md`. The bundled CSVs already match the HTML,
   so you don't need to run anything to reproduce the dashboard.

## The three most important files

| File | Why |
|---|---|
| `01_dashboard_reference.html` | Shows you exactly what each chart looks like. |
| `02_csv_exports/loans.csv` | Master per-loan fact table (1,109 loans × 213 columns). Everything else joins to this. |
| `02_csv_exports/data_dictionary.pdf` | Maps each CSV to a dashboard visual and gives you a ThoughtSpot recipe. |

## Naming conventions

Same concept = same column name across every CSV:

- **`Branch Channel`**, **`Product Type`**, **`LoanAmount`**, **`LoanGuid`** keep the raw sectG spelling (preserved spaces and casing) so they join cleanly back to `loans.csv`.
- Counts → **`loan_count`** (never `count` or `total_loans`).
- Probabilities → **`avg_probability`** or **`ml_probability`** (never `avg_prob`).
- $ totals → **`total_value`** (overall) or **`expected_value`** (probability-weighted).
- Time-series CSVs include **`snapshot_date`** so multiple runs can be appended without overwriting history.

## Quick numbers to sanity-check against

When you wire up the Overview tab, you should see these (they're in the
CSVs and rendered on the HTML):

- **1,109** active pipeline loans (708 live + 401 dead)
- **~$100M** December 2025 total: $68M already funded + $32.4M projected
- **59** at-risk loans flagged on the Watch List
- **253** loans in the Moneyball matrix (filter: is_at_risk ∨ moneyball_flag)
- **$145M** total revenue at risk (sum across risk buckets)

If your ThoughtSpot numbers don't match these, something is being
aggregated wrong — the CSVs are the source of truth.

## Questions

Reach out to Ajer at ajersher61@gmail.com. Happy to jump on a call if
anything is unclear about the data model, the counterfactual
recommendations, or the feature engineering.
