# Forecasting DB Schema Profile

_Generated: 2026-05-05T22:21:02_

**Database:** `Forecasting`  
**Tables:** 22

## Tables

| table | rows | cols |
| --- | --- | --- |
| `already_funded` | 156 | 7 |
| `backtest_monthly` | 24 | 11 |
| `bottleneck_heatmap` | 24 | 10 |
| `channel_split` | 2 | 8 |
| `current_bottlenecks` | 38 | 12 |
| `cycle_times_by_product` | 10 | 12 |
| `cycle_times_per_loan` | 5,660 | 7 |
| `feature_importance` | 52 | 2 |
| `industry_benchmarks_transitions` | 24 | 6 |
| `loans` | 1,109 | 213 |
| `moneyball_quadrant_summary` | 4 | 8 |
| `optimization_recommendations` | 6 | 11 |
| `product_breakdown` | 10 | 8 |
| `pull_through_monthly` | 206 | 5 |
| `revenue_at_risk_buckets` | 5 | 13 |
| `scorecards` | 12 | 27 |
| `stage_conversion_rates` | 42 | 5 |
| `stage_funnel` | 12 | 8 |
| `summary_kpis` | 1 | 22 |
| `velocity_by_stage` | 6 | 10 |
| `velocity_distribution` | 32 | 7 |
| `what_if_scenarios` | 4 | 25 |

## Naming convention audit (`loans`)

_CLAUDE.md handoff names are checked against the actual `loans` schema. The last three expected names are aggregate-only conventions and aren't expected to appear in `loans` itself — they should land in the aggregate tables._

| expected | actual | status |
| --- | --- | --- |
| `Branch Channel` | `Branch Channel` | OK |
| `Product Type` | `Product Type` | OK |
| `LoanAmount` | `LoanAmount` | OK |
| `LoanGuid` | `LoanGuid` | OK |
| `loan_count` | _(not found)_ | MISSING _(aggregate-only convention)_ |
| `avg_probability` | _(not found)_ | MISSING _(aggregate-only convention)_ |
| `total_expected_value` | _(not found)_ | MISSING _(aggregate-only convention)_ |

### Aggregate-name presence across all tables

| expected | found_in | status |
| --- | --- | --- |
| `total_expected_value` | moneyball_quadrant_summary | OK |
| `avg_probability` | channel_split, current_bottlenecks, moneyball_quadrant_summary, product_breakdown, revenue_at_risk_buckets, stage_funnel, velocity_by_stage, velocity_distribution | OK |
| `loan_count` | channel_split, current_bottlenecks, cycle_times_by_product, moneyball_quadrant_summary, optimization_recommendations, product_breakdown, revenue_at_risk_buckets, stage_funnel, velocity_by_stage, velocity_distribution | OK |

## Suspected type-coercion failures

_String-typed columns whose names suggest numeric or date values. These are likely CSV-load casualties that will need explicit casting before use._

| schema | table | column | type | max_len | looks_like |
| --- | --- | --- | --- | --- | --- |
| dbo | `loans` | `counterfactual_probability` | nvarchar | 255 | numeric |
| dbo | `loans` | `probability_delta` | nvarchar | 255 | numeric |
| dbo | `loans` | `expected_value_uplift` | nvarchar | 255 | numeric |
| dbo | `loans` | `f_credit_score` | nvarchar | 255 | numeric |
| dbo | `loans` | `f_days_past_lock_expiry` | nvarchar | 255 | numeric |
| dbo | `loans` | `f_days_since_lock` | nvarchar | 255 | numeric |
| dbo | `loans` | `f_days_until_lock_expiry` | nvarchar | 255 | numeric |
| dbo | `loans` | `DecisionCreditScore` | nvarchar | 255 | numeric |
| dbo | `loans` | `Borrower Experian Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Borrower TransUnion Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Borrower Equifax Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Coborrower Experian Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Coborrower TransUnion Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Coborrower Equifax Score` | nvarchar | 255 | numeric |
| dbo | `loans` | `Credit Score Type 1` | nvarchar | 255 | numeric |
| dbo | `loans` | `Credit Score Type 2` | nvarchar | 255 | numeric |
| dbo | `loans` | `Purchase Price` | nvarchar | 255 | numeric |
| dbo | `loans` | `Appraised Value` | nvarchar | 255 | numeric |
| dbo | `loans` | `PurchasePrice` | nvarchar | 255 | numeric |
| dbo | `loans` | `AppraisedValue` | nvarchar | 255 | numeric |
| dbo | `loans` | `Rate Lock Status` | nvarchar | 255 | numeric |
| dbo | `loans` | `ARM - Rate Margin` | nvarchar | 255 | numeric |
| dbo | `loans` | `Property County` | nvarchar | 255 | numeric |
| dbo | `loans` | `Internal Assigned Lender Account Executive Name` | nvarchar | 255 | numeric |
| dbo | `loans` | `Commission - Rebate Fee Percentage of Loan Amount` | nvarchar | 255 | numeric |
| dbo | `loans` | `Commission - Rebate Fee Total` | nvarchar | 255 | numeric |
| dbo | `loans` | `Approved Fee (YSP)` | nvarchar | 255 | numeric |
| dbo | `loans` | `GFE - Loan discount (total)` | nvarchar | 255 | numeric |
| dbo | `loans` | `GFE - Appraisal fee` | nvarchar | 255 | numeric |
| dbo | `loans` | `GFE - Credit report fee` | nvarchar | 255 | numeric |
| dbo | `loans` | `GFE - Underwriting fee` | nvarchar | 255 | numeric |
| dbo | `loans` | `Pre-qual Date` | nvarchar | 255 | date |
| dbo | `loans` | `Pre-approved Date` | nvarchar | 255 | date |
| dbo | `loans` | `Registration` | nvarchar | 255 | numeric |
| dbo | `loans` | `RegistrationD` | nvarchar | 255 | date,numeric |
| dbo | `loans` | `Respa App D` | nvarchar | 255 | date |
| dbo | `loans` | `HMDA App D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Submitted D` | nvarchar | 255 | date |
| dbo | `loans` | `DocumentCheckD` | nvarchar | 255 | date |
| dbo | `loans` | `PreProcessingD` | nvarchar | 255 | date |
| dbo | `loans` | `ProcessingD` | nvarchar | 255 | date |
| dbo | `loans` | `Submitted D` | nvarchar | 255 | date |
| dbo | `loans` | `Underwriting D` | nvarchar | 255 | date |
| dbo | `loans` | `ConditionReviewD` | nvarchar | 255 | date |
| dbo | `loans` | `FinalUnderwritingD` | nvarchar | 255 | date |
| dbo | `loans` | `Approved D` | nvarchar | 255 | date |
| dbo | `loans` | `Clear To Close D` | nvarchar | 255 | date |
| dbo | `loans` | `Docs D` | nvarchar | 255 | date |
| dbo | `loans` | `DocsOrderedD` | nvarchar | 255 | date |
| dbo | `loans` | `DocsDrawnD` | nvarchar | 255 | date |
| dbo | `loans` | `DocsBackD` | nvarchar | 255 | date |
| dbo | `loans` | `FundingConditionsD` | nvarchar | 255 | date |
| dbo | `loans` | `Scheduled Funding D` | nvarchar | 255 | date |
| dbo | `loans` | `Funded D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Closed D` | nvarchar | 255 | date |
| dbo | `loans` | `Recorded D` | nvarchar | 255 | date |
| dbo | `loans` | `Purchase D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Shipped D` | nvarchar | 255 | date |
| dbo | `loans` | `Rate Lock D` | nvarchar | 255 | date,numeric |
| dbo | `loans` | `Rate Lock Expiration D` | nvarchar | 255 | date,numeric |
| dbo | `loans` | `Loan OnHold D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Canceled D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Denied D` | nvarchar | 255 | date |
| dbo | `loans` | `Loan Suspended D` | nvarchar | 255 | date |
| dbo | `loans` | `Withdrawn D` | nvarchar | 255 | date |
| dbo | `loans` | `DaysOpenToSubmitted` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysSubmittedToApproved` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysApprovedToCTC` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysCTCToFunded` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysTotalSubmitToFund` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysTotalOpenToFund` | nvarchar | 255 | numeric |
| dbo | `loans` | `LockDurationDays` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysSubmittedToUW` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysUWToApproved` | nvarchar | 255 | numeric |
| dbo | `loans` | `DaysDocsToFunded` | nvarchar | 255 | numeric |
| dbo | `loans` | `TIL Disclosure / GFE Ordered Date` | nvarchar | 255 | date |
| dbo | `loans` | `TIL Disclosure / GFE Due Date` | nvarchar | 255 | date |
| dbo | `loans` | `TIL Disclosure / GFE Received Date` | nvarchar | 255 | date |

---

## `dbo.already_funded`

**Rows:** 156  |  **Columns:** 7

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `snapshot_date` | datetime |  | YES |
| 2 | `LoanGuid` | float |  | YES |
| 3 | `Product Type` | nvarchar | 255 | YES |
| 4 | `Branch Channel` | nvarchar | 255 | YES |
| 5 | `Loan Purpose` | nvarchar | 255 | YES |
| 6 | `LoanAmount` | float |  | YES |
| 7 | `Funded D` | datetime |  | YES |

### Sample (TOP 3)

| snapshot_date | LoanGuid | Product Type | Branch Channel | Loan Purpose | LoanAmount | Funded D |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-12-15 00:00:00 | 82511403.0 | NONCONFORMING | Wholesale | Purchase |  | 2025-12-15 00:00:00 |
| 2025-12-15 00:00:00 | 82511385.0 | NONCONFORMING | Wholesale | Purchase |  | 2025-12-10 00:00:00 |
| 2025-12-15 00:00:00 | 82511393.0 | NONCONFORMING | Wholesale | Refinance CashOut |  | 2025-12-12 00:00:00 |

---

## `dbo.backtest_monthly`

**Rows:** 24  |  **Columns:** 11

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `year` | float |  | YES |
| 2 | `month` | nvarchar | 255 | YES |
| 3 | `snapshot_day` | float |  | YES |
| 4 | `method` | nvarchar | 255 | YES |
| 5 | `already_funded` | float |  | YES |
| 6 | `projected_pipeline` | nvarchar | 255 | YES |
| 7 | `projected` | nvarchar | 255 | YES |
| 8 | `actual` | float |  | YES |
| 9 | `error_pct` | float |  | YES |
| 10 | `direction` | nvarchar | 255 | YES |
| 11 | `training_mode` | nvarchar | 255 | YES |

### Sample (TOP 3)

| year | month | snapshot_day | method | already_funded | projected_pipeline | projected | actual | error_pct | direction | training_mode |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024.0 | 2024-01 | 15.0 | ML | 11983351.0 | 20963224.33878807 | 32946575.33878807 | 36630894.0 | -10.0579545266133 | under | rolling |
| 2024.0 | 2024-02 | 15.0 | ML | 20886738.0 | 25778356.445105243 | 46665094.44510524 | 57139314.0 | -18.3310208360127 | under | rolling |
| 2024.0 | 2024-03 | 15.0 | ML | 30650752.0 | 33485388.50184687 | 64136140.501846865 | 60458258.0 | 6.08334183536493 | over | rolling |

---

## `dbo.bottleneck_heatmap`

**Rows:** 24  |  **Columns:** 10

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `transition` | nvarchar | 255 | YES |
| 2 | `Product Type` | nvarchar | 255 | YES |
| 3 | `median_days` | float |  | YES |
| 4 | `p25_days` | float |  | YES |
| 5 | `p75_days` | float |  | YES |
| 6 | `std_days` | float |  | YES |
| 7 | `benchmark_median` | float |  | YES |
| 8 | `benchmark_fast` | float |  | YES |
| 9 | `benchmark_slow` | float |  | YES |
| 10 | `vs_benchmark` | float |  | YES |

### Sample (TOP 3)

| transition | Product Type | median_days | p25_days | p75_days | std_days | benchmark_median | benchmark_fast | benchmark_slow | vs_benchmark |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Open at  Submitted | Overall | 0.0 | 0.0 | 0.0 | 2.4 | 1.0 | 0.0 | 3.0 |  |
| Open at  Submitted | NONCONFORMING | 0.0 | 0.0 | 0.0 |  | 1.0 |  |  | -1.0 |
| Open at  Submitted | CONFORMING | 0.0 | 0.0 | 0.0 |  | 1.0 |  |  | -1.0 |

---

## `dbo.channel_split`

**Rows:** 2  |  **Columns:** 8

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Branch Channel` | nvarchar | 255 | YES |
| 2 | `loan_count` | float |  | YES |
| 3 | `total_value` | float |  | YES |
| 4 | `live_loans` | float |  | YES |
| 5 | `live_value` | float |  | YES |
| 6 | `projected_value` | float |  | YES |
| 7 | `avg_probability` | float |  | YES |
| 8 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| Branch Channel | loan_count | total_value | live_loans | live_value | projected_value | avg_probability | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Wholesale | 792.0 | 199881749.0 | 649.0 | 141177336.0 | 31773788.0 | 0.2971 | 2025-12-15 00:00:00 |
| Retail | 241.0 | 67517319.0 | 59.0 | 5809336.0 | 670551.0 | 0.0534 | 2025-12-15 00:00:00 |

