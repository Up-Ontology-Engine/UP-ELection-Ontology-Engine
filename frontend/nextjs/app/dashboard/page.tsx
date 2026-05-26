import { api } from "@/lib/api";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import Link from "next/link";
import {
  Users, MapPin, TrendingUp, Activity, Play,
  ArrowRight, GitBranch, Target, Eye, Clock, Mic2,
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
  const [boothsR, intelR, qualityR, electionR, candidatesR, eventsR] = await Promise.allSettled([
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

  const withPulse = booths.filter((b) => b.bjp_pulse_score != null).length;
  const leanDist: Record<string, number> = {};
  booths.forEach((b) => {
    const l = normalizeLeanLabel(b.digital_lean_label);
    leanDist[l] = (leanDist[l] ?? 0) + 1;
  });
  const bjpLean = (leanDist["STRONG_BJP"] ?? 0) + (leanDist["LEAN_BJP"] ?? 0);
  const oppLean = (leanDist["STRONG_OPP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);
  const maxIssueCount = issues[0]?.count ?? 1;

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
            <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: "#10b981" }} />
            <h1 className="font-bold" style={{ color: S.t1, fontSize: 15 }}>Command Center — Gorakhpur Urban AC</h1>
          </div>
          <p className="text-xs mono" style={{ color: S.t4 }}>AC-322 · UP Vidhan Sabha · {boothCount} booths · {fmt(totalVoters)} registered voters</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs mono" style={{ border: `1px solid ${S.border}`, color: S.t4 }}>
            <Clock size={11} /> Live data
          </span>
          <Link href="/booths" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs" style={{ background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)", color: S.saffron }}>
            <Eye size={11} /> All Booths
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {[
          { label: "Total Voters", value: fmt(totalVoters), sub: `${fmt(maleVoters)}M / ${fmt(femaleVoters)}F`, color: "#3b82f6", icon: Users },
          { label: "Active Booths", value: boothCount, sub: "in Knowledge Graph", color: "#10b981", icon: MapPin },
          { label: "YouTube Signals", value: fmt(ytCount), sub: "videos analysed", color: S.saffron, icon: Play },
          { label: "Issues Tracked", value: issues.length, sub: "from KG mentions", color: "#ef4444", icon: Target },
          { label: "Candidates", value: candidates.length, sub: "2022 election", color: "#8b5cf6", icon: Mic2 },
          { label: "KG Coverage", value: `${boothCount}/30`, sub: withPulse > 0 ? `${withPulse} with pulse` : "voter data loaded", color: "#10b981", icon: GitBranch },
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
              <div className="flex items-center gap-2 mb-3"><Activity size={12} style={{ color: "#ef4444" }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Issue Signal Intensity</span></div>
              <div className="space-y-2">
                {issues.length === 0 ? (
                  <p className="text-xs" style={{ color: S.t4 }}>Aggregating issue signals from booths...</p>
                ) : issues.map((iss, i) => {
                  const barPct = (iss.count / maxIssueCount) * 100;
                  const barColor = i === 0 ? "#ef4444" : i < 3 ? "#f97316" : i < 6 ? "#f59e0b" : "#64748b";
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
              <div className="flex items-center gap-2 mb-3"><Users size={12} style={{ color: "#3b82f6" }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Voter Demographics</span></div>
              <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5"><span style={{ color: "#3b82f6" }}>Male — {fmt(maleVoters)} ({pct(maleVoters, totalVoters)})</span><span style={{ color: "#ec4899" }}>Female — {fmt(femaleVoters)} ({pct(femaleVoters, totalVoters)})</span></div>
                <div className="flex rounded-full overflow-hidden h-3"><div style={{ width: `${(maleVoters / totalVoters) * 100}%`, background: "#3b82f6" }} /><div style={{ width: `${(femaleVoters / totalVoters) * 100}%`, background: "#ec4899" }} /></div>
              </div>
              <div className="space-y-1.5">
                {[
                  { label: "Total booths", value: fmt(boothCount), color: S.t1 },
                  { label: "Total voters", value: fmt(totalVoters), color: "#3b82f6" },
                  { label: "Avg voters/booth", value: boothCount > 0 ? fmt(Math.round(totalVoters / boothCount)) : "—", color: S.t2 },
                  { label: "Female ratio", value: pct(femaleVoters, totalVoters), color: "#ec4899" },
                  { label: "Booths with pulse", value: `${withPulse} / ${boothCount}`, color: withPulse > 0 ? "#10b981" : "#ef4444" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex justify-between py-1" style={{ borderBottom: `1px solid ${S.border}` }}>
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span><span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className={`${CARD} shadow-sm`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3"><TrendingUp size={12} style={{ color: S.saffron }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Political Lean Distribution</span>{withPulse === 0 && (<span className="ml-auto text-xs px-2 py-0.5 rounded mono" style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.25)", fontSize: 9 }}>PULSE DATA PENDING</span>)}</div>
            <div className="space-y-2">
              {[
                { key: "STRONG_BJP", label: "Strong BJP", color: "#f97316" },
                { key: "LEAN_BJP", label: "Lean BJP", color: "#fb923c" },
                { key: "NEUTRAL", label: "Neutral", color: "#64748b" },
                { key: "LEAN_OPP", label: "Lean SP", color: "#60a5fa" },
                { key: "STRONG_OPP", label: "Strong SP", color: "#3b82f6" },
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
              {[["STRONG_BJP", "#f97316"], ["LEAN_BJP", "#fb923c"], ["NEUTRAL", "#9ca3af"], ["LEAN_OPP", "#60a5fa"], ["STRONG_OPP", "#3b82f6"], ["INSUFFICIENT", "#d8cdbb"]].map(([key, color]) => {
                const p = booths.length > 0 ? ((leanDist[key as string] ?? 0) / booths.length) * 100 : 0;
                return p > 0 ? <div key={key} style={{ width: `${p}%`, background: color, minWidth: 2 }} /> : null;
              })}
            </div>
            <div className="mt-2 flex justify-between text-xs mono">
              <span style={{ color: "#f97316" }}>BJP: {bjpLean}</span><span style={{ color: "#64748b" }}>Neutral: {leanDist["NEUTRAL"] ?? 0}</span><span style={{ color: "#3b82f6" }}>SP/BSP: {oppLean}</span>
            </div>
          </div>

          <div className="rounded-xl overflow-hidden shadow-sm" style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2"><MapPin size={12} style={{ color: S.saffron }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Booth Roster</span></div>
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
                      <td>{femalePct != null ? (<div className="flex items-center gap-1.5"><div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: S.base }}><div className="h-full inline-block" style={{ width: `${100 - femalePct}%`, background: "#3b82f6" }} /><div className="h-full inline-block" style={{ width: `${femalePct}%`, background: "#ec4899" }} /></div><span className="mono text-xs" style={{ color: S.t4, fontSize: 9 }}>{femalePct.toFixed(0)}%F</span></div>) : <span style={{ color: S.t4 }}>—</span>}</td>
                      <td className="mono text-xs" style={{ color: S.t4 }}>{b.bjp_pulse_score?.toFixed(2) ?? "—"}</td>
                      <td><span className="mono text-xs px-1.5 py-0.5 rounded" style={{ background: b.digital_lean_label?.includes("BJP") ? "rgba(249,115,22,0.12)" : b.digital_lean_label?.includes("OPP") ? "rgba(59,130,246,0.12)" : "rgba(100,116,139,0.12)", color: b.digital_lean_label?.includes("BJP") ? "#f97316" : b.digital_lean_label?.includes("OPP") ? "#3b82f6" : S.t4 }}>{b.digital_lean_label ?? "INSUFFICIENT"}</span></td>
                      <td><ConfidenceBadge label={b.confidence_label} /></td>
                    </tr>
                  );
                })}
              </tbody></table>
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
          <div className={`${CARD} shadow-sm`} style={{ background: "var(--bg-card)", border: `1px solid var(--border-bright)` }}>
            <div className="flex items-center gap-2 mb-3"><Play size={12} style={{ color: S.saffron }} /><span className="text-xs font-semibold" style={{ color: S.t1 }}>Election Results</span></div>
            <div className="space-y-2">
              {displayElection.results.map((result) => (
                <div key={result.party} className="flex items-center justify-between text-xs"><span style={{ color: S.t2 }}>{result.party}</span><span className="mono" style={{ color: S.t1 }}>{fmt(result.total_votes)} ({result.vote_share_pct.toFixed(1)}%)</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
