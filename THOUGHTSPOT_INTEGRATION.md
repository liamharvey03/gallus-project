# ThoughtSpot Integration Research

## Overview

Augie wants us to build inside ThoughtSpot rather than standalone HTML dashboards. ThoughtSpot has an official MCP server that works directly with Claude Code, plus REST APIs and a Python SDK for programmatic data operations. This document outlines how to transfer our dashboard work into ThoughtSpot without disrupting what Gallus already has there.

## What ThoughtSpot Is

ThoughtSpot is a BI/analytics platform where users can search data using natural language, create interactive dashboards ("Liveboards"), and share insights. Gallus already uses it for their client-facing analytics. FlexPoint currently sees their data through ThoughtSpot.

## Integration Paths (3 options, ranked by feasibility)

### Option A: ThoughtSpot MCP Server (Recommended — easiest to start)

ThoughtSpot has an **official MCP server** that can be added to Claude Code. This lets us interact with ThoughtSpot directly from Claude Code sessions — query data, create answers, build Liveboards.

**Setup (DONE):**

MCP config is at `/Users/ajersher/Gallus-Proj/.mcp.json`:

```json
{
  "mcpServers": {
    "ThoughtSpot": {
      "command": "npx",
      "args": ["mcp-remote", "https://agent.thoughtspot.app/mcp"]
    }
  }
}
```

**Auth status:** OAuth flow completed successfully (Apr 15, 2026). Token cached in `~/.mcp-auth/`. If auth expires, clear with `rm -rf ~/.mcp-auth` and re-run `npx mcp-remote https://agent.thoughtspot.app/mcp` to re-authenticate.

**Instance URL:** `https://gallus.thoughtspot.cloud`

**Available MCP Tools:**

| Tool | What it does |
|---|---|
| `ping` | Test connectivity |
| `getDataSourceSuggestions` | Find relevant data models for a query |
| `getRelevantQuestions` | Break a user query into analytical sub-questions |
| `getAnswer` | Execute a question, get data + visualization |
| `createLiveboard` | Create a persistent Liveboard from answers |

**What we can do with it:**
1. Query FlexPoint's existing ThoughtSpot data to understand what's already there
2. Create new Liveboards that replicate our dashboard tabs
3. Build answers (visualizations) programmatically via natural language
4. Ensure we don't overwrite or break existing content

**Limitations:**
- MCP tools are query/create focused — you can't push raw data through MCP
- The `createLiveboard` tool creates from existing answers, not from arbitrary JSON
- Custom visualizations (like our Moneyball bubble chart) may not be replicable in ThoughtSpot's native chart types

### Option B: REST API v2 + Python SDK (For data pipeline)

For pushing our model's predictions, scores, and computed metrics into ThoughtSpot as a data source.

**Setup:**

```bash
pip install thoughtspot-rest-api
```

**Authentication:**
```python
from thoughtspot_rest_api import TSRestApiV2

ts = TSRestApiV2(server_url="https://your-gallus-instance.thoughtspot.cloud")
ts.auth_session_login(username="ajer@gallusinsights.com", password="...")
# OR
ts.auth_token_full(username="ajer@gallusinsights.com", secret_key="...")
```

**Key capabilities:**
- **Import TML** (ThoughtSpot Modeling Language) — programmatically create worksheets, answers, liveboards
- **Export TML** — export existing objects to understand their structure
- **Metadata search** �� find existing liveboards, answers, data sources
- **Data API** — retrieve data from existing visualizations
- **Create/update objects** — liveboards, answers, worksheets

**Use case:** Push our `dashboard_demo_data.json` as a ThoughtSpot data source, then build Liveboards on top of it.

### Option C: TML (ThoughtSpot Modeling Language) Export/Import

TML is ThoughtSpot's YAML-based format for defining objects (worksheets, answers, liveboards) as code. We can:
1. Export existing Gallus ThoughtSpot objects to see their structure
2. Write new TML definitions for our analytics
3. Import them without touching existing content

**Python library:** `pip install thoughtspot_tml`

This is the safest approach for not breaking existing content — TML imports create new objects, they don't overwrite unless you explicitly specify.

## Recommended Integration Strategy