---

## `dbo.current_bottlenecks`

**Rows:** 38  |  **Columns:** 12

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Product Type` | nvarchar | 255 | YES |
| 2 | `stage` | nvarchar | 255 | YES |
| 3 | `rank` | float |  | YES |
| 4 | `loan_count` | float |  | YES |
| 5 | `total_value` | float |  | YES |
| 6 | `avg_days_at_stage` | float |  | YES |
| 7 | `median_days_at_stage` | float |  | YES |
| 8 | `p25_days_at_stage` | float |  | YES |
| 9 | `p75_days_at_stage` | float |  | YES |
| 10 | `avg_probability` | float |  | YES |
| 11 | `pct_over_30d` | float |  | YES |
| 12 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| Product Type | stage | rank | loan_count | total_value | avg_days_at_stage | median_days_at_stage | p25_days_at_stage | p75_days_at_stage | avg_probability | pct_over_30d | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | Opened | 0.0 | 57.0 | 0.0 | 13.4 | 12.0 | 7.0 | 19.0 | 0.0022 | 0.0 | 2025-12-15 00:00:00 |
| Overall | Application | 1.0 | 28.0 | 0.0 | 5.7 | 4.0 | 0.0 | 6.0 | 0.0653 | 0.0 | 2025-12-15 00:00:00 |
| Overall | Submitted | 2.0 | 79.0 | 0.0 | 3.7 | 3.0 | 0.0 | 5.0 | 0.0819 | 0.0 | 2025-12-15 00:00:00 |

---

## `dbo.cycle_times_by_product`

**Rows:** 10  |  **Columns:** 12

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Product Type` | nvarchar | 255 | YES |
| 2 | `loan_count` | float |  | YES |
| 3 | `median` | float |  | YES |
| 4 | `mean` | float |  | YES |
| 5 | `std` | float |  | YES |
| 6 | `p10` | float |  | YES |
| 7 | `p25` | float |  | YES |
| 8 | `p75` | float |  | YES |
| 9 | `p90` | float |  | YES |
| 10 | `above_sla` | float |  | YES |
| 11 | `above_sla_pct` | float |  | YES |
| 12 | `sla_threshold_days` | float |  | YES |

### Sample (TOP 3)

| Product Type | loan_count | median | mean | std | p10 | p25 | p75 | p90 | above_sla | above_sla_pct | sla_threshold_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | 5660.0 | 29.0 | 33.1 | 18.4 | 17.0 | 22.0 | 38.0 | 52.0 | 868.0 | 15.3 | 45.0 |
| 2ND | 709.0 | 34.0 | 37.8 | 18.6 | 21.0 | 26.0 | 44.0 | 59.2 | 166.0 | 23.4 | 45.0 |
| CONFORMING | 639.0 | 28.0 | 33.1 | 21.9 | 17.0 | 21.0 | 36.0 | 51.0 | 95.0 | 14.9 | 45.0 |

---

## `dbo.cycle_times_per_loan`

**Rows:** 5,660  |  **Columns:** 7

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `LoanGuid` | float |  | YES |
| 2 | `Product Type` | nvarchar | 255 | YES |
| 3 | `Branch Channel` | nvarchar | 255 | YES |
| 4 | `Loan Purpose` | nvarchar | 255 | YES |
| 5 | `LoanAmount` | float |  | YES |
| 6 | `Funded D` | datetime |  | YES |
| 7 | `cycle_days` | float |  | YES |

### Sample (TOP 3)

| LoanGuid | Product Type | Branch Channel | Loan Purpose | LoanAmount | Funded D | cycle_days |
| --- | --- | --- | --- | --- | --- | --- |
| 92301060003.0 | NONCONFORMING | Wholesale | Refinance CashOut | 430500.0 | 2023-01-31 00:00:00 | 25.0 |
| 92301060004.0 | NONCONFORMING | Wholesale | Refinance CashOut | 658000.0 | 2023-01-31 00:00:00 | 25.0 |
| 32301030001.0 | FHA | Retail | Refinance CashOut | 490000.0 | 2023-01-30 00:00:00 | 27.0 |

---

## `dbo.feature_importance`

**Rows:** 52  |  **Columns:** 2

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `feature` | nvarchar | 255 | YES |
| 2 | `importance` | float |  | YES |

### Sample (TOP 3)

| feature | importance |
| --- | --- |
| lock_expiry_vs_month_end | 0.678298830651075 |
| days_at_stage | 0.0632375598982729 |
| stage_only_probability | 0.0499098761763443 |

---

## `dbo.industry_benchmarks_transitions`

**Rows:** 24  |  **Columns:** 6

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `transition` | nvarchar | 255 | YES |
| 2 | `Product Type` | nvarchar | 255 | YES |
| 3 | `benchmark_fast` | float |  | YES |
| 4 | `benchmark_median` | float |  | YES |
| 5 | `benchmark_slow` | float |  | YES |
| 6 | `source` | nvarchar | 255 | YES |

### Sample (TOP 3)

| transition | Product Type | benchmark_fast | benchmark_median | benchmark_slow | source |
| --- | --- | --- | --- | --- | --- |
| Open at  Submitted | overall | 0.0 | 1.0 | 3.0 | ICE Mortgage Technology 2024, Ellie Mae OIR, LendingTree |
| Open at  Submitted | NONCONFORMING | 0.0 | 1.0 | 3.0 | ICE Mortgage Technology 2024, Ellie Mae OIR, LendingTree |
| Open at  Submitted | CONFORMING | 0.0 | 1.0 | 2.0 | ICE Mortgage Technology 2024, Ellie Mae OIR, LendingTree |

---

## `dbo.loans`

