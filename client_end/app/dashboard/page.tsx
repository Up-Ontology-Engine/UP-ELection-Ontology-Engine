import { api } from "@/lib/api";
import Link from "next/link";
import {
  Users, MapPin, TrendingUp, Activity, Shield, Play,
  ArrowRight, Database, GitBranch, Target, Eye, Clock,
  AlertCircle, CheckCircle, Mic2, Zap, AlertTriangle,
  ListChecks, TrendingDown,
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

function pct(a: number, b: number) {
  return b > 0 ? `${((a / b) * 100).toFixed(1)}%` : "—";
}

const SEVERITY_COLOR = { high: "#cc2200", medium: "#d97706", low: "#138808" };
const PRIORITY_COLOR = { high: "#cc2200", medium: "#d97706", low: "#138808" };
const PARTY_COLOR: Record<string, string> = {
  BJP: "#f97316", SP: "#10b981", BSP: "#3b82f6",
};

export default async function DashboardPage() {
  const [boothsR, intelR, qualityR, electionR, breakdownR, recsR] =
    await Promise.allSettled([
      api.booths(AC_ID),
      api.intelSummary(AC_ID),
      api.quality(AC_ID),
      api.electionResults(AC_ID, 2022),
      api.issueBreakdown(AC_ID),
      api.recommendations(AC_ID),
    ]);

  const booths    = boothsR.status    === "fulfilled" ? boothsR.value.booths   : [];
  const intel     = intelR.status     === "fulfilled" ? intelR.value            : null;
  const quality   = qualityR.status   === "fulfilled" ? qualityR.value          : null;
  const election  = electionR.status  === "fulfilled" ? electionR.value         : null;
  const breakdown = breakdownR.status === "fulfilled" ? breakdownR.value.issues : [];
  const recs      = recsR.status      === "fulfilled" ? recsR.value             : null;

  const vs           = intel?.voter_stats;
  const totalVoters  = vs?.total_voters  ?? booths.reduce((s, b) => s + (b.total_voters  ?? 0), 0);
  const maleVoters   = vs?.male_voters   ?? booths.reduce((s, b) => s + (b.male_voters   ?? 0), 0);
  const femaleVoters = vs?.female_voters ?? booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const boothCount   = vs?.total         ?? booths.length;

  const videos     = intel?.videos    ?? [];
  const ytCount    = intel?.youtube_count ?? 0;
  const candidates = intel?.candidates    ?? [];

  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = b.digital_lean_label ?? "INSUFFICIENT";
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const withPulse = booths.filter((b) => b.bjp_pulse_score != null).length;
  const bjpLean   = (leanDist["STRONG_BJP"] ?? 0) + (leanDist["LEAN_BJP"] ?? 0);
  const oppLean   = (leanDist["STRONG_OPP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);

  const highSeverity  = breakdown.filter((i) => i.severity === "high").length;
  const risingIssues  = breakdown.filter((i) => i.trend === "rising").length;
  const maxSignals    = breakdown[0]?.total_signals ?? 1;
  const qualityScore  = quality?.avg_confidence != null
    ? `${Math.round(quality.avg_confidence * 100)}%` : "—";

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

      {/* ── AC verdict banner (only if recommendations loaded) ─────────── */}
      {recs && (
        <div className="mb-5 rounded-xl p-3 flex flex-wrap items-center gap-4"
          style={{ background: S.surface, border: `1px solid ${S.border}`, borderLeft: "4px solid #003380" }}>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold" style={{ color: S.t4 }}>AC Lean</span>
            <span className="mono text-xs font-bold px-2 py-0.5 rounded"
              style={{ background: "#eef3fb", color: "#003380", border: "1px solid #c0cfe0" }}>
              {recs.overall_lean}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold" style={{ color: S.t4 }}>Confidence</span>
            <span className="mono text-xs font-bold px-2 py-0.5 rounded"
              style={{
                background: recs.confidence === "HIGH" ? "#eef7ef" : "#fffbeb",
                color: recs.confidence === "HIGH" ? "#138808" : "#92400e",
                border: `1px solid ${recs.confidence === "HIGH" ? "#b7dfbc" : "#fcd9a0"}`,
              }}>
              {recs.confidence}
            </span>
          </div>
          <p className="text-xs flex-1" style={{ color: S.t3 }}>{recs.verdict}</p>
          <Link href="/actions" className="text-xs font-semibold flex items-center gap-1"
            style={{ color: "#003380" }}>
            View actions <ArrowRight size={10} />
          </Link>
        </div>
      )}

      {/* ── KPI row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {[
          { label: "Total Voters",    value: fmt(totalVoters),   sub: `${fmt(maleVoters)}M / ${fmt(femaleVoters)}F`, color: "#3b82f6", icon: Users       },
          { label: "Active Booths",   value: boothCount,          sub: `${withPulse} with pulse data`,                color: "#10b981", icon: MapPin      },
          { label: "High-Severity",   value: highSeverity,        sub: "issues from signals",                         color: "#cc2200", icon: AlertTriangle},
          { label: "Rising Trends",   value: risingIssues,        sub: "issues up this week",                         color: "#d97706", icon: TrendingUp  },
          { label: "Data Quality",    value: qualityScore,        sub: "avg confidence",                              color: "#10b981", icon: Shield      },
          { label: "YT Signals",      value: fmt(ytCount),        sub: "videos analysed",                             color: S.saffron, icon: Play        },
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

      {/* ── Main grid ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-12 gap-4">

        {/* ── LEFT col (8 cols) ── */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">

          {/* Pain Point Summary + Voter split */}
          <div className="grid grid-cols-2 gap-4">

            {/* Pain Point Summary — from issueBreakdown */}
            <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={12} style={{ color: "#cc2200" }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Top Pain Signals</span>
                <Link href="/pain-points"
                  className="ml-auto text-xs flex items-center gap-0.5 hover:underline"
                  style={{ color: S.t4 }}>
                  Detail <ArrowRight size={9} />
                </Link>
              </div>
              <div className="space-y-2">
                {breakdown.length === 0 ? (
                  <p className="text-xs" style={{ color: S.t4 }}>
                    No verified issue data available.
                  </p>
                ) : breakdown.slice(0, 8).map((iss, i) => {
                  const color = SEVERITY_COLOR[iss.severity];
                  const barPct = (iss.total_signals / maxSignals) * 100;
                  return (
                    <div key={iss.issue}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="mono w-4 text-right text-xs" style={{ color: S.t4 }}>{i + 1}</span>
                        <span className="text-xs flex-1 capitalize" style={{ color: S.t2 }}>
                          {iss.issue.replace(/_/g, " ")}
                        </span>
                        {iss.trend === "rising" && (
                          <TrendingUp size={9} style={{ color: "#cc2200", flexShrink: 0 }} />
                        )}
                        <span className="mono text-xs font-bold" style={{ color, width: 20, textAlign: "right" }}>
                          {iss.total_signals}
                        </span>
                      </div>
                      <div className="flex h-1.5 rounded-full overflow-hidden ml-6"
                        style={{ background: S.base }}>
                        <div style={{ width: `${barPct}%`, background: color }} />
                      </div>
                      <div className="flex gap-1 ml-6 mt-0.5">
                        <div className="h-0.5 rounded-full"
                          style={{ width: `${iss.total_signals > 0 ? (iss.negative_count / iss.total_signals) * 100 : 0}%`, background: "#cc2200", opacity: 0.6, maxWidth: `${barPct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              {breakdown.length > 8 && (
                <Link href="/pain-points"
                  className="mt-2 text-xs flex items-center gap-1 hover:underline"
                  style={{ color: S.t4 }}>
                  +{breakdown.length - 8} more issues <ArrowRight size={9} />
                </Link>
              )}
            </div>

            {/* Voter demographics */}
            <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-3">
                <Users size={12} style={{ color: "#3b82f6" }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Voter Demographics</span>
              </div>
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
              <div className="space-y-1.5">
                {[
                  { label: "Total booths",     value: fmt(boothCount),                                                    color: S.t1 },
                  { label: "Total voters",     value: fmt(totalVoters),                                                   color: "#3b82f6" },
                  { label: "Avg voters/booth", value: boothCount > 0 ? fmt(Math.round(totalVoters / boothCount)) : "—",   color: S.t2 },
                  { label: "Female ratio",     value: pct(femaleVoters, totalVoters),                                     color: "#ec4899" },
                  { label: "Booths with pulse",value: `${withPulse} / ${boothCount}`,                                     color: withPulse > 0 ? "#10b981" : "#ef4444" },
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

          {/* Political lean */}
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
                { key: "STRONG_BJP",   label: "Strong BJP",    color: "#f97316" },
                { key: "LEAN_BJP",     label: "Lean BJP",      color: "#fb923c" },
                { key: "NEUTRAL",      label: "Neutral",       color: "#64748b" },
                { key: "LEAN_OPP",     label: "Lean Opp",      color: "#60a5fa" },
                { key: "STRONG_OPP",   label: "Strong Opp",    color: "#3b82f6" },
                { key: "INSUFFICIENT", label: "Awaiting data", color: "#1e3a5f" },
              ].map(({ key, label, color }) => {
                const count  = leanDist[key] ?? 0;
                const pctVal = booths.length > 0 ? (count / booths.length) * 100 : 0;
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
                ["LEAN_OPP","#60a5fa"],["STRONG_OPP","#3b82f6"],["INSUFFICIENT","#94a3b8"],
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

          {/* Priority Actions */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <ListChecks size={12} style={{ color: "#003380" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Priority Actions</span>
              <Link href="/actions"
                className="ml-auto text-xs flex items-center gap-0.5 hover:underline"
                style={{ color: S.t4 }}>
                Full plan <ArrowRight size={9} />
              </Link>
            </div>
            <div className="space-y-2">
              {!recs || recs.actions.length === 0 ? (
                <p className="text-xs" style={{ color: S.t4 }}>
                  No recommendations — insufficient data.
                </p>
              ) : recs.actions.slice(0, 3).map((action, i) => (
                <div key={i} className="flex gap-2.5 p-2.5 rounded-lg"
                  style={{ background: S.base, border: `1px solid ${S.border}` }}>
                  <span className="inline-flex h-5 w-5 flex-none items-center justify-center rounded text-xs font-bold"
                    style={{ background: PRIORITY_COLOR[action.priority] ?? "#003380", color: "#fff", fontSize: 10 }}>
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold leading-snug" style={{ color: S.t1 }}>{action.title}</p>
                    <p className="text-xs mt-0.5 leading-snug" style={{ color: S.t4 }}>{action.target_segment}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

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
                  const color = PARTY_COLOR[r.party] ?? "#94a3b8";
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
                    <p className="text-xs" style={{ color: S.t4 }}>Votes cast</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(election.turnout.total_votes)}</p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: S.t4 }}>Registered</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(election.turnout.total_voters)}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Intelligence Feed */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Play size={12} style={{ color: "#ef4444" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Intelligence Feed</span>
              <span className="ml-auto flex items-center gap-1 text-xs" style={{ color: "#ef4444" }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#ef4444" }} />
                {ytCount} videos
              </span>
            </div>
            <div className="space-y-0 max-h-52 overflow-y-auto pr-1">
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
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Candidate Roster</span>
              <Link href="/drivers"
                className="ml-auto text-xs flex items-center gap-0.5 hover:underline"
                style={{ color: S.t4 }}>
                Full profiles <ArrowRight size={9} />
              </Link>
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
                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#f97316" }} />
                      )}
                      <span className="text-xs font-medium truncate" style={{ color: S.t1 }}>{c.name}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {c.party && <span className="mono text-xs" style={{ color: "#8b5cf6", fontSize: 9 }}>{c.party}</span>}
                      <span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{c.year ?? "—"}</span>
                    </div>
                  </div>
                  {c.is_incumbent && (
                    <CheckCircle size={10} style={{ color: "#f97316", flexShrink: 0 }} aria-label="Incumbent" />
                  )}
                  {c.is_primary_opp && !c.is_incumbent && (
                    <AlertCircle size={10} style={{ color: "#3b82f6", flexShrink: 0 }} aria-label="Primary opposition" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Data pipeline — live counts only */}
          <div className={CARD} style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <div className="flex items-center gap-2 mb-3">
              <Database size={12} style={{ color: "#10b981" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Data Pipeline</span>
              <Link href="/infrastructure"
                className="ml-auto text-xs flex items-center gap-0.5 hover:underline"
                style={{ color: S.t4 }}>
                Full status <ArrowRight size={9} />
              </Link>
            </div>
            <div className="space-y-1.5">
              {[
                { label: "PostgreSQL booths",  value: fmt(boothCount),       ok: boothCount > 0,           color: "#10b981" },
                { label: "YouTube videos",     value: fmt(ytCount),           ok: ytCount > 0,              color: S.saffron },
                { label: "Issue signals",      value: fmt(breakdown.reduce((s, i) => s + i.total_signals, 0)), ok: breakdown.length > 0, color: S.saffron },
                { label: "Distinct issues",    value: breakdown.length,       ok: breakdown.length > 0,    color: "#3b82f6" },
                { label: "Candidates in KG",   value: candidates.length,      ok: candidates.length > 0,   color: "#8b5cf6" },
                { label: "Booth pulse data",   value: `${withPulse}/${boothCount}`, ok: withPulse > 0,     color: withPulse > 0 ? "#10b981" : "#ef4444" },
                { label: "Avg data quality",   value: qualityScore,           ok: quality != null,          color: "#10b981" },
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
                { href: "/pain-points",    label: "Pain Point Engine",       color: "#cc2200"  },
                { href: "/actions",        label: "Action Recommendations",  color: "#003380"  },
                { href: "/booths",         label: "Booth Intelligence",      color: "#10b981"  },
                { href: "/heatmap",        label: "Constituency Heatmap",    color: S.saffron  },
                { href: "/drivers",        label: "Candidate + Drivers",     color: "#8b5cf6"  },
                { href: "/graph",          label: "Knowledge Graph",         color: "#3b82f6"  },
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
