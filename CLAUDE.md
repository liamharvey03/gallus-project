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

### Feb 11, 2026 call — original directives:

1. **Add Product Type and Loan Purpose first** — "I guarantee you if we start by product and purpose, that's going to add a lot of value." Fannie/Freddie loans behave differently than FHA/government loans. Purchase loans close faster than refis.

2. **Focus on variables with explanatory power** — "I don't want to add too many variables because too many variables can add noise." Use the basketball/dunking analogy: height matters, food preferences don't.

3. **The pipeline stage is the foundation** — Historical probability of funding given current pipeline stage, stratified by product and purpose. This is the core of the model.

4. **Time-at-stage matters** — How long a loan has been sitting at its current stage affects probability. A loan at "Approved" for 5 days is different from one there for 45 days.

5. **Back-test against known outcomes** — "Take information as of December of last year, you should be able to predict January of this year. Then compare to actuals." This is the validation method.

6. **Don't introduce exogenous factors yet** — No interest rates, no macro. Keep it internal pipeline data for now.

7. **Run 3-5 models, compare** — Different methodologies, find highest predictive power.

8. **Don't over-engineer explainability yet** — Focus on accuracy first. Explanatory framework comes later.

### Apr 8, 2026 call — enhancement directives (all implemented):

9. **Actionable recommendations with probability deltas** — "If you take this action, you increase probability from 16% to 34%." Show specific steps to improve funding likelihood. → DONE: counterfactual scoring.

10. **Moneyball difficulty × probability matrix** — Y-axis: probability, X-axis: difficulty, bubble size: loan amount. Target upper-left quadrant. Identify loans that can move quadrants with simple actions. → DONE: Moneyball Matrix in Revenue at Risk tab.

11. **Industry standards / benchmarks** — Research competitive benchmarks for stage transition times. "Is VA at 20 days good or bad?" → DONE: ICE Mortgage Technology 2024 benchmarks in heatmap.

12. **Show variance alongside medians** — Domino's pizza analogy. Need IQR or std dev. "Competitive medians and low variances." → DONE: IQR throughout Pipeline Health.

13. **Split all analytics by product type** — "You cannot just look at it in aggregate." → DONE: product filter in Pipeline Health.

14. **Balanced scorecard** — Single composite number per product that can be tracked. → DONE: 0-100 composite in Scorecards.

15. **Red-team AI conclusions** — "Like the CIA... red team the hell out of them." Stress-test with industry knowledge. → DONE: confidence badges, caveats, overlap analysis.

16. **Build inside ThoughtSpot** — "It doesn't make sense for Ajer and Liam to be building anything outside of ThoughtSpot." → RESEARCHED: see `THOUGHTSPOT_INTEGRATION.md`. Pending Gallus access.

