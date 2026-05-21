"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, LineChart, Line, ReferenceLine, PieChart, Pie, Cell
} from "recharts";
import type { BoothRow } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";

interface Props {
  leanData: { name: string; value: number }[];
  issueData: { issue: string; count: number }[];
  booths: BoothRow[];
}

const LEAN_COLORS: Record<string, string> = {
  STRONG_BJP: "#f97316", LEAN_BJP: "#fb923c",
  NEUTRAL: "#94a3b8", LEAN_OPP: "#60a5fa", STRONG_OPP: "#3b82f6",
};

export default function DashboardCharts({ leanData, issueData, booths }: Props) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const TICK   = isDark ? "#4d6480" : "#7890a8";
  const GRID   = isDark ? "#1a2b44" : "#dde4ef";
  const T1     = isDark ? "#f0f4fa" : "#0a1628";
  const T3     = isDark ? "#4d6480" : "#4a6280";

  const TT = {
    contentStyle: {
      background: isDark ? "#0f1929" : "#ffffff",
      border: `1px solid ${isDark ? "#1a2b44" : "#c0cfe0"}`,
      borderRadius: 4, color: T1, fontSize: 11, padding: "6px 10px",
    },
    labelStyle: { color: T3, fontSize: 10 },
    itemStyle: { color: isDark ? "#8ba0bc" : "#4a6280" },
  };

  const LEAN_COLORS_THEMED: Record<string, string> = {
    ...LEAN_COLORS,
    NEUTRAL: isDark ? "#374151" : "#94a3b8",
    INSUFFICIENT: isDark ? "#1e2b3c" : "#c0cfe0",
  };

  const pulseData = booths
    .filter((b) => b.bjp_pulse_score != null && b.opp_pulse_score != null)
    .slice(0, 60)
    .map((b) => ({
      name: `B${b.booth_number}`,
      bjp: b.bjp_pulse_score!,
      opp: b.opp_pulse_score!,
    }));

  const voterBuckets = [
    { range: "<500",      count: booths.filter((b) => (b.total_voters ?? 0) < 500).length },
    { range: "500-800",   count: booths.filter((b) => (b.total_voters ?? 0) >= 500  && (b.total_voters ?? 0) < 800).length },
    { range: "800-1100",  count: booths.filter((b) => (b.total_voters ?? 0) >= 800  && (b.total_voters ?? 0) < 1100).length },
    { range: "1100-1400", count: booths.filter((b) => (b.total_voters ?? 0) >= 1100 && (b.total_voters ?? 0) < 1400).length },
    { range: ">1400",     count: booths.filter((b) => (b.total_voters ?? 0) >= 1400).length },
  ];

  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Issue frequency */}
      <div className="card p-4 col-span-2">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold" style={{ color: "var(--text-1)" }}>Issue Distribution Across Booths</p>
            <p className="text-xs" style={{ color: "var(--text-3)" }}>Booth count per primary issue</p>
          </div>
        </div>
        {issueData.length === 0 ? (
          <div className="flex items-center justify-center h-36 text-xs" style={{ color: "var(--text-3)" }}>No issue data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={issueData} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
              <XAxis dataKey="issue" tick={{ fill: TICK, fontSize: 9 }} axisLine={false} tickLine={false}
                interval={0} angle={-25} textAnchor="end" height={40} />
              <YAxis tick={{ fill: TICK, fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip {...TT} />
              <Bar dataKey="count" name="Booths" fill="#f97316" radius={[2, 2, 0, 0]}
                label={{ position: "top", fill: TICK, fontSize: 9 }} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Voter bucket distribution */}
      <div className="card p-4">
        <p className="text-xs font-semibold mb-0.5" style={{ color: "var(--text-1)" }}>Booth Size Distribution</p>
        <p className="text-xs mb-3" style={{ color: "var(--text-3)" }}>By voter count range</p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={voterBuckets} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
            <XAxis dataKey="range" tick={{ fill: TICK, fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: TICK, fontSize: 9 }} axisLine={false} tickLine={false} />
            <Tooltip {...TT} />
            <Bar dataKey="count" name="Booths" fill="#3b82f6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* BJP vs Opp pulse comparison */}
      <div className="card p-4 col-span-2">
        <p className="text-xs font-semibold mb-0.5" style={{ color: "var(--text-1)" }}>BJP vs Opposition Pulse — Booth Comparison</p>
        <p className="text-xs mb-3" style={{ color: "var(--text-3)" }}>Pulse scores across {pulseData.length} booths with data</p>
        {pulseData.length === 0 ? (
          <div className="flex items-center justify-center h-36 text-xs" style={{ color: "var(--text-3)" }}>No pulse data</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={pulseData}>
              <CartesianGrid strokeDasharray="2 4" stroke={GRID} />
              <XAxis dataKey="name" tick={{ fill: TICK, fontSize: 8 }} axisLine={false} tickLine={false}
                interval={Math.floor(pulseData.length / 8)} />
              <YAxis domain={[-1, 1]} tick={{ fill: TICK, fontSize: 9 }} axisLine={false} tickLine={false} />
              <ReferenceLine y={0} stroke={GRID} strokeDasharray="4 2" />
              <Tooltip {...TT} />
              <Line type="monotone" dataKey="bjp" name="BJP" stroke="#f97316" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="opp" name="Opp" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Lean pie */}
      <div className="card p-4">
        <p className="text-xs font-semibold mb-0.5" style={{ color: "var(--text-1)" }}>Lean Split</p>
        <p className="text-xs mb-2" style={{ color: "var(--text-3)" }}>All booths</p>
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie data={leanData} dataKey="value" cx="50%" cy="50%" outerRadius={60} innerRadius={30}
              label={(p) => (p.value ?? 0) > 0 ? `${p.value}` : ""} labelLine={false}>
              {leanData.map((d, i) => (
                <Cell key={i} fill={LEAN_COLORS_THEMED[d.name] ?? (isDark ? "#374151" : "#94a3b8")} stroke="none" />
              ))}
            </Pie>
            <Tooltip {...TT} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