**Rows:** 1,109  |  **Columns:** 213

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `snapshot_date` | datetime |  | YES |
| 2 | `LoanGuid` | nvarchar | 255 | YES |
| 3 | `Product Type` | nvarchar | 255 | YES |
| 4 | `Loan Purpose` | nvarchar | 255 | YES |
| 5 | `Branch Channel` | nvarchar | 255 | YES |
| 6 | `current_stage` | nvarchar | 255 | YES |
| 7 | `stage_rank` | float |  | YES |
| 8 | `days_at_stage` | float |  | YES |
| 9 | `LoanAmount` | float |  | YES |
| 10 | `status` | nvarchar | 255 | YES |
| 11 | `elimination_reason` | nvarchar | 255 | YES |
| 12 | `failure_archetype` | nvarchar | 255 | YES |
| 13 | `ml_probability` | float |  | YES |
| 14 | `expected_value` | float |  | YES |
| 15 | `base_probability` | float |  | YES |
| 16 | `is_at_risk` | bit |  | YES |
| 17 | `risk_reasons` | nvarchar | 255 | YES |
| 18 | `recommended_action` | nvarchar | 255 | YES |
| 19 | `counterfactual_probability` | nvarchar | 255 | YES |
| 20 | `probability_delta` | nvarchar | 255 | YES |
| 21 | `expected_value_uplift` | nvarchar | 255 | YES |
| 22 | `recovery_rank` | nvarchar | 255 | YES |
| 23 | `recovery_gap` | nvarchar | 255 | YES |
| 24 | `momentum_rank` | nvarchar | 255 | YES |
| 25 | `moneyball_difficulty` | nvarchar | 255 | YES |
| 26 | `moneyball_quadrant` | nvarchar | 255 | YES |
| 27 | `moneyball_is_movable` | bit |  | YES |
| 28 | `moneyball_cf_quadrant` | nvarchar | 255 | YES |
| 29 | `velocity` | float |  | YES |
| 30 | `velocity_band` | nvarchar | 255 | YES |
| 31 | `f_approved_to_lock_speed` | nvarchar | 255 | YES |
| 32 | `f_branch_channel` | nvarchar | 255 | YES |
| 33 | `f_cltv` | float |  | YES |
| 34 | `f_credit_score` | nvarchar | 255 | YES |
| 35 | `f_days_at_stage` | float |  | YES |
| 36 | `f_days_past_lock_expiry` | nvarchar | 255 | YES |
| 37 | `f_days_remaining` | float |  | YES |
| 38 | `f_days_since_lock` | nvarchar | 255 | YES |
| 39 | `f_days_since_open` | float |  | YES |
| 40 | `f_days_until_lock_expiry` | nvarchar | 255 | YES |
| 41 | `f_fresh_lock_late_stage` | float |  | YES |
| 42 | `f_is_locked` | float |  | YES |
| 43 | `f_likely_lock_extended` | float |  | YES |
| 44 | `f_loan_amount` | float |  | YES |
| 45 | `f_loan_purpose` | nvarchar | 255 | YES |
| 46 | `f_lock_already_expired` | float |  | YES |
| 47 | `f_lock_expired_not_progressed` | float |  | YES |
| 48 | `f_lock_expiring_not_progressed` | float |  | YES |
| 49 | `f_lock_expiry_vs_month_end` | nvarchar | 255 | YES |
| 50 | `f_lock_period` | float |  | YES |
| 51 | `f_locked_at_early_stage` | float |  | YES |
| 52 | `f_long_days_expiring_lock` | float |  | YES |
| 53 | `f_ltv` | float |  | YES |
| 54 | `f_note_rate` | float |  | YES |
| 55 | `f_occupancy_type` | nvarchar | 255 | YES |
| 56 | `f_product_type` | nvarchar | 255 | YES |
| 57 | `f_stage_only_probability` | float |  | YES |
| 58 | `f_stage_rank` | float |  | YES |
| 59 | `f_stages_per_day` | float |  | YES |
| 60 | `f_stale_at_approved` | float |  | YES |
| 61 | `f_unlocked_at_late_stage` | float |  | YES |
| 62 | `Loan Number` | nvarchar | 255 | YES |
| 63 | `Loan Status` | nvarchar | 255 | YES |
| 64 | `IsFunded` | float |  | YES |
| 65 | `DecisionCreditScore` | nvarchar | 255 | YES |
| 66 | `Borrower Experian Score` | nvarchar | 255 | YES |
| 67 | `Borrower TransUnion Score` | nvarchar | 255 | YES |
| 68 | `Borrower Equifax Score` | nvarchar | 255 | YES |
| 69 | `Coborrower Experian Score` | nvarchar | 255 | YES |
| 70 | `Coborrower TransUnion Score` | nvarchar | 255 | YES |
| 71 | `Coborrower Equifax Score` | nvarchar | 255 | YES |
| 72 | `Credit Score Type 1` | nvarchar | 255 | YES |
| 73 | `Credit Score Type 2` | nvarchar | 255 | YES |
| 74 | `Transm Qual Bottom R` | nvarchar | 255 | YES |
| 75 | `LTV` | float |  | YES |
| 76 | `LTV_N` | float |  | YES |
| 77 | `CLTV` | float |  | YES |
| 78 | `Gross Ltv R` | float |  | YES |
| 79 | `Borrower Age` | nvarchar | 255 | YES |
| 80 | `Loan Amount` | float |  | YES |
| 81 | `Total Loan Amount` | float |  | YES |
| 82 | `Purchase Price` | nvarchar | 255 | YES |
| 83 | `Appraised Value` | nvarchar | 255 | YES |
| 84 | `PurchasePrice` | nvarchar | 255 | YES |
| 85 | `AppraisedValue` | nvarchar | 255 | YES |
| 86 | `NoteRate` | float |  | YES |
| 87 | `Note Rate` | float |  | YES |
| 88 | `Term` | float |  | YES |
| 89 | `Lien Position` | nvarchar | 255 | YES |
| 90 | `Loan Type` | nvarchar | 255 | YES |
| 91 | `Amortization Type` | nvarchar | 255 | YES |
| 92 | `Doc Type` | float |  | YES |
| 93 | `Bank Stms Income Type` | float |  | YES |
| 94 | `Occupancy Type` | nvarchar | 255 | YES |
| 95 | `Lock Period (days)` | float |  | YES |
| 96 | `Rate Lock Status` | nvarchar | 255 | YES |
| 97 | `Loan Amount Locked` | float |  | YES |
| 98 | `Has Prepayment Penalty` | bit |  | YES |
| 99 | `Loan Program Name` | nvarchar | 255 | YES |
| 100 | `ARM - Rate Margin` | nvarchar | 255 | YES |
| 101 | `Property State` | nvarchar | 255 | YES |
| 102 | `Property City` | nvarchar | 255 | YES |
| 103 | `Property County` | nvarchar | 255 | YES |
| 104 | `Property Zip` | nvarchar | 255 | YES |
| 105 | `ProdIsSpInRuralArea` | float |  | YES |
| 106 | `Branch` | nvarchar | 255 | YES |
| 107 | `Internal Assigned Loan Officer Name` | nvarchar | 255 | YES |
| 108 | `Internal Assigned Processor Name` | nvarchar | 255 | YES |
| 109 | `Internal Assigned Underwriter Name` | nvarchar | 255 | YES |
| 110 | `Internal Assigned Manager Name` | nvarchar | 255 | YES |
| 111 | `Internal Assigned Lender Account Executive Name` | nvarchar | 255 | YES |
| 112 | `Originating Company Name` | nvarchar | 255 | YES |
| 113 | `Interviewer Company Name` | nvarchar | 255 | YES |
| 114 | `Agent Broker Company Name` | nvarchar | 255 | YES |
| 115 | `Mortgage Originator` | float |  | YES |
| 116 | `Warehouse Lender` | nvarchar | 255 | YES |
| 117 | `Funding Bank Name` | nvarchar | 255 | YES |
| 118 | `Commission - Borrower Points Percentage Of Loan Amount` | float |  | YES |
| 119 | `Commission - Borrower Points Total` | nvarchar | 255 | YES |
| 120 | `Commission - Rebate Fee Percentage of Loan Amount` | nvarchar | 255 | YES |
| 121 | `Commission - Rebate Fee Total` | nvarchar | 255 | YES |
| 122 | `Commission - Gross Profit Total` | nvarchar | 255 | YES |
| 123 | `Commission - Net Profit` | nvarchar | 255 | YES |
| 124 | `Approved Fee (YSP)` | nvarchar | 255 | YES |
| 125 | `GFE - Loan origination fee (total)` | float |  | YES |
| 126 | `GFE - Loan discount (total)` | nvarchar | 255 | YES |
| 127 | `GFE - Appraisal fee` | nvarchar | 255 | YES |
| 128 | `GFE - Credit report fee` | nvarchar | 255 | YES |
| 129 | `GFE - Underwriting fee` | nvarchar | 255 | YES |
| 130 | `Discount Points` | float |  | YES |
| 131 | `Application Fee` | float |  | YES |
| 132 | `Processing fee` | float |  | YES |
| 133 | `Lender Fees Collected` | float |  | YES |
| 134 | `Investor Lock Projected Profit` | float |  | YES |
| 135 | `Investor Lock Projected Profit Amt` | float |  | YES |
| 136 | `day one lock price BE` | float |  | YES |
| 137 | `Investor Lock Loan Num` | nvarchar | 255 | YES |
| 138 | `Investor Lock Lp Investor Nm` | nvarchar | 255 | YES |
| 139 | `Investor Purchase` | nvarchar | 255 | YES |
| 140 | `Investor Lock Brok Comp Price` | float |  | YES |
| 141 | `InvestorLockCommitmentT` | float |  | YES |
| 142 | `Lead New Date` | datetime |  | YES |
| 143 | `Loan Open Date` | datetime |  | YES |
| 144 | `Pre-qual Date` | nvarchar | 255 | YES |
| 145 | `Pre-approved Date` | nvarchar | 255 | YES |
| 146 | `Registration` | nvarchar | 255 | YES |
| 147 | `RegistrationD` | nvarchar | 255 | YES |
| 148 | `Respa App D` | nvarchar | 255 | YES |
| 149 | `HMDA App D` | nvarchar | 255 | YES |
| 150 | `Loan Submitted D` | nvarchar | 255 | YES |
| 151 | `DocumentCheckD` | nvarchar | 255 | YES |
| 152 | `PreProcessingD` | nvarchar | 255 | YES |
| 153 | `ProcessingD` | nvarchar | 255 | YES |
| 154 | `Submitted D` | nvarchar | 255 | YES |
| 155 | `Underwriting D` | nvarchar | 255 | YES |
| 156 | `ConditionReviewD` | nvarchar | 255 | YES |
| 157 | `FinalUnderwritingD` | nvarchar | 255 | YES |
| 158 | `Approved D` | nvarchar | 255 | YES |
| 159 | `Estimated Closing D` | datetime |  | YES |
| 160 | `Clear To Close D` | nvarchar | 255 | YES |
| 161 | `PreDocQCD` | nvarchar | 255 | YES |
| 162 | `Docs D` | nvarchar | 255 | YES |
| 163 | `DocsOrderedD` | nvarchar | 255 | YES |
| 164 | `DocsDrawnD` | nvarchar | 255 | YES |
| 165 | `DocsBackD` | nvarchar | 255 | YES |
| 166 | `FundingConditionsD` | nvarchar | 255 | YES |
| 167 | `Scheduled Funding D` | nvarchar | 255 | YES |
| 168 | `Funded D` | nvarchar | 255 | YES |
| 169 | `Loan Closed D` | nvarchar | 255 | YES |
| 170 | `Recorded D` | nvarchar | 255 | YES |
| 171 | `Purchase D` | nvarchar | 255 | YES |
| 172 | `Loan Shipped D` | nvarchar | 255 | YES |
| 173 | `Rate Lock D` | nvarchar | 255 | YES |
| 174 | `Rate Lock Expiration D` | nvarchar | 255 | YES |
| 175 | `Loan OnHold D` | nvarchar | 255 | YES |
| 176 | `Loan Canceled D` | nvarchar | 255 | YES |
| 177 | `Loan Denied D` | nvarchar | 255 | YES |
| 178 | `Loan Suspended D` | nvarchar | 255 | YES |
| 179 | `Withdrawn D` | nvarchar | 255 | YES |
| 180 | `DaysOpenToSubmitted` | nvarchar | 255 | YES |
| 181 | `DaysSubmittedToApproved` | nvarchar | 255 | YES |
| 182 | `DaysApprovedToCTC` | nvarchar | 255 | YES |
| 183 | `DaysCTCToFunded` | nvarchar | 255 | YES |
| 184 | `DaysTotalSubmitToFund` | nvarchar | 255 | YES |
| 185 | `DaysTotalOpenToFund` | nvarchar | 255 | YES |
| 186 | `LockDurationDays` | nvarchar | 255 | YES |
| 187 | `DaysSubmittedToUW` | nvarchar | 255 | YES |
| 188 | `DaysUWToApproved` | nvarchar | 255 | YES |
| 189 | `DaysDocsToFunded` | nvarchar | 255 | YES |
| 190 | `WasCanceled` | float |  | YES |
| 191 | `WasDenied` | float |  | YES |
| 192 | `WasSuspended` | float |  | YES |
| 193 | `WasOnHold` | float |  | YES |
| 194 | `WasWithdrawn` | float |  | YES |
| 195 | `HasRateLock` | float |  | YES |
| 196 | `WasApproved` | float |  | YES |
| 197 | `ReachedCTC` | float |  | YES |
| 198 | `SubmittedMonth` | nvarchar | 255 | YES |
| 199 | `SubmittedYear` | nvarchar | 255 | YES |
| 200 | `SubmittedDayOfWeek` | nvarchar | 255 | YES |
| 201 | `custLoan391` | nvarchar | 255 | YES |
| 202 | `custLoan377` | nvarchar | 255 | YES |
| 203 | `custLoan408` | float |  | YES |
| 204 | `custLoan391ID` | float |  | YES |
| 205 | `OnlyMon` | float |  | YES |
| 206 | `TIL Disclosure / GFE Ordered Date` | nvarchar | 255 | YES |
| 207 | `TIL Disclosure / GFE Due Date` | nvarchar | 255 | YES |
| 208 | `TIL Disclosure / GFE Received Date` | nvarchar | 255 | YES |
| 209 | `DidFund` | float |  | YES |
| 210 | `Outcome` | nvarchar | 255 | YES |
| 211 | `expected_funding` | float |  | YES |
| 212 | `is_locked_flag` | bit |  | YES |
| 213 | `eliminated` | bit |  | YES |

### Per-column profile

