#!/usr/bin/env python3
"""
Build outputs/flexpoint_dashboard.jsx with embedded data.

Reads dashboard_demo_data.json, pre-computes chart data (monthly pull-through,
cycle-time buckets), and writes a self-contained React component.
"""
import json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "outputs" / "dashboard_demo_data.json"
JSX_PATH  = ROOT / "outputs" / "flexpoint_dashboard.jsx"

# ── 1. Read & process data ──────────────────────────────────────────────────
with open(JSON_PATH) as f:
    raw = json.load(f)

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# Monthly overall pull-through
monthly = defaultdict(lambda: {"f": 0, "t": 0})
for r in raw["pull_through"]:
    monthly[r["month"]]["f"] += r["funded_count"]
    monthly[r["month"]]["t"] += r["total_count"]

pt_data, rates = [], []
sorted_months = sorted(monthly)
for i, m in enumerate(sorted_months):
    v = monthly[m]
    rate = round(v["f"] / v["t"] * 100, 1) if v["t"] else 0
    yr, mn = m.split("-")
    entry = {"month": f"{MONTHS[int(mn)-1]} \u2019{yr[2:]}", "rate": rate}
    if i == len(sorted_months) - 1:
        entry["partial"] = True  # Dec '25 is a partial-month snapshot
    pt_data.append(entry)
    rates.append(rate)
pt_avg = round(sum(rates) / len(rates), 1)

# Cycle-time histogram buckets
vals = raw["cycle_times"]["overall"]["values"]
buckets = [
    {"range": "0\u201315 days",  "count": sum(1 for v in vals if v <= 15),            "sla": False},
    {"range": "16\u201330 days", "count": sum(1 for v in vals if 16 <= v <= 30),       "sla": False},
    {"range": "31\u201345 days", "count": sum(1 for v in vals if 31 <= v <= 45),       "sla": False},
    {"range": "45+ days",        "count": sum(1 for v in vals if v > 45),              "sla": True},
]

# Process backtest accuracy sparkline labels
backtest = raw.get("backtest_accuracy", {})
for entry in backtest.get("recent_months", []):
    yr, mn = entry["month"].split("-")
    entry["label"] = f"{MONTHS[int(mn)-1]} '{yr[2:]}"

# Compact embedded object (no raw values arrays)
embedded = {
    "summary":          raw["summary"],
    "liveLoans":        [l for l in raw["loan_table"] if l["status"] == "live"],
    "deadLoans":        [l for l in raw["loan_table"] if l["status"] == "dead"],
    "ptChart":          pt_data,
    "ptAvg":            pt_avg,
    "cycleBuckets":     buckets,
    "cycleStats":       {k: v for k, v in raw["cycle_times"]["overall"].items() if k != "values"},
    "backtest":         backtest,
    "stageFunnel":      raw.get("stage_funnel", []),
    "channelSplit":     raw.get("channel_split", []),
    "productBreakdown": raw.get("product_breakdown", []),
    "atRiskLoans":      raw.get("at_risk_loans", []),
    "revenueAtRisk":    raw.get("revenue_at_risk", {}),
    "bottleneckDetection": raw.get("bottleneck_detection", {}),
    "velocityMomentum": raw.get("velocity_momentum", {}),
    "whatIfScenarios":  raw.get("what_if_scenarios", {}),
    "performanceScorecards": raw.get("performance_scorecards", {}),
    "optimizationRecommendations": raw.get("optimization_recommendations", {}),
    "moneyballMatrix":  raw.get("moneyball_matrix", {}),
}

data_js = json.dumps(embedded, indent=2)

# ── 2. Build JSX ────────────────────────────────────────────────────────────
IMPORTS = '''\
import React, { useState } from "react";
import {
  LineChart, BarChart, AreaChart, Line, Bar, Area,
  XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid, Cell
} from "recharts";
'''

