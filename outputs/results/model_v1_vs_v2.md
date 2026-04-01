# FlexPoint v1 vs v2 Model Comparison

Generated: 2026-02-22 18:13

## v2 Model Metrics (Fixed, 2024 train / 2025 test)

| Model | Brier | AUC | LogLoss |
|---|---|---|---|
| GradientBoosting **BEST** | 0.039543 | 0.981239 | 0.126034 |
| RandomForest | 0.045981 | 0.976619 | 0.151662 |
| LogisticRegression | 0.057278 | 0.959397 | 0.183804 |

## v2 Feature Importance (Top 15)

| Rank | Feature | Importance |
|---|---|---|
| 1 | lock_expiry_vs_month_end | 0.684389 |
| 2 | days_at_stage | 0.071017 |
| 3 | stage_only_probability | 0.057039 |
| 4 | days_until_lock_expiry | 0.034514 |
| 5 | lock_period | 0.032957 |
| 6 | credit_score | 0.022797 |
| 7 | loan_amount | 0.019561 |
| 8 | note_rate | 0.014259 |
| 9 | cltv | 0.013336 |
| 10 | days_remaining | 0.012469 |
| 11 | days_since_lock | 0.010401 |
| 12 | stage_rank | 0.007778 |
| 13 | ltv | 0.006580 |
| 14 | is_locked | 0.003370 |
| 15 | loan_purpose_Purchase | 0.001862 |

## ML MAPE by Snapshot Day

| Day | v1 | v2 Fixed | v2 Rolling |
|---|---|---|---|
| 0 | n/a | 17.1% | 19.8% |
| 1 | 15.7% | 15.8% | 18.7% |
| 8 | 9.7% | 7.3% | 9.9% |
| 15 | 6.4% | 4.8% | 5.7% |
| 22 | 5.3% | 4.0% | 4.6% |

## Nov/Dec 2025 Day-15 ML Error

| Month | v1 | v2 Fixed | v2 Rolling |
|---|---|---|---|
| 2025-11 | +28.1% | +18.1% | +12.7% |
| 2025-12 | +15.5% | +8.0% | +6.0% |
