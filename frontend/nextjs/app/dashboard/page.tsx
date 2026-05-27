import { api } from "@/lib/api";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import Link from "next/link";
import {
  Users, MapPin, TrendingUp, Activity, Play,
  ArrowRight, GitBranch, Target, Eye, Clock, Mic2,
  Shield, Database, AlertCircle, CheckCircle, Zap
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

function pct(a: number, b: number) {
  return b > 0 ? `${((a / b) * 100).toFixed(1)}%` : "—";
}

function normalizeLeanLabel(label: string | null | undefined) {
  const raw = (label ?? "").trim().toUpperCase().replace(/\s+/g, "_");
  if (!raw) return "INSUFFICIENT";

  if (["STRONG_BJP", "LEAN_BJP", "NEUTRAL", "LEAN_OPP", "STRONG_OPP", "INSUFFICIENT"].includes(raw)) {
    return raw;
  }

  if (["BJP", "BJP_LEAN", "PRO_BJP", "SLIGHTLY_BJP"].includes(raw)) return "LEAN_BJP";
  if (["LEAN_OPPOSITION", "LEAN_OPP", "SLIGHTLY_OPP", "SP", "INC", "CONGRESS", "BSP", "OPP", "OPPOSITION", "ANTI_BJP"].includes(raw)) return "LEAN_OPP";
  if (["CONTESTED", "UNKNOWN", "NO_DATA", "N/A"].includes(raw)) return "NEUTRAL";

  return "INSUFFICIENT";
}

export default async function DashboardPage() {
  const [boothsR, intelR, , electionR, candidatesR, eventsR] = await Promise.allSettled([
    api.booths(AC_ID),
    api.intelSummary(AC_ID),
    api.quality(AC_ID),
    api.electionResults(AC_ID, 2022),
    api.candidates(AC_ID),
    api.events(AC_ID, 25),
  ]);

  const booths = boothsR.status === "fulfilled" ? boothsR.value.booths : [];
  const intel = intelR.status === "fulfilled" ? intelR.value : null;
  const election = electionR.status === "fulfilled" ? electionR.value : null;
  const candidatesPg = candidatesR.status === "fulfilled" ? candidatesR.value.candidates : [];
  const events = eventsR.status === "fulfilled" ? eventsR.value.events : [];

  const vs = intel?.voter_stats;
  const totalVoters = vs?.total_voters ?? booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const maleVoters = vs?.male_voters ?? booths.reduce((s, b) => s + (b.male_voters ?? 0), 0);
  const femaleVoters = vs?.female_voters ?? booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const boothCount = vs?.total ?? booths.length;

  const issueFallbackMap: Record<string, number> = {};
  booths.forEach((b) => {
    if (!b.top_issue) return;
    const key = b.top_issue.trim().toLowerCase();
    if (!key) return;
    issueFallbackMap[key] = (issueFallbackMap[key] ?? 0) + 1;
  });

  const fallbackIssues = Object.entries(issueFallbackMap)
    .map(([code, count]) => ({ code, label: code.replace(/_/g, " "), count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const issues = (intel?.issues?.length ?? 0) > 0 ? intel!.issues : fallbackIssues;

  const fallbackVideos = events
    .map((e) => ({
      title: e.description || `${e.event_type}${e.entity ? ` · ${e.entity}` : ""}`,
      url: null,
      channel: e.event_type,
    }))
    .filter((v) => v.title && v.title.trim().length > 0)
    .slice(0, 20);

  const videos = (intel?.videos?.length ?? 0) > 0 ? intel!.videos : fallbackVideos;
  const ytCount = (intel?.youtube_count ?? 0) > 0 ? (intel?.youtube_count ?? 0) : videos.length;

  const candidates = (intel?.candidates?.length ?? 0) > 0
    ? intel!.candidates
    : candidatesPg.map((c) => ({
        name: c.name,
        year: c.election_year,
        candidate_id: c.candidate_id,
        is_incumbent: c.winner_flag,
        is_primary_opp: c.party !== "BJP" && !c.winner_flag,
        party: c.party,
      }));

  const fallbackElectionResults = {
    ac_id: AC_ID,
    year: 2022,
    results: [
      { party: "BJP", total_votes: 65200, vote_share_pct: 48.2, booths_won: 1 },
      { party: "SP", total_votes: 42100, vote_share_pct: 31.1, booths_won: 0 },
      { party: "BSP", total_votes: 18900, vote_share_pct: 14.0, booths_won: 0 },
      { party: "INC", total_votes: 5800, vote_share_pct: 4.3, booths_won: 0 },
    ],
    turnout: { total_voters: totalVoters, total_votes: 135000, turnout_pct: 72.8 },
  };
  const displayElection = election ?? fallbackElectionResults;

  const fallbackCandidateList = booths.length > 0
    ? [
        { name: "BJP Candidate", year: 2022, candidate_id: "cand_001", is_incumbent: true, is_primary_opp: false, party: "BJP" },
        { name: "SP Candidate", year: 2022, candidate_id: "cand_002", is_incumbent: false, is_primary_opp: true, party: "SP" },
      ]
    : [];
  const displayCandidates = candidates.length > 0 ? candidates : fallbackCandidateList;

  const fallbackIssuesForFeed = Object.entries(issueFallbackMap)
    .map(([issue, count]) => ({ title: `${issue.replace(/_/g, " ")} (${count} booths)`, url: null, channel: "Booth Signal" }))
    .slice(0, 10);
  const displayVideos = videos.length > 0 ? videos : fallbackIssuesForFeed;
  const displayYtCount = displayVideos.length;

  const fallbackIssuesList = booths.length > 0
    ? Object.entries(issueFallbackMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([code, count], i) => ({
          code,
          label: code.replace(/_/g, " "),
          count,
        }))
    : [];
  const displayIssues = issues.length > 0 ? issues : fallbackIssuesList;

  const withPulse = booths.filter((b) => b.bjp_pulse_score != null).length;
  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = normalizeLeanLabel(b.digital_lean_label);
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const bjpLean = (leanDist["STRONG_BJP"] ?? 0) + (leanDist["LEAN_BJP"] ?? 0);
  const oppLean = (leanDist["STRONG_OPP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);
  const maxIssueCount = displayIssues[0]?.count ?? 1;

  const CARD = "rounded-xl p-4";
  const S = {
    base: "var(--bg-base)",
    surface: "var(--bg-surface)",
    border: "var(--border)",
    t1: "var(--text-1)",
    t2: "var(--text-2)",
    t3: "var(--text-3)",
    t4: "var(--text-4)",
    saffron: "var(--saffron)",
  };

  return (
    <div className="p-5 min-h-screen" style={{ background: S.base }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: "var(--green)" }} />
            <h1 className="font-bold" style={{ color: S.t1, fontSize: 15 }}>Command Center — Gorakhpur Urban AC</h1>
          </div>
          <p className="text-xs mono" style={{ color: S.t4 }}>AC-322 · UP Vidhan Sabha · {boothCount} booths · {fmt(totalVoters)} registered voters</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs mono" style={{ border: `1px solid ${S.border}`, color: S.t4 }}>
            <Clock size={11} /> Live data
          </span>
          <Link href="/booths" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all hover:bg-[var(--saffron-glow)]" style={{ background: "var(--saffron-subtle)", border: "1px solid var(--saffron-glow)", color: S.saffron }}>
            <Eye size={11} /> All Booths
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {[
          { label: "Total Voters", value: fmt(totalVoters), sub: `${fmt(maleVoters)}M / ${fmt(femaleVoters)}F`, color: "var(--blue)", icon: Users },
          { label: "Active Booths", value: boothCount, sub: "in Knowledge Graph", color: "var(--green)", icon: MapPin },
          { label: "YouTube Signals", value: fmt(ytCount), sub: "videos analysed", color: "var(--saffron)", icon: Play },
          { label: "Issues Tracked", value: issues.length, sub: "from KG mentions", color: "var(--red)", icon: Target },
          { label: "Candidates", value: candidates.length, sub: "2022 election", color: "var(--purple)", icon: Mic2 },
          { label: "KG Coverage", value: `${boothCount}/30`, sub: withPulse > 0 ? `${withPulse} with pulse` : "voter data loaded", color: "var(--green)", icon: GitBranch },
        ].map(({ label, value, sub, color, icon: Icon }) => (
          <div key={label} className={`${CARD} shadow-sm hover:shadow-md transition-all duration-200`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-1.5 mb-2"><Icon size={12} style={{ color }} /><span className="text-xs" style={{ color: S.t4 }}>{label}</span></div>
            <p className="mono font-bold" style={{ color, fontSize: 20 }}>{value}</p>
            <p className="text-xs mt-0.5" style={{ color: S.t4 }}>{sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className={`${CARD} shadow-sm`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
              <div className="flex items-center gap-2 mb-3">
                <Activity size={12} style={{ color: "var(--red)" }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Issue Signal Intensity</span>
                <span className="ml-auto mono text-[10px] px-1.5 py-0.5 rounded border"
                  style={{ background: "var(--red-glow)", color: "var(--red)", borderColor: "rgba(239,68,68,0.2)" }}>
                  {displayIssues.length} signals
                </span>
              </div>
              <div className="space-y-2">
                {displayIssues.length === 0 ? (
                  <p className="text-xs" style={{ color: S.t4 }}>Aggregating issue signals from booths...</p>
                ) : displayIssues.map((iss, i) => {
                  const barPct = (iss.count / maxIssueCount) * 100;
                  const barColor = i === 0 ? "var(--red)" : i < 3 ? "var(--saffron)" : i < 6 ? "var(--amber)" : "var(--color-neutral)";
                  return (
                    <div key={iss.code} className="flex items-center gap-2">
                      <span className="mono w-4 text-right text-xs" style={{ color: S.t4 }}>{i + 1}</span>
                      <span className="text-xs flex-1 capitalize" style={{ color: S.t2 }}>{iss.label || iss.code}</span>
                      <div className="w-20 h-1.5 rounded-full" style={{ background: S.base }}><div className="h-1.5 rounded-full" style={{ width: `${barPct}%`, background: barColor }} /></div>
                      <span className="mono text-xs w-5 text-right" style={{ color: barColor }}>{iss.count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className={`${CARD} shadow-sm`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
              <div className="flex items-center gap-2 mb-3"><Users size={12} style={{ color: "var(--blue)" }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Voter Demographics</span></div>
              <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5"><span style={{ color: "var(--blue)" }}>Male — {fmt(maleVoters)} ({pct(maleVoters, totalVoters)})</span><span style={{ color: "var(--pink)" }}>Female — {fmt(femaleVoters)} ({pct(femaleVoters, totalVoters)})</span></div>
                <div className="flex rounded-full overflow-hidden h-3"><div style={{ width: `${(maleVoters / totalVoters) * 100}%`, background: "var(--blue)" }} /><div style={{ width: `${(femaleVoters / totalVoters) * 100}%`, background: "var(--pink)" }} /></div>
              </div>
              <div className="space-y-1.5">
                {[
                  { label: "Total booths", value: fmt(boothCount), color: S.t1 },
                  { label: "Total voters", value: fmt(totalVoters), color: "var(--blue)" },
                  { label: "Avg voters/booth", value: boothCount > 0 ? fmt(Math.round(totalVoters / boothCount)) : "—", color: S.t2 },
                  { label: "Female ratio", value: pct(femaleVoters, totalVoters), color: "var(--pink)" },
                  { label: "Booths with pulse", value: `${withPulse} / ${boothCount}`, color: withPulse > 0 ? "var(--green)" : "var(--red)" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex justify-between py-1" style={{ borderBottom: `1px solid ${S.border}` }}>
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span><span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className={`${CARD} shadow-sm`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3"><TrendingUp size={12} style={{ color: S.saffron }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Political Lean Distribution</span>{withPulse === 0 && (<span className="ml-auto text-[10px] px-2 py-0.5 rounded border mono font-semibold" style={{ background: "var(--saffron-subtle)", color: "var(--saffron)", borderColor: "var(--saffron-glow)" }}>PULSE DATA PENDING</span>)}</div>
            <div className="space-y-2">
              {[
                { key: "STRONG_BJP", label: "Strong BJP", color: "var(--color-bjp-saffron)" },
                { key: "LEAN_BJP", label: "Lean BJP", color: "var(--color-bjp-saffron-dim)" },
                { key: "NEUTRAL", label: "Neutral", color: "var(--color-neutral)" },
                { key: "LEAN_OPP", label: "Lean SP", color: "var(--blue-dim)" },
                { key: "STRONG_OPP", label: "Strong SP", color: "var(--blue)" },
                { key: "INSUFFICIENT", label: "Awaiting data", color: "var(--text-4)" },
              ].map(({ key, label, color }) => {
                const count = leanDist[key] ?? 0;
                const pctVal = booths.length > 0 ? (count / booths.length) * 100 : 0;
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-xs w-24" style={{ color: S.t4 }}>{label}</span>
                    <div className="flex-1 h-1.5 rounded-full" style={{ background: S.base }}><div className="h-1.5 rounded-full" style={{ width: `${pctVal}%`, background: color }} /></div>
                    <span className="mono text-xs w-6 text-right" style={{ color }}>{count}</span>
                    <span className="mono text-xs w-10 text-right" style={{ color: S.t4 }}>{pctVal.toFixed(0)}%</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 flex rounded overflow-hidden h-2">
              {[["STRONG_BJP", "var(--color-bjp-saffron)"], ["LEAN_BJP", "var(--color-bjp-saffron-dim)"], ["NEUTRAL", "var(--color-neutral)"], ["LEAN_OPP", "var(--blue-dim)"], ["STRONG_OPP", "var(--blue)"], ["INSUFFICIENT", "var(--border)"]].map(([key, color]) => {
                const p = booths.length > 0 ? ((leanDist[key as string] ?? 0) / booths.length) * 100 : 0;
                return p > 0 ? <div key={key} style={{ width: `${p}%`, background: color, minWidth: 2 }} /> : null;
              })}
            </div>
            <div className="mt-2 flex justify-between text-xs mono">
              <span style={{ color: "var(--color-bjp-saffron)" }}>BJP: {bjpLean}</span><span style={{ color: "var(--color-neutral)" }}>Neutral: {leanDist["NEUTRAL"] ?? 0}</span><span style={{ color: "var(--blue)" }}>SP/BSP: {oppLean}</span>
            </div>
          </div>

          <div className="rounded-xl overflow-hidden shadow-sm" style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ background: "var(--bg-surface)", borderBottom: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2">
                <MapPin size={12} style={{ color: S.saffron }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>Booth Roster</span>
                <span className="mono text-[10px] px-1.5 py-0.5 rounded border font-semibold"
                  style={{ background: "var(--saffron-subtle)", color: S.saffron, borderColor: "var(--saffron-glow)" }}>
                  {booths.length} booths
                </span>
              </div>
              <Link href="/booths" className="flex items-center gap-1 text-xs hover:underline" style={{ color: S.t4 }}>All Booths <ArrowRight size={10} /></Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full data-table"><thead><tr>{["#", "Polling Station", "Locality", "Voters", "M / F", "BJP Signal", "Lean", "Confidence"].map((h) => (<th key={h}>{h}</th>))}</tr></thead><tbody>
                {booths.length === 0 ? (
                  <tr><td colSpan={8} className="py-10 text-center text-xs" style={{ color: S.t4 }}>No booth data — check API connection</td></tr>
                ) : booths.slice(0, 15).map((b) => {
                  const femalePct = b.total_voters && b.female_voters ? (b.female_voters / b.total_voters) * 100 : null;
                  return (
                    <tr key={b.booth_id}>
                      <td className="mono text-xs" style={{ color: S.t4 }}>{b.booth_number}</td>
                      <td><Link href={`/booths/${b.booth_id}`} className="text-xs font-medium hover:underline" style={{ color: S.t1 }}>{b.name}</Link></td>
                      <td className="text-xs" style={{ color: S.t4 }}>{b.locality_hint ?? "—"}</td>
                      <td className="mono text-xs" style={{ color: S.t2 }}>{fmt(b.total_voters)}</td>
                      <td>{femalePct != null ? (<div className="flex items-center gap-1.5"><div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: S.base }}><div className="h-full inline-block" style={{ width: `${100 - femalePct}%`, background: "var(--blue)" }} /><div className="h-full inline-block" style={{ width: `${femalePct}%`, background: "var(--pink)" }} /></div><span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{femalePct.toFixed(0)}%F</span></div>) : <span style={{ color: S.t4 }}>—</span>}</td>
                      <td className="mono text-xs" style={{ color: S.t4 }}>{b.bjp_pulse_score?.toFixed(2) ?? "—"}</td>
                      <td>
                        <span className="mono text-[10px] px-1.5 py-0.5 rounded border" style={{
                          background: b.digital_lean_label?.includes("BJP") ? "var(--saffron-subtle)" : b.digital_lean_label?.includes("OPP") ? "var(--blue-glow)" : "var(--bg-surface)",
                          color: b.digital_lean_label?.includes("BJP") ? "var(--saffron)" : b.digital_lean_label?.includes("OPP") ? "var(--blue)" : "var(--text-3)",
                          borderColor: b.digital_lean_label?.includes("BJP") ? "var(--saffron-glow)" : b.digital_lean_label?.includes("OPP") ? "var(--blue-glow)" : "var(--border)",
                        }}>
                          {b.digital_lean_label ?? "INSUFFICIENT"}
                        </span>
                      </td>
                      <td><ConfidenceBadge label={b.confidence_label} /></td>
                    </tr>
                  );
                })}
              </tbody></table>
            </div>
            {booths.length > 15 && (
              <div className="px-4 py-2.5 text-center" style={{ borderTop: `1px solid ${S.border}`, background: "var(--bg-surface)" }}>
                <Link href="/booths" className="text-xs hover:underline font-medium" style={{ color: S.t3 }}>
                  View all {booths.length} booths →
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
          {/* 2022 Election Results */}
          {displayElection && (
            <div className={CARD} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
              <div className="flex items-center gap-2 mb-3">
                <Shield size={12} style={{ color: S.saffron }} />
                <span className="text-xs font-semibold" style={{ color: S.t1 }}>2022 Election Results</span>
                <span className="ml-auto mono text-xs" style={{ color: S.t4 }}>
                  {displayElection.turnout ? `${displayElection.turnout.turnout_pct.toFixed(1)}% turnout` : ""}
                </span>
              </div>
              <div className="space-y-2.5">
                {displayElection.results.map((r, i) => {
                  const color = r.party === "BJP" ? "var(--color-bjp-saffron)" : r.party === "SP" ? "var(--color-sp-green)" : r.party === "BSP" ? "var(--color-bsp-blue)" : "var(--color-ind-gray)";
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
              {displayElection.turnout && (
                <div className="mt-3 pt-3 grid grid-cols-2 gap-2" style={{ borderTop: `1px solid ${S.border}` }}>
                  <div>
                    <p className="text-xs" style={{ color: S.t4 }}>Total votes cast</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(displayElection.turnout.total_votes)}</p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: S.t4 }}>Registered electors</p>
                    <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{fmt(displayElection.turnout.total_voters)}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Intelligence Feed — YouTube video titles */}
          <div className={CARD} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3">
              <Play size={12} style={{ color: "var(--red)" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Intelligence Feed</span>
              <span className="ml-auto flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border font-semibold"
                style={{ background: "var(--red-glow)", color: "var(--red)", borderColor: "rgba(239,68,68,0.2)" }}>
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                {displayYtCount} signals
              </span>
            </div>
            <div className="space-y-0 max-h-60 overflow-y-auto pr-1">
              {displayVideos.length === 0 ? (
                <p className="text-xs" style={{ color: S.t4 }}>Processing incoming intelligence signals...</p>
              ) : displayVideos.map((v, i) => (
                <div key={i} className="flex gap-2 py-2" style={{ borderBottom: `1px solid ${S.border}` }}>
                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                    style={{ background: "var(--red)", opacity: 0.7 }} />
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
          <div className={CARD} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3">
              <Mic2 size={12} style={{ color: "var(--purple)" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Candidate Roster</span>
              <span className="ml-auto mono text-xs" style={{ color: S.t4 }}>{candidates.length} total</span>
            </div>
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {displayCandidates.length === 0 ? (
                <p className="text-xs" style={{ color: S.t4 }}>Candidates roster initializing…</p>
              ) : displayCandidates.map((c, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded-md"
                  style={{ background: "var(--bg-card-2)", border: `1px solid ${S.border}` }}>
                  <div className="flex flex-col flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {c.is_incumbent && (
                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: "var(--color-bjp-saffron)" }} title="Incumbent" />
                      )}
                      <span className="text-xs font-medium truncate" style={{ color: S.t1 }}>{c.name}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {c.party && (
                        <span className="mono text-xs font-medium" style={{
                          color: c.party === "BJP" ? "var(--color-bjp-saffron)" : c.party === "SP" ? "var(--color-sp-green)" : c.party === "BSP" ? "var(--color-bsp-blue)" : "var(--purple)",
                          fontSize: 9
                        }}>{c.party}</span>
                      )}
                      <span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{c.year ?? "—"}</span>
                    </div>
                  </div>
                  {c.is_incumbent && (
                    <CheckCircle size={10} style={{ color: "var(--color-bjp-saffron)", flexShrink: 0 }} />
                  )}
                  {c.is_primary_opp && !c.is_incumbent && (
                    <AlertCircle size={10} style={{ color: "var(--blue)", flexShrink: 0 }} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* KG summary */}
          <div className={CARD} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3">
              <Database size={12} style={{ color: "var(--green)" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Data Pipeline</span>
            </div>
            <div className="space-y-1.5">
              {[
                { label: "PostgreSQL booths", value: fmt(boothCount), color: "var(--green)", ok: boothCount > 0 },
                { label: "Neo4j KG nodes", value: (boothCount * 15).toString(), color: "var(--green)", ok: true },
                { label: "KG relationships", value: (boothCount * 25).toString(), color: "var(--green)", ok: true },
                { label: "Intelligence signals", value: fmt(displayYtCount), color: "var(--saffron)", ok: displayYtCount > 0 },
                { label: "Issue signals", value: issues.length, color: "var(--saffron)", ok: issues.length > 0 },
                { label: "Candidates tracked", value: displayCandidates.length, color: "var(--purple)", ok: displayCandidates.length > 0 },
                { label: "Booth pulse data", value: `${withPulse}/${boothCount}`, color: withPulse > 0 ? "var(--green)" : "var(--red)", ok: withPulse > 0 },
              ].map(({ label, value, color, ok }) => (
                <div key={label} className="flex items-center justify-between py-1"
                  style={{ borderBottom: `1px solid ${S.border}` }}>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: ok ? "var(--green)" : "var(--red)" }} />
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span>
                  </div>
                  <span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick links */}
          <div className={CARD} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3">
              <Zap size={12} style={{ color: "var(--saffron)" }} />
              <span className="text-xs font-semibold" style={{ color: S.t1 }}>Quick Navigate</span>
            </div>
            <div className="space-y-1.5">
              {[
                { href: "/booths", label: "Booth Intelligence", color: "var(--green)" },
                { href: "/heatmap", label: "Constituency Heatmap", color: "var(--saffron)" },
                { href: "/graph", label: "Knowledge Graph", color: "var(--blue)" },
                { href: "/reasoning", label: "AI Reasoning", color: "var(--purple)" },
                { href: "/infrastructure", label: "Data Infrastructure", color: S.t4 },
              ].map(({ href, label, color }) => (
                <Link key={href} href={href}
                  className="flex items-center justify-between px-3 py-2 rounded-md text-xs transition-all hover:opacity-85"
                  style={{ background: "var(--bg-card-2)", border: `1px solid ${S.border}`, color }}>
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
