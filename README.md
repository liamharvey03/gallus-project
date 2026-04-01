# FlexPoint Loan Funding Forecasting Model
## Master Context Document — For Claude Code / AI-Assisted Development

> **Use this file as persistent context when working on this project.**
> Paste it into Claude Code's CLAUDE.md, Cursor's .cursorrules, or any AI coding session.

---

## 1. WHAT WE'RE BUILDING

A **pipeline-based funding forecasting model** for FlexPoint, a mortgage company. The model predicts **how much dollar volume will fund by end of month** given the current state of the loan pipeline.

### The output looks like this (currently shown on ThoughtSpot):
```
February 2025 Projected Fundings: $118M
├── Already funded (Feb 1-11):     $38.6M
├── Projected remainder:           $79.4M
│   ├── Retail:                    $5.9M
│   └── Wholesale:                 $73.5M
└── Weekly breakdown:              [Week 1] [Week 2] [Week 3] [Week 4]
```

**This is a FORECASTING problem, not a classification problem.** We are not predicting "will this loan fund yes/no" in isolation. We are predicting aggregate dollar volume by scoring every active loan in the pipeline with a probability of funding within the time horizon, then summing `P(fund) × LoanAmount`.

### Why the previous attempt failed
The prior analysis built a classification model (Random Forest, AUC 0.99) on completed loans using features like `Rate Lock Status` and `DaysApprovedToCTC`. This is circular — those features only exist for loans that already progressed far enough, which is a proxy for the outcome. It answers "can I distinguish funded from canceled loans after the fact?" (yes, trivially) instead of "given the pipeline right now, what will fund this month?"

---

## 2. THE CLIENT'S DIRECTION (from Augie, the stakeholder)

From the Feb 11, 2026 call — these are direct instructions, not suggestions:

1. **Add Product Type and Loan Purpose first** — "I guarantee you if we start by product and purpose, that's going to add a lot of value." Fannie/Freddie loans behave differently than FHA/government loans. Purchase loans close faster than refis.

2. **Focus on variables with explanatory power** — "I don't want to add too many variables because too many variables can add noise." Use the basketball/dunking analogy: height matters, food preferences don't.

3. **The pipeline stage is the foundation** — Historical probability of funding given current pipeline stage, stratified by product and purpose. This is the core of the model.

4. **Time-at-stage matters** — How long a loan has been sitting at its current stage affects probability. A loan at "Approved" for 5 days is different from one there for 45 days.

5. **Back-test against known outcomes** — "Take information as of December of last year, you should be able to predict January of this year. Then compare to actuals." This is the validation method.

6. **Don't introduce exogenous factors yet** — No interest rates, no macro. Keep it internal pipeline data for now.

7. **Run 3-5 models, compare** — Different methodologies, find highest predictive power.

8. **Don't over-engineer explainability yet** — Focus on accuracy first. Explanatory framework comes later.

---

## 3. THE DATA

**Source:** `sectG.csv` — 15,272 loans × 152 columns, Jan 2023 – Jan 2026.

### 3.1 Target Definition
A loan is **funded** if it has a non-null `Funded D` date. The `IsFunded` column is misleading (only 79 flagged) — **5,661 loans actually funded** (statuses: Loan Sold, Funded, Loan Shipped, Recorded). ~824 loans are still in-progress.

### 3.2 Loan Outcomes
| Status | Count | % |
|---|---|---|
| Loan Cancelled | 7,490 | 49% |
| Loan Sold (funded) | 5,330 | 35% |
| Loan Denied | 651 | 4% |
| Loan Withdrawn | 459 | 3% |
| In-Progress (various) | 824 | 5% |
| Other funded (Shipped, Funded, Recorded) | 276 | 2% |

**Overall pull-through rate: ~37% (5,661 funded / 15,272 total)**

### 3.3 Pipeline Stages (ordered)
These are the milestone date columns representing the pipeline. Each loan has timestamps for stages it reached:

