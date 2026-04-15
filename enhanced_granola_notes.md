# Predictive Model Project – Kickoff Call

Wed, 08 Apr 26 · mariana@gallusinsights.com, augiedelrio@gallusinsights.com, lcharvey@uchicago.edu, israel@gallusinsights.com

### Dashboard Enhancements Presented

- Added weekly actions section at top
  - 6 ranked recommendations with dollar estimates
  - Shows immediate recovery opportunities
  - Emphasizes actionable value for customers
- Enhanced watch list with probability scores
  - 59 flagged loans with risk explanations
  - Shows why loans identified as high-risk
  - Includes probability percentages for funding
- Live pipeline ranked by expected value
  - Organized from highest to lowest expected value
  - Shows funding probabilities for prioritization

### Suggestions/Changes Augie Wants in Detail

- Add actionable recommendations to risk identification
  - Example: “Take this action to increase probability from 16% to 34%”
  - Show specific steps to improve funding likelihood
  - Focus on real value through probability increases
- Create difficulty vs. probability matrix (Moneyball approach)
  - Y-axis: Probability to fund
  - X-axis: Difficulty to execute
  - Bubble size: Loan amount
  - Target upper-left quadrant (high probability, low effort)
  - Identify loans that can move quadrants with simple actions
- Industry standards integration needed
  - Research competitive benchmarks for stage transition times
  - VA loans at 20 days may be normal vs. FHA complexity
  - Add context for what constitutes good/bad performance
- Show variance alongside medians
  - Medians alone insufficient (Domino’s pizza analogy)
  - Need interquartile ranges or standard deviations
  - Prevent good median masking poor service variance
  - Apply across all metrics: conversion rates, cycle times, etc.
- Split all analytics by product type
  - Cannot analyze in aggregate
  - Different products have different normal timelines
  - Show totals for overview but detail by product essential

### Revenue at Risk Analysis ($145M Total)

- Stalled high value loans: $79M (97 loans)
  - Above median amounts, 30+ days same stage
  - Action: Priority escalation, clear conditions
- Low probability high value: $64M (47 loans)
  - Large loans <25% funding chance
  - Action: Viability check or stop ops investment
- Rate lock expiring: $1.5M (7 loans)
  - Locks expire within 7 days, not at CTC
  - Action: Expedite underwriting or extend locks
- No lock at late stage: $443K (3 loans)
  - Past approved without rate lock
  - Action: Contact borrower for lock

### What-If Scenarios ($40M Potential Upside)

- Rate lock improvement: $22M opportunity
  - 292 unlocked loans at approved (7% avg probability)
  - Locked loans same stage average 61%
  - Even 40% lock rate adds significant value
- Accelerate approved to CTC: $9.8M
  - Reduce bottleneck stage cycle time
  - Prevent lock expiration and borrower walkaway
- Reactivate stale pipeline: $5.8M
  - 178 loans sitting 30+ days same stage
  - Targeted reengagement campaign potential
- Retail channel optimization: $700K
  - Retail 5% vs wholesale 30% pull-through
  - Closing half the gap adds significant value

### Things to Research

- Industry standards for pipeline health metrics
  - Stage transition times by product type
  - Determine if VA 20-day approved to CTC acceptable
- Variance analysis implementation
  - Interquartile ranges vs standard deviations
  - Best practices for showing performance consistency
- Product-specific benchmarking
  - Split all conversion rates by loan type
  - Research competitive cycle time standards

### Use of AI and AI Agents

- Create Claude agent for 24/7 operational insights
  - Enterprise Claude access available through Gallus
  - Focus on actionable recommendations
  - Develop diagnosis methodology for mortgage operations
- Red team AI conclusions
  - Use Claude/ChatGPT to stress-test findings
  - Challenge recommendations with industry knowledge
  - Validate conclusions before implementation
- Multi-agent architecture consideration
  - Sub-agents for different processes
  - Sandbox approach to reduce hallucination risk
  - Chain agents for complex analysis workflows
- Maintain transparency alongside AI recommendations
  - Show underlying data supporting AI suggestions
  - Allow users to understand reasoning
  - Enable pushback on questionable recommendations

### Next Steps

- Mariana: Review all call recordings and create prioritized to-do list
- Mariana: Follow up with Ramito for ThoughtSpot access for Ajer and Liam
- Team: Implement difficulty vs probability matrix visualization
- Team: Add industry benchmarking research to pipeline health
- Team: Integrate variance metrics across all dashboards
- Team: Explore Claude agent development for summer project
- Augie: Provide Gallus email access and enterprise Claude tokens
- All: Tennis and dinner Monday 6-7pm at Quadrangle Club, then EBC

---

Chat with meeting transcript: https://notes.granola.ai/t/699b7308-af45-403d-98d4-fa63d544c1a9-00demib2