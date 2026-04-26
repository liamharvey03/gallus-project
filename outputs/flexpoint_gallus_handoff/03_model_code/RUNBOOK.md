# FlexPoint Model — Runbook

How to regenerate the CSV export on a fresh pull of FlexPoint loan data.

You only need this if you want to refresh the CSVs yourself. The
bundle already includes a complete snapshot (see `../02_csv_exports/`)
that matches the HTML dashboard.

---

## 1. Install

Python 3.10+ recommended.

```bash
cd 03_model_code
pip install -r requirements.txt
pip install fpdf2          # only needed if you want to rebuild the PDF
```

Dependencies are standard: pandas, numpy, scikit-learn, xgboost, lightgbm,
lifelines, matplotlib, seaborn, scipy.

## 2. Point it at a dataset

The model expects `data/sectG.csv` *inside this folder* (relative to
`config.py`). The bundled copy is already there — same file as the
top-level `04_source_dataset/sectG.csv`, mirrored here so the code finds
it without configuration.

The column contract is defined in `config.py`:

- `DATE_COLUMNS` — 40+ milestone/event dates that get parsed as datetime.
- `STAGE_MAP` — the 13 pipeline stages and their ordering.
- `FUNDED_STATUSES` / `FAILED_STATUSES` — terminal loan states.
- `INDUSTRY_BENCHMARKS` — ICE Mortgage Technology 2024 benchmarks.

To run on a fresh extract, drop the new file in as `data/sectG.csv`
(overwriting the bundled one) — as long as the columns match, the
pipeline runs as-is.

## 3. Run the export

From inside this folder (`03_model_code/`):

```bash
python src/export_for_thoughtspot.py
```

This runs the full v3 pipeline end-to-end:

1. `data_prep` — loads and cleans sectG.csv.
2. `pipeline_snapshot` — reconstructs pipeline state at the snapshot date
   (default: 2025-12-15 — change `SNAPSHOT_DATE` in
   `src/generate_dashboard_data.py`).
3. `feature_engineering_v3` — builds 31 `f_*` features.
4. `models.train_and_select` — trains GradientBoosting, selects best by
   Brier score.
5. `elimination_filter` — flags dead loans (5 conservative rules).
6. `scorer` — scores each live loan + runs counterfactuals.
7. Writes 22 CSVs + README.md to `outputs/thoughtspot_export/`
   (inside `03_model_code/`). To refresh the handoff bundle, copy these
   over `../02_csv_exports/`.

Expected runtime: 2–4 minutes on a laptop.

## 4. Regenerate the PDF (optional)

```bash
python src/build_handoff_pdf.py
```

Writes `outputs/flexpoint_gallus_handoff/02_csv_exports/data_dictionary.pdf`.

## 5. Key files to know

| File | What it does |
|---|---|
| `config.py` | Single source of truth for column names, stage ordering, benchmarks. |
| `src/export_for_thoughtspot.py` | Top-level entry point. Orchestrates everything and writes CSVs. |
| `src/pipeline_snapshot.py` | Reconstructs "what's in the pipeline on date T." |
| `src/feature_engineering_v3.py` | The 31 `f_*` features — this is the feature contract the ML model sees. |
| `src/scorer.py` | Scores loans and computes counterfactual recommendations. |
| `src/generate_dashboard_data.py` | Legacy orchestrator that built the HTML dashboard's 16 data sections — useful if you want to cross-check numbers against the HTML. |

## 6. Changing the snapshot date

Open `src/generate_dashboard_data.py` and edit:

```python
SNAPSHOT_DATE = pd.Timestamp("2025-12-15")
```

(`export_for_thoughtspot.py` imports this constant.)

Pick any date where you want the pipeline reconstructed. The CSVs will
be written with that date stamped in the `snapshot_date` column of
loans.csv so you can append multiple runs without overwriting history.

## 7. If something breaks

Most failures come from column name mismatches in a new extract. Check:

1. All columns in `config.DATE_COLUMNS` exist and parse as dates.
2. `Loan Status` values use the spellings in `config.FUNDED_STATUSES`
   and `config.FAILED_STATUSES`.
3. `Product Type` values are in `config.PRODUCT_GROUPS` (add any new
   ones if needed).

Questions: ajersher61@gmail.com.
