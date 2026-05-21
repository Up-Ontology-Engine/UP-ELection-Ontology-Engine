"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend
} from "recharts";
import type { BoothSummary } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";

interface Props { summary: BoothSummary }

export default function BoothDetailCharts({ summary }: Props) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  // Theme-driven chart colors — deterministic, not hardcoded to one mode
  const CHART_BG     = isDark ? "#0f1929" : "#ffffff";
  const CHART_BORDER = isDark ? "#1a2b44" : "#c0cfe0";
  const TICK_COLOR   = isDark ? "#94a3b8" : "#4a6280";
  const GRID_COLOR   = isDark ? "#1a2b44" : "#dde4ef";
  const LABEL_COLOR  = isDark ? "#f0f4fa" : "#0a1628";
  const MUTED_COLOR  = isDark ? "#4d6480" : "#7890a8";

  const TOOLTIP_STYLE = {
    contentStyle: {
      background: isDark ? "#111827" : "#ffffff",
      border: `1px solid ${CHART_BORDER}`,
      borderRadius: 8,
      color: LABEL_COLOR,
      fontSize: 12,
    },
    labelStyle: { color: TICK_COLOR },
  };

  // Historical results data
  const histData: Record<number, Record<string, number>> = {};
  summary.historical.full_history.forEach((h) => {
    if (!histData[h.election_year]) histData[h.election_year] = { year: h.election_year };
    if (h.vote_share != null) histData[h.election_year][h.party] = h.vote_share;
  });
  const histRows = Object.values(histData).sort((a, b) => a.year - b.year);

  // Parties in history
  const parties = [...new Set(summary.historical.full_history.map((h) => h.party))];
  const partyColors: Record<string, string> = {
    BJP: "#f97316", भाजपा: "#f97316",
    SP: "#10b981", BSP: "#3b82f6",
    INC: "#8b5cf6", Congress: "#8b5cf6",
  };
  const defaultColors = ["#94a3b8", "#f59e0b", "#ec4899"];

  // Pulse detail
  const pulseData = summary.digital_pulse.pulse_detail.map((p) => ({
    source: p.source,
    bjp: p.bjp_events,
    opp: p.opp_events,
    total: p.event_count,
    avg_polarity: p.avg_polarity,
  }));

  // Issue momentum
  const momentumData = Object.entries(summary.issue_momentum).map(([k, v]) => ({
    issue: k.replace(/_/g, " "),
    change: v,
  })).sort((a, b) => Math.abs(b.change) - Math.abs(a.change));

  const chartBox = {
    background: CHART_BG,
    border: `1px solid ${CHART_BORDER}`,
    borderRadius: 12,
    padding: 20,
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Historical vote shares */}
      <div style={chartBox}>
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>
          Historical Vote Share (%)
        </h3>
        {histRows.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-4)" }}>No historical data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={histRows} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis dataKey="year" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, color: TICK_COLOR }} />
              {parties.map((p, i) => (
                <Bar key={p} dataKey={p} fill={partyColors[p] ?? defaultColors[i % defaultColors.length]}
                  radius={[2, 2, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Digital pulse by source */}
      <div style={chartBox}>
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>
          Digital Pulse by Source
        </h3>
        {pulseData.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-4)" }}>No pulse events.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pulseData} layout="vertical" barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis type="number" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="source" type="category" tick={{ fill: TICK_COLOR, fontSize: 10 }} axisLine={false} tickLine={false} width={80} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, color: TICK_COLOR }} />
              <Bar dataKey="bjp" name="BJP" fill="#f97316" radius={[0, 2, 2, 0]} />
              <Bar dataKey="opp" name="Opp" fill="#3b82f6" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* BJP vote share trend */}
      {summary.historical.bjp_vote_shares.length >= 2 && (
        <div style={chartBox}>
          <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-1)" }}>
            BJP Vote Share Trend
          </h3>
          <p className="text-xs mb-4" style={{ color: MUTED_COLOR }}>
            Trend:{" "}
            <span style={{ color: summary.historical.trend === "declining" ? "#ef4444" : "#10b981" }}>
              {summary.historical.trend}
            </span>
          </p>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={summary.historical.bjp_vote_shares.map((v, i) => ({ idx: i + 1, share: v }))}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis dataKey="idx" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="share" stroke="#f97316" strokeWidth={2} dot={{ fill: "#f97316", r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Issue momentum */}
      {momentumData.length > 0 && (
        <div style={chartBox}>
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>
            Issue Momentum (% change)
          </h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={momentumData} layout="vertical" barCategoryGap="15%">
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis type="number" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="issue" type="category" tick={{ fill: TICK_COLOR, fontSize: 10 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="change" name="Momentum" fill="#8b5cf6" radius={[0, 2, 2, 0]} label={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
