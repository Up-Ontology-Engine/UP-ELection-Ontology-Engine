"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid
} from "recharts";

interface Props {
  boothData: { name: string; voters: number; male: number; female: number }[];
  localityRows: [string, number][];
  totalMale: number;
  totalFemale: number;
}

const TOOLTIP_STYLE = {
  contentStyle: { background: "#111827", border: "1px solid #1e2d45", borderRadius: 8, color: "#f1f5f9", fontSize: 11 },
  labelStyle: { color: "#94a3b8" },
};

export default function DemographicsCharts({ boothData, localityRows, totalMale, totalFemale }: Props) {
  const pieData = [
    { name: "Male", value: totalMale },
    { name: "Female", value: totalFemale },
  ];

  const localityData = localityRows.map(([loc, voters]) => ({ locality: loc.slice(0, 16), voters }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      {/* Gender pie */}
      <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Gender Distribution</h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}
              label={(p) => `${String(p.name ?? "")} ${((p.percent ?? 0) * 100).toFixed(1)}%`}
              labelLine={false}>
              <Cell fill="#3b82f6" />
              <Cell fill="#ec4899" />
            </Pie>
            <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
            <Tooltip {...TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Locality voters */}
      <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Voters by Locality (Top 10)</h3>
        {localityData.length === 0 ? (
          <p className="text-sm" style={{ color: "#475569" }}>No locality data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={localityData} layout="vertical" barCategoryGap="15%">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
              <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="locality" type="category" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="voters" fill="#10b981" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Top booths by voters */}
      <div className="rounded-xl p-5 md:col-span-2" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
        <h3 className="text-sm font-semibold text-white mb-4">Male vs Female Voters — Top 20 Booths by Size</h3>
        {boothData.length === 0 ? (
          <p className="text-sm" style={{ color: "#475569" }}>No booth data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={boothData} barCategoryGap="10%">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <Bar dataKey="male" name="Male" fill="#3b82f6" stackId="a" />
              <Bar dataKey="female" name="Female" fill="#ec4899" stackId="a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