17. **Create a Claude agent** — "Working 24/7... actionable insights for mortgage operations." Multi-agent architecture. → NOT YET BUILT. Pending Gallus enterprise API access.

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
├── CLAUDE.md                     # This file — project context
├── config.py                     # Stage definitions, feature lists, constants
├── data/
│   └── sectG.csv                 # Raw loan data (15,272 loans × 152 cols)
├── src/
│   ├── data_prep.py              # Load, clean, parse dates, define targets
│   ├── pipeline_snapshot.py      # Reconstruct pipeline state at any date T
│   ├── eda.py                    # Correlation matrices, distribution analysis
│   ├── transition_tables.py      # Build P(fund | stage, product, purpose) tables
│   ├── feature_engineering_v3.py # v3 feature set (27 features: 15 v2 + 12 interactions)
│   ├── models.py                 # Train and compare models (GBM selected)
│   ├── backtest.py               # Monthly backtesting harness
│   ├── elimination_filter.py     # Dead-loan detection (5 conservative rules)
│   ├── generate_dashboard_data.py # Orchestrator: builds all 16 dashboard data sections
│   ├── build_dashboard_jsx.py    # Builds JSX + embeds data for dashboard HTML
│   └── patch_dashboard_whatif.py # What-if scenario patching utility
├── outputs/
│   ├── flexpoint_dashboard_v2.html  # Main dashboard (self-contained, 7 tabs, ~10K lines)
│   ├── dashboard_demo_data.json     # Generated data (16 sections)
│   ├── dashboardv2_script.pdf       # Speaker script for client presentation
│   ├── generate_script_pdf.py       # Script PDF generator
│   └── results/                     # Backtest CSVs, feature importance, etc.
├── THOUGHTSPOT_INTEGRATION.md       # ThoughtSpot integration research & strategy
└── requirements.txt
```

---

## 7. DEVELOPMENT STATUS

### Phase 1–4: COMPLETE
- Config, data prep, pipeline snapshot, transition tables — all built
- v3 feature engineering: 27 features (15 base + 12 lock/velocity interactions)
- GradientBoosting model selected (best Brier score), trained on 2024, tested on 2025
- Backtest: 5.8% MAPE across 24 months, 19/24 within 10%
- Elimination filter: 5 conservative rules, flags ~36% of pipeline as dead (<2% funding rate)

### Phase 5: Dashboard v2 — COMPLETE
The dashboard (`outputs/flexpoint_dashboard_v2.html`) is a self-contained dark-themed HTML file with embedded React, Recharts, and inline data. It has **7 tabs** powered by **16 data sections** generated by `src/generate_dashboard_data.py`.

**Dashboard tabs and their data sources:**

| Tab | Data Sections | What It Shows |
|---|---|---|
| Overview | summary, stage_funnel, channel_split, product_breakdown, backtest_accuracy, optimization_recommendations | KPI row, action recommendations (with confidence caveats), funnel, breakdowns |
| Watch List | at_risk_loans, loan_table | At-risk loans with **counterfactual actions + impact columns**, live/dead loan tables |
| Revenue at Risk | revenue_at_risk, moneyball_matrix | $145M at risk, **Moneyball bubble chart** (difficulty × probability), top 12 recovery opportunities with **counterfactual recommendations** |
| Pipeline Health | bottleneck_detection, velocity_momentum | Stage transition heatmap **with industry benchmarks + IQR variance**, **product filter dropdown**, conversion funnel, velocity bands, momentum alerts |
| Trends | pull_through, cycle_times | Monthly pull-through chart, cycle time distributions |
| What-If | what_if_scenarios | 4 operational levers, **overlap-adjusted totals ($18.7M realistic vs $38.9M raw)**, **confidence badges**, **caveats per scenario**, **red-team analysis footer** |
| Scorecards | performance_scorecards | Product/channel comparison, **composite score (0-100)**, efficiency rankings, trend analysis |

**Data generation pipeline:**
```
sectG.csv → data_prep → transition_tables → feature_engineering_v3 → models.train_and_select()
  → pipeline_snapshot (at 2025-12-15) → elimination_filter → 16 section builders
  → dashboard_demo_data.json → flexpoint_dashboard_v2.html (DATA re-embedded)
```

**To regenerate the dashboard data:**
```bash
/Users/ajersher/anaconda3/bin/python3 src/generate_dashboard_data.py
```
Note: After regenerating the JSON, the DATA object in `flexpoint_dashboard_v2.html` must be re-embedded (currently done manually or via agent — `build_dashboard_jsx.py` only generates the older 3-tab version).

### Phase 5.5: Dashboard v3 Enhancements — COMPLETE (Apr 14-15, 2026)

Seven enhancements from Augie's April 8 call directives:

1. **Counterfactual Probability Deltas** — Each at-risk and recovery loan shows "if you do X, probability goes from Y% to Z%, adding $N." Uses `_counterfactual_score()` helper that re-runs feature engineering + ML on modified raw columns. 49/59 at-risk loans have actionable recommendations. Top feature lever: rate lock (lock_expiry_vs_month_end, 0.678 importance).

2. **Moneyball Matrix** — Scatter/bubble chart (difficulty × probability, size = loan amount). 4 quadrants: easy_win, quick_fix, stretch, long_shot. 43 "movable" loans highlighted in gold (can shift quadrants with a single action). Placed in Revenue at Risk tab.

3. **Variance Metrics (IQR)** — p25-p75 ranges shown alongside all medians: heatmap cells, bottleneck pileup, velocity stage metrics. Addresses Augie's Domino's pizza analogy.

4. **Product-Level Splits** — Product filter dropdown in Pipeline Health tab. Conversion funnel, velocity distribution, and bottleneck pileup all filter by product. New data: `conversion_by_product`, `current_bottlenecks_by_product`, `distribution_by_product`.

5. **Balanced Composite Scorecard** — 0-100 weighted composite per product/channel: pull-through 30%, cycle time 20%, revenue efficiency 20%, trend 15%, pipeline probability 15%. Color-coded in Scorecards tab. Rankings sorted by composite.

6. **Industry Benchmarks** — "Industry" column in Pipeline Health heatmap showing ICE Mortgage Technology 2024 benchmarks with fast-slow ranges. Delta indicators per product cell (e.g., "-6.0d vs ind." in green). Key finding: FlexPoint is ~6 days faster than industry on Approved→CTC across all products. Sources documented with confidence levels in `config.py`.

7. **Red-Team Analysis** — What-If tab shows overlap-adjusted totals (52% measured overlap). Confidence badges (medium/low) on each scenario. "Assumptions & Caveats" section per card. Red-team footer in methodology section covering correlation-vs-causation and overlap. Recommendation caveats on lock and re-engagement actions.

### Phase 6: ThoughtSpot Integration — RESEARCHED (not yet built)

Full research at `THOUGHTSPOT_INTEGRATION.md`. Key findings:
- ThoughtSpot has an **official MCP server** (`https://agent.thoughtspot.app/mcp`) compatible with Claude Code
- MCP tools: ping, getDataSourceSuggestions, getRelevantQuestions, getAnswer, createLiveboard
- Python SDK: `pip install thoughtspot-rest-api` for programmatic data operations
- Integration strategy: 4 phases (explore → push data → build liveboards → Spotter agent)
- Prerequisites: Gallus email + ThoughtSpot access from Augie/Ramito, CORS whitelist update