| # | Date Column | Stage Label | Coverage (funded) | Coverage (failed) |
|---|---|---|---|---|
| 0 | `Loan Open Date` | Opened | 100% | 100% |
| 1 | `Respa App D` | Application | 100% | 72% |
| 2 | `Submitted D` | Submitted | 100% | 63% |
| 3 | `Underwriting D` | Underwriting | 97% | 39% |
| 4 | `Approved D` | Approved | 100% | 29% |
| 5 | `ConditionReviewD` | Condition Review | 92% | 5% |
| 6 | `FinalUnderwritingD` | Final UW | 86% | 1% |
| 7 | `Clear To Close D` | CTC | 99% | 1% |
| 8 | `Docs D` | Docs | 99% | 0.3% |
| 9 | `DocsBackD` | Docs Back | 79% | 0% |
| 10 | `FundingConditionsD` | Funding Conditions | 93% | 0% |
| 11 | `Scheduled Funding D` | Sched Funding | 99% | 0.4% |
| 12 | `Funded D` | Funded | 100% | 0% |

**Key insight from coverage:** Failed loans almost never get past Approved. Once a loan reaches CTC or beyond, it almost always funds. The modeling value is in stages 2-7 (Submitted through CTC).

### 3.4 Key Feature Columns

**Augie's priority variables:**
- `Product Type` — NONCONFORMING (36%), FHA (12%), 2ND (10%), CONFORMING (9%), FHA BOND (4%), etc.
- `Loan Purpose` — Purchase (60%), Refinance CashOut (29%), Refinance (10%)
- `Branch Channel` — Wholesale (84%), Retail (16%). Use as feature, don't split.

**Other useful features:**
- `Loan Type` — Conventional (78%), FHA (18%), VA (2%)
- `Occupancy Type` — Primary (76%), Investment (23%), Secondary (1%)
- `LoanAmount` — mean $447K, median $350K, range $0–$11.3M
- `DecisionCreditScore` — mean 650, median 719 (many zeros dragging mean down)
- `NoteRate` — mean 6.83%, median 7.0%
- `LTV` — mean 64%, median 75%
- `Term` — almost all 360 months
- `Lock Period (days)`, `Rate Lock Status`
- `Property State` — geographic distribution

**Pre-computed duration columns (use for analysis, but derive your own from dates too):**
- `DaysOpenToSubmitted` — mean 0.6 days
- `DaysSubmittedToApproved` — mean 6.7 days (median 5)
- `DaysApprovedToCTC` — mean 22.1 days (median 18) ← **most variance here**
- `DaysCTCToFunded` — mean 6.0 days (median 5)
- `DaysTotalOpenToFund` — mean 35.1 days (median 29)

**Terminal event dates (for failure):**
- `Loan Canceled D`, `Loan Denied D`, `Withdrawn D`, `Loan Suspended D`

### 3.5 Observed Differences That Matter
| Dimension | Funded Rate | Notes |
|---|---|---|
| NONCONFORMING | 53% | Highest pull-through |
| VA | 34% | Lowest pull-through |
| Purchase | 42% | Closes faster |
| Refinance | 23% | Slowest |
| Wholesale | 42% | Bulk of volume |
| Retail | 10% | Very low pull-through |

### 3.6 Monthly Funding Volume
Ranges from ~$79M to ~$176M per month. Average ~$110M. The model needs to predict within this range.

---

## 4. THE MODELING APPROACH

### 4.1 Core Architecture: Pipeline Snapshot → Probability → Dollar Projection