| name | type | nulls | distinct | empty_str | min | max | avg | zeros | date_min | date_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `snapshot_date` | datetime | 0 | 1 |  |  |  |  |  | 2025-12-15 00:00:00 | 2025-12-15 00:00:00 |
| `LoanGuid` | nvarchar | 0 | >1000 | 0 |  |  |  |  |  |  |
| `Product Type` | nvarchar | 363 | 10 | 0 |  |  |  |  |  |  |
| `Loan Purpose` | nvarchar | 0 | 4 | 0 |  |  |  |  |  |  |
| `Branch Channel` | nvarchar | 0 | 3 | 0 |  |  |  |  |  |  |
| `current_stage` | nvarchar | 0 | 12 | 0 |  |  |  |  |  |  |
| `stage_rank` | float | 0 | 12 |  | 0 | 11 | 2.697 | 342 |  |  |
| `days_at_stage` | float | 0 | 271 |  | 0 | 1071 | 127.7268 | 120 |  |  |
| `LoanAmount` | float | 515 | 372 |  | 15 | 7.1e+06 | 528759.2542 | 0 |  |  |
| `status` | nvarchar | 0 | 2 | 0 |  |  |  |  |  |  |
| `elimination_reason` | nvarchar | 708 | 5 | 0 |  |  |  |  |  |  |
| `failure_archetype` | nvarchar | 708 | 4 | 0 |  |  |  |  |  |  |
| `ml_probability` | float | 0 | 941 |  | 0.0009917 | 0.9943 | 0.178 | 0 |  |  |
| `expected_value` | float | 515 | 546 |  | 0.0281 | 1.913e+06 | 55879.6955 | 0 |  |  |
| `base_probability` | float | 0 | 51 |  | 0 | 1 | 0.1689 | 367 |  |  |
| `is_at_risk` | bit | 0 | 2 |  | 0 | 1 | 0.0532 | 1050 |  |  |
| `risk_reasons` | nvarchar | 1050 | 19 | 0 |  |  |  |  |  |  |
| `recommended_action` | nvarchar | 1060 | 2 | 0 |  |  |  |  |  |  |
| `counterfactual_probability` | nvarchar | 1060 | 49 | 0 |  |  |  |  |  |  |
| `probability_delta` | nvarchar | 1050 | 50 | 0 |  |  |  |  |  |  |
| `expected_value_uplift` | nvarchar | 1050 | 50 | 0 |  |  |  |  |  |  |
| `recovery_rank` | nvarchar | 1097 | 12 | 0 |  |  |  |  |  |  |
| `recovery_gap` | nvarchar | 1097 | 12 | 0 |  |  |  |  |  |  |
| `momentum_rank` | nvarchar | 1098 | 11 | 0 |  |  |  |  |  |  |
| `moneyball_difficulty` | nvarchar | 856 | 78 | 0 |  |  |  |  |  |  |
| `moneyball_quadrant` | nvarchar | 856 | 4 | 0 |  |  |  |  |  |  |
| `moneyball_is_movable` | bit | 0 | 2 |  | 0 | 1 | 0.0388 | 1066 |  |  |
| `moneyball_cf_quadrant` | nvarchar | 1066 | 2 | 0 |  |  |  |  |  |  |
| `velocity` | float | 0 | 204 |  | 0 | 2 | 0.1896 | 342 |  |  |
| `velocity_band` | nvarchar | 0 | 4 | 0 |  |  |  |  |  |  |
| `f_approved_to_lock_speed` | nvarchar | 845 | 64 | 0 |  |  |  |  |  |  |
| `f_branch_channel` | nvarchar | 0 | 3 | 0 |  |  |  |  |  |  |
| `f_cltv` | float | 0 | 344 |  | 0 | 103 | 72.8983 | 80 |  |  |
| `f_credit_score` | nvarchar | 262 | 226 | 0 |  |  |  |  |  |  |
| `f_days_at_stage` | float | 0 | 271 |  | 0 | 1071 | 127.7268 | 120 |  |  |
| `f_days_past_lock_expiry` | nvarchar | 1066 | 31 | 0 |  |  |  |  |  |  |
| `f_days_remaining` | float | 0 | 1 |  | 16 | 16 | 16 | 0 |  |  |
| `f_days_since_lock` | nvarchar | 834 | 59 | 0 |  |  |  |  |  |  |
| `f_days_since_open` | float | 0 | 254 |  | 0 | 1071 | 134.018 | 30 |  |  |
| `f_days_until_lock_expiry` | nvarchar | 834 | 55 | 0 |  |  |  |  |  |  |
| `f_fresh_lock_late_stage` | float | 0 | 2 |  | 0 | 1 | 0.0289 | 1077 |  |  |
| `f_is_locked` | float | 0 | 2 |  | 0 | 1 | 0.248 | 834 |  |  |
| `f_likely_lock_extended` | float | 0 | 2 |  | 0 | 1 | 0.0388 | 1066 |  |  |
| `f_loan_amount` | float | 515 | 372 |  | 15 | 7.1e+06 | 528759.2542 | 0 |  |  |
| `f_loan_purpose` | nvarchar | 0 | 4 | 0 |  |  |  |  |  |  |
| `f_lock_already_expired` | float | 0 | 2 |  | 0 | 1 | 0.0388 | 1066 |  |  |
| `f_lock_expired_not_progressed` | float | 0 | 2 |  | 0 | 1 | 0.0388 | 1066 |  |  |
| `f_lock_expiring_not_progressed` | float | 0 | 2 |  | 0 | 1 | 0.0099 | 1098 |  |  |
| `f_lock_expiry_vs_month_end` | nvarchar | 716 | 68 | 0 |  |  |  |  |  |  |
| `f_lock_period` | float | 0 | 26 |  | 0 | 62 | 20.4247 | 362 |  |  |
| `f_locked_at_early_stage` | float | 0 | 2 |  | 0 | 1 | 0.1686 | 922 |  |  |
| `f_long_days_expiring_lock` | float | 0 | 2 |  | 0 | 1 | 0.009 | 1099 |  |  |
| `f_ltv` | float | 0 | 340 |  | 0 | 100 | 65.9757 | 80 |  |  |
| `f_note_rate` | float | 458 | 49 |  | 0 | 11.25 | 5.8484 | 91 |  |  |
| `f_occupancy_type` | nvarchar | 0 | 3 | 0 |  |  |  |  |  |  |
| `f_product_type` | nvarchar | 363 | 10 | 0 |  |  |  |  |  |  |
| `f_stage_only_probability` | float | 0 | 11 |  | 0 | 1 | 0.1731 | 342 |  |  |
| `f_stage_rank` | float | 0 | 12 |  | 0 | 11 | 2.697 | 342 |  |  |
| `f_stages_per_day` | float | 0 | 204 |  | 0 | 2 | 0.1896 | 342 |  |  |
| `f_stale_at_approved` | float | 0 | 2 |  | 0 | 1 | 0.1948 | 893 |  |  |
| `f_unlocked_at_late_stage` | float | 0 | 2 |  | 0 | 1 | 0.0027 | 1106 |  |  |
| `Loan Number` | nvarchar | 0 | >1000 | 0 |  |  |  |  |  |  |
| `Loan Status` | nvarchar | 0 | 21 | 0 |  |  |  |  |  |  |
| `IsFunded` | float | 0 | 2 |  | 0 | 1 | 0.0397 | 1065 |  |  |
| `DecisionCreditScore` | nvarchar | 262 | 226 | 0 |  |  |  |  |  |  |
| `Borrower Experian Score` | nvarchar | 271 | 238 | 0 |  |  |  |  |  |  |
| `Borrower TransUnion Score` | nvarchar | 309 | 210 | 0 |  |  |  |  |  |  |
| `Borrower Equifax Score` | nvarchar | 274 | 223 | 0 |  |  |  |  |  |  |
| `Coborrower Experian Score` | nvarchar | 964 | 90 | 0 |  |  |  |  |  |  |
| `Coborrower TransUnion Score` | nvarchar | 973 | 88 | 0 |  |  |  |  |  |  |
| `Coborrower Equifax Score` | nvarchar | 962 | 90 | 0 |  |  |  |  |  |  |
| `Credit Score Type 1` | nvarchar | 264 | 227 | 0 |  |  |  |  |  |  |
| `Credit Score Type 2` | nvarchar | 264 | 227 | 0 |  |  |  |  |  |  |
| `Transm Qual Bottom R` | nvarchar | 484 | 609 | 0 |  |  |  |  |  |  |
| `LTV` | float | 0 | 340 |  | 0 | 100 | 65.9757 | 80 |  |  |
| `LTV_N` | float | 0 | 340 |  | 0 | 100 | 65.9757 | 80 |  |  |
| `CLTV` | float | 0 | 344 |  | 0 | 103 | 72.8983 | 80 |  |  |
| `Gross Ltv R` | float | 0 | 352 |  | 0 | 103.3 | 66.1544 | 80 |  |  |
| `Borrower Age` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Loan Amount` | float | 458 | 373 |  | 0 | 7.1e+06 | 482462.361 | 57 |  |  |
| `Total Loan Amount` | float | 0 | 653 |  | 0 | 5.08e+07 | 567251.4256 | 70 |  |  |
| `Purchase Price` | nvarchar | 803 | 1 | 0 |  |  |  |  |  |  |
| `Appraised Value` | nvarchar | 959 | 1 | 0 |  |  |  |  |  |  |
| `PurchasePrice` | nvarchar | 803 | 1 | 0 |  |  |  |  |  |  |
| `AppraisedValue` | nvarchar | 959 | 1 | 0 |  |  |  |  |  |  |
| `NoteRate` | float | 458 | 49 |  | 0 | 11.25 | 5.8484 | 91 |  |  |
| `Note Rate` | float | 458 | 49 |  | 0 | 11.25 | 5.8484 | 91 |  |  |
| `Term` | float | 0 | 6 |  | 120 | 480 | 355.5636 | 0 |  |  |
| `Lien Position` | nvarchar | 0 | 2 | 0 |  |  |  |  |  |  |
| `Loan Type` | nvarchar | 0 | 5 | 0 |  |  |  |  |  |  |
| `Amortization Type` | nvarchar | 0 | 2 | 0 |  |  |  |  |  |  |
| `Doc Type` | float | 0 | 11 |  | 0 | 22 | 8.2552 | 587 |  |  |
| `Bank Stms Income Type` | float | 58 | 6 |  | 1 | 6 | 1.2255 | 0 |  |  |
| `Occupancy Type` | nvarchar | 0 | 3 | 0 |  |  |  |  |  |  |
| `Lock Period (days)` | float | 0 | 26 |  | 0 | 62 | 20.4247 | 362 |  |  |
| `Rate Lock Status` | nvarchar | 8 | 2 | 0 |  |  |  |  |  |  |
| `Loan Amount Locked` | float | 0 | 2 |  | 0 | 1 | 0.9125 | 97 |  |  |
| `Has Prepayment Penalty` | bit | 5 | 2 |  | 0 | 1 | 0.1902 | 894 |  |  |
| `Loan Program Name` | nvarchar | 363 | 85 | 0 |  |  |  |  |  |  |
| `ARM - Rate Margin` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Property State` | nvarchar | 234 | 36 | 0 |  |  |  |  |  |  |
| `Property City` | nvarchar | 134 | 525 | 0 |  |  |  |  |  |  |
| `Property County` | nvarchar | 136 | 224 | 0 |  |  |  |  |  |  |
| `Property Zip` | nvarchar | 134 | 719 | 0 |  |  |  |  |  |  |
| `ProdIsSpInRuralArea` | float | 0 | 2 |  | 0 | 1 | 0.0072 | 1101 |  |  |
| `Branch` | nvarchar | 0 | 6 | 0 |  |  |  |  |  |  |
| `Internal Assigned Loan Officer Name` | nvarchar | 71 | 433 | 0 |  |  |  |  |  |  |
| `Internal Assigned Processor Name` | nvarchar | 191 | 14 | 0 |  |  |  |  |  |  |
| `Internal Assigned Underwriter Name` | nvarchar | 387 | 18 | 0 |  |  |  |  |  |  |
| `Internal Assigned Manager Name` | nvarchar | 921 | 9 | 0 |  |  |  |  |  |  |
| `Internal Assigned Lender Account Executive Name` | nvarchar | 225 | 58 | 0 |  |  |  |  |  |  |
| `Originating Company Name` | nvarchar | 274 | 264 | 0 |  |  |  |  |  |  |
| `Interviewer Company Name` | nvarchar | 69 | 257 | 0 |  |  |  |  |  |  |
| `Agent Broker Company Name` | nvarchar | 86 | 250 | 0 |  |  |  |  |  |  |
| `Mortgage Originator` | float | 0 | 3 |  | 0 | 2 | 1.6528 | 78 |  |  |
| `Warehouse Lender` | nvarchar | 0 | 4 | 0 |  |  |  |  |  |  |
| `Funding Bank Name` | nvarchar | 925 | 73 | 0 |  |  |  |  |  |  |
| `Commission - Borrower Points Percentage Of Loan Amount` | float | 0 | 1 |  | 0 | 0 | 0 | 1109 |  |  |
| `Commission - Borrower Points Total` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Commission - Rebate Fee Percentage of Loan Amount` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Commission - Rebate Fee Total` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Commission - Gross Profit Total` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Commission - Net Profit` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Approved Fee (YSP)` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `GFE - Loan origination fee (total)` | float | 0 | 6 |  | 0 | 22116 | 33.263 | 1104 |  |  |
| `GFE - Loan discount (total)` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `GFE - Appraisal fee` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `GFE - Credit report fee` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `GFE - Underwriting fee` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Discount Points` | float | 0 | 304 |  | 0 | 85000 | 1579.6847 | 787 |  |  |
| `Application Fee` | float | 0 | 15 |  | 0 | 110000 | 164.4382 | 1084 |  |  |
| `Processing fee` | float | 0 | 17 |  | 0 | 1750 | 35.3246 | 1060 |  |  |
| `Lender Fees Collected` | float | 0 | 906 |  | -882.4 | 200404.32 | 3920.4643 | 176 |  |  |
| `Investor Lock Projected Profit` | float | 0 | 433 |  | -6 | 6.565 | 0.6033 | 444 |  |  |
| `Investor Lock Projected Profit Amt` | float | 0 | 638 |  | -273000 | 109710.5 | 2690.8488 | 444 |  |  |
| `day one lock price BE` | float | 0 | 294 |  | 0 | 106.391 | 36.524 | 713 |  |  |
| `Investor Lock Loan Num` | nvarchar | 1010 | 55 | 0 |  |  |  |  |  |  |
| `Investor Lock Lp Investor Nm` | nvarchar | 78 | 23 | 0 |  |  |  |  |  |  |
| `Investor Purchase` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Investor Lock Brok Comp Price` | float | 0 | 304 |  | 98.625 | 107.9289 | 100.8834 | 0 |  |  |
| `InvestorLockCommitmentT` | float | 0 | 4 |  | 0 | 3 | 1.9784 | 139 |  |  |
| `Lead New Date` | datetime | 835 | 184 |  |  |  |  |  | 2023-01-09 00:00:00 | 2025-12-12 00:00:00 |
| `Loan Open Date` | datetime | 0 | 254 |  |  |  |  |  | 2023-01-09 00:00:00 | 2025-12-15 00:00:00 |
| `Pre-qual Date` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Pre-approved Date` | nvarchar | 1030 | 52 | 0 |  |  |  |  |  |  |
| `Registration` | nvarchar | 363 | 114 | 0 |  |  |  |  |  |  |
| `RegistrationD` | nvarchar | 924 | 13 | 0 |  |  |  |  |  |  |
| `Respa App D` | nvarchar | 422 | 114 | 0 |  |  |  |  |  |  |
| `HMDA App D` | nvarchar | 421 | 114 | 0 |  |  |  |  |  |  |
| `Loan Submitted D` | nvarchar | 394 | 118 | 0 |  |  |  |  |  |  |
| `DocumentCheckD` | nvarchar | 437 | 120 | 0 |  |  |  |  |  |  |
| `PreProcessingD` | nvarchar | 1080 | 26 | 0 |  |  |  |  |  |  |
| `ProcessingD` | nvarchar | 1080 | 23 | 0 |  |  |  |  |  |  |
| `Submitted D` | nvarchar | 363 | 114 | 0 |  |  |  |  |  |  |
| `Underwriting D` | nvarchar | 408 | 136 | 0 |  |  |  |  |  |  |
| `ConditionReviewD` | nvarchar | 850 | 29 | 0 |  |  |  |  |  |  |
| `FinalUnderwritingD` | nvarchar | 890 | 26 | 0 |  |  |  |  |  |  |
| `Approved D` | nvarchar | 470 | 132 | 0 |  |  |  |  |  |  |
| `Estimated Closing D` | datetime | 0 | 265 |  |  |  |  |  | 2023-02-23 00:00:00 | 2026-02-28 00:00:00 |
| `Clear To Close D` | nvarchar | 882 | 27 | 0 |  |  |  |  |  |  |
| `PreDocQCD` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Docs D` | nvarchar | 906 | 21 | 0 |  |  |  |  |  |  |
| `DocsOrderedD` | nvarchar | 901 | 23 | 0 |  |  |  |  |  |  |
| `DocsDrawnD` | nvarchar | 905 | 21 | 0 |  |  |  |  |  |  |
| `DocsBackD` | nvarchar | 966 | 18 | 0 |  |  |  |  |  |  |
| `FundingConditionsD` | nvarchar | 972 | 20 | 0 |  |  |  |  |  |  |
| `Scheduled Funding D` | nvarchar | 923 | 16 | 0 |  |  |  |  |  |  |
| `Funded D` | nvarchar | 925 | 16 | 0 |  |  |  |  |  |  |
| `Loan Closed D` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Recorded D` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Purchase D` | nvarchar | 1095 | 6 | 0 |  |  |  |  |  |  |
| `Loan Shipped D` | nvarchar | 969 | 13 | 0 |  |  |  |  |  |  |
| `Rate Lock D` | nvarchar | 716 | 73 | 0 |  |  |  |  |  |  |
| `Rate Lock Expiration D` | nvarchar | 716 | 68 | 0 |  |  |  |  |  |  |
| `Loan OnHold D` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `Loan Canceled D` | nvarchar | 962 | 15 | 0 |  |  |  |  |  |  |
| `Loan Denied D` | nvarchar | 1104 | 2 | 0 |  |  |  |  |  |  |
| `Loan Suspended D` | nvarchar | 1107 | 2 | 0 |  |  |  |  |  |  |
| `Withdrawn D` | nvarchar | 1109 | 0 | 0 |  |  |  |  |  |  |
| `DaysOpenToSubmitted` | nvarchar | 363 | 19 | 0 |  |  |  |  |  |  |
| `DaysSubmittedToApproved` | nvarchar | 470 | 34 | 0 |  |  |  |  |  |  |
| `DaysApprovedToCTC` | nvarchar | 882 | 68 | 0 |  |  |  |  |  |  |
| `DaysCTCToFunded` | nvarchar | 925 | 18 | 0 |  |  |  |  |  |  |
| `DaysTotalSubmitToFund` | nvarchar | 925 | 61 | 0 |  |  |  |  |  |  |
| `DaysTotalOpenToFund` | nvarchar | 925 | 60 | 0 |  |  |  |  |  |  |
| `LockDurationDays` | nvarchar | 716 | 25 | 0 |  |  |  |  |  |  |
| `DaysSubmittedToUW` | nvarchar | 408 | 29 | 0 |  |  |  |  |  |  |
| `DaysUWToApproved` | nvarchar | 482 | 17 | 0 |  |  |  |  |  |  |
| `DaysDocsToFunded` | nvarchar | 926 | 14 | 0 |  |  |  |  |  |  |
| `WasCanceled` | float | 0 | 2 |  | 0 | 1 | 0.1326 | 962 |  |  |
| `WasDenied` | float | 0 | 2 |  | 0 | 1 | 0.0045 | 1104 |  |  |
| `WasSuspended` | float | 0 | 2 |  | 0 | 1 | 0.0018 | 1107 |  |  |
| `WasOnHold` | float | 0 | 1 |  | 0 | 0 | 0 | 1109 |  |  |
| `WasWithdrawn` | float | 0 | 1 |  | 0 | 0 | 0 | 1109 |  |  |
| `HasRateLock` | float | 0 | 2 |  | 0 | 1 | 0.3544 | 716 |  |  |
| `WasApproved` | float | 0 | 2 |  | 0 | 1 | 0.5762 | 470 |  |  |
| `ReachedCTC` | float | 0 | 2 |  | 0 | 1 | 0.2047 | 882 |  |  |
| `SubmittedMonth` | nvarchar | 363 | 9 | 0 |  |  |  |  |  |  |
| `SubmittedYear` | nvarchar | 363 | 3 | 0 |  |  |  |  |  |  |
| `SubmittedDayOfWeek` | nvarchar | 363 | 6 | 0 |  |  |  |  |  |  |
| `custLoan391` | nvarchar | 1007 | 5 | 0 |  |  |  |  |  |  |
| `custLoan377` | nvarchar | 231 | 4 | 0 |  |  |  |  |  |  |
| `custLoan408` | float | 0 | 2 |  | 0 | 1 | 0.0135 | 1094 |  |  |
| `custLoan391ID` | float | 58 | 6 |  | 1 | 6 | 1.2255 | 0 |  |  |
| `OnlyMon` | float | 0 | 3 |  | 0 | 360 | 7.0334 | 1066 |  |  |
| `TIL Disclosure / GFE Ordered Date` | nvarchar | 458 | 112 | 0 |  |  |  |  |  |  |
| `TIL Disclosure / GFE Due Date` | nvarchar | 446 | 94 | 0 |  |  |  |  |  |  |
| `TIL Disclosure / GFE Received Date` | nvarchar | 493 | 120 | 0 |  |  |  |  |  |  |
| `DidFund` | float | 0 | 2 |  | 0 | 1 | 0.1659 | 925 |  |  |
| `Outcome` | nvarchar | 0 | 3 | 0 |  |  |  |  |  |  |
| `expected_funding` | float | 515 | 328 |  | 0 | 1.833e+06 | 86105.6931 | 239 |  |  |
| `is_locked_flag` | bit | 0 | 2 |  | 0 | 1 | 0.248 | 834 |  |  |
| `eliminated` | bit | 0 | 2 |  | 0 | 1 | 0.3616 | 708 |  |  |

### Sample (TOP 3)

| column | row1 | row2 | row3 |
| --- | --- | --- | --- |
| `snapshot_date` | 2025-12-15 00:00:00 | 2025-12-15 00:00:00 | 2025-12-15 00:00:00 |
| `LoanGuid` | 82510405 | 62510409 | 82510414 |
| `Product Type` | NONCONFORMING | CONFORMING | NONCONFORMING |
| `Loan Purpose` | Refinance | Refinance CashOut | Refinance CashOut |
| `Branch Channel` | Wholesale | Retail | Wholesale |
| `current_stage` | Approved | Submitted | Approved |
| `stage_rank` | 4.0 | 2.0 | 4.0 |
| `days_at_stage` | 48.0 | 59.0 | 54.0 |
| `LoanAmount` | 311500.0 | 140000.0 | 460000.0 |
| `status` | live | dead | dead |
| `elimination_reason` |  | submitted_unlocked_stale | approved_expired_lock |
| `failure_archetype` |  | Stale Pre-Approval | Lock Expired, Gave Up |
| `ml_probability` | 0.00917787699213683 | 0.00127666218360505 | 0.00742552481713536 |
| `expected_value` | 2858.90868305062 | 178.732705704707 | 3415.74141588226 |
| `base_probability` | 0.149100257069408 | 0.0 | 0.165103189493433 |
| `is_at_risk` | False | False | False |
| `risk_reasons` |  |  |  |
| `recommended_action` |  |  |  |
| `counterfactual_probability` |  |  |  |
| `probability_delta` |  |  |  |
| `expected_value_uplift` |  |  |  |
| `recovery_rank` |  |  |  |
| `recovery_gap` |  |  |  |
| `momentum_rank` |  |  |  |
| `moneyball_difficulty` | 52 |  |  |
| `moneyball_quadrant` | long_shot |  |  |
| `moneyball_is_movable` | False | False | False |
| `moneyball_cf_quadrant` |  |  |  |
| `velocity` | 0.0677966101694915 | 0.0338983050847457 | 0.0677966101694915 |
| `velocity_band` | Slow | Stalled | Slow |
| `f_approved_to_lock_speed` |  |  | 8 |
| `f_branch_channel` | Wholesale | Retail | Wholesale |
| `f_cltv` | 75.0 | 40.0 | 80.0 |
| `f_credit_score` | 691 | 787 | 712 |
| `f_days_at_stage` | 48.0 | 59.0 | 54.0 |
| `f_days_past_lock_expiry` |  |  | 14 |
| `f_days_remaining` | 16.0 | 16.0 | 16.0 |
| `f_days_since_lock` |  |  | 46 |
| `f_days_since_open` | 59.0 | 59.0 | 59.0 |
| `f_days_until_lock_expiry` |  |  | -14 |
| `f_fresh_lock_late_stage` | 0.0 | 0.0 | 0.0 |
| `f_is_locked` | 0.0 | 0.0 | 1.0 |
| `f_likely_lock_extended` | 0.0 | 0.0 | 1.0 |
| `f_loan_amount` | 311500.0 | 140000.0 | 460000.0 |
| `f_loan_purpose` | Refinance | Refinance CashOut | Refinance CashOut |
| `f_lock_already_expired` | 0.0 | 0.0 | 1.0 |
| `f_lock_expired_not_progressed` | 0.0 | 0.0 | 1.0 |
| `f_lock_expiring_not_progressed` | 0.0 | 0.0 | 0.0 |
| `f_lock_expiry_vs_month_end` |  |  | -30 |
| `f_lock_period` | 30.0 | 30.0 | 32.0 |
| `f_locked_at_early_stage` | 0.0 | 0.0 | 1.0 |
| `f_long_days_expiring_lock` | 0.0 | 0.0 | 0.0 |
| `f_ltv` | 75.0 | 40.0 | 80.0 |
| `f_note_rate` | 6.75 | 6.125 | 7.5 |
| `f_occupancy_type` | Investment | Primary Residence | Primary Residence |
| `f_product_type` | NONCONFORMING | CONFORMING | NONCONFORMING |
| `f_stage_only_probability` | 0.229818053347465 | 0.0184210526315789 | 0.229818053347465 |
| `f_stage_rank` | 4.0 | 2.0 | 4.0 |
| `f_stages_per_day` | 0.0677966101694915 | 0.0338983050847457 | 0.0677966101694915 |
| `f_stale_at_approved` | 1.0 | 0.0 | 1.0 |
| `f_unlocked_at_late_stage` | 0.0 | 0.0 | 0.0 |
| `Loan Number` | 82510405 | 62510409 | 82510414 |
| `Loan Status` | Approved | Registered | Loan Cancelled |
| `IsFunded` | 0.0 | 0.0 | 0.0 |
| `DecisionCreditScore` | 691 | 787 | 712 |
| `Borrower Experian Score` | 684 | 789 | 726 |
| `Borrower TransUnion Score` | 691 |  | 712 |
| `Borrower Equifax Score` | 691 | 787 | 650 |
| `Coborrower Experian Score` |  |  |  |
| `Coborrower TransUnion Score` |  |  |  |
| `Coborrower Equifax Score` |  |  |  |
| `Credit Score Type 1` | 691 | 654 | 712 |
| `Credit Score Type 2` | 691 | 654 | 712 |
| `Transm Qual Bottom R` |  | 30.563 | 36.573 |
| `LTV` | 75.0 | 40.0 | 80.0 |
| `LTV_N` | 75.0 | 40.0 | 80.0 |
| `CLTV` | 75.0 | 40.0 | 80.0 |
| `Gross Ltv R` | 75.0 | 40.0 | 80.0 |
| `Borrower Age` |  |  |  |
| `Loan Amount` | 311500.0 | 140000.0 | 460000.0 |
| `Total Loan Amount` | 302250.0 | 140000.0 | 460000.0 |
| `Purchase Price` | 0 | 0 | 0 |
| `Appraised Value` |  |  |  |
| `PurchasePrice` | 0 | 0 | 0 |
| `AppraisedValue` |  |  |  |
| `NoteRate` | 6.75 | 6.125 | 7.5 |
| `Note Rate` | 6.75 | 6.125 | 7.5 |
| `Term` | 360.0 | 360.0 | 360.0 |
| `Lien Position` | Other | Other | Other |
| `Loan Type` | Conventional | Conventional | Conventional |
| `Amortization Type` | Fixed | Fixed | Fixed |
| `Doc Type` | 20.0 | 0.0 | 15.0 |
| `Bank Stms Income Type` | 1.0 | 1.0 | 1.0 |
| `Occupancy Type` | Investment | Primary Residence | Primary Residence |
| `Lock Period (days)` | 30.0 | 30.0 | 32.0 |
| `Rate Lock Status` | Not Locked | Not Locked | Locked |
| `Loan Amount Locked` | 1.0 | 1.0 | 1.0 |
| `Has Prepayment Penalty` | True | False | False |
| `Loan Program Name` | 30 YR FIXED DSCR - Flex 3 YR PPP 6mo Int. | 30 YR FIXED CONFORMING FLEXPOINT | 30 YR FIXED Flex Expanded Doc |
| `ARM - Rate Margin` |  |  |  |
| `Property State` | FL | TX | OR |
| `Property City` | Orlando | Plano | Beaverton |
| `Property County` | Orange | Collin | Washington |
| `Property Zip` | 32837 | 75025 | 97007 |
| `ProdIsSpInRuralArea` | 0.0 | 0.0 | 0.0 |
| `Branch` | SBI-Wholesale | Keller Williams McKinney | SBI-Wholesale |
| `Internal Assigned Loan Officer Name` | Angela Ivey | Adam Efazat | Ali Karimi |
| `Internal Assigned Processor Name` | La Ray Reed | Susie Meza | Rosie Perez |
| `Internal Assigned Underwriter Name` | Steve Vo |  | Jesse Martinez |
| `Internal Assigned Manager Name` |  |  |  |
| `Internal Assigned Lender Account Executive Name` | Rich Marfino |  | Tammy Blanchard |
| `Originating Company Name` | Innovative Mortgage Services, Inc. |  | Altamont Mortgage Funding, Inc. |
| `Interviewer Company Name` | Innovative Mortgage Services, Inc. | FlexPoint, Inc. | Altamont Mortgage Funding, Inc. |
| `Agent Broker Company Name` | Innovative Mortgage Services, Inc. |  | Altamont Mortgage Funding, Inc. |
| `Mortgage Originator` | 2.0 | 1.0 | 2.0 |
| `Warehouse Lender` | Blank | Blank | Blank |
| `Funding Bank Name` |  |  |  |
| `Commission - Borrower Points Percentage Of Loan Amount` | 0.0 | 0.0 | 0.0 |
| `Commission - Borrower Points Total` |  |  |  |
| `Commission - Rebate Fee Percentage of Loan Amount` |  |  |  |
| `Commission - Rebate Fee Total` |  |  |  |
| `Commission - Gross Profit Total` |  |  |  |
| `Commission - Net Profit` |  |  |  |
| `Approved Fee (YSP)` |  |  |  |
| `GFE - Loan origination fee (total)` | 0.0 | 0.0 | 0.0 |
| `GFE - Loan discount (total)` |  |  |  |
| `GFE - Appraisal fee` |  |  |  |
| `GFE - Credit report fee` |  |  |  |
| `GFE - Underwriting fee` |  |  |  |
| `Discount Points` | 3400.31 | 1978.2 | 0.0 |
| `Application Fee` | 300.0 | 0.0 | 0.0 |
| `Processing fee` | 0.0 | 0.0 | 0.0 |
| `Lender Fees Collected` | 6950.35 | 3435.22 | 2944.96 |
| `Investor Lock Projected Profit` | 1.125 | 1.413 | 2.45 |
| `Investor Lock Projected Profit Amt` | 3400.31 | 1978.2 | 11270.0 |
| `day one lock price BE` | 0.0 | 0.0 | 102.7 |
| `Investor Lock Loan Num` |  |  |  |
| `Investor Lock Lp Investor Nm` | FlexPoint, Non QM | FlexPoint, Inc. | FlexPoint, Inc. |
| `Investor Purchase` |  |  |  |
| `Investor Lock Brok Comp Price` | 100.0 | 100.0 | 102.7 |
| `InvestorLockCommitmentT` | 2.0 | 2.0 | 3.0 |
| `Lead New Date` |  |  |  |
| `Loan Open Date` | 2025-10-17 00:00:00 | 2025-10-17 00:00:00 | 2025-10-17 00:00:00 |
| `Pre-qual Date` |  |  |  |
| `Pre-approved Date` |  |  |  |
| `Registration` | 10/20/2025 | 10/17/2025 | 10/17/2025 |
| `RegistrationD` |  |  |  |
| `Respa App D` | 10/17/2025 |  | 10/17/2025 |
| `HMDA App D` | 10/17/2025 |  | 10/17/2025 |
| `Loan Submitted D` | 10/24/2025 |  | 10/20/2025 |
| `DocumentCheckD` | 10/24/2025 |  | 10/20/2025 |
| `PreProcessingD` |  |  |  |
| `ProcessingD` |  |  |  |
| `Submitted D` | 10/20/2025 | 10/17/2025 | 10/17/2025 |
| `Underwriting D` | 10/27/2025 |  | 10/21/2025 |
| `ConditionReviewD` |  |  |  |
| `FinalUnderwritingD` |  |  |  |
| `Approved D` | 10/28/2025 |  | 10/22/2025 |
| `Estimated Closing D` | 2025-11-19 00:00:00 | 2025-11-16 00:00:00 | 2025-11-14 00:00:00 |
| `Clear To Close D` |  |  |  |
| `PreDocQCD` |  |  |  |
| `Docs D` |  |  |  |
| `DocsOrderedD` |  |  |  |
| `DocsDrawnD` |  |  |  |
| `DocsBackD` |  |  |  |
| `FundingConditionsD` |  |  |  |
| `Scheduled Funding D` |  |  |  |
| `Funded D` |  |  |  |
| `Loan Closed D` |  |  |  |
| `Recorded D` |  |  |  |
| `Purchase D` |  |  |  |
| `Loan Shipped D` |  |  |  |
| `Rate Lock D` |  |  | 10/30/2025 |
| `Rate Lock Expiration D` |  |  | 12/1/2025 |
| `Loan OnHold D` |  |  |  |
| `Loan Canceled D` |  |  | 12/30/2025 |
| `Loan Denied D` |  |  |  |
| `Loan Suspended D` |  |  |  |
| `Withdrawn D` |  |  |  |
| `DaysOpenToSubmitted` | 3 | 0 | 0 |
| `DaysSubmittedToApproved` | 8 |  | 5 |
| `DaysApprovedToCTC` |  |  |  |
| `DaysCTCToFunded` |  |  |  |
| `DaysTotalSubmitToFund` |  |  |  |
| `DaysTotalOpenToFund` |  |  |  |
| `LockDurationDays` |  |  | 32 |
| `DaysSubmittedToUW` | 7 |  | 4 |
| `DaysUWToApproved` | 1 |  | 1 |
| `DaysDocsToFunded` |  |  |  |
| `WasCanceled` | 0.0 | 0.0 | 1.0 |
| `WasDenied` | 0.0 | 0.0 | 0.0 |
| `WasSuspended` | 0.0 | 0.0 | 0.0 |
| `WasOnHold` | 0.0 | 0.0 | 0.0 |
| `WasWithdrawn` | 0.0 | 0.0 | 0.0 |
| `HasRateLock` | 0.0 | 0.0 | 1.0 |
| `WasApproved` | 1.0 | 0.0 | 1.0 |
| `ReachedCTC` | 0.0 | 0.0 | 0.0 |
| `SubmittedMonth` | 10 | 10 | 10 |
| `SubmittedYear` | 2025 | 2025 | 2025 |
| `SubmittedDayOfWeek` | 2 | 6 | 6 |
| `custLoan391` |  |  |  |
| `custLoan377` | 1.00% to 1.24% | 1.00% to 1.24% |  |
| `custLoan408` | 0.0 | 0.0 | 0.0 |
| `custLoan391ID` | 1.0 | 1.0 | 1.0 |
| `OnlyMon` | 0.0 | 0.0 | 0.0 |
| `TIL Disclosure / GFE Ordered Date` | 10/20/2025 |  | 11/14/2025 |
| `TIL Disclosure / GFE Due Date` | 12/20/2025 |  | 12/1/2025 |
| `TIL Disclosure / GFE Received Date` | 10/24/2025 |  | 11/4/2025 |
| `DidFund` | 0.0 | 0.0 | 0.0 |
| `Outcome` | Active | Active | Failed |
| `expected_funding` | 46444.7300771208 | 0.0 | 75947.4671669793 |
| `is_locked_flag` | False | False | True |
| `eliminated` | False | True | True |

---

## `dbo.moneyball_quadrant_summary`

**Rows:** 4  |  **Columns:** 8

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `quadrant` | nvarchar | 255 | YES |
| 2 | `loan_count` | float |  | YES |
| 3 | `total_value` | float |  | YES |
| 4 | `total_expected_value` | float |  | YES |
| 5 | `avg_probability` | float |  | YES |
| 6 | `snapshot_date` | datetime |  | YES |
| 7 | `movable_count` | float |  | YES |
| 8 | `total_loans_all_quadrants` | float |  | YES |

### Sample (TOP 3)

| quadrant | loan_count | total_value | total_expected_value | avg_probability | snapshot_date | movable_count | total_loans_all_quadrants |
| --- | --- | --- | --- | --- | --- | --- | --- |
| easy_win | 70.0 | 33964798.0 | 27670540.0 | 0.8041 | 2025-12-15 00:00:00 | 43.0 | 253.0 |
| stretch | 2.0 | 797500.0 | 345901.0 | 0.4317 | 2025-12-15 00:00:00 | 43.0 | 253.0 |
| quick_fix | 65.0 | 43102146.0 | 2405237.0 | 0.0601 | 2025-12-15 00:00:00 | 43.0 | 253.0 |

---

## `dbo.optimization_recommendations`

**Rows:** 6  |  **Columns:** 11

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `priority` | float |  | YES |
| 2 | `title` | nvarchar | 255 | YES |
| 3 | `description` | nvarchar | 255 | YES |
| 4 | `estimated_impact` | float |  | YES |
| 5 | `effort` | nvarchar | 255 | YES |
| 6 | `loan_count` | float |  | YES |
| 7 | `category` | nvarchar | 255 | YES |
| 8 | `urgency` | nvarchar | 255 | YES |
| 9 | `confidence_caveat` | nvarchar | 255 | YES |
| 10 | `snapshot_date` | datetime |  | YES |
| 11 | `_total_estimated_impact_all` | float |  | YES |

### Sample (TOP 3)

| priority | title | description | estimated_impact | effort | loan_count | category | urgency | confidence_caveat | snapshot_date | _total_estimated_impact_all |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | Secure rate locks on 3 unlocked late-stage loans | These loans have reached Approved or later without a rate lock. Unlocked late... | 0.0 | low | 3.0 | lock_management | immediate | Lock status correlates with funding but the relationship may not be fully cau... | 2025-12-15 00:00:00 | 7149296.0 |
| 2.0 | Rush CTC for 7 loans with locks expiring in 14 days | Rate locks expire before these loans reach Clear-to-Close. Each day of delay ... | 1202526.0 | medium | 7.0 | pipeline_acceleration | immediate |  | 2025-12-15 00:00:00 | 7149296.0 |
| 3.0 | Clear final conditions on 26 near-certain CTC+ loans | These 26 loans are at CTC or beyond with 80%+ ML probability â€” they represe... | 484313.0 | low | 26.0 | pipeline_acceleration | this_week |  | 2025-12-15 00:00:00 | 7149296.0 |

---

## `dbo.product_breakdown`

**Rows:** 10  |  **Columns:** 8

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Product Type` | nvarchar | 255 | YES |
| 2 | `loan_count` | float |  | YES |
| 3 | `total_value` | float |  | YES |
| 4 | `live_loans` | float |  | YES |
| 5 | `live_value` | float |  | YES |
| 6 | `projected_value` | float |  | YES |
| 7 | `avg_probability` | float |  | YES |
| 8 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| Product Type | loan_count | total_value | live_loans | live_value | projected_value | avg_probability | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NONCONFORMING | 439.0 | 142951460.0 | 401.0 | 116064514.0 | 23070178.0 | 0.3044 | 2025-12-15 00:00:00 |
| FHA | 79.0 | 19689354.0 | 59.0 | 11085209.0 | 3004382.0 | 0.3165 | 2025-12-15 00:00:00 |
| 2ND | 96.0 | 8906642.0 | 82.0 | 7685102.0 | 2507933.0 | 0.3179 | 2025-12-15 00:00:00 |

