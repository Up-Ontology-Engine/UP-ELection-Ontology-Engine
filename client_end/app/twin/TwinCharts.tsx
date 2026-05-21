"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell, Legend, RadarChart,
  PolarGrid, PolarAngleAxis, Radar
} from "recharts";
import type { BoothRow } from "@/lib/api";

interface Props {
  booths: BoothRow[];
  narrativeTypes: Record<string, number>;
}

const TOOLTIP_STYLE = {
  contentStyle: { background: "#111827", border: "1px solid #1e2d45", borderRadius: 8, color: "#f1f5f9", fontSize: 11 },
  labelStyle: { color: "#94a3b8" },
};

export default function TwinCharts({ booths, narrativeTypes }: Props) {
  // Lean distribution for pie
  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = b.digital_lean_label ?? "UNKNOWN";
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const pieData = Object.entries(leanDist).map(([name, value]) => ({ name, value }));
  const LEAN_COLORS: Record<string, string> = {
    STRONG_BJP: "#f97316", LEAN_BJP: "#fb923c",
    NEUTRAL: "#64748b", LEAN_OPP: "#60a5fa",
    STRONG_OPP: "#3b82f6", UNKNOWN: "#374151", INSUFFICIENT: "#374151",
  };

  // Issue frequency across booths
  const issueDist: Record<string, number> = {};
  booths.forEach((b) => { if (b.top_issue) issueDist[b.top_issue] = (issueDist[b.top_issue] ?? 0) + 1; });
  const issueData = Object.entries(issueDist)
    .sort((a, b) => b[1] - a[1]).slice(0, 8)
    .map(([issue, count]) => ({ issue: issue.replace(/_/g, " "), count }));

  // Confidence distribution
  const confDist: Record<string, number> = {};
  booths.forEach((b) => {
    const c = b.confidence_label ?? "UNKNOWN";
    confDist[c] = (confDist[c] ?? 0) + 1;
  });
  const confData = Object.entries(confDist).map(([name, value]) => ({ name, value }));
  const CONF_COLORS: Record<string, string> = { HIGH: "#10b981", MEDIUM: "#f59e0b", LOW: "#ef4444", UNKNOWN: "#475569" };

  // Narrative radar (use top 5 narrative types, score = booth count)
  const narrativeRadar = Object.entries(narrativeTypes)
    .slice(0, 6)
    .map(([type, count]) => ({ subject: type.replace(/_/g, " ").slice(0, 14), A: count }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Lean distribution pie */}
      <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Political Lean Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={75}
              label={(p) => `${((p.percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
              {pieData.map((d, i) => (
                <Cell key={i} fill={LEAN_COLORS[d.name] ?? "#94a3b8"} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 10, color: "#94a3b8" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Issue frequency */}
      <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Issue Frequency (# Booths)</h3>
        {issueData.length === 0 ? (
          <p className="text-sm" style={{ color: "#475569" }}>No issue data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={issueData} layout="vertical" barCategoryGap="10%">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
              <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="issue" type="category" tick={{ fill: "#94a3b8", fontSize: 9 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#f97316" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Confidence pie */}
      <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Data Confidence Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={confData} dataKey="value" cx="50%" cy="50%" outerRadius={75}
              label={(p) => `${String(p.name ?? "")} ${((p.percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
              {confData.map((d, i) => (
                <Cell key={i} fill={CONF_COLORS[d.name] ?? "#475569"} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Narrative radar */}
      {narrativeRadar.length > 0 && (
        <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <h3 className="text-sm font-semibold text-white mb-4">Narrative Intensity Radar</h3>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={narrativeRadar}>
              <PolarGrid stroke="#1e2d45" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 9 }} />
              <Radar name="Booths" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
              <Tooltip {...TOOLTIP_STYLE} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
