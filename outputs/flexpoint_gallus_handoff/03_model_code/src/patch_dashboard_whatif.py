#!/usr/bin/env python3
"""
Patch flexpoint_dashboard_v2.html to add the What-If Scenario Engine tab.

Steps:
1. Insert what_if_scenarios data into the DATA object
2. Add the WhatIfTab React component
3. Add "What-If" to TABS array
4. Add rendering line for the new tab
"""
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
HTML_PATH = PROJECT / "outputs" / "flexpoint_dashboard_v2.html"
DATA_PATH = PROJECT / "outputs" / "dashboard_demo_data.json"

# ── Load data ────────────────────────────────────────────────────────────────
with open(DATA_PATH) as f:
    data = json.load(f)

wi = data["what_if_scenarios"]
wi_json = json.dumps(wi, indent=2, ensure_ascii=False)

# ── Load HTML ────────────────────────────────────────────────────────────────
html = HTML_PATH.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Inject what_if data into the DATA object (before closing `};`)
# ─────────────────────────────────────────────────────────────────────────────
DATA_CLOSE = '};'

# Find the last occurrence of `};` that closes DATA (it's on its own line)
# We'll insert before the final `};` that ends the DATA block.
# The exact closing marker from the HTML is '};' on a line by itself right after
# the velocityMomentum section.
INSERT_MARKER = '  }\n};'

wi_block = f',\n  "whatIfScenarios": {wi_json}\n'

# Insert before the closing `};` of DATA
old_data_close = '  }\n};'
new_data_close = '  }' + wi_block + '};'

if old_data_close in html:
    html = html.replace(old_data_close, new_data_close, 1)
    print("✓ Injected whatIfScenarios into DATA object")