---

## `dbo.pull_through_monthly`

**Rows:** 206  |  **Columns:** 5

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `month` | nvarchar | 255 | YES |
| 2 | `Product Type` | nvarchar | 255 | YES |
| 3 | `pull_through_rate` | float |  | YES |
| 4 | `funded_count` | float |  | YES |
| 5 | `total_count` | float |  | YES |

### Sample (TOP 3)

| month | Product Type | pull_through_rate | funded_count | total_count |
| --- | --- | --- | --- | --- |
| 2024-01 | 2ND | 0.2632 | 10.0 | 38.0 |
| 2024-01 | CONFORMING | 0.2143 | 6.0 | 28.0 |
| 2024-01 | FHA | 0.1111 | 4.0 | 36.0 |

---

## `dbo.revenue_at_risk_buckets`

**Rows:** 5  |  **Columns:** 13

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `id` | nvarchar | 255 | YES |
| 2 | `label` | nvarchar | 255 | YES |
| 3 | `description` | nvarchar | 255 | YES |
| 4 | `action` | nvarchar | 255 | YES |
| 5 | `loan_count` | float |  | YES |
| 6 | `total_value` | float |  | YES |
| 7 | `expected_value` | float |  | YES |
| 8 | `value_at_risk` | float |  | YES |
| 9 | `avg_probability` | float |  | YES |
| 10 | `snapshot_date` | datetime |  | YES |
| 11 | `_total_at_risk` | float |  | YES |
| 12 | `_total_recovery_potential` | float |  | YES |
| 13 | `_live_pipeline_value` | float |  | YES |

