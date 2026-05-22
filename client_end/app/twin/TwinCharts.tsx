"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell, Legend, RadarChart,
  PolarGrid, PolarAngleAxis, Radar
} from "recharts";
import type { BoothRow } from "@/lib/api";
import { useChartColors } from "@/lib/chartTheme";

interface Props {
  booths: BoothRow[];
  narrativeTypes: Record<string, number>;
}

export default function TwinCharts({ booths, narrativeTypes }: Props) {
  const C = useChartColors();

  const TT = {
    contentStyle: { background: C.bgCard, border: `1px solid ${C.border}`, borderRadius: 8, color: C.t1, fontSize: 11 },
    labelStyle: { color: C.t3 },
    cursor: { fill: C.cursor },
  };

  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = b.digital_lean_label ?? "UNKNOWN";
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const pieData = Object.entries(leanDist).map(([name, value]) => ({ name, value }));
  const LEAN_COLORS: Record<string, string> = {
    STRONG_BJP: "#f97316", LEAN_BJP: "#fb923c",
    NEUTRAL: "#64748b", LEAN_OPP: "#60a5fa",
    STRONG_OPP: "#3b82f6", UNKNOWN: "#94a3b8", INSUFFICIENT: "#94a3b8",
  };

  const issueDist: Record<string, number> = {};
  booths.forEach((b) => { if (b.top_issue) issueDist[b.top_issue] = (issueDist[b.top_issue] ?? 0) + 1; });
  const issueData = Object.entries(issueDist)
    .sort((a, b) => b[1] - a[1]).slice(0, 8)
    .map(([issue, count]) => ({ issue: issue.replace(/_/g, " "), count }));

  const confDist: Record<string, number> = {};
  booths.forEach((b) => {
    const c = b.confidence_label ?? "UNKNOWN";
    confDist[c] = (confDist[c] ?? 0) + 1;
  });
  const confData = Object.entries(confDist).map(([name, value]) => ({ name, value }));
  const CONF_COLORS: Record<string, string> = { HIGH: "#10b981", MEDIUM: "#f59e0b", LOW: "#ef4444", UNKNOWN: "#64748b" };

  const narrativeRadar = Object.entries(narrativeTypes)
    .slice(0, 6)
    .map(([type, count]) => ({ subject: type.replace(/_/g, " ").slice(0, 14), A: count }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Lean distribution pie */}
      <div className="card rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>Political Lean Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={75}
              label={(p) => `${((p.percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
              {pieData.map((d, i) => (
                <Cell key={i} fill={LEAN_COLORS[d.name] ?? C.t3} />
              ))}
            </Pie>
            <Tooltip {...TT} />
            <Legend wrapperStyle={{ fontSize: 10, color: C.t3 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Issue frequency */}
      <div className="card rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>Issue Frequency (# Booths)</h3>
        {issueData.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-4)" }}>No issue data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={issueData} layout="vertical" barCategoryGap="10%">
              <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
              <XAxis type="number" tick={{ fill: C.t3, fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="issue" type="category" tick={{ fill: C.t3, fontSize: 9 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip {...TT} />
              <Bar dataKey="count" fill="#f97316" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Confidence pie */}
      <div className="card rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>Data Confidence Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={confData} dataKey="value" cx="50%" cy="50%" outerRadius={75}
              label={(p) => `${String(p.name ?? "")} ${((p.percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
              {confData.map((d, i) => (
                <Cell key={i} fill={CONF_COLORS[d.name] ?? C.t3} />
              ))}
            </Pie>
            <Tooltip {...TT} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Narrative radar */}
      {narrativeRadar.length > 0 && (
        <div className="card rounded-xl p-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-1)" }}>Narrative Intensity Radar</h3>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={narrativeRadar}>
              <PolarGrid stroke={C.border} />
              <PolarAngleAxis dataKey="subject" tick={{ fill: C.t3, fontSize: 9 }} />
              <Radar name="Booths" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
              <Tooltip {...TT} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