# The component code is a plain string (no f-string) so {} are literal JSX.
COMPONENT = r'''
// ─── Formatting helpers ─────────────────────────────────────────────────────

const fmtM = (v) => {
  if (!v && v !== 0) return "$0";
  if (Math.abs(v) >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
  if (Math.abs(v) >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M";
  if (Math.abs(v) >= 1e3) return "$" + Math.round(v / 1e3).toLocaleString() + "K";
  return "$" + Math.round(v).toLocaleString();
};

const fmtK = (v) => {
  if (!v && v !== 0) return "$0";
  if (Math.abs(v) >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  if (Math.abs(v) >= 1e3) return "$" + Math.round(v / 1e3).toLocaleString() + "K";
  return "$" + Math.round(v).toLocaleString();
};

const probColor = (v) =>
  v > 0.7 ? "#3DAA7F" : v > 0.4 ? "#E8913A" : "#E85A5A";

const RULE_LABELS = {
  opened_stale: "Stale at Open (30+ days)",
  application_stale: "Stale at App (30+ days)",
  submitted_unlocked_stale: "Submitted, No Lock (22+ days)",
  underwriting_unlocked_stale: "UW, No Lock (22+ days)",
  approved_expired_lock: "Lock Expired at Approved",
};

// ─── StatCard ───────────────────────────────────────────────────────────────

function StatCard({ title, value, subtitle, color }) {
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <p
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "#9CA3AF",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          margin: 0,
        }}
      >
        {title}
      </p>
      <p
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: color || "#1A2332",
          margin: "8px 0 0",
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </p>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        {subtitle}
      </p>
    </div>
  );
}

// ─── Probability bar ────────────────────────────────────────────────────────

function ProbBar({ value }) {
  const pct = Math.round(value * 100);
  const color = probColor(value);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 100 }}>
      <div
        style={{
          width: 52,
          height: 6,
          borderRadius: 3,
          background: "#E5E7EB",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: pct + "%",
            height: "100%",
            borderRadius: 3,
            background: color,
          }}
        />
      </div>
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color,
          fontVariantNumeric: "tabular-nums",
          minWidth: 32,
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

// ─── Tooltip ────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label, suffix, formatter }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: "white",
        padding: "8px 14px",
        borderRadius: 8,
        boxShadow: "0 4px 12px rgba(0,0,0,0.10)",
        border: "1px solid #E5E7EB",
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, color: "#374151" }}>{label}</div>
      {payload.map((entry, i) => {
        const v = entry.value;
        const display = formatter ? formatter(v) : (typeof v === "number" ? v.toLocaleString() : v);
        return (
          <div key={i} style={{ color: entry.stroke || entry.fill || "#4A90D9", marginTop: 2 }}>
            {payload.length > 1 && <span style={{ fontWeight: 600 }}>{entry.name}: </span>}
            {display}
            {suffix || ""}
          </div>
        );
      })}
    </div>
  );
}

// ─── Loan Priority Table ────────────────────────────────────────────────────

function LoanTable() {
  const [tab, setTab] = useState("live");
  const [expanded, setExpanded] = useState(false);
  const VISIBLE_ROWS = 15;
  const allLoans = tab === "live" ? DATA.liveLoans : DATA.deadLoans;
  const loans = expanded ? allLoans : allLoans.slice(0, VISIBLE_ROWS);
  const hasMore = allLoans.length > VISIBLE_ROWS;
  const isDead = tab === "dead";

  const tabStyle = (key, activeColor) => ({
    padding: "14px 24px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    background: "transparent",
    border: "none",
    borderBottom: tab === key ? "2.5px solid " + activeColor : "2.5px solid transparent",
    color: tab === key ? activeColor : "#9CA3AF",
    transition: "all 0.15s ease",
  });

  const th = (label, extra) => (
    <th
      style={{
        padding: "11px 16px",
        fontSize: 10,
        fontWeight: 700,
        color: "#9CA3AF",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        whiteSpace: "nowrap",
        ...extra,
      }}
    >
      {label}
    </th>
  );

  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ border: "1px solid #E5E7EB", overflow: "hidden" }}
    >
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #E5E7EB" }}>
        <button style={tabStyle("live", "#E8913A")} onClick={() => { setTab("live"); setExpanded(false); }}>
          Live Pipeline ({DATA.liveLoans.length})
        </button>
        <button style={tabStyle("dead", "#E85A5A")} onClick={() => { setTab("dead"); setExpanded(false); }}>
          Eliminated ({DATA.deadLoans.length})
        </button>
      </div>

      {/* Callout */}
      <div
        style={{
          padding: "10px 24px",
          fontSize: 13,
          lineHeight: 1.5,
          background: isDead ? "#FEF2F2" : "#EFF6FF",
          color: isDead ? "#991B1B" : "#1E40AF",
          borderBottom: "1px solid " + (isDead ? "#FECACA" : "#DBEAFE"),
        }}
      >
        {isDead
          ? "These loans match historical dead-loan patterns (<2% funding rate). Removing them sharpens projections."
          : "Ranked by expected value \u2014 probability \u00d7 loan amount. Focus your team\u2019s effort top-down."}
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB", textAlign: "left" }}>
              {th("#", { width: 48 })}
              {th("Product")}
              {th("Stage")}
              {th("Days", { textAlign: "right" })}
              {th("Probability")}
              {th("Amount", { textAlign: "right" })}
              {th("Exp. Value", { textAlign: "right" })}
              {isDead && th("Elimination Rule")}
              {isDead && th("Archetype")}
            </tr>
          </thead>
          <tbody>
            {loans.map((loan, i) => (
              <tr
                key={loan.loan_guid}
                style={{
                  borderTop: "1px solid #F3F4F6",
                  background: isDead
                    ? "rgba(254,242,242,0.25)"
                    : i % 2 === 1
                    ? "#FAFBFC"
                    : "white",
                  opacity: isDead ? 0.72 : 1,
                  fontSize: 13,
                }}
              >
                <td style={{ padding: "10px 16px", color: "#D1D5DB", fontWeight: 600 }}>
                  {i + 1}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    fontWeight: 600,
                    color: isDead ? "#9CA3AF" : "#1A2332",
                  }}
                >
                  {loan.product_type || "\u2014"}
                </td>
                <td style={{ padding: "10px 16px", color: "#4B5563" }}>
                  {loan.current_stage}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontVariantNumeric: "tabular-nums",
                    color: "#4B5563",
                  }}
                >
                  {loan.days_at_stage}d
                </td>
                <td style={{ padding: "10px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <ProbBar value={loan.ml_probability} />
                    {!isDead && loan.ml_probability < 0.25 && (
                      <span title="Low probability, high expected value" style={{ color: "#E8913A", fontSize: 14, lineHeight: 1, cursor: "help" }}>{"\u26a0"}</span>
                    )}
                  </div>
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    fontVariantNumeric: "tabular-nums",
                    color: "#4B5563",
                  }}
                >
                  {fmtK(loan.loan_amount)}
                </td>
                <td
                  style={{
                    padding: "10px 16px",
                    textAlign: "right",
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    fontWeight: 700,
                    fontVariantNumeric: "tabular-nums",
                    color: isDead ? "#9CA3AF" : "#1A2332",
                  }}
                >
                  {fmtK(loan.expected_value)}
                </td>
                {isDead && (
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "#6B7280" }}>
                    {RULE_LABELS[loan.elimination_rule] || loan.elimination_rule || "\u2014"}
                  </td>
                )}
                {isDead && (
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "#6B7280" }}>
                    {loan.failure_archetype || "\u2014"}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Show all / collapse toggle */}
      {hasMore && (
        <div style={{ textAlign: "center", padding: "12px 0", borderTop: "1px solid #F3F4F6" }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: "none",
              border: "1px solid #D1D5DB",
              borderRadius: 6,
              padding: "6px 20px",
              fontSize: 12,
              fontWeight: 600,
              color: "#6B7280",
              cursor: "pointer",
            }}
          >
            {expanded ? "Collapse" : "Show all " + allLoans.length + " loans"}
          </button>
        </div>
      )}

      {/* Low-probability footnote (live tab only) */}
      {!isDead && allLoans.some((l) => l.ml_probability < 0.25) && (
        <div style={{ padding: "8px 24px 12px", fontSize: 11, color: "#9CA3AF" }}>
          {"\u26a0"} Low-probability, high-value loans &mdash; consider whether ops effort is justified despite large expected value.
        </div>
      )}
    </div>
  );
}

// ─── Pull-Through Chart ─────────────────────────────────────────────────────

function PTDot(props) {
  const { cx, cy, index, payload } = props;
  if (!cx || !cy) return null;
  if (payload && payload.partial) {
    // Hollow dashed circle for partial month
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill="white" stroke="#4A90D9" strokeWidth={2} strokeDasharray="3 2" />
        <text x={cx + 10} y={cy - 8} fontSize={9} fill="#9CA3AF" fontStyle="italic">Partial month</text>
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={2.5} fill="#4A90D9" strokeWidth={0} />;
}

function PullThroughChart() {
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Pull-Through Rate \u2014 Monthly Trend
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        Funded loans as % of active pipeline at month start
      </p>
      <div style={{ height: 280, marginTop: 20 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={DATA.ptChart} margin={{ top: 8, right: 60, bottom: 30, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              interval={2}
              angle={-40}
              textAnchor="end"
              height={55}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => v + "%"}
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              domain={[0, "dataMax + 5"]}
              width={48}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip suffix="%" />} />
            <ReferenceLine
              y={DATA.ptAvg}
              stroke="#D1D5DB"
              strokeDasharray="6 3"
              label={{
                value: "Avg " + DATA.ptAvg + "%",
                fill: "#9CA3AF",
                fontSize: 10,
                position: "insideTopRight",
              }}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#4A90D9"
              strokeWidth={2.5}
              dot={<PTDot />}
              activeDot={{ r: 5, stroke: "#4A90D9", strokeWidth: 2, fill: "white" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Cycle Time Chart ───────────────────────────────────────────────────────

function CycleTimeChart() {
  const cs = DATA.cycleStats;
  return (
    <div
      className="bg-white rounded-lg shadow-sm"
      style={{ padding: 24, border: "1px solid #E5E7EB" }}
    >
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Application to Funding \u2014 Cycle Times
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        <span style={{ color: "#E85A5A", fontWeight: 600 }}>{cs.above_sla_pct}%</span> of
        loans exceed 45-day SLA
      </p>
      <div style={{ height: 260, marginTop: 20 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={DATA.cycleBuckets}
            margin={{ top: 8, right: 16, bottom: 5, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
            <XAxis
              dataKey="range"
              tick={{ fontSize: 12, fill: "#6B7280" }}
              tickLine={false}
              axisLine={{ stroke: "#E5E7EB" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              width={50}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => v.toLocaleString()}
            />
            <Tooltip content={<ChartTooltip suffix=" loans" />} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={90}>
              {DATA.cycleBuckets.map((entry, i) => (
                <Cell key={i} fill={entry.sla ? "#E85A5A" : "#4A90D9"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginTop: 14,
          fontSize: 11,
          color: "#9CA3AF",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: 4,
            background: "#4A90D9",
            marginRight: 6,
          }}
        />
        Within SLA
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: 4,
            background: "#E85A5A",
            marginLeft: 20,
            marginRight: 6,
          }}
        />
        SLA Breach
        <span
          style={{
            marginLeft: "auto",
            display: "flex",
            gap: 20,
            fontWeight: 600,
            color: "#6B7280",
          }}
        >
          <span>Median: {cs.median}d</span>
          <span>P75: {cs.p75}d</span>
          <span>P90: {cs.p90}d</span>
        </span>
      </div>
    </div>
  );
}

// ─── Model Accuracy Card ───────────────────────────────────────────────────

function ModelAccuracyCard() {
  const b = DATA.backtest;
  if (!b || !b.mape_day15) return <StatCard title="Model Accuracy" value="N/A" subtitle="No backtest data" />;
  return (
    <div className="bg-white rounded-lg shadow-sm" style={{ padding: 24, border: "1px solid #E5E7EB" }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em", margin: 0 }}>
        Model Accuracy
      </p>
      <p style={{ fontSize: 28, fontWeight: 700, color: "#3DAA7F", margin: "8px 0 0", letterSpacing: "-0.02em" }}>
        {b.mape_day15}% MAPE
      </p>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
        {b.months_within_10pct}/{b.total_months} months within 10%
      </p>
      {b.recent_months && b.recent_months.length > 0 && (
        <div style={{ height: 56, marginTop: 10 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={b.recent_months} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
              <Area type="monotone" dataKey="actual" stroke="#D1D5DB" fill="#F3F4F6" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="projected" stroke="#3DAA7F" fill="rgba(61,170,127,0.1)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Pipeline Stage Funnel ─────────────────────────────────────────────────

function StageFunnel() {
  const data = DATA.stageFunnel || [];
  if (data.length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow-sm" style={{ padding: 24, border: "1px solid #E5E7EB" }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Pipeline Stage Distribution
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 16px" }}>
        Active loans by stage &mdash; identifies bottlenecks
      </p>
      <div style={{ height: Math.max(320, data.length * 32) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 90 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#9CA3AF" }} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="stage" tick={{ fontSize: 12, fill: "#4B5563" }} tickLine={false} axisLine={false} width={90} />
            <Tooltip content={<ChartTooltip suffix=" loans" />} />
            <Bar dataKey="total_loans" fill="#607D8B" radius={[0, 4, 4, 0]} barSize={16} name="Total" />
            <Bar dataKey="live_loans" fill="#4A90D9" radius={[0, 4, 4, 0]} barSize={16} name="Live" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: "flex", alignItems: "center", marginTop: 12, fontSize: 11, color: "#9CA3AF", gap: 16 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 4, background: "#607D8B" }} />
          Total (incl. eliminated)
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 4, background: "#4A90D9" }} />
          Live pipeline
        </span>
      </div>
    </div>
  );
}

// ─── Channel Split ─────────────────────────────────────────────────────────

function ChannelSplit() {
  const channels = DATA.channelSplit || [];
  if (channels.length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow-sm" style={{ padding: 24, border: "1px solid #E5E7EB" }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Channel Breakdown
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 16px" }}>
        Wholesale vs Retail pipeline
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(" + channels.length + ", 1fr)", gap: 14 }}>
        {channels.map((ch) => (
          <div key={ch.channel} style={{ padding: "18px 20px", borderRadius: 8, background: "#F9FAFB", border: "1px solid #E5E7EB" }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.04em", margin: 0 }}>{ch.channel || "Unknown"}</p>
            <p style={{ fontSize: 22, fontWeight: 700, color: "#E8913A", margin: "6px 0 4px" }}>
              {fmtM(ch.projected_value)}
            </p>
            <p style={{ fontSize: 12, color: "#6B7280", margin: 0 }}>
              from {fmtM(ch.live_value)} live &middot; {ch.live_loans} loans &middot; {(ch.avg_probability * 100).toFixed(0)}% avg
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Product Breakdown ─────────────────────────────────────────────────────

function ProductBreakdown() {
  const raw = DATA.productBreakdown || [];
  const data = raw.filter(p => p.projected_value > 0);
  if (data.length === 0) return null;
  return (
    <div className="bg-white rounded-lg shadow-sm" style={{ padding: 24, border: "1px solid #E5E7EB" }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
        Product Type Breakdown
      </h3>
      <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 16px" }}>
        Projected funding by product
      </p>
      <div style={{ height: Math.max(200, data.length * 36) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 110 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
            <XAxis type="number" tickFormatter={fmtM} tick={{ fontSize: 11, fill: "#9CA3AF" }} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="product" tick={{ fontSize: 12, fill: "#4B5563" }} tickLine={false} axisLine={false} width={110} />
            <Tooltip content={<ChartTooltip formatter={fmtM} />} />
            <Bar dataKey="projected_value" fill="#E8913A" radius={[0, 6, 6, 0]} barSize={20} name="Projected" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── At-Risk Watch List ────────────────────────────────────────────────────

function AtRiskTable() {
  const loans = DATA.atRiskLoans || [];
  if (loans.length === 0) return null;
  const [expanded, setExpanded] = useState(false);
  const VISIBLE = 10;
  const shown = expanded ? loans : loans.slice(0, VISIBLE);
  const hasMore = loans.length > VISIBLE;

  const riskColor = (reason) => {
    if (reason.includes("expires within")) return "#E85A5A";
    if (reason.includes("already expired")) return "#E85A5A";
    if (reason.includes("No rate lock")) return "#E8913A";
    if (reason.includes("Sitting at")) return "#E8913A";
    if (reason.includes("probability")) return "#9CA3AF";
    return "#6B7280";
  };

  return (
    <div className="bg-white rounded-lg shadow-sm" style={{ border: "1px solid #E5E7EB", overflow: "hidden" }}>
      <div style={{ padding: "16px 24px", borderBottom: "1px solid #E5E7EB" }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1A2332", margin: 0 }}>
          At-Risk Watch List
          <span style={{ fontSize: 13, fontWeight: 400, color: "#E85A5A", marginLeft: 8 }}>
            {loans.length} loans need attention
          </span>
        </h3>
        <p style={{ fontSize: 13, color: "#9CA3AF", margin: "4px 0 0" }}>
          Live loans with warning signs &mdash; could still fund but need ops intervention
        </p>
      </div>
      <div style={{ padding: "8px 24px", background: "#FEF2F2", fontSize: 12, color: "#991B1B", borderBottom: "1px solid #FECACA" }}>
        Total at-risk value: {fmtM(loans.reduce((s, l) => s + l.expected_value, 0))} expected &middot; {fmtM(loans.reduce((s, l) => s + l.loan_amount, 0))} pipeline
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB", textAlign: "left" }}>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em", width: 36 }}>#</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em" }}>Product</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em" }}>Stage</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em", textAlign: "right" }}>Days</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em" }}>Prob</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em", textAlign: "right" }}>Amount</th>
              <th style={{ padding: "11px 16px", fontSize: 10, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.06em" }}>Risk Reasons</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((loan, i) => (
              <tr key={loan.loan_guid || i} style={{ borderTop: "1px solid #F3F4F6", background: i % 2 === 1 ? "#FFFBF7" : "white", fontSize: 13 }}>
                <td style={{ padding: "10px 16px", color: "#D1D5DB", fontWeight: 600 }}>{i + 1}</td>
                <td style={{ padding: "10px 16px", fontWeight: 600, color: "#1A2332" }}>{loan.product_type || "\u2014"}</td>
                <td style={{ padding: "10px 16px", color: "#4B5563" }}>{loan.current_stage}</td>
                <td style={{ padding: "10px 16px", textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#4B5563" }}>{loan.days_at_stage}d</td>
                <td style={{ padding: "10px 16px" }}><ProbBar value={loan.ml_probability} /></td>
                <td style={{ padding: "10px 16px", textAlign: "right", fontFamily: "ui-monospace, monospace", fontSize: 12, fontVariantNumeric: "tabular-nums", color: "#4B5563" }}>{fmtK(loan.loan_amount)}</td>
                <td style={{ padding: "10px 16px" }}>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {loan.risk_reasons.map((reason, j) => {
                      const rc = riskColor(reason);
                      return (
                        <span key={j} style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600,
                          background: rc + "18",
                          color: rc,
                          border: "1px solid " + rc + "30",
                        }}>{reason}</span>
                      );
                    })}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasMore && (
        <div style={{ textAlign: "center", padding: "12px 0", borderTop: "1px solid #F3F4F6" }}>
          <button onClick={() => setExpanded(!expanded)} style={{
            background: "none", border: "1px solid #D1D5DB", borderRadius: 6,
            padding: "6px 20px", fontSize: 12, fontWeight: 600, color: "#6B7280", cursor: "pointer",
          }}>
            {expanded ? "Collapse" : "Show all " + loans.length + " at-risk loans"}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "watchlist", label: "Watch List" },
  { key: "trends", label: "Trends" },
];

export default function FlexPointDashboard() {
  const s = DATA.summary;
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F5F6F8",
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header
        style={{
          background: "#1A2332",
          padding: "20px 32px 0",
          boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            margin: "0 auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <h1
                style={{
                  fontSize: 21,
                  fontWeight: 700,
                  color: "white",
                  margin: 0,
                  letterSpacing: "-0.01em",
                }}
              >
                FlexPoint Funding Forecast
              </h1>
              <p style={{ fontSize: 13, color: "#8B95A5", margin: "3px 0 0" }}>
                Pipeline Intelligence &mdash; Gallus Insights
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 14, color: "#E5E7EB", fontWeight: 600, margin: 0 }}>
                December 2025
              </p>
              <p style={{ fontSize: 11, color: "#6B7280", margin: "3px 0 0" }}>
                Snapshot: {s.snapshot_date} &middot; Model: {s.model_used}
              </p>
            </div>
          </div>

          {/* ── Tab bar ──────────────────────────────────────────────────── */}
          <div style={{ display: "flex", gap: 0, marginTop: 16 }}>
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: "10px 24px",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  background: activeTab === tab.key ? "#F5F6F8" : "transparent",
                  border: "none",
                  borderRadius: activeTab === tab.key ? "8px 8px 0 0" : "0",
                  color: activeTab === tab.key ? "#1A2332" : "#8B95A5",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "28px 32px 16px" }}>

        {/* ── TAB: Overview ─────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div>
            {/* Summary cards — 5 columns */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 20,
              }}
            >
              <StatCard
                title="Total Pipeline"
                value={fmtM(s.total_pipeline_value)}
                subtitle={s.total_pipeline_loans.toLocaleString() + " active loans"}
              />
              <StatCard
                title="Live Pipeline"
                value={fmtM(s.live_pipeline_value)}
                subtitle={s.live_pipeline_loans.toLocaleString() + " loans passing filter"}
                color="#3DAA7F"
              />
              <StatCard
                title="Eliminated"
                value={fmtM(s.dead_pipeline_value)}
                subtitle={s.elimination_stats.pct_eliminated + "% of pipeline"}
                color="#E85A5A"
              />
              <StatCard
                title="Projected Funding"
                value={fmtM(s.projected_total)}
                subtitle={"Dec 2025 \u2014 " + fmtM(s.already_funded_value) + " already funded"}
                color="#E8913A"
              />
              <ModelAccuracyCard />
            </div>

            {/* Pipeline Stage Funnel */}
            <div style={{ marginTop: 24 }}>
              <StageFunnel />
            </div>

            {/* Channel + Product side by side */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>
              <ChannelSplit />
              <ProductBreakdown />
            </div>
          </div>
        )}

        {/* ── TAB: Watch List ──────────────────────────────────────────── */}
        {activeTab === "watchlist" && (
          <div>
            {/* At-Risk Watch List */}
            <AtRiskTable />

            {/* Loan table */}
            <div style={{ marginTop: 24 }}>
              <LoanTable />
            </div>
          </div>
        )}

        {/* ── TAB: Trends ──────────────────────────────────────────────── */}
        {activeTab === "trends" && (
          <div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 24,
              }}
            >
              <PullThroughChart />
              <CycleTimeChart />
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "#9CA3AF",
            padding: "28px 0 4px",
          }}
        >
          FlexPoint Funding Forecast &middot; Data as of {s.snapshot_date} &middot;{" "}
          {(s.overall_pull_through * 100).toFixed(1)}% historical pull-through &middot;
          Median cycle: {s.median_cycle_days} days
        </div>
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "#B0BEC5",
            padding: "0 0 16px",
          }}
        >
          A 1% pull-through improvement &asymp; $400K additional revenue per $1B funded volume
        </div>
      </div>
    </div>
  );
}
'''

# ── 3. Write JSX file ───────────────────────────────────────────────────────
with open(JSX_PATH, "w", encoding="utf-8") as f:
    f.write(IMPORTS)
    f.write("\n// Embedded data — generated from outputs/dashboard_demo_data.json\n")
    f.write("const DATA = ")
    f.write(data_js)
    f.write(";\n")
    f.write(COMPONENT)

size_kb = JSX_PATH.stat().st_size / 1024
print(f"Generated: {JSX_PATH}  ({size_kb:.0f} KB)")
print(f"  Live loans: {len(embedded['liveLoans'])}")
print(f"  Dead loans: {len(embedded['deadLoans'])}")
print(f"  Chart points: {len(pt_data)} months, {len(buckets)} buckets")