```
For a given prediction date T and target month-end E:

1. RECONSTRUCT PIPELINE at date T
   - For each loan, find its current stage (latest milestone date ≤ T)
   - Exclude: already funded before T, canceled/denied/withdrawn before T
   - Include: "already funded this month" bucket (funded between month-start and T)

2. SCORE EACH ACTIVE LOAN
   a. Base probability: P(fund_by_E | current_stage, product_type, purpose)
      → From historical transition tables, stratified
   b. Time-at-stage adjustment: penalize loans sitting too long
      → Empirical: Approved→CTC takes median 18 days. At 40+ days, probability drops.
   c. ML refinement: adjust base probability using loan-level features
      → Credit score, LTV, loan amount, channel, occupancy, lock status, etc.
   d. Time-horizon adjustment: P(fund by month-end) depends on days remaining
      → A loan at CTC with 20 days left has higher P than with 3 days left

3. AGGREGATE
   Monthly_projection = Σ(already_funded_amount) + Σ(P_i × LoanAmount_i)
   Split by: retail/wholesale, weekly buckets
```

### 4.2 Pipeline Reconstruction Method

To determine a loan's stage at date T, walk backward through the stage columns:
```python
STAGE_MAP = [
    ('Funded D', 'Funded', 12),
    ('Scheduled Funding D', 'Sched Fund', 11),
    ('FundingConditionsD', 'Fund Cond', 10),
    ('DocsBackD', 'Docs Back', 9),
    ('Docs D', 'Docs', 8),
    ('Clear To Close D', 'CTC', 7),
    ('FinalUnderwritingD', 'Final UW', 6),
    ('ConditionReviewD', 'Cond Review', 5),
    ('Approved D', 'Approved', 4),
    ('Underwriting D', 'Underwriting', 3),
    ('Submitted D', 'Submitted', 2),
    ('Respa App D', 'Application', 1),
    ('Loan Open Date', 'Opened', 0),
]

def get_stage_at(row, as_of_date):
    """Return (stage_label, stage_rank) for the loan at as_of_date."""
    for col, label, rank in STAGE_MAP:
        dt = row[col + '_dt']
        if pd.notna(dt) and dt <= as_of_date:
            return label, rank
    return None, -1  # Not yet in pipeline
```

### 4.3 Proof of Concept (Already Validated)

Naive stage-probability model predicting Sep 2025 from a Sep 15 snapshot:
- **Projected: $146.5M**
- **Actual: $139.8M**
- **Error: 4.7%**

This is with ZERO product/purpose stratification, ZERO time-at-stage adjustment, ZERO ML refinement. The architecture works. Now we layer on sophistication.

### 4.4 Models to Build and Compare

1. **Stratified Transition Table** — P(fund | stage × product × purpose), no ML. Baseline.
2. **Logistic Regression** — Stage + product + purpose + time-at-stage + loan features. Interpretable.
3. **Gradient Boosting (XGBoost/LightGBM)** — Same features, nonlinear. Expected best performer.
4. **Survival/Hazard Model** — Model time-to-funding as a survival process. Natural fit for the "how long has it been sitting" question.
5. **Ensemble** — Blend of the above weighted by backtest performance.

### 4.5 Feature Engineering Priorities