else:
    print("ERROR: Could not find DATA closing marker")
    print("Looking for:", repr(old_data_close))
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Add the WhatIfTab React component (before the Main Dashboard comment)
# ─────────────────────────────────────────────────────────────────────────────
WHATIF_COMPONENT = r"""
// ─── Tab: What-If Scenario Engine ─────────────────────────────────────────

function WhatIfTab() {
  const wi = DATA.whatIfScenarios;
  const scenarios = (wi && wi.scenarios) ? wi.scenarios : [];

  const scenarioColors = {
    reduce_appr_ctc:            { accent: "var(--blue)",   dim: "var(--blue-dim)" },
    improve_lock_rate:          { accent: "var(--copper)", dim: "var(--copper-glow)" },
    reactivate_stale:           { accent: "var(--red)",    dim: "var(--red-dim)" },
    retail_channel_optimization:{ accent: "var(--green)",  dim: "var(--green-dim)" },
  };

  const scenarioIcons = {
    reduce_appr_ctc:             "⟳",
    improve_lock_rate:           "◈",
    reactivate_stale:            "▲",
    retail_channel_optimization: "◑",
  };

  const totalDelta      = wi ? wi.total_potential_delta : 0;
  const currentProj     = wi ? wi.current_projected : 0;
  const upsidePct       = wi ? wi.total_upside_pct : 0;
  const livePipeline    = wi ? wi.live_pipeline_value : 0;

  return (
    <div>
      {/* Hero Banner */}
      <div className="fade-up" style={{
        marginBottom: 20,
        padding: "28px 32px",
        background: "linear-gradient(135deg, #151920 0%, #1a1f2e 100%)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 12,
        borderLeft: "3px solid var(--copper)",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Background glow */}
        <div style={{
          position: "absolute", top: -40, right: -40,
          width: 200, height: 200, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(212,149,106,0.06) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 24 }}>
          {/* Left: headline */}
          <div style={{ flex: 1 }}>
            <p style={{ fontFamily: "var(--font-sans)", fontSize: 10, fontWeight: 600, color: "var(--copper)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>
              What-If Scenario Engine
            </p>
            <h2 style={{ fontFamily: "var(--font-sans)", fontSize: 22, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: 6 }}>
              {fmtM(totalDelta)} in recoverable funding volume
            </h2>
            <p style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: 600 }}>
              Four operational levers — if pulled simultaneously — could add <strong style={{ color: "var(--copper)" }}>{upsidePct}%</strong> to
              the current projected month-end total. Each scenario is computed from historical pipeline data
              and the current active pipeline snapshot as of {DATA.summary.snapshot_date}.
            </p>
          </div>

          {/* Right: summary metrics */}
          <div style={{ display: "flex", gap: 12, flexShrink: 0 }}>
            <div style={{ padding: "16px 20px", background: "var(--bg-surface)", borderRadius: 8, border: "1px solid var(--border-subtle)", textAlign: "center", minWidth: 110 }}>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, color: "var(--copper)", letterSpacing: "-0.02em" }}>{fmtM(currentProj)}</p>
              <p style={{ fontFamily: "var(--font-sans)", fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>Current Projection</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", padding: "0 4px" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 20, color: "var(--text-muted)" }}>→</span>
            </div>
            <div style={{ padding: "16px 20px", background: "rgba(212,149,106,0.08)", borderRadius: 8, border: "1px solid rgba(212,149,106,0.25)", textAlign: "center", minWidth: 110 }}>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, color: "var(--copper)", letterSpacing: "-0.02em" }}>{fmtM(currentProj + totalDelta)}</p>
              <p style={{ fontFamily: "var(--font-sans)", fontSize: 10, color: "var(--copper-dim)", marginTop: 4 }}>If All Levers Pulled</p>
            </div>
          </div>
        </div>

        {/* Total potential bar */}
        <div style={{ marginTop: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--text-muted)" }}>
              Total potential upside across {scenarios.length} levers
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--copper)", fontWeight: 600 }}>
              +{upsidePct}% vs current projection
            </span>
          </div>
          <div style={{ height: 6, borderRadius: 3, background: "var(--bg-surface)", overflow: "hidden" }}>
            <div style={{
              height: "100%", borderRadius: 3,
              width: Math.min(100, upsidePct) + "%",
              background: "linear-gradient(90deg, var(--copper) 0%, #E8A87A 100%)",
              transition: "width 0.8s ease",
            }} />
          </div>
        </div>
      </div>

      {/* Scenario Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        {scenarios.map((s, i) => {
          const colors = scenarioColors[s.id] || { accent: "var(--copper)", dim: "var(--copper-glow)" };
          const icon = scenarioIcons[s.id] || "◆";
          const totalImpact = totalDelta > 0 ? (s.delta / totalDelta * 100) : 0;
          const currentPct = livePipeline > 0 ? (s.current_value / livePipeline * 100) : 0;
          const improvedPct = livePipeline > 0 ? (s.improved_value / livePipeline * 100) : 0;

          return (
            <div key={s.id} className="fade-up" style={{
              animationDelay: (i * 80) + "ms",
              padding: "22px 24px",
              background: "var(--bg-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 10,
              borderTop: "2px solid " + colors.accent,
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}>
              {/* Header */}
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span style={{
                      fontFamily: "var(--font-mono)", fontSize: 14,
                      color: colors.accent, width: 22, textAlign: "center",
                    }}>{icon}</span>
                    <h3 style={{ fontFamily: "var(--font-sans)", fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{s.lever}</h3>
                  </div>
                  <p style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.55 }}>{s.description}</p>
                </div>

                {/* Delta badge */}
                <div style={{
                  flexShrink: 0, textAlign: "right",
                  padding: "10px 14px",
                  background: colors.dim,
                  borderRadius: 8,
                  border: "1px solid " + colors.accent.replace(")", ", 0.3)").replace("var(", ""),
                  minWidth: 110,
                }}>
                  <p style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color: colors.accent, letterSpacing: "-0.02em" }}>
                    +{fmtM(s.delta)}
                  </p>
                  <p style={{ fontFamily: "var(--font-sans)", fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>potential upside</p>
                </div>
              </div>

              {/* Before / After */}
              <div style={{ background: "var(--bg-surface)", borderRadius: 8, padding: "14px 16px" }}>
                <div style={{ display: "flex", gap: 0, marginBottom: 10 }}>
                  <div style={{ flex: 1, paddingRight: 12, borderRight: "1px solid var(--border-subtle)" }}>
                    <p style={{ fontFamily: "var(--font-sans)", fontSize: 9, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Current State</p>
                    <p style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{s.current_state}</p>
                  </div>
                  <div style={{ flex: 1, paddingLeft: 12 }}>
                    <p style={{ fontFamily: "var(--font-sans)", fontSize: 9, fontWeight: 600, color: colors.accent, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Target State</p>
                    <p style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--text-primary)", lineHeight: 1.5 }}>{s.target_state}</p>
                  </div>
                </div>

                {/* Expected Value bar: before → after */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
                      {fmtM(s.current_value)} now
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: colors.accent }}>
                      {fmtM(s.improved_value)} projected
                    </span>
                  </div>
                  <div style={{ height: 8, borderRadius: 4, background: "var(--bg-card)", overflow: "hidden", position: "relative" }}>
                    {/* Current bar */}
                    <div style={{
                      position: "absolute", top: 0, left: 0,
                      width: Math.min(100, improvedPct) + "%",
                      height: "100%", borderRadius: 4,
                      background: colors.dim,
                    }} />
                    {/* Delta portion */}
                    <div style={{
                      position: "absolute", top: 0,
                      left: Math.min(100, currentPct) + "%",
                      width: Math.min(100 - currentPct, improvedPct - currentPct) + "%",
                      height: "100%",
                      background: colors.accent,
                      transition: "width 0.7s ease",
                    }} />
                  </div>
                </div>
              </div>

              {/* Bottom metadata row */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
                    {s.affected_loans.toLocaleString()} loans affected
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
                    {fmtM(s.affected_value)} in scope
                  </span>
                </div>
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
                  padding: "3px 8px", borderRadius: 4,
                  background: colors.dim,
                  color: colors.accent,
                }}>
                  {Math.round(totalImpact)}% of total upside
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Methodology Footer */}
      <div className="fade-up" style={{
        animationDelay: "360ms",
        padding: "18px 24px",
        background: "var(--bg-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 10,
      }}>
        <SectionTitle title="Methodology Notes" sub="How each scenario's impact estimate is calculated" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 4 }}>
          {scenarios.map((s) => (
            <div key={s.id + "_meth"} style={{
              padding: "10px 14px",
              background: "var(--bg-surface)",
              borderRadius: 6,
              borderLeft: "2px solid var(--border)",
            }}>
              <p style={{ fontFamily: "var(--font-sans)", fontSize: 11, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>{s.lever}</p>
              <p style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5 }}>{s.methodology}</p>
            </div>
          ))}
        </div>
        <p style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--text-muted)", marginTop: 14, lineHeight: 1.6, fontStyle: "italic" }}>
          All estimates are conservative and use actual historical loan data (Jan 2023–Dec 2025). Scenarios are additive
          only if the underlying borrower populations don't fully overlap. Actual recoverable volume may be higher or lower
          depending on market conditions and operational capacity.
        </p>
      </div>
    </div>
  );
}

"""

