"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid,
  RadialBarChart, RadialBar, LabelList,
} from "recharts";
import type { BoothRow } from "@/lib/api";
import { useChartColors } from "@/lib/chartTheme";

type BoothChartRow = {
  booth_number: number;
  male: number;
  female: number;
  total: number;
  bjp_share: number;
  sp_share: number;
  bsp_share: number;
  turnout_pct: number | null;
  lean: string;
  label: string;
};

interface Props {
  booths: BoothRow[];
  boothChartData: BoothChartRow[];
  electionResults: { party: string; total_votes: number; vote_share_pct: number; booths_won: number }[];
  totalMale: number;
  totalFemale: number;
  leanCounts: Record<string, number>;
  turnoutPct: number | null;
}

const ACCENT = {
  bjp:    "#f97316",
  sp:     "#10b981",
  bsp:    "#3b82f6",
  inc:    "#a78bfa",
  male:   "#3b82f6",
  female: "#ec4899",
  green:  "#10b981",
  amber:  "#f59e0b",
  red:    "#ef4444",
  slate:  "#64748b",
};

const PARTY_COLORS: Record<string, string> = {
  BJP: ACCENT.bjp,
  SP:  ACCENT.sp,
  BSP: ACCENT.bsp,
  INC: ACCENT.inc,
};