### Sample (TOP 3)

| column | row1 | row2 | row3 |
| --- | --- | --- | --- |
| `id` | stalled_high_value | low_prob_high_val | lock_expiring |
| `label` | Stalled High-Value Loans | Low Probability, High Value | Rate Lock Expiring |
| `description` | Above-median loans sitting at the same stage for 30+ days | Top-quartile loan amounts with <25% funding probability | Loans with rate locks expiring within 7 days that haven't reached CTC |
| `action` | Priority escalation â€” clear conditions or re-engage borrower | Assess viability â€” re-engage or reallocate resources | Expedite underwriting or extend lock |
| `loan_count` | 97.0 | 47.0 | 7.0 |
| `total_value` | 85612468.0 | 66012600.0 | 3134000.0 |
| `expected_value` | 6328014.0 | 1903389.0 | 1672626.0 |
| `value_at_risk` | 79284454.0 | 64109211.0 | 1461374.0 |
| `avg_probability` | 0.0826 | 0.0205 | 0.5931 |
| `snapshot_date` | 2025-12-15 00:00:00 | 2025-12-15 00:00:00 | 2025-12-15 00:00:00 |
| `_total_at_risk` | 145297723.0 | 145297723.0 | 145297723.0 |
| `_total_recovery_potential` | 10405393.0 | 10405393.0 | 10405393.0 |
| `_live_pipeline_value` | 146986672.0 | 146986672.0 | 146986672.0 |