COMPONENT_INSERT_MARKER = "// ─── Main Dashboard ────────────────────────────────────────────────────────"

if COMPONENT_INSERT_MARKER in html:
    html = html.replace(COMPONENT_INSERT_MARKER, WHATIF_COMPONENT + COMPONENT_INSERT_MARKER)
    print("✓ Inserted WhatIfTab component")
else:
    print("ERROR: Could not find component insertion point")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Add "What-If" to TABS array
# ─────────────────────────────────────────────────────────────────────────────
OLD_TABS = """const TABS = [
  { key: "overview", label: "Overview" },
  { key: "watchlist", label: "Watch List" },
  { key: "revenue", label: "Revenue at Risk" },
  { key: "health", label: "Pipeline Health" },
  { key: "trends", label: "Trends" },
];"""

NEW_TABS = """const TABS = [
  { key: "overview", label: "Overview" },
  { key: "watchlist", label: "Watch List" },
  { key: "revenue", label: "Revenue at Risk" },
  { key: "health", label: "Pipeline Health" },
  { key: "trends", label: "Trends" },
  { key: "whatif", label: "What-If" },
];"""

if OLD_TABS in html:
    html = html.replace(OLD_TABS, NEW_TABS)
    print("✓ Added What-If to TABS array")
else:
    print("ERROR: Could not find TABS array")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Add rendering line for the new tab
# ─────────────────────────────────────────────────────────────────────────────
OLD_RENDER = """        {activeTab === "trends" && <TrendsTab />}

        {/* Footer */}"""

NEW_RENDER = """        {activeTab === "trends" && <TrendsTab />}
        {activeTab === "whatif" && <WhatIfTab />}

        {/* Footer */}"""

if OLD_RENDER in html:
    html = html.replace(OLD_RENDER, NEW_RENDER)
    print("✓ Added WhatIfTab render line")
else:
    print("ERROR: Could not find render insertion point")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Write out
# ─────────────────────────────────────────────────────────────────────────────
HTML_PATH.write_text(html, encoding="utf-8")
print(f"\n✓ Patched: {HTML_PATH}")
print(f"  File size: {HTML_PATH.stat().st_size:,} bytes")