### Potential Phase 7 features (not yet built):
- Early Warning Predictive Alerts (re-score loans at T+7/T+14, flag probability drops)
- Cohort Funnel Analysis (track loan cohorts through pipeline)
- Historical Pattern Intelligence (contextual benchmarking by loan profile)
- Monthly Narrative / Executive Summary (auto-generated plain-English report)
- Claude Agent for 24/7 operational insights (Augie's vision — multi-agent architecture)

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

1. **"Product and purpose matter"** — DONE. Scorecards tab proves NONCONFORMING is 40% pull-through vs VA at 34%. Bottleneck heatmap shows different cycle times by product. Augie was right.

2. **"The model is more accurate"** — DONE. 5.8% MAPE, 19/24 months within 10%. Oct 2025 was <0.1% error.

3. **"Here are the most important variables"** — DONE. Top feature: lock_expiry_vs_month_end (0.678 importance). Feature importance in `outputs/results/feature_importance_v3.csv`.

4. **"It works across time"** — DONE. Backtested Jan 2024–Dec 2025. Results in `outputs/results/backtest_results_v3.csv`.

5. **"Here's the projection"** — DONE. Overview tab: $100.6M projected, $68M already funded, wholesale/retail split, weekly breakdown.

6. **"Tell me what to DO about it"** — DONE. Optimization Recommendations at top of Overview: 6 ranked actions, $7.1M estimated impact. Revenue at Risk: $145M categorized with recovery actions. What-If: $18.7M realistic upside (overlap-adjusted).

7. **"If you do X, probability goes from 16% to 34%"** — DONE. Counterfactual scoring on 49/59 at-risk loans. Watch List shows Action + Impact columns. Revenue at Risk recovery table shows recommended action + probability delta.

8. **"Moneyball — pick up the easy chips first"** — DONE. Bubble scatter chart with difficulty × probability × loan amount. 4 quadrants, 43 movable loans highlighted in gold.

9. **"Show variance, not just medians"** — DONE. IQR (p25-p75) on heatmap cells, bottleneck pileup, velocity metrics.

10. **"Split everything by product"** — DONE. Product filter dropdown on Pipeline Health tab filters conversion funnel, velocity distribution, and bottleneck pileup.

11. **"Industry benchmarks — is VA at 20 days good or bad?"** — DONE. Industry column in heatmap (ICE Mortgage Technology 2024). FlexPoint is ~6d faster than industry on Approved→CTC.

12. **"Red-team the conclusions"** — DONE. Overlap-adjusted What-If totals, confidence badges, caveats per scenario, analytical footnotes.

13. **"Balanced scorecard — single number"** — DONE. Composite score (0-100) per product in Scorecards tab.

**Speaker script for the presentation:** `outputs/dashboardv2_script.pdf` — verbatim read-off script (may need updating to cover new features).
