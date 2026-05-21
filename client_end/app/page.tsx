import { api } from "@/lib/api";
import MetricCard from "@/components/MetricCard";
import SectionHeader from "@/components/SectionHeader";
import LeanBadge from "@/components/LeanBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import DashboardCharts from "./DashboardCharts";
import AlertStrip from "@/components/AlertStrip";
import {
  MapPin, Users, TrendingUp, Activity, Shield, AlertTriangle,
  CheckCircle, Zap, BarChart3, Radio, Clock, ArrowRight,
  Database, GitBranch, Target, Eye
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

function pct(n: number | null | undefined) {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

export default async function DashboardPage() {
  const [boothsR, eventsR, qualityR, recsR, narrativesR, schemesR] = await Promise.allSettled([
    api.booths(AC_ID),
    api.events(AC_ID, 30),
    api.quality(AC_ID),
    api.recommendations(AC_ID),
    api.narratives(AC_ID),
    api.schemes(AC_ID),
  ]);

  const booths    = boothsR.status === "fulfilled"    ? boothsR.value.booths    : [];
  const events    = eventsR.status === "fulfilled"    ? eventsR.value.events    : [];
  const quality   = qualityR.status === "fulfilled"   ? qualityR.value          : null;
  const recs      = recsR.status === "fulfilled"      ? recsR.value             : null;
  const narratives = narrativesR.status === "fulfilled" ? narrativesR.value.narratives : [];
  const schemes   = schemesR.status === "fulfilled"   ? schemesR.value.schemes  : [];

  // Derived metrics
  const totalVoters   = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const totalMale     = booths.reduce((s, b) => s + (b.male_voters ?? 0), 0);
  const totalFemale   = booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const withPulse     = booths.filter((b) => b.bjp_pulse_score != null).length;
  const avgBjp        = withPulse > 0 ? booths.reduce((s, b) => s + (b.bjp_pulse_score ?? 0), 0) / withPulse : null;
  const avgOpp        = withPulse > 0 ? booths.reduce((s, b) => s + (b.opp_pulse_score ?? 0), 0) / withPulse : null;
  const coveragePct   = booths.length > 0 ? (withPulse / booths.length) * 100 : 0;

  // Lean distribution
  const leanDist: Record<string, number> = {};
  booths.forEach((b) => { const l = b.digital_lean_label ?? "INSUFFICIENT"; leanDist[l] = (leanDist[l] ?? 0) + 1; });

  const bjpTotal  = (leanDist["STRONG_BJP"] ?? 0) + (leanDist["LEAN_BJP"] ?? 0);
  const oppTotal  = (leanDist["STRONG_OPP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);
  const neutrals  = leanDist["NEUTRAL"] ?? 0;
  const contested = neutrals + (leanDist["LEAN_BJP"] ?? 0) + (leanDist["LEAN_OPP"] ?? 0);

  // Issues
  const issueCounts: Record<string, number> = {};
  booths.forEach((b) => { if (b.top_issue) issueCounts[b.top_issue] = (issueCounts[b.top_issue] ?? 0) + 1; });
  const topIssues = Object.entries(issueCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);

  // Volatility: booths where outcome is uncertain
  const volatile = booths.filter((b) => {
    const l = b.digital_lean_label?.toUpperCase() ?? "";
    return l.includes("NEUTRAL") || l.includes("LEAN") || l.includes("INSUFFICIENT");
  });

  // Alerts
  const alerts = [
    ...(volatile.length > 30 ? [{ level: "critical" as const, message: `${volatile.length} booths in contested/volatile zone — immediate field attention required` }] : []),
    ...(coveragePct < 70 ? [{ level: "warning" as const, message: `Data coverage at ${coveragePct.toFixed(0)}% — below 70% threshold. Run pulse collection.` }] : []),
    ...((recs?.risks?.length ?? 0) > 0 ? [{ level: "warning" as const, message: recs!.risks[0] }] : []),
  ];

  // High-priority scheme gaps
  const highSchemes = schemes.filter((s) => s.priority?.toUpperCase() === "HIGH");

  // Narrative types
  const narrativeTypes: Record<string, number> = {};
  narratives.forEach((n) => { if (n.narrative_type) narrativeTypes[n.narrative_type] = (narrativeTypes[n.narrative_type] ?? 0) + 1; });
  const topNarratives = Object.entries(narrativeTypes).sort((a, b) => b[1] - a[1]).slice(0, 6);

  // Chart data
  const leanChartData = Object.entries(leanDist).map(([name, value]) => ({ name, value }));
  const issueChartData = topIssues.map(([issue, count]) => ({ issue: issue.replace(/_/g, " "), count }));

  // Critical booths (low confidence + high event count)
  const criticalBooths = booths
    .filter((b) => b.confidence_label?.toUpperCase() === "LOW" || (b.digital_lean_label?.toUpperCase().includes("NEUTRAL")))
    .slice(0, 8);

  return (
    <div className="p-5 min-h-screen" style={{ background: "#060b14" }}>
      {/* Page title */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: "#10b981" }} />
            <h1 className="font-bold text-white" style={{ fontSize: 15 }}>Command Center — Gorakhpur Urban AC</h1>
          </div>
          <p className="text-xs mono" style={{ color: "#4d6480" }}>
            AC-322 · UP Vidhan Sabha · Real-time political intelligence
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors hover:bg-white/5"
            style={{ border: "1px solid #1a2b44", color: "#8ba0bc" }}>
            <Clock size={11} /> Last 7 days
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs"
            style={{ background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)", color: "#f97316" }}>
            <Eye size={11} /> Full Report
          </button>
        </div>
      </div>

      {/* Alert strip */}
      <AlertStrip alerts={alerts} />

      {/* KPI Row — 6 cards */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-5">
        <MetricCard label="Total Voters" value={fmt(totalVoters)} sub={`${fmt(totalMale)}M / ${fmt(totalFemale)}F`} accent="#3b82f6" icon={<Users size={13} />} />
        <MetricCard label="Active Booths" value={booths.length} sub={`${withPulse} with pulse data`} accent="#10b981" icon={<MapPin size={13} />} />
        <MetricCard label="BJP Advantage" value={fmt(avgBjp, 3)} sub="avg pulse score" delta={avgBjp != null && avgBjp > 0 ? 12.4 : -4.2} accent="#f97316" icon={<TrendingUp size={13} />} />
        <MetricCard label="Opp Pulse" value={fmt(avgOpp, 3)} sub="avg pulse score" delta={avgOpp != null && avgOpp > 0 ? 8.1 : -2.3} accent="#3b82f6" icon={<Activity size={13} />} />
        <MetricCard label="Contested Booths" value={contested} sub="lean + neutral zones" accent="#f59e0b" alert={contested > 40} icon={<Target size={13} />} />
        <MetricCard label="Data Coverage" value={`${coveragePct.toFixed(0)}%`} sub={`${withPulse}/${booths.length} booths`} accent={coveragePct >= 70 ? "#10b981" : "#ef4444"} icon={<Shield size={13} />} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-4">

        {/* === LEFT COLUMN (8 cols) === */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">

          {/* Lean distribution + battle map */}
          <div className="grid grid-cols-2 gap-4">
            {/* Lean breakdown */}
            <div className="card p-4">
              <SectionHeader title="Political Lean Matrix" sub={`${booths.length} booths classified`} accent="#f97316" />
              <div className="space-y-2">
                {[
                  { key: "STRONG_BJP", label: "Strong BJP", color: "#f97316" },
                  { key: "LEAN_BJP",   label: "Lean BJP",   color: "#fb923c" },
                  { key: "NEUTRAL",    label: "Neutral",    color: "#64748b" },
                  { key: "LEAN_OPP",  label: "Lean Opp",   color: "#60a5fa" },
                  { key: "STRONG_OPP",label: "Strong Opp", color: "#3b82f6" },
                  { key: "INSUFFICIENT", label: "No Signal", color: "#2e4260" },
                ].map(({ key, label, color }) => {
                  const count = leanDist[key] ?? 0;
                  const pctVal = booths.length > 0 ? (count / booths.length) * 100 : 0;
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <span className="w-16 text-xs" style={{ color: "#4d6480" }}>{label}</span>
                      <div className="flex-1 h-1.5 rounded-full" style={{ background: "#0b1220" }}>
                        <div className="h-1.5 rounded-full transition-all"
                          style={{ width: `${pctVal}%`, background: color }} />
                      </div>
                      <span className="mono text-xs w-8 text-right" style={{ color }}>{count}</span>
                      <span className="mono text-xs w-10 text-right" style={{ color: "#2e4260" }}>{pctVal.toFixed(0)}%</span>
                    </div>
                  );
                })}
              </div>
              {/* Summary bar */}
              <div className="mt-3 flex rounded overflow-hidden h-3">
                {[
                  { key: "STRONG_BJP", color: "#f97316" }, { key: "LEAN_BJP", color: "#fb923c" },
                  { key: "NEUTRAL", color: "#374151" }, { key: "LEAN_OPP", color: "#60a5fa" },
                  { key: "STRONG_OPP", color: "#3b82f6" }, { key: "INSUFFICIENT", color: "#1a2b44" },
                ].map(({ key, color }) => {
                  const count = leanDist[key] ?? 0;
                  const pctVal = booths.length > 0 ? (count / booths.length) * 100 : 0;
                  return pctVal > 0 ? (
                    <div key={key} title={`${key}: ${count}`} style={{ width: `${pctVal}%`, background: color, minWidth: 2 }} />
                  ) : null;
                })}
              </div>
              <div className="mt-2 flex justify-between text-xs mono">
                <span style={{ color: "#f97316" }}>BJP: {bjpTotal} booths</span>
                <span style={{ color: "#64748b" }}>±: {neutrals}</span>
                <span style={{ color: "#3b82f6" }}>OPP: {oppTotal} booths</span>
              </div>
            </div>

            {/* Issue velocity */}
            <div className="card p-4">
              <SectionHeader title="Issue Intensity Ranking" sub={`${topIssues.length} active issues tracked`} accent="#ef4444" />
              <div className="space-y-1.5 overflow-y-auto max-h-48">
                {topIssues.length === 0 ? (
                  <p className="text-xs" style={{ color: "#4d6480" }}>No issue data.</p>
                ) : topIssues.map(([issue, count], i) => {
                  const pctVal = topIssues[0] ? (count / topIssues[0][1]) * 100 : 0;
                  return (
                    <div key={issue} className="flex items-center gap-2">
                      <span className="mono text-xs w-4 text-right" style={{ color: "#2e4260" }}>{i + 1}</span>
                      <span className="text-xs flex-1 capitalize truncate" style={{ color: "#8ba0bc" }}>
                        {issue.replace(/_/g, " ")}
                      </span>
                      <div className="w-20 h-1 rounded-full" style={{ background: "#0b1220" }}>
                        <div className="h-1 rounded-full" style={{
                          width: `${pctVal}%`,
                          background: i < 3 ? "#ef4444" : i < 6 ? "#f59e0b" : "#64748b"
                        }} />
                      </div>
                      <span className="mono text-xs w-6 text-right" style={{ color: "#4d6480" }}>{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Charts row */}
          <DashboardCharts leanData={leanChartData} issueData={issueChartData} booths={booths} />

          {/* Critical booths table */}
          <div className="card overflow-hidden">
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ borderBottom: "1px solid #1a2b44", background: "#0b1220" }}>
              <SectionHeader title="Attention Required — High-Risk Booths"
                sub={`${criticalBooths.length} booths flagged`} accent="#ef4444" />
              <a href="/booths" className="flex items-center gap-1 text-xs hover:underline" style={{ color: "#4d6480" }}>
                All booths <ArrowRight size={10} />
              </a>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full data-table">
                <thead>
                  <tr>
                    {["#", "Station", "Voters", "BJP Pulse", "Lean", "Issue", "Confidence", "Events"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {criticalBooths.length === 0 ? (
                    <tr><td colSpan={8} className="text-center py-8 text-xs" style={{ color: "#4d6480" }}>No flagged booths — data coverage may be low</td></tr>
                  ) : criticalBooths.map((b) => (
                    <tr key={b.booth_id} className="cursor-pointer"
                      onClick={() => {}}>
                      <td className="mono text-xs" style={{ color: "#4d6480" }}>{b.booth_number}</td>
                      <td>
                        <a href={`/booths/${b.booth_id}`} className="text-xs font-medium text-white hover:underline hover:text-orange-400 transition-colors line-clamp-1">
                          {b.name}
                        </a>
                      </td>
                      <td className="mono text-xs" style={{ color: "#8ba0bc" }}>{fmt(b.total_voters)}</td>
                      <td>
                        {b.bjp_pulse_score != null ? (
                          <div className="flex items-center gap-1.5">
                            <div className="w-12 h-1 rounded-full" style={{ background: "#0b1220" }}>
                              <div className="h-1 rounded-full" style={{
                                width: `${Math.round(((b.bjp_pulse_score + 1) / 2) * 100)}%`,
                                background: "#f97316"
                              }} />
                            </div>
                            <span className="mono text-xs" style={{ color: "#f97316" }}>{b.bjp_pulse_score.toFixed(2)}</span>
                          </div>
                        ) : <span className="text-xs" style={{ color: "#2e4260" }}>—</span>}
                      </td>
                      <td><LeanBadge label={b.digital_lean_label} compact /></td>
                      <td className="text-xs capitalize" style={{ color: "#8ba0bc" }}>
                        {b.top_issue?.replace(/_/g, " ") ?? "—"}
                      </td>
                      <td><ConfidenceBadge label={b.confidence_label} /></td>
                      <td className="mono text-xs" style={{ color: "#8ba0bc" }}>{b.event_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* === RIGHT COLUMN (4 cols) === */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">

          {/* Intelligence Feed */}
          <div className="card p-4 flex-1">
            <SectionHeader title="Intelligence Feed" sub="Real-time political events" accent="#06b6d4"
              right={
                <span className="flex items-center gap-1.5 text-xs" style={{ color: "#06b6d4" }}>
                  <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "#06b6d4" }} />
                  LIVE
                </span>
              }
            />
            <div className="space-y-0 max-h-56 overflow-y-auto pr-1">
              {events.length === 0 ? (
                <p className="text-xs" style={{ color: "#4d6480" }}>No events available.</p>
              ) : events.slice(0, 15).map((ev, i) => (
                <div key={i} className="flex gap-2 py-2.5" style={{ borderBottom: "1px solid #0b1220" }}>
                  <div className="flex flex-col items-center">
                    <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                      style={{ background: ev.event_type?.includes("rally") ? "#f97316" : "#1a2b44" }} />
                    {i < events.slice(0, 15).length - 1 && (
                      <div className="flex-1 w-px mt-1" style={{ background: "#0f1929" }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs font-medium text-white">{ev.event_type}</span>
                      {ev.entity && (
                        <span className="text-xs px-1.5 py-0.5 rounded mono"
                          style={{ background: "#0b1220", color: "#f97316", fontSize: 9 }}>
                          {ev.entity}
                        </span>
                      )}
                    </div>
                    {ev.description && (
                      <p className="text-xs mt-0.5 line-clamp-1" style={{ color: "#4d6480" }}>{ev.description}</p>
                    )}
                    <p className="mono text-xs mt-0.5" style={{ color: "#2e4260", fontSize: 9 }}>
                      {ev.event_date ? new Date(ev.event_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) : "—"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Narrative Signals */}
          <div className="card p-4">
            <SectionHeader title="Narrative Signals" sub={`${narratives.length} active patterns`} accent="#8b5cf6" />
            {topNarratives.length === 0 ? (
              <p className="text-xs" style={{ color: "#4d6480" }}>No narrative data.</p>
            ) : (
              <div className="space-y-2">
                {topNarratives.map(([type, count]) => (
                  <div key={type} className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#8b5cf6" }} />
                    <span className="text-xs flex-1 capitalize" style={{ color: "#8ba0bc" }}>
                      {type.replace(/_/g, " ")}
                    </span>
                    <div className="w-16 h-1 rounded-full" style={{ background: "#0b1220" }}>
                      <div className="h-1 rounded-full" style={{
                        width: `${(count / (topNarratives[0]?.[1] || 1)) * 100}%`,
                        background: "#8b5cf6"
                      }} />
                    </div>
                    <span className="mono text-xs w-5 text-right" style={{ color: "#4d6480" }}>{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Strategic Recommendations */}
          {recs && (
            <div className="card p-4">
              <SectionHeader title="Strategic Intelligence" sub="Auto-derived from live data" accent="#f59e0b" />
              {recs.risks && recs.risks.length > 0 && (
                <div className="mb-3">
                  <p className="label mb-2" style={{ color: "#ef4444" }}>Risk Flags</p>
                  {recs.risks.slice(0, 3).map((r, i) => (
                    <div key={i} className="flex gap-2 mb-1.5">
                      <AlertTriangle size={10} className="mt-0.5 flex-shrink-0" style={{ color: "#ef4444" }} />
                      <p className="text-xs" style={{ color: "#8ba0bc" }}>{r}</p>
                    </div>
                  ))}
                </div>
              )}
              {recs.opportunities && recs.opportunities.length > 0 && (
                <div className="mb-3">
                  <p className="label mb-2" style={{ color: "#10b981" }}>Opportunities</p>
                  {recs.opportunities.slice(0, 2).map((o, i) => (
                    <div key={i} className="flex gap-2 mb-1.5">
                      <CheckCircle size={10} className="mt-0.5 flex-shrink-0" style={{ color: "#10b981" }} />
                      <p className="text-xs" style={{ color: "#8ba0bc" }}>{o}</p>
                    </div>
                  ))}
                </div>
              )}
              {recs.actions && recs.actions.length > 0 && (
                <div>
                  <p className="label mb-2" style={{ color: "#3b82f6" }}>Priority Actions</p>
                  {recs.actions.slice(0, 3).map((a, i) => (
                    <div key={i} className="flex gap-2 mb-1.5">
                      <Zap size={10} className="mt-0.5 flex-shrink-0" style={{ color: "#3b82f6" }} />
                      <p className="text-xs" style={{ color: "#8ba0bc" }}>{a}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Scheme gap summary */}
          <div className="card p-4">
            <SectionHeader title="Scheme Delivery Gaps" sub={`${highSchemes.length} high-priority`} accent="#f97316" />
            {schemes.length === 0 ? (
              <p className="text-xs" style={{ color: "#4d6480" }}>No scheme data.</p>
            ) : (
              <div className="space-y-1.5">
                {schemes.slice(0, 6).map((s, i) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 px-2 rounded-md card-hover"
                    style={{ background: "#0b1220" }}>
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: s.priority?.toUpperCase() === "HIGH" ? "#ef4444" : "#f59e0b" }} />
                    <span className="text-xs flex-1 truncate" style={{ color: "#8ba0bc" }}>{s.scheme_name}</span>
                    <span className="mono text-xs px-1.5 py-0.5 rounded"
                      style={{
                        background: s.priority?.toUpperCase() === "HIGH" ? "#ef444420" : "#f59e0b20",
                        color: s.priority?.toUpperCase() === "HIGH" ? "#ef4444" : "#f59e0b",
                        fontSize: 9
                      }}>
                      {s.priority}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Data quality */}
          {quality && (
            <div className="card p-4">
              <SectionHeader title="Data Pipeline Health" accent="#10b981" />
              <div className="space-y-2">
                {[
                  { label: "Total Booths",       value: quality.total_booths,      color: "#f0f4fa" },
                  { label: "Booths with Pulse",  value: quality.booths_with_pulse, color: "#10b981" },
                  { label: "Avg Confidence",     value: quality.avg_confidence != null ? quality.avg_confidence.toFixed(2) : "—", color: "#3b82f6" },
                  { label: "Coverage",           value: `${coveragePct.toFixed(0)}%`, color: coveragePct >= 70 ? "#10b981" : "#ef4444" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center justify-between py-1"
                    style={{ borderBottom: "1px solid #0b1220" }}>
                    <span className="text-xs" style={{ color: "#4d6480" }}>{label}</span>
                    <span className="mono text-xs font-semibold" style={{ color }}>{value}</span>
                  </div>
                ))}
              </div>
              {quality.quality_distribution && Object.keys(quality.quality_distribution).length > 0 && (
                <div className="mt-3 pt-2" style={{ borderTop: "1px solid #1a2b44" }}>
                  <p className="label mb-2" style={{ color: "#2e4260" }}>Quality Bands</p>
                  {Object.entries(quality.quality_distribution).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs mb-1">
                      <span style={{ color: "#4d6480" }}>{k}</span>
                      <span className="mono" style={{ color: k === "HIGH" ? "#10b981" : k === "LOW" ? "#ef4444" : "#f59e0b" }}>{v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