---

## `dbo.scorecards`

**Rows:** 12  |  **Columns:** 27

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `pull_through_rate` | float |  | YES |
| 2 | `pt_recent_3m` | float |  | YES |
| 3 | `pt_prior_3m` | float |  | YES |
| 4 | `pt_trend_delta` | float |  | YES |
| 5 | `pt_trend` | nvarchar | 255 | YES |
| 6 | `median_cycle_days` | float |  | YES |
| 7 | `avg_loan_amount` | float |  | YES |
| 8 | `funded_volume_6m` | float |  | YES |
| 9 | `pipeline_volume_6m` | float |  | YES |
| 10 | `revenue_efficiency` | float |  | YES |
| 11 | `current_active_loans` | float |  | YES |
| 12 | `current_projected_value` | float |  | YES |
| 13 | `avg_pipeline_probability` | float |  | YES |
| 14 | `efficiency_score` | float |  | YES |
| 15 | `composite_score` | float |  | YES |
| 16 | `name` | nvarchar | 255 | YES |
| 17 | `dimension` | nvarchar | 255 | YES |
| 18 | `industry_benchmark_pt` | float |  | YES |
| 19 | `industry_benchmark_cycle` | float |  | YES |
| 20 | `benchmark_note` | nvarchar | 255 | YES |
| 21 | `sub_pull_through` | float |  | YES |
| 22 | `sub_cycle_time` | float |  | YES |
| 23 | `sub_revenue_efficiency` | float |  | YES |
| 24 | `sub_trend` | float |  | YES |
| 25 | `sub_pipeline_probability` | float |  | YES |
| 26 | `rank` | float |  | YES |
| 27 | `tier` | nvarchar | 255 | YES |

### Sample (TOP 3)

| column | row1 | row2 | row3 |
| --- | --- | --- | --- |
| `pull_through_rate` | 0.276 | 0.2415 | 0.0299 |
| `pt_recent_3m` | 0.3388 | 0.309 | 0.0303 |
| `pt_prior_3m` | 0.2813 | 0.2145 | 0.0 |
| `pt_trend_delta` | 0.0575 | 0.0945 | 0.0303 |
| `pt_trend` | up | up | up |
| `median_cycle_days` | 34.0 | 28.0 | 30.5 |
| `avg_loan_amount` | 185527.0 | 478809.0 | 306981.0 |
| `funded_volume_6m` | 42299807.0 | 77006486.0 | 355960.0 |
| `pipeline_volume_6m` | 51038181.0 | 110065726.0 | 355960.0 |
| `revenue_efficiency` | 0.8288 | 0.6996 | 1.0 |
| `current_active_loans` | 82.0 | 43.0 | 1.0 |
| `current_projected_value` | 2507933.0 | 2402878.0 | 0.0 |
| `avg_pipeline_probability` | 0.3179 | 0.299 | 0.0172 |
| `efficiency_score` | 51213.0 | 115635.0 | 9164.0 |
| `composite_score` | 68.3 | 70.6 | 45.9 |
| `name` | 2ND | CONFORMING | CONVENTIONAL BOND |
| `dimension` | product | product | product |
| `industry_benchmark_pt` | 0.75 | 0.75 | 0.75 |
| `industry_benchmark_cycle` | 42.0 | 42.0 | 43.0 |
| `benchmark_note` | Industry 'closing rate' is measured from formal application on a 90-day cycle... | Industry 'closing rate' is measured from formal application on a 90-day cycle... | Industry 'closing rate' is measured from formal application on a 90-day cycle... |
| `sub_pull_through` | 55.2 | 48.3 | 6.0 |
| `sub_cycle_time` | 44.0 | 68.0 | 58.0 |
| `sub_revenue_efficiency` | 100.0 | 100.0 | 100.0 |
| `sub_trend` | 100.0 | 100.0 | 80.3 |
| `sub_pipeline_probability` | 53.0 | 49.8 | 2.9 |
| `rank` | 4.0 | 3.0 | 9.0 |
| `tier` | mid | mid | bottom |