### Phase 1: Connect and Explore (low risk, do first)

1. Get Gallus email + ThoughtSpot access from Augie/Ramito
2. Add ThoughtSpot MCP server to Claude Code settings
3. Use `getDataSourceSuggestions` and `ping` to explore what data/models exist
4. Export existing Liveboards via REST API to understand the structure
5. Document what FlexPoint currently sees in ThoughtSpot

### Phase 2: Push Model Data (medium risk)

1. Create a new data source/worksheet in ThoughtSpot for our model predictions
2. Push `dashboard_demo_data.json` (or a subset) as a new table/connection
3. Options for data source:
   - **Direct database connection** — if Gallus uses a cloud DB (Snowflake, BigQuery, Redshift), we could write our predictions to a table there and ThoughtSpot would pick it up
   - **CSV upload** — simplest but manual; ThoughtSpot supports CSV data loads
   - **REST API data push** — programmatic but requires appropriate permissions

### Phase 3: Build Liveboards (creative work)

Map our 7 dashboard tabs to ThoughtSpot Liveboards:

| Our Tab | ThoughtSpot Liveboard | Feasibility |
|---|---|---|
| Overview | KPI tiles + funnel chart + bar charts | High ��� native ThoughtSpot |
| Watch List | Table visualization with filters | High |
| Revenue at Risk | KPI tiles + table | High |
| Pipeline Health | Heatmap may need custom viz; conversion bars are native | Medium |
| Trends | Line chart + bar chart | High |
| What-If | May need custom HTML embed or Spotter agent | Low-Medium |
| Scorecards | Table + KPI tiles | High |

**Challenges:**
- **Moneyball bubble chart** — ThoughtSpot's native scatter chart supports bubble size, but customization (quadrant lines, colors by category) may be limited
- **What-If scenarios** — interactive what-if analysis isn't native to ThoughtSpot; may need to embed as custom HTML or use Spotter agent
- **Counterfactual columns** — these are computed by our ML model, not from raw data. Need to pre-compute and push as data columns

### Phase 4: Spotter Agent Integration (advanced)

ThoughtSpot's Spotter is their AI analytics agent. With the MCP server's beta `createConversation` and `sendConversationMessage` tools, we could:
- Build a conversational interface where users ask questions about the pipeline
- Spotter would query ThoughtSpot data using natural language
- Combine with our model predictions for AI-driven recommendations

This aligns with Augie's vision of a "Claude agent working 24/7."

## What NOT to Do

- **Don't modify existing Liveboards** — FlexPoint already uses ThoughtSpot. Any changes to existing content could disrupt their workflow.
- **Don't replace the existing data model** — add our predictions alongside, don't restructure.
- **Don't skip the exploration phase** — we need to understand what's already there before building.
- **Don't assume ThoughtSpot can replicate everything** �� some of our custom visualizations (Moneyball matrix, counterfactual impact badges) may need to remain as an embedded HTML supplement.

## Prerequisites (Need from Augie/Ramito)

1. Gallus email addresses for Ajer and Liam (Augie said he'd do this)
2. ThoughtSpot user accounts with at least "Analyst" role
3. CORS whitelist update: add "agent.thoughtspot.app" to ThoughtSpot security settings
4. The ThoughtSpot instance URL (e.g., `gallus.thoughtspot.cloud`)
5. Understanding of what data model/worksheets FlexPoint currently uses
6. Permission to create new Liveboards and data sources (not modify existing)

## Current Status (Apr 15, 2026)

- MCP server config: DONE (`.mcp.json` in project root)
- OAuth authentication: DONE (token cached)
- Instance URL: `https://gallus.thoughtspot.cloud`
- ThoughtSpot MCP tools available: ping, getDataSourceSuggestions, getRelevantQuestions, getAnswer, createLiveboard

## Next Steps (Phase 1: Explore)

1. Use `ping` to verify MCP connection works
2. Use `getDataSourceSuggestions` to discover what data models exist for FlexPoint
3. Use `getAnswer` to query existing data and understand the schema
4. Document what FlexPoint currently sees in ThoughtSpot
5. Then proceed to Phase 2: push our model predictions as a new data source
