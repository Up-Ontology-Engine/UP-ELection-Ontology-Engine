import { api } from "@/lib/api";
import type { BoothRow, BoothElectionRow } from "@/lib/api";
import DemographicsCharts from "./DemographicsCharts";
import Link from "next/link";
import { Users, TrendingUp, Shield, Activity, ChevronRight } from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

function pct(a: number, b: number, dec = 1) {
  return b > 0 ? `${((a / b) * 100).toFixed(dec)}%` : "—";
}

export default async function DemographicsPage() {
  const [boothsRes, electionRes, boothRowsRes] = await Promise.allSettled([
    api.booths(AC_ID),
    api.electionResults(AC_ID, 2022),
    api.boothElectionRows(AC_ID, 2022),
  ]);

  const booths     = boothsRes.status     === "fulfilled" ? boothsRes.value.booths       : [];
  const election   = electionRes.status   === "fulfilled" ? electionRes.value             : null;
  const boothRows  = boothRowsRes.status  === "fulfilled" ? boothRowsRes.value.rows       : [];

  // Aggregate voter stats
  const totalVoters  = booths.reduce((s, b) => s + (b.total_voters  ?? 0), 0);
  const totalMale    = booths.reduce((s, b) => s + (b.male_voters   ?? 0), 0);
  const totalFemale  = booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const genderRatio  = totalMale > 0 ? Math.round((totalFemale / totalMale) * 1000) : null;

  // Turnout
  const turnout = election?.turnout;
  const turnoutPct = turnout?.turnout_pct ?? null;

  // Lean distribution
  const leanCounts: Record<string, number> = {};
  booths.forEach((b) => {
    const l = b.digital_lean_label ?? "INSUFFICIENT";
    leanCounts[l] = (leanCounts[l] ?? 0) + 1;
  });
  const bjpTotal = (leanCounts["STRONG_BJP"] ?? 0) + (leanCounts["LEAN_BJP"] ?? 0);
  const oppTotal = (leanCounts["STRONG_OPP"] ?? 0) + (leanCounts["LEAN_OPP"] ?? 0);

  // BJP vote share from election results
  const bjpResult  = election?.results.find((r) => r.party === "BJP");
  const bjpVoteShare = bjpResult?.vote_share_pct ?? null;

  // Per-booth pivoted data for charts
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

  const boothMap: Record<number, BoothChartRow> = {};
  booths.forEach((b) => {
    boothMap[b.booth_number] = {
      booth_number: b.booth_number,
      male:   b.male_voters   ?? 0,
      female: b.female_voters ?? 0,
      total:  b.total_voters  ?? 0,
      bjp_share: 0, sp_share: 0, bsp_share: 0,
      turnout_pct: null,
      lean: b.digital_lean_label ?? "INSUFFICIENT",
      label: `B${b.booth_number}`,
    };
  });

  boothRows.forEach((r: BoothElectionRow) => {
    const entry = boothMap[r.booth_number];
    if (!entry) return;
    if (r.party === "BJP") entry.bjp_share = r.vote_share;
    if (r.party === "SP")  entry.sp_share  = r.vote_share;
    if (r.party === "BSP") entry.bsp_share = r.vote_share;
    if (r.turnout_percent != null) entry.turnout_pct = r.turnout_percent;
  });

  const boothChartData = Object.values(boothMap).sort((a, b) => a.booth_number - b.booth_number);

  // Segments
  const segments: { label: string; count: number; desc: string; color: string; sub: string }[] = [
    {
      label: "Women-Priority",
      count: booths.filter((b) => b.female_voters && b.male_voters && b.female_voters > b.male_voters).length,
      desc:  "Female voters exceed male",
      color: "#ec4899",
      sub:   `of ${booths.length} booths`,
    },
    {
      label: "Strong BJP",
      count: leanCounts["STRONG_BJP"] ?? 0,
      desc:  "BJP margin > 40 pts",
      color: "#f97316",
      sub:   `of ${booths.length} booths`,
    },
    {
      label: "Lean BJP",
      count: leanCounts["LEAN_BJP"] ?? 0,
      desc:  "BJP margin 15–40 pts",
      color: "#fb923c",
      sub:   `of ${booths.length} booths`,
    },
    {
      label: "High Confidence",
      count: booths.filter((b) => b.confidence_label?.toUpperCase() === "HIGH").length,
      desc:  "Signal confidence: HIGH",
      color: "#10b981",
      sub:   `of ${booths.length} booths`,
    },
    {
      label: "Avg Turnout > 60%",
      count: boothChartData.filter((b) => (b.turnout_pct ?? 0) > 60).length,
      desc:  "Turnout above 60%",
      color: "#3b82f6",
      sub:   `of ${booths.length} booths`,
    },
    {
      label: "Low Turnout < 50%",
      count: boothChartData.filter((b) => b.turnout_pct != null && b.turnout_pct < 50).length,
      desc:  "Turnout below 50%",
      color: "#ef4444",
      sub:   `of ${booths.length} booths`,
    },
  ];

  const CARD = "rounded-xl p-5";
  const BG   = { background: "#0a0e1a" };
  const SURF = { background: "#111827", border: "1px solid #1e2d45" };

  return (
    <div className="min-h-screen p-5" style={BG}>

      {/* ── Header ── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 text-xs mono mb-2" style={{ color: "#475569" }}>
            <span>Gorakhpur Urban AC</span>
            <ChevronRight size={10} />
            <span style={{ color: "#94a3b8" }}>Demographics</span>
          </div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-1.5 h-8 rounded-full" style={{ background: "linear-gradient(180deg,#10b981,#3b82f6)" }} />
            <div>
              <h1 className="text-xl font-bold text-white">Demographic Intelligence</h1>
              <p className="text-xs mt-0.5" style={{ color: "#475569" }}>
                Voter composition · 2022 Election Results · Booth Segmentation · Gorakhpur Urban AC-322
              </p>
            </div>
          </div>
        </div>
        <Link href="/booths"
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-all"
          style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.25)", color: "#f97316" }}>
          <Activity size={11} /> Booth Intelligence
        </Link>
      </div>

      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          {
            label: "Registered Voters",
            value: fmt(totalVoters),
            sub1:  `${fmt(totalMale)} male`,
            sub2:  `${fmt(totalFemale)} female`,
            icon:  Users,
            color: "#3b82f6",
            bar:   null,
          },
          {
            label: "Gender Ratio",
            value: genderRatio != null ? `${genderRatio}` : "—",
            sub1:  "females per 1,000 males",
            sub2:  `${pct(totalFemale, totalVoters)} female electorate`,
            icon:  Users,
            color: "#ec4899",
            bar:   genderRatio != null ? Math.min(100, (genderRatio / 1100) * 100) : null,
          },
          {
            label: "2022 Turnout",
            value: turnoutPct != null ? `${turnoutPct.toFixed(1)}%` : "—",
            sub1:  turnout ? `${fmt(turnout.total_votes)} votes cast` : "—",
            sub2:  turnout ? `of ${fmt(turnout.total_voters)} registered` : "—",
            icon:  TrendingUp,
            color: "#10b981",
            bar:   turnoutPct,
          },
          {
            label: "BJP Vote Share 2022",
            value: bjpVoteShare != null ? `${bjpVoteShare.toFixed(1)}%` : "—",
            sub1:  `${bjpTotal} of ${booths.length} booths BJP-leaning`,
            sub2:  `${oppTotal} opp-leaning · ${leanCounts["NEUTRAL"] ?? 0} neutral`,
            icon:  Shield,
            color: "#f97316",
            bar:   bjpVoteShare,
          },
        ].map(({ label, value, sub1, sub2, icon: Icon, color, bar }) => (
          <div key={label} className={CARD} style={SURF}>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: `${color}18` }}>
                <Icon size={13} style={{ color }} />
              </div>
              <span className="text-xs" style={{ color: "#64748b" }}>{label}</span>
            </div>
            <p className="text-2xl font-bold text-white mb-0.5">{value}</p>
            <p className="text-xs" style={{ color: "#94a3b8" }}>{sub1}</p>
            <p className="text-xs mt-0.5" style={{ color: "#475569" }}>{sub2}</p>
            {bar != null && (
              <div className="mt-3 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                <div className="h-1 rounded-full transition-all"
                  style={{ width: `${Math.min(100, bar)}%`, background: color }} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Segment Cards ── */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
        {segments.map((s) => (
          <div key={s.label} className="rounded-xl px-3.5 py-3"
            style={{ background: `${s.color}09`, border: `1px solid ${s.color}28` }}>
            <p className="text-2xl font-bold text-white">{s.count}</p>
            <p className="text-xs font-medium mt-0.5" style={{ color: s.color }}>{s.label}</p>
            <p className="text-xs mt-0.5" style={{ color: "#475569" }}>{s.desc}</p>
            <div className="mt-2 h-0.5 rounded-full" style={{ background: "#1e2d45" }}>
              <div className="h-0.5 rounded-full"
                style={{ width: `${booths.length > 0 ? (s.count / booths.length) * 100 : 0}%`, background: s.color }} />
            </div>
          </div>
        ))}
      </div>

      {/* ── Charts ── */}
      <DemographicsCharts
        booths={booths}
        boothChartData={boothChartData}
        electionResults={election?.results ?? []}
        totalMale={totalMale}
        totalFemale={totalFemale}
        leanCounts={leanCounts}
        turnoutPct={turnoutPct}
      />

      {/* ── Booth Table ── */}
      <div className="rounded-xl overflow-hidden mt-5" style={SURF}>
        <div className="px-5 py-3.5 flex items-center justify-between"
          style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
          <div className="flex items-center gap-2">
            <Activity size={13} style={{ color: "#10b981" }} />
            <h3 className="text-sm font-semibold text-white">Booth-Level Voter Composition — 2022</h3>
          </div>
          <span className="mono text-xs px-2 py-0.5 rounded"
            style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.2)", fontSize: 10 }}>
            {booths.length} BOOTHS
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
                {["#", "Name", "Total", "Male", "Female", "% Female", "BJP %", "SP %", "Turnout", "Lean"].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left font-semibold uppercase tracking-wider"
                    style={{ color: "#334155", fontSize: 10 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {boothChartData.map((b, i) => {
                const booth  = booths.find((x) => x.booth_number === b.booth_number);
                const fPct   = b.total > 0 ? (b.female / b.total * 100) : 0;
                const leanColor = b.lean.includes("STRONG_BJP") ? "#f97316"
                  : b.lean.includes("LEAN_BJP")   ? "#fb923c"
                  : b.lean.includes("STRONG_OPP") ? "#3b82f6"
                  : b.lean.includes("LEAN_OPP")   ? "#60a5fa"
                  : b.lean === "NEUTRAL"           ? "#64748b"
                  :                                  "#1e3a5f";
                return (
                  <tr key={b.booth_number}
                    style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4514" }}>
                    <td className="px-3 py-2 mono" style={{ color: "#334155" }}>{b.booth_number}</td>
                    <td className="px-3 py-2 text-white max-w-40 truncate font-medium">
                      {booth?.name ?? `Booth ${b.booth_number}`}
                    </td>
                    <td className="px-3 py-2 mono font-semibold" style={{ color: "#f1f5f9" }}>{fmt(b.total)}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-8 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                          <div className="h-1 rounded-full" style={{ width: `${b.total > 0 ? (b.male/b.total)*100 : 0}%`, background: "#3b82f6" }} />
                        </div>
                        <span className="mono" style={{ color: "#3b82f6" }}>{fmt(b.male)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-8 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                          <div className="h-1 rounded-full" style={{ width: `${fPct}%`, background: "#ec4899" }} />
                        </div>
                        <span className="mono" style={{ color: "#ec4899" }}>{fmt(b.female)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className="mono font-semibold"
                        style={{ color: fPct > 50 ? "#ec4899" : "#64748b" }}>
                        {fPct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-10 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                          <div className="h-1 rounded-full" style={{ width: `${b.bjp_share}%`, background: "#f97316" }} />
                        </div>
                        <span className="mono" style={{ color: "#f97316" }}>{b.bjp_share.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-10 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                          <div className="h-1 rounded-full" style={{ width: `${b.sp_share}%`, background: "#10b981" }} />
                        </div>
                        <span className="mono" style={{ color: "#10b981" }}>{b.sp_share.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-10 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                          <div className="h-1 rounded-full"
                            style={{ width: `${b.turnout_pct ?? 0}%`,
                              background: (b.turnout_pct ?? 0) > 60 ? "#10b981" : (b.turnout_pct ?? 0) > 50 ? "#f59e0b" : "#ef4444" }} />
                        </div>
                        <span className="mono" style={{ color: "#94a3b8" }}>
                          {b.turnout_pct != null ? `${b.turnout_pct.toFixed(1)}%` : "—"}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className="mono px-1.5 py-0.5 rounded"
                        style={{ background: `${leanColor}18`, color: leanColor, border: `1px solid ${leanColor}30`, fontSize: 9 }}>
                        {b.lean.replace("_", " ")}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
