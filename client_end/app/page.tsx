import { api } from "@/lib/api";
import Link from "next/link";
import {
  Users, MapPin, TrendingUp, Activity, Shield, Play,
  ArrowRight, Database, GitBranch, Target, Eye, Clock,
  AlertCircle, CheckCircle, Mic2, Zap
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

function pct(a: number, b: number) {
  return b > 0 ? `${((a / b) * 100).toFixed(1)}%` : "—";
}

export default async function DashboardPage() {
  const [boothsR, intelR, qualityR, electionR] = await Promise.allSettled([
    api.booths(AC_ID),
    api.intelSummary(AC_ID),
    api.quality(AC_ID),
    api.electionResults(AC_ID, 2022),
  ]);

  const booths   = boothsR.status    === "fulfilled" ? boothsR.value.booths   : [];
  const intel    = intelR.status     === "fulfilled" ? intelR.value            : null;
  const quality  = qualityR.status   === "fulfilled" ? qualityR.value          : null;
  const election = electionR.status  === "fulfilled" ? electionR.value         : null;

  const vs = intel?.voter_stats;
  const totalVoters  = vs?.total_voters  ?? booths.reduce((s, b) => s + (b.total_voters  ?? 0), 0);
  const maleVoters   = vs?.male_voters   ?? booths.reduce((s, b) => s + (b.male_voters   ?? 0), 0);
  const femaleVoters = vs?.female_voters ?? booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const boothCount   = vs?.total         ?? booths.length;

  const issues   = intel?.issues   ?? [];
  const videos   = intel?.videos   ?? [];
  const ytCount  = intel?.youtube_count ?? 0;
  const candidates = intel?.candidates ?? [];

  // Lean distribution from booths
  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = b.digital_lean_label ?? "INSUFFICIENT";
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const withPulse = booths.filter((b) => b.bjp_pulse_score != null).length;
  const bjpLean   = (leanDist["STRONG_BJP"] ?? 0) + (leanDist["LEAN_BJP"] ?? 0);
  const oppLean   = (leanDist["STRONG_OPP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);
  const maxIssueCount = issues[0]?.count ?? 1;

  const CARD = "rounded-xl p-4";
  const S = {
    base:    "var(--bg-base)",
    surface: "var(--bg-surface)",
    border:  "var(--border)",
    t1:      "var(--text-1)",
    t2:      "var(--text-2)",
    t3:      "var(--text-3)",
    t4:      "var(--text-4)",
    saffron: "var(--saffron)",
  };

  return (
    <div className="p-5 min-h-screen" style={{ background: S.base }}>

      {/* ── Title ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: "#10b981" }} />
            <h1 className="font-bold" style={{ color: S.t1, fontSize: 15 }}>
              Command Center — Gorakhpur Urban AC
            </h1>
          </div>
          <p className="text-xs mono" style={{ color: S.t4 }}>
            AC-322 · UP Vidhan Sabha · {boothCount} booths · {fmt(totalVoters)} registered voters
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs mono"
            style={{ border: `1px solid ${S.border}`, color: S.t4 }}>
            <Clock size={11} /> Live data
          </span>
          <Link href="/booths" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs"
            style={{ background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)", color: S.saffron }}>
            <Eye size={11} /> All Booths
          </Link>
        </div>
      </div>

      {/* ── KPI row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {[
          { label: "Total Voters",   value: fmt(totalVoters),    sub: `${fmt(maleVoters)}M / ${fmt(femaleVoters)}F`,   color: "#3b82f6",  icon: Users       },
          { label: "Active Booths",  value: boothCount,           sub: "in Knowledge Graph",                           color: "#10b981",  icon: MapPin      },
          { label: "YouTube Signals",value: fmt(ytCount),         sub: "videos analysed",                              color: S.saffron,  icon: Play        },
          { label: "Issues Tracked", value: issues.length,        sub: "from KG mentions",                             color: "#ef4444",  icon: Target      },
          { label: "Candidates",     value: candidates.length,    sub: "2022 election",                                color: "#8b5cf6",  icon: Mic2        },
          { label: "KG Coverage",    value: `${boothCount}/30`,   sub: withPulse > 0 ? `${withPulse} with pulse` : "voter data loaded", color: "#10b981", icon: GitBranch },
        ].map(({ label, value, sub, color, icon: Icon }) => (
          <div key={label} className={CARD}
            style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-1.5 mb-2">
              <Icon size={12} style={{ color }} />
              <span className="text-xs" style={{ color: S.t4 }}>{label}</span>
            </div>
            <p className="mono font-bold" style={{ color, fontSize: 20 }}>{value}</p>
            <p className="text-xs mt-0.5" style={{ color: S.t4 }}>{sub}</p>
          </div>
        ))}
      </div>

      {/* ── Main 8/4 grid ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-12 gap-4">

        {/* ── LEFT col (8 cols) ── */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">

          {/* Issue distribution + voter split */}
          <div className="grid grid-cols-2 gap-4">

            {/* Issue Intensity (Neo4j YouTube signals) */}
            <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-3">
                <Activity size={12} style={{ color: "#ef4444" }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>
                  Issue Signal Intensity
                </span>
                <span className="ml-auto mono text-xs px-1.5 py-0.5 rounded"
                  style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)", fontSize: 9 }}>
                  {ytCount} YT videos
                </span>
              </div>
              <div className="space-y-2">
                {issues.length === 0 ? (
                  <p className="text-xs" style={{ color: S.t4 }}>No issue data from Neo4j.</p>
                ) : issues.map((iss, i) => {
                  const barPct = (iss.count / maxIssueCount) * 100;
                  const barColor = i === 0 ? "#ef4444" : i < 3 ? "#f97316" : i < 6 ? "#f59e0b" : "#64748b";
                  return (
                    <div key={iss.code} className="flex items-center gap-2">
                      <span className="mono w-4 text-right text-xs" style={{ color: S.t4 }}>{i + 1}</span>
                      <span className="text-xs flex-1 capitalize" style={{ color: S.t2 }}>
                        {iss.label || iss.code}
                      </span>
                      <div className="w-20 h-1.5 rounded-full" style={{ background: S.base }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${barPct}%`, background: barColor }} />
                      </div>
                      <span className="mono text-xs w-5 text-right" style={{ color: barColor }}>{iss.count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Voter demographics */}
            <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-3">
                <Users size={12} style={{ color: "#3b82f6" }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Voter Demographics</span>
              </div>

              {/* Gender split bar */}
              <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5">
                  <span style={{ color: "#3b82f6" }}>Male — {fmt(maleVoters)} ({pct(maleVoters, totalVoters)})</span>
                  <span style={{ color: "#ec4899" }}>Female — {fmt(femaleVoters)} ({pct(femaleVoters, totalVoters)})</span>
                </div>
                <div className="flex rounded-full overflow-hidden h-3">
                  <div style={{ width: `${(maleVoters / totalVoters) * 100}%`, background: "#3b82f6" }} />
                  <div style={{ width: `${(femaleVoters / totalVoters) * 100}%`, background: "#ec4899" }} />
                </div>
              </div>

              {/* Per-booth voter stats */}
              <div className="space-y-1.5">
                {[
                  { label: "Total booths",       value: fmt(boothCount),                                  color: S.t1 },
                  { label: "Total voters",        value: fmt(totalVoters),                                  color: "#3b82f6" },
                  { label: "Avg voters/booth",    value: boothCount > 0 ? fmt(Math.round(totalVoters / boothCount)) : "—", color: S.t2 },
                  { label: "Female ratio",        value: pct(femaleVoters, totalVoters),                   color: "#ec4899" },
                  { label: "Booths with pulse",   value: `${withPulse} / ${boothCount}`,                   color: withPulse > 0 ? "#10b981" : "#ef4444" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex justify-between py-1"
                    style={{ borderBottom: `1px solid ${S.border}` }}>
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span>
                    <span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Political lean (from booth_metrics, may be all INSUFFICIENT) */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp size={12} style={{ color: S.saffron }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Political Lean Distribution</span>
              {withPulse === 0 && (
                <span className="ml-auto text-xs px-2 py-0.5 rounded mono"
                  style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.25)", fontSize: 9 }}>
                  PULSE DATA PENDING
                </span>
              )}
            </div>
            <div className="space-y-2">
              {[
                { key: "STRONG_BJP", label: "Strong BJP",   color: "#f97316" },
                { key: "LEAN_BJP",   label: "Lean BJP",     color: "#fb923c" },
                { key: "NEUTRAL",    label: "Neutral",      color: "#64748b" },
                { key: "LEAN_OPP",   label: "Lean Opp",     color: "#60a5fa" },
                { key: "STRONG_OPP", label: "Strong Opp",   color: "#3b82f6" },
                { key: "INSUFFICIENT",label: "Awaiting data",color: "#1e3a5f"},
              ].map(({ key, label, color }) => {
                const count   = leanDist[key] ?? 0;
                const pctVal  = booths.length > 0 ? (count / booths.length) * 100 : 0;
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-xs w-24" style={{ color: S.t4 }}>{label}</span>
                    <div className="flex-1 h-1.5 rounded-full" style={{ background: S.base }}>
                      <div className="h-1.5 rounded-full" style={{ width: `${pctVal}%`, background: color }} />
                    </div>
                    <span className="mono text-xs w-6 text-right" style={{ color }}>{count}</span>
                    <span className="mono text-xs w-10 text-right" style={{ color: S.t4 }}>{pctVal.toFixed(0)}%</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 flex rounded overflow-hidden h-2">
              {[
                ["STRONG_BJP","#f97316"],["LEAN_BJP","#fb923c"],["NEUTRAL","#374151"],
                ["LEAN_OPP","#60a5fa"],["STRONG_OPP","#3b82f6"],["INSUFFICIENT","#1a2b44"],
              ].map(([key, color]) => {
                const p = booths.length > 0 ? ((leanDist[key as string] ?? 0) / booths.length) * 100 : 0;
                return p > 0 ? <div key={key} style={{ width: `${p}%`, background: color, minWidth: 2 }} /> : null;
              })}
            </div>
            <div className="mt-2 flex justify-between text-xs mono">
              <span style={{ color: "#f97316" }}>BJP: {bjpLean}</span>
              <span style={{ color: "#64748b" }}>Neutral: {leanDist["NEUTRAL"] ?? 0}</span>
              <span style={{ color: "#3b82f6" }}>Opp: {oppLean}</span>
            </div>
          </div>

          {/* Booth table */}
          <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${S.border}` }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: S.surface, borderBottom: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2">
                <MapPin size={12} style={{ color: S.saffron }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Booth Roster</span>
                <span className="mono text-xs px-1.5 py-0.5 rounded"
                  style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, border: "1px solid rgba(249,115,22,0.2)", fontSize: 9 }}>
                  {booths.length} booths
                </span>
              </div>
              <Link href="/booths" className="flex items-center gap-1 text-xs hover:underline" style={{ color: S.t4 }}>
                All Booths <ArrowRight size={10} />
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full data-table">
                <thead>
                  <tr>
                    {["#", "Polling Station", "Locality", "Voters", "M / F", "BJP Pulse", "Lean", "Confidence"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {booths.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-10 text-center text-xs" style={{ color: S.t4 }}>
                        No booth data — check API connection
                      </td>
                    </tr>
                  ) : booths.slice(0, 15).map((b) => {
                    const femalePct = b.total_voters && b.female_voters
                      ? (b.female_voters / b.total_voters) * 100 : null;
                    return (
                      <tr key={b.booth_id}>
                        <td className="mono text-xs" style={{ color: S.t4 }}>{b.booth_number}</td>
                        <td>
                          <Link href={`/booths/${b.booth_id}`}
                            className="text-xs font-medium hover:underline" style={{ color: S.t1 }}>
                            {b.name}
                          </Link>
                        </td>
                        <td className="text-xs" style={{ color: S.t4 }}>{b.locality_hint ?? "—"}</td>
                        <td className="mono text-xs" style={{ color: S.t2 }}>{fmt(b.total_voters)}</td>
                        <td>
                          {femalePct != null ? (
                            <div className="flex items-center gap-1.5">
                              <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: S.base }}>
                                <div className="h-full inline-block" style={{ width: `${100 - femalePct}%`, background: "#3b82f6" }} />
                                <div className="h-full inline-block" style={{ width: `${femalePct}%`, background: "#ec4899" }} />
                              </div>
                              <span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{femalePct.toFixed(0)}%F</span>
                            </div>
                          ) : <span style={{ color: S.t4 }}>—</span>}
                        </td>
                        <td className="mono text-xs" style={{ color: S.t4 }}>
                          {b.bjp_pulse_score?.toFixed(2) ?? "—"}
                        </td>
                        <td>
                          <span className="mono text-xs px-1.5 py-0.5 rounded" style={{
                            background: "var(--bg-surface)",
                            color: S.t4,
                            border: `1px solid ${S.border}`,
                            fontSize: 9,
                          }}>
                            {b.digital_lean_label ?? "AWAITING"}
                          </span>
                        </td>
                        <td className="mono text-xs" style={{ color: S.t4 }}>
                          {b.confidence_label ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {booths.length > 15 && (
              <div className="px-4 py-2.5 text-center"
                style={{ borderTop: `1px solid ${S.border}`, background: S.surface }}>
                <Link href="/booths" className="text-xs hover:underline" style={{ color: S.t4 }}>
                  View all {booths.length} booths →
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT col (4 cols) ── */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">

          {/* 2022 Election Results */}
          {election && (
            <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-3">
                <Shield size={12} style={{ color: S.saffron }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>2022 Election Results</span>
                <span className="ml-auto mono text-xs" style={{ color: S.t4 }}>
                  {election.turnout ? `${election.turnout.turnout_pct.toFixed(1)}% turnout` : ""}
                </span>
              </div>
              <div className="space-y-2.5">
                {election.results.map((r, i) => {
                  const color = r.party === "BJP" ? "#f97316" : r.party === "SP" ? "#10b981" : r.party === "BSP" ? "#3b82f6" : "#94a3b8";
                  return (
                    <div key={r.party}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="mono text-xs w-4" style={{ color: S.t4 }}>{i + 1}</span>
                          <span className="text-xs font-medium" style={{ color }}>{r.party}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="mono text-xs" style={{ color: S.t4 }}>{fmt(r.total_votes)}</span>
                          <span className="mono text-xs font-bold" style={{ color }}>{r.vote_share_pct.toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: S.base }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${r.vote_share_pct}%`, background: color }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              {election.turnout && (
                <div className="mt-3 pt-3 grid grid-cols-2 gap-2" style={{ borderTop: `1px solid ${S.border}` }}>
                  <div>
                    <p className="text-xs" style={{ color: S.t4 }}>Total votes cast</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(election.turnout.total_votes)}</p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: S.t4 }}>Registered electors</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(election.turnout.total_voters)}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Intelligence Feed — YouTube video titles */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Play size={12} style={{ color: "#ef4444" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Intelligence Feed</span>
              <span className="ml-auto flex items-center gap-1 text-xs" style={{ color: "#ef4444" }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#ef4444" }} />
                {ytCount} videos
              </span>
            </div>
            <div className="space-y-0 max-h-60 overflow-y-auto pr-1">
              {videos.length === 0 ? (
                <p className="text-xs" style={{ color: S.t4 }}>No YouTube data from Neo4j.</p>
              ) : videos.map((v, i) => (
                <div key={i} className="flex gap-2 py-2" style={{ borderBottom: `1px solid ${S.border}` }}>
                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                    style={{ background: "#ef4444", opacity: 0.7 }} />
                  <div className="flex-1 min-w-0">
                    {v.url ? (
                      <a href={v.url} target="_blank" rel="noopener noreferrer"
                        className="text-xs leading-snug hover:underline line-clamp-2"
                        style={{ color: S.t2 }}>
                        {v.title}
                      </a>
                    ) : (
                      <p className="text-xs leading-snug line-clamp-2" style={{ color: S.t2 }}>{v.title}</p>
                    )}
                    {v.channel && (
                      <p className="mono text-xs mt-0.5" style={{ color: S.t4, fontSize: 9 }}>{v.channel}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Candidates */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Mic2 size={12} style={{ color: "#8b5cf6" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>
                Candidate Roster
              </span>
              <span className="ml-auto mono text-xs" style={{ color: S.t4 }}>{candidates.length} total</span>
            </div>
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {candidates.length === 0 ? (
                <p className="text-xs" style={{ color: S.t4 }}>No candidate data.</p>
              ) : candidates.map((c, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded-md"
                  style={{ background: S.base, border: `1px solid ${S.border}` }}>
                  <div className="flex flex-col flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {c.is_incumbent && (
                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: "#f97316" }} title="Incumbent" />
                      )}
                      <span className="text-xs font-medium truncate" style={{ color: S.t1 }}>{c.name}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {c.party && (
                        <span className="mono text-xs" style={{ color: "#8b5cf6", fontSize: 9 }}>{c.party}</span>
                      )}
                      <span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{c.year ?? "—"}</span>
                    </div>
                  </div>
                  {c.is_incumbent && (
                    <CheckCircle size={10} style={{ color: "#f97316", flexShrink: 0 }} title="Incumbent" />
                  )}
                  {c.is_primary_opp && !c.is_incumbent && (
                    <AlertCircle size={10} style={{ color: "#3b82f6", flexShrink: 0 }} title="Primary opposition" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* KG summary */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Database size={12} style={{ color: "#10b981" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Data Pipeline</span>
            </div>
            <div className="space-y-1.5">
              {[
                { label: "PostgreSQL booths",  value: fmt(boothCount),    color: "#10b981",  ok: boothCount > 0  },
                { label: "Neo4j KG nodes",     value: "1,133",            color: "#10b981",  ok: true            },
                { label: "KG relationships",   value: "1,798",            color: "#10b981",  ok: true            },
                { label: "YouTube videos",     value: fmt(ytCount),       color: S.saffron,  ok: ytCount > 0     },
                { label: "Issue signals",      value: issues.length,      color: S.saffron,  ok: issues.length > 0 },
                { label: "Candidates in KG",  value: candidates.length,  color: "#8b5cf6",  ok: candidates.length > 0 },
                { label: "Booth pulse data",  value: `${withPulse}/${boothCount}`, color: withPulse > 0 ? "#10b981" : "#ef4444", ok: withPulse > 0 },
              ].map(({ label, value, color, ok }) => (
                <div key={label} className="flex items-center justify-between py-1"
                  style={{ borderBottom: `1px solid ${S.border}` }}>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: ok ? "#10b981" : "#ef4444" }} />
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span>
                  </div>
                  <span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick links */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Zap size={12} style={{ color: S.saffron }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Quick Navigate</span>
            </div>
            <div className="space-y-1.5">
              {[
                { href: "/booths",         label: "Booth Intelligence",      color: "#10b981"  },
                { href: "/heatmap",        label: "Constituency Heatmap",    color: S.saffron  },
                { href: "/graph",          label: "Knowledge Graph",         color: "#3b82f6"  },
                { href: "/reasoning",      label: "AI Reasoning",            color: "#8b5cf6"  },
                { href: "/infrastructure", label: "Data Infrastructure",     color: S.t4       },
              ].map(({ href, label, color }) => (
                <Link key={href} href={href}
                  className="flex items-center justify-between px-3 py-2 rounded-md text-xs transition-all hover:opacity-80"
                  style={{ background: S.base, border: `1px solid ${S.border}`, color }}>
                  {label}
                  <ArrowRight size={10} />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