---

## `dbo.stage_conversion_rates`

**Rows:** 42  |  **Columns:** 5

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Product Type` | nvarchar | 255 | YES |
| 2 | `stage` | nvarchar | 255 | YES |
| 3 | `reached_count` | float |  | YES |
| 4 | `funded_count` | float |  | YES |
| 5 | `conversion_rate` | float |  | YES |

### Sample (TOP 3)

| Product Type | stage | reached_count | funded_count | conversion_rate |
| --- | --- | --- | --- | --- |
| Overall | Submitted | 11227.0 | 5660.0 | 0.5041 |
| Overall | Underwriting | 8964.0 | 5492.0 | 0.6127 |
| Overall | Approved | 8194.0 | 5654.0 | 0.69 |

---

## `dbo.stage_funnel`

**Rows:** 12  |  **Columns:** 8

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `stage` | nvarchar | 255 | YES |
| 2 | `rank` | float |  | YES |
| 3 | `loan_count` | float |  | YES |
| 4 | `total_value` | float |  | YES |
| 5 | `live_loans` | float |  | YES |
| 6 | `live_value` | float |  | YES |
| 7 | `avg_probability` | float |  | YES |
| 8 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| stage | rank | loan_count | total_value | live_loans | live_value | avg_probability | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Opened | 0.0 | 342.0 | 110418830.0 | 57.0 | 0.0 | 0.0022 | 2025-12-15 00:00:00 |
| Application | 1.0 | 32.0 | 1306350.0 | 28.0 | 0.0 | 0.0653 | 2025-12-15 00:00:00 |
| Submitted | 2.0 | 96.0 | 5228065.0 | 79.0 | 0.0 | 0.0819 | 2025-12-15 00:00:00 |

---

## `dbo.summary_kpis`

**Rows:** 1  |  **Columns:** 22

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `snapshot_date` | datetime |  | YES |
| 2 | `month` | nvarchar | 255 | YES |
| 3 | `model_used` | nvarchar | 255 | YES |
| 4 | `total_pipeline_loans` | float |  | YES |
| 5 | `total_pipeline_value` | float |  | YES |
| 6 | `live_pipeline_loans` | float |  | YES |
| 7 | `live_pipeline_value` | float |  | YES |
| 8 | `dead_pipeline_loans` | float |  | YES |
| 9 | `dead_pipeline_value` | float |  | YES |
| 10 | `already_funded_loans` | float |  | YES |
| 11 | `already_funded_value` | float |  | YES |
| 12 | `projected_total` | float |  | YES |
| 13 | `overall_pull_through` | float |  | YES |
| 14 | `median_cycle_days` | float |  | YES |
| 15 | `elimination_total` | float |  | YES |
| 16 | `elimination_count` | float |  | YES |
| 17 | `elimination_pct` | float |  | YES |
| 18 | `elim_opened_stale` | float |  | YES |
| 19 | `elim_underwriting_unlocked_stale` | float |  | YES |
| 20 | `elim_approved_expired_lock` | float |  | YES |
| 21 | `elim_submitted_unlocked_stale` | float |  | YES |
| 22 | `elim_application_stale` | float |  | YES |

### Sample (TOP 3)

| column | row1 |
| --- | --- |
| `snapshot_date` | 2025-12-15 00:00:00 |
| `month` | 2025-12 |
| `model_used` | GradientBoosting |
| `total_pipeline_loans` | 1109.0 |
| `total_pipeline_value` | 314082997.0 |
| `live_pipeline_loans` | 708.0 |
| `live_pipeline_value` | 146986672.0 |
| `dead_pipeline_loans` | 401.0 |
| `dead_pipeline_value` | 167096325.0 |
| `already_funded_loans` | 156.0 |
| `already_funded_value` | 68191001.0 |
| `projected_total` | 100635340.82 |
| `overall_pull_through` | 0.3903 |
| `median_cycle_days` | 29.0 |
| `elimination_total` | 1109.0 |
| `elimination_count` | 401.0 |
| `elimination_pct` | 36.2 |
| `elim_opened_stale` | 285.0 |
| `elim_underwriting_unlocked_stale` | 52.0 |
| `elim_approved_expired_lock` | 43.0 |
| `elim_submitted_unlocked_stale` | 17.0 |
| `elim_application_stale` | 4.0 |

---

## `dbo.velocity_by_stage`

**Rows:** 6  |  **Columns:** 10

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `stage` | nvarchar | 255 | YES |
| 2 | `loan_count` | float |  | YES |
| 3 | `avg_velocity` | float |  | YES |
| 4 | `median_velocity` | float |  | YES |
| 5 | `p25_velocity` | float |  | YES |
| 6 | `p75_velocity` | float |  | YES |
| 7 | `avg_days_at_stage` | float |  | YES |
| 8 | `avg_probability` | float |  | YES |
| 9 | `pct_stalled` | float |  | YES |
| 10 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| stage | loan_count | avg_velocity | median_velocity | p25_velocity | p75_velocity | avg_days_at_stage | avg_probability | pct_stalled | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Approved | 206.0 | 0.0723 | 0.0678 | 0.046 | 0.0976 | 63.0 | 0.1125 | 31.1 | 2025-12-15 00:00:00 |
| Cond Review | 9.0 | 0.0909 | 0.082 | 0.0495 | 0.1429 | 1.9 | 0.8763 | 33.3 | 2025-12-15 00:00:00 |
| Final UW | 7.0 | 0.137 | 0.1579 | 0.1111 | 0.1647 | 0.0 | 0.9044 | 0.0 | 2025-12-15 00:00:00 |

---

## `dbo.velocity_distribution`

**Rows:** 32  |  **Columns:** 7

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `Product Type` | nvarchar | 255 | YES |
| 2 | `band` | nvarchar | 255 | YES |
| 3 | `loan_count` | float |  | YES |
| 4 | `total_value` | float |  | YES |
| 5 | `expected_value` | float |  | YES |
| 6 | `avg_probability` | float |  | YES |
| 7 | `snapshot_date` | datetime |  | YES |

### Sample (TOP 3)

| Product Type | band | loan_count | total_value | expected_value | avg_probability | snapshot_date |
| --- | --- | --- | --- | --- | --- | --- |
| Overall | Fast Track | 1.0 | 381175.0 | 375133.0 | 0.9841 | 2025-12-15 00:00:00 |
| Overall | On Pace | 24.0 | 11792275.0 | 11069040.0 | 0.9269 | 2025-12-15 00:00:00 |
| Overall | Slow | 158.0 | 92426228.0 | 14806709.0 | 0.2021 | 2025-12-15 00:00:00 |

---

## `dbo.what_if_scenarios`

**Rows:** 4  |  **Columns:** 25

### Columns

| # | name | type | max_len | nullable |
| --- | --- | --- | --- | --- |
| 1 | `id` | nvarchar | 255 | YES |
| 2 | `lever` | nvarchar | 255 | YES |
| 3 | `description` | nvarchar | -1 | YES |
| 4 | `current_state` | nvarchar | 255 | YES |
| 5 | `target_state` | nvarchar | 255 | YES |
| 6 | `current_value` | float |  | YES |
| 7 | `improved_value` | float |  | YES |
| 8 | `delta` | float |  | YES |
| 9 | `pct_improvement` | float |  | YES |
| 10 | `affected_loans` | float |  | YES |
| 11 | `affected_value` | float |  | YES |
| 12 | `methodology` | nvarchar | 255 | YES |
| 13 | `confidence` | nvarchar | 255 | YES |
| 14 | `confidence_note` | nvarchar | 255 | YES |
| 15 | `caveats` | nvarchar | -1 | YES |
| 16 | `hist_retail_rate` | float |  | YES |
| 17 | `hist_wholesale_rate` | float |  | YES |
| 18 | `_totals_current_projected` | float |  | YES |
| 19 | `_totals_total_potential_delta` | float |  | YES |
| 20 | `_totals_adjusted_potential_delta` | float |  | YES |
| 21 | `_totals_overlap_discount` | float |  | YES |
| 22 | `_totals_total_upside_pct` | float |  | YES |
| 23 | `_totals_adjusted_upside_pct` | float |  | YES |
| 24 | `_totals_live_loans_count` | float |  | YES |
| 25 | `_totals_live_pipeline_value` | float |  | YES |

### Sample (TOP 3)

| column | row1 | row2 | row3 |
| --- | --- | --- | --- |
| `id` | reduce_appr_ctc | improve_lock_rate | reactivate_stale |
| `lever` | Accelerate Approved â†’ CTC | Lock Rate on Approved Loans | Reactivate Stale Pipeline |
| `description` | The Approvedâ†’CTC transition is the pipeline's longest and most variable sta... | Unlocked loans at the Approved stage have significantly lower ML-predicted fu... | Loans sitting 30+ days at the same mid-pipeline stage (Underwriting through C... |
| `current_state` | Median 18d Approvedâ†’CTC Â· 259 loans stalled >15d at Approved | 292 unlocked loans at Approved (avg prob 7%) vs 133 locked (avg prob 61%) | 178 loans stalled 30+ days at stages Underwritingâ€“CTC Â· avg prob 9% |
| `target_state` | Reduce median to 15d via weekly condition review cadence | Convert 40% of unlocked Approved loans to locked status | Re-engage 30% of stalled loans to restore pipeline-average probability |
| `current_value` | 12708249.0 | 3500763.0 | 8427060.0 |
| `improved_value` | 22465036.0 | 26122809.0 | 14224307.0 |
| `delta` | 9756787.0 | 22622046.0 | 5797247.0 |
| `pct_improvement` | 76.8 | 54.5 | 5.5 |
| `affected_loans` | 259.0 | 292.0 | 178.0 |
| `affected_value` | 121959841.0 | 103708999.0 | 104760171.0 |
| `methodology` | Historical funding-rate differential between <15d and â‰¤18d Aâ†’CTC cohorts,... | Probability gap between locked and unlocked loans at Approved stage (from ML ... | Probability gap between stalled loans and overall pipeline average, applied t... |
| `confidence` | medium | low | low |
| `confidence_note` | Historical correlation is strong but assumes operational changes can replicat... | Lock status is strongly correlated with funding but the relationship is likel... | Stale loans are often stale for cause â€” appraisal issues, borrower walkaway... |
| `caveats` | Loans that naturally clear conditions in <15d may have simpler profiles â€” n... | The probability gap (unlocked vs locked) likely reflects loan health rather t... | Industry re-engagement response rates are typically 5-15%, lower than the 30%... |
| `hist_retail_rate` |  |  |  |
| `hist_wholesale_rate` |  |  |  |
| `_totals_current_projected` | 32444340.0 | 32444340.0 | 32444340.0 |
| `_totals_total_potential_delta` | 38884123.0 | 38884123.0 | 38884123.0 |
| `_totals_adjusted_potential_delta` | 18664379.0 | 18664379.0 | 18664379.0 |
| `_totals_overlap_discount` | 0.48 | 0.48 | 0.48 |
| `_totals_total_upside_pct` | 119.8 | 119.8 | 119.8 |
| `_totals_adjusted_upside_pct` | 57.5 | 57.5 | 57.5 |
| `_totals_live_loans_count` | 708.0 | 708.0 | 708.0 |
| `_totals_live_pipeline_value` | 146986672.0 | 146986672.0 | 146986672.0 |