function ChartCard({ title, sub, children, wide, C }: {
  title: string; sub?: string; children: React.ReactNode; wide?: boolean;
  C: { t3: string; t4: string; border: string; bgSurf: string; bgCard: string };
}) {
  return (
    <div className={`card rounded-xl overflow-hidden ${wide ? "md:col-span-2" : ""}`}>
      <div className="px-5 py-3.5" style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>{title}</p>
        {sub && <p className="text-xs mt-0.5" style={{ color: "var(--text-4)" }}>{sub}</p>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function DonutLabel({ cx, cy, label, sub, t1, t4 }: {
  cx: number; cy: number; label: string; sub: string; t1: string; t4: string;
}) {
  return (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle">
      <tspan x={cx} dy="-8" fontSize={18} fontWeight={700} fill={t1}>{label}</tspan>
      <tspan x={cx} dy="20" fontSize={11} fill={t4}>{sub}</tspan>
    </text>
  );
}

export default function DemographicsCharts({
  boothChartData,
  electionResults,
  totalMale,
  totalFemale,
  leanCounts,
}: Props) {
  const C = useChartColors();

  const TOOLTIP = {
    contentStyle: { background: C.bgCard, border: `1px solid ${C.border}`, borderRadius: 8, color: C.t1, fontSize: 11 },
    labelStyle: { color: C.t3 },
    cursor: { fill: C.cursor },
  };

  const LEAN_COLORS: Record<string, string> = {
    STRONG_BJP:   ACCENT.bjp,
    LEAN_BJP:     "#fb923c",
    NEUTRAL:      ACCENT.slate,
    LEAN_OPP:     "#60a5fa",
    STRONG_OPP:   ACCENT.bsp,
    INSUFFICIENT: C.border,
  };

  const totalVoters = totalMale + totalFemale;

  const genderData = [
    { name: "Male",   value: totalMale,   color: ACCENT.male   },
    { name: "Female", value: totalFemale, color: ACCENT.female },
  ];
  const femPct = totalVoters > 0 ? ((totalFemale / totalVoters) * 100).toFixed(1) : "—";

  const partyData = electionResults.map((r) => ({
    name:  r.party,
    value: r.vote_share_pct,
    color: PARTY_COLORS[r.party] ?? ACCENT.slate,
    votes: r.total_votes,
    booths_won: r.booths_won,
  }));
  const bjpShare = partyData.find((p) => p.name === "BJP")?.value ?? 0;

  const leanData = Object.entries(leanCounts)
    .map(([key, count]) => ({ name: key.replace(/_/g, " "), value: count, fill: LEAN_COLORS[key] ?? ACCENT.slate }))
    .sort((a, b) => b.value - a.value);

  const partyBarData = boothChartData.map((b) => ({
    label: b.label,
    BJP:   b.bjp_share,
    SP:    b.sp_share,
    BSP:   b.bsp_share,
    Other: Math.max(0, 100 - b.bjp_share - b.sp_share - b.bsp_share),
  }));

  const femaleBarData = [...boothChartData]
    .map((b) => ({
      label:     b.label,
      femalePct: b.total > 0 ? parseFloat(((b.female / b.total) * 100).toFixed(1)) : 0,
    }))
    .sort((a, b) => b.femalePct - a.femalePct);

  const turnoutData = boothChartData
    .filter((b) => b.turnout_pct != null)
    .map((b) => ({
      label:   b.label,
      turnout: parseFloat((b.turnout_pct ?? 0).toFixed(1)),
      fill:    (b.turnout_pct ?? 0) > 60 ? ACCENT.green : (b.turnout_pct ?? 0) > 50 ? ACCENT.amber : ACCENT.red,
    }));

  const gridStroke = C.border + "66";
  const cardProps = { C: { ...C, bgSurf: C.bgSurf, bgCard: C.bgCard } };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

      {/* 1 — Gender donut */}
      <ChartCard title="Gender Distribution" sub={`${femPct}% female electorate`} {...cardProps}>
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={genderData} dataKey="value" nameKey="name" cx="50%" cy="50%"
              innerRadius={68} outerRadius={95} paddingAngle={3}>
              {genderData.map((d) => <Cell key={d.name} fill={d.color} stroke="none" />)}
            </Pie>
            <DonutLabel cx={200} cy={120} label={`${femPct}%`} sub="female" t1={C.t1} t4={C.t4} />
            <Legend iconType="circle" iconSize={8}
              wrapperStyle={{ fontSize: 12, color: C.t3, paddingTop: 12 }}
              formatter={(val) => {
                const item = genderData.find((d) => d.name === val);
                return `${val} — ${item?.value.toLocaleString("en-IN")}`;
              }}
            />
            <Tooltip {...TOOLTIP} formatter={(v: unknown) => [(v as number).toLocaleString("en-IN"), "Voters"]} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 2 — Party vote share donut */}
      <ChartCard title="2022 Party Vote Shares" sub={`BJP dominant · ${bjpShare.toFixed(1)}% share`} {...cardProps}>
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={partyData} dataKey="value" nameKey="name" cx="50%" cy="50%"
              innerRadius={68} outerRadius={95} paddingAngle={3}>
              {partyData.map((d) => <Cell key={d.name} fill={d.color} stroke="none" />)}
            </Pie>
            <DonutLabel cx={200} cy={120} label={`${bjpShare.toFixed(0)}%`} sub="BJP" t1={C.t1} t4={C.t4} />
            <Legend iconType="circle" iconSize={8}
              wrapperStyle={{ fontSize: 12, color: C.t3, paddingTop: 12 }}
              formatter={(val) => {
                const d = partyData.find((p) => p.name === val);
                return `${val} — ${d?.value.toFixed(1)}% (${d?.booths_won ?? 0} booths)`;
              }}
            />
            <Tooltip {...TOOLTIP}
              formatter={(v: unknown, name: unknown) => {
                const d = partyData.find((p) => p.name === name);
                return [`${(v as number).toFixed(1)}% · ${d?.votes.toLocaleString("en-IN")} votes`, String(name)];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 3 — Lean distribution radial bars */}
      <ChartCard title="Political Lean Distribution"
        sub={`${Object.values(leanCounts).reduce((s, v) => s + v, 0)} total booths classified`} {...cardProps}>
        <ResponsiveContainer width="100%" height={240}>
          <RadialBarChart cx="50%" cy="50%" innerRadius={20} outerRadius={110}
            data={leanData.map((d) => ({ ...d, max: boothChartData.length }))}
            startAngle={180} endAngle={0}>
            <RadialBar dataKey="value" background={{ fill: C.border + "40" }} cornerRadius={4}>
              {leanData.map((d) => <Cell key={d.name} fill={d.fill} />)}
              <LabelList dataKey="value" position="insideStart" fill={C.t3} fontSize={10} />
            </RadialBar>
            <Legend iconType="circle" iconSize={8}
              wrapperStyle={{ fontSize: 11, color: C.t3, paddingTop: 8 }}
              formatter={(val) => {
                const d = leanData.find((x) => x.name === val);
                return `${val} (${d?.value ?? 0})`;
              }}
            />
            <Tooltip {...TOOLTIP} formatter={(v: unknown, name: unknown) => [`${v as number} booths`, String(name)]} />
          </RadialBarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 4 — Female % per booth */}
      <ChartCard title="Female Voter % by Booth" sub="Sorted high → low · 50% parity line" {...cardProps}>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={femaleBarData} layout="vertical" barCategoryGap="12%">
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} horizontal={false} />
            <XAxis type="number" domain={[40, 55]} tick={{ fill: C.t3, fontSize: 10 }}
              axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <YAxis dataKey="label" type="category" tick={{ fill: C.t4, fontSize: 9 }}
              axisLine={false} tickLine={false} width={28} />
            <Tooltip {...TOOLTIP} formatter={(v: unknown) => [`${v as number}%`, "Female %"]} />
            <Bar dataKey="femalePct" name="Female %" radius={[0, 3, 3, 0]}>
              {femaleBarData.map((d) => (
                <Cell key={d.label} fill={d.femalePct >= 50 ? ACCENT.female : "#9333ea"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 5 — BJP / SP / BSP stacked bar per booth */}
      <ChartCard title="Vote Share by Booth — 2022 Results"
        sub="BJP · SP · BSP stacked; all 30 booths" wide {...cardProps}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={partyBarData} barCategoryGap="6%" stackOffset="none">
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey="label" tick={{ fill: C.t4, fontSize: 8 }}
              axisLine={false} tickLine={false} interval={0} />
            <YAxis tick={{ fill: C.t3, fontSize: 10 }} axisLine={false} tickLine={false}
              tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
            <Tooltip {...TOOLTIP}
              formatter={(v: unknown, name: unknown) => [`${(v as number).toFixed(1)}%`, String(name)]} />
            <Legend iconType="square" iconSize={8}
              wrapperStyle={{ fontSize: 11, color: C.t3, paddingTop: 8 }} />
            <Bar dataKey="BJP"   stackId="a" fill={ACCENT.bjp}  radius={[0, 0, 0, 0]} />
            <Bar dataKey="SP"    stackId="a" fill={ACCENT.sp}   radius={[0, 0, 0, 0]} />
            <Bar dataKey="BSP"   stackId="a" fill={ACCENT.bsp}  radius={[0, 0, 0, 0]} />
            <Bar dataKey="Other" stackId="a" fill={C.t4}        radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 6 — Turnout per booth */}
      <ChartCard title="Turnout % by Booth — 2022"
        sub="Green > 60% · Amber 50–60% · Red < 50%" wide {...cardProps}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={turnoutData} barCategoryGap="6%">
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey="label" tick={{ fill: C.t4, fontSize: 8 }}
              axisLine={false} tickLine={false} interval={0} />
            <YAxis tick={{ fill: C.t3, fontSize: 10 }} axisLine={false} tickLine={false}
              tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
            <Tooltip {...TOOLTIP} formatter={(v: unknown) => [`${v as number}%`, "Turnout"]} />
            <Bar dataKey="turnout" radius={[3, 3, 0, 0]}>
              {turnoutData.map((d) => <Cell key={d.label} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

    </div>
  );
}