**Tier 1 — Must have (Augie's directives):**
- Current pipeline stage (ordinal: 0-12)
- Product Type (categorical)
- Loan Purpose (categorical)
- Days at current stage (continuous — derived from milestone dates)

**Tier 2 — High expected value:**
- Branch Channel (Wholesale/Retail)
- Days remaining in month (continuous)
- LoanAmount (continuous)
- Rate Lock Status (binary — but watch for leakage, see Section 5)
- Lock Period (days)

**Tier 3 — Test for marginal value:**
- DecisionCreditScore
- LTV / CLTV
- NoteRate
- Occupancy Type
- Property State (may need to group into regions)
- Loan Type (partially redundant with Product Type)

### 4.6 Backtesting Protocol

For each month M in [Jan 2024, Feb 2024, ..., Dec 2025]:
1. Freeze pipeline at day 15 of month M (mid-month prediction)
2. Also freeze at day 1 (beginning of month — hardest) and day 22 (late month — easiest)
3. Predict total fundings for month M
4. Compare to actual fundings
5. Report: MAE, MAPE, directional accuracy, by-channel accuracy

The model should achieve **<10% MAPE at mid-month** across all test months. The naive POC already hits 4.7% at mid-month for one month.

---

## 5. KNOWN PITFALLS AND WATCHPOINTS

### 5.1 Data Leakage
- **Rate Lock Status** has a 0.6% vs 79.3% funding rate split. It's powerful but potentially leaky — loans get locked because they're progressing toward funding. It may be reflecting the outcome rather than predicting it. Discuss with Augie whether lock status is knowable at prediction time and whether it's a cause or effect.
- **Time-at-stage features for later stages** (e.g., `DaysCTCToFunded`) are inherently leaky when building a classifier on completed loans — they encode the outcome. Only use time-at-CURRENT-stage, not future stages.
- **Pipeline stage itself** when used on completed loans: a loan that reached "Funded" trivially predicts funding. The stage feature is only legitimate when scoring in-progress loans. For training, use stage-at-T (reconstructed snapshot), not final stage.

### 5.2 Feature Validity at Prediction Time
Every feature must pass the test: **"Would I know this value at the moment of prediction?"**
- ✅ Product Type — known at origination
- ✅ Loan Purpose — known at origination
- ✅ Current stage — knowable from pipeline
- ✅ Days at current stage — knowable
- ✅ Credit score, LTV, loan amount — known at origination
- ⚠️ Rate Lock Status — may change; check if it's a leading or lagging indicator
- ❌ DaysApprovedToCTC — only knowable after CTC, so not available for loans still at Approved
- ❌ Final loan status — this IS the target

### 5.3 Class Imbalance
At any pipeline snapshot, most active loans will NOT fund this month (they may fund next month, or fail). The positive rate varies by how far into the month you are. Handle with calibrated probabilities, not raw predictions.

### 5.4 Temporal Drift
Mortgage markets shift. 2023 volume and behavior may differ from 2025. Weight recent history more heavily or use rolling windows for transition probability tables.

### 5.5 Small Cell Sizes
When stratifying by stage × product × purpose, some cells will have very few loans. Use hierarchical smoothing: if a cell has <20 observations, blend with the parent (stage × product) or (stage × purpose) estimate.

---

## 6. PROJECT STRUCTURE

```
flexpoint-forecast/
├── CLAUDE.md                     # This file (symlink or copy of README.md)
├── config.py                     # Stage definitions, feature lists, constants
├── data/
│   └── sectG.csv                 # Raw loan data
├── src/
│   ├── data_prep.py              # Load, clean, parse dates, define targets
│   ├── pipeline_snapshot.py      # Reconstruct pipeline state at any date T
│   ├── eda.py                    # Correlation matrices, distribution analysis
│   ├── transition_tables.py      # Build P(fund | stage, product, purpose) tables
│   ├── feature_engineering.py    # Build ML feature set from snapshots
│   ├── models.py                 # Train and compare models
│   ├── backtest.py               # Monthly backtesting harness
│   └── scorer.py                 # Score active pipeline → monthly projection
├── outputs/
│   ├── figures/                  # EDA plots, backtest charts
│   └── results/                  # Backtest results, model comparison tables
└── requirements.txt
```

---

## 7. DEVELOPMENT SEQUENCE

### Phase 1: Foundation (Week 1)
- [ ] `config.py` — Constants and stage definitions
- [ ] `data_prep.py` — Load data, parse all dates, define funded/failed/active
- [ ] `pipeline_snapshot.py` — Reconstruct pipeline at any date T
- [ ] `transition_tables.py` — Build stratified P(fund | stage × product × purpose) tables
- [ ] Validate: reproduce the 4.7% POC result, then beat it with stratification

### Phase 2: EDA & Feature Selection (Week 1-2)
- [ ] `eda.py` — Correlation with funding outcome, by-segment analysis
- [ ] Time-at-stage distributions by outcome
- [ ] Identify top features, validate Augie's intuition with data
- [ ] Produce the "Augie was right" evidence (product/purpose add value)

### Phase 3: Model Training (Week 2-3)
- [ ] `feature_engineering.py` — Build snapshot-based training set
- [ ] `models.py` — Logistic, GBM, survival model, compare on held-out data
- [ ] Feature importance analysis
- [ ] Calibration — ensure predicted probabilities are well-calibrated

### Phase 4: Backtesting (Week 3)
- [ ] `backtest.py` — Monthly backtest harness across 2024-2025
- [ ] Measure MAPE at day 1, day 15, day 22 of each month
- [ ] Compare: naive stage-prob vs stratified vs ML-enhanced
- [ ] Produce backtest summary table for Augie

### Phase 5: Delivery (Week 4)
- [ ] `scorer.py` — Production scoring logic
- [ ] Documentation of model, features, and results
- [ ] Presentation-ready backtest results and recommendations

---

## 8. KEY CONSTANTS AND DEFINITIONS

```python
# Terminal funded statuses
FUNDED_STATUSES = ['Loan Sold', 'Funded', 'Loan Shipped', 'Recorded', 'Loan Archived']

# Terminal failed statuses
FAILED_STATUSES = ['Loan Cancelled', 'Loan Denied', 'Loan Withdrawn', 'Lead Cancelled']

# A loan is "funded" if Funded D is non-null (5,661 loans)
# A loan is "failed" if Loan Status in FAILED_STATUSES (8,842 loans)
# A loan is "active" if neither (824 loans)

# Stage ordering for pipeline reconstruction
STAGE_MAP = [
    ('Funded D',            'Funded',          12),
    ('Scheduled Funding D', 'Sched Fund',      11),
    ('FundingConditionsD',  'Fund Cond',       10),
    ('DocsBackD',           'Docs Back',        9),
    ('Docs D',              'Docs',             8),
    ('Clear To Close D',    'CTC',              7),
    ('FinalUnderwritingD',  'Final UW',         6),
    ('ConditionReviewD',    'Cond Review',      5),
    ('Approved D',          'Approved',         4),
    ('Underwriting D',      'Underwriting',     3),
    ('Submitted D',         'Submitted',        2),
    ('Respa App D',         'Application',      1),
    ('Loan Open Date',      'Opened',           0),
]

# Product type groupings (for thin-cell smoothing)
PRODUCT_GROUPS = {
    'CONV_CONF': ['CONFORMING', 'HOMEREADY', 'HOME POSSIBLE', 'CONVENTIONAL BOND', 'CONVENTIONAL BOND STD MI'],
    'CONV_NONCONF': ['NONCONFORMING'],
    'FHA': ['FHA', 'FHA BOND'],
    'VA': ['VA'],
    'OTHER': ['2ND', 'ZERO INTEREST PROGRAM', 'HELOC', 'HOME EQUITY', 'RURAL'],
}
```

---

## 9. WHAT SUCCESS LOOKS LIKE

For the Wednesday calls with Augie, Mariana, and Israel:

1. **"Product and purpose matter"** — Show stratified transition tables proving different funding rates and velocities by product and purpose. Augie guaranteed this; confirm it with data.

2. **"The model is more accurate"** — Backtest table showing month-by-month predictions vs actuals with MAPE <10% at mid-month, and demonstrably better than the current simple model.

3. **"Here are the most important variables"** — Ranked feature importance from the ML model, showing which variables actually move the needle and which are noise.

4. **"It works across time"** — Backtest stability — the model doesn't just work for one month, it generalizes across 2024-2025.

5. **"Here's the projection"** — Ability to score the current active pipeline and produce the same output format as the ThoughtSpot dashboard: total projected, already funded vs remaining, retail/wholesale split.
