import { api } from "@/lib/api";
import TwinCharts from "./TwinCharts";
import { Cpu, AlertTriangle, TrendingUp, Activity } from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

export default async function TwinPage() {
  const [boothsRes, narrativesRes, schemesRes, candidatesRes] = await Promise.allSettled([
    api.booths(AC_ID),
    api.narratives(AC_ID),
    api.schemes(AC_ID),
    api.candidates(AC_ID),
  ]);

  const booths = boothsRes.status === "fulfilled" ? boothsRes.value.booths : [];
  const narratives = narrativesRes.status === "fulfilled" ? narrativesRes.value.narratives : [];
  const schemes = schemesRes.status === "fulfilled" ? schemesRes.value.schemes : [];
  const candidates = candidatesRes.status === "fulfilled" ? candidatesRes.value.candidates : [];

  // Twin state assembly from available data
  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const boothsWithPulse = booths.filter((b) => b.bjp_pulse_score != null);
  const avgBjp = boothsWithPulse.length > 0
    ? boothsWithPulse.reduce((s, b) => s + (b.bjp_pulse_score ?? 0), 0) / boothsWithPulse.length
    : null;
  const avgOpp = boothsWithPulse.length > 0
    ? boothsWithPulse.reduce((s, b) => s + (b.opp_pulse_score ?? 0), 0) / boothsWithPulse.length
    : null;

  // Volatility: booths where lean is not decisive
  const volatileBooths = booths.filter((b) => {
    const label = b.digital_lean_label?.toUpperCase() ?? "";
    return label.includes("NEUTRAL") || label.includes("INSUFFICIENT");
  });

  // Swing potential (lean lean vs strong)
  const leanBooths = booths.filter((b) => b.digital_lean_label?.toUpperCase().startsWith("LEAN"));

  // TwinCell state vectors
  const twinCells = booths.map((b) => ({
    id: b.booth_id,
    number: b.booth_number,
    name: b.name,
    voters: b.total_voters ?? 0,
    lean: b.digital_lean_label ?? "UNKNOWN",
    bjpPulse: b.bjp_pulse_score,
    oppPulse: b.opp_pulse_score,
    volatility: b.digital_lean_label?.toUpperCase().includes("NEUTRAL") ? "HIGH"
      : b.digital_lean_label?.toUpperCase().startsWith("LEAN") ? "MEDIUM" : "LOW",
    issue: b.top_issue,
    confidence: b.confidence_label ?? "UNKNOWN",
    eventCount: b.event_count ?? 0,
  }));

  // Scheme gap summary
  const highPrioritySchemes = schemes.filter((s) => s.priority?.toUpperCase() === "HIGH");

  // Top narrative types
  const narrativeTypes: Record<string, number> = {};
  narratives.forEach((n) => {
    const t = n.narrative_type ?? "unknown";
    narrativeTypes[t] = (narrativeTypes[t] ?? 0) + 1;
  });
  const topNarratives = Object.entries(narrativeTypes).sort((a, b) => b[1] - a[1]).slice(0, 5);

  // Scenario templates
  const scenarios = [
    {
      id: "water_delivery",
      name: "Water Delivery Push",
      desc: "Accelerate water supply scheme delivery to high-gap booths",
      targetBooths: twinCells.filter((c) => c.issue?.includes("water")).length,
      projectedLift: "+4–6% swing in neutral booths",
      priority: "HIGH",
    },
    {
      id: "youth_employment",
      name: "Youth Employment Outreach",
      desc: "Employment camps + skill training awareness in volatile booths",
      targetBooths: volatileBooths.length,
      projectedLift: "+2–4% swing potential",
      priority: "MEDIUM",
    },
    {
      id: "women_welfare",
      name: "Women Welfare Campaign",
      desc: "Target women-priority booths with scheme direct-benefit messaging",
      targetBooths: booths.filter((b) => b.female_voters && b.male_voters && b.female_voters > b.male_voters * 0.9).length,
      projectedLift: "+3–5% vote share in targeted booths",
      priority: "HIGH",
    },
  ];

  return (
    <div className="min-h-screen p-6" style={{ background: "#0a0e1a" }}>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-2 h-6 rounded-full" style={{ background: "#f59e0b" }} />
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Cpu size={20} style={{ color: "#f59e0b" }} /> Gorakhpur Digital Twin
          </h1>
        </div>
        <p className="text-sm ml-5" style={{ color: "#94a3b8" }}>
          Constituency state model · {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
        </p>
      </div>

      {/* Twin State KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Total Voters</p>
          <p className="text-2xl font-bold text-white">{fmt(totalVoters)}</p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #f59e0b33" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Volatile Booths</p>
          <p className="text-2xl font-bold" style={{ color: "#f59e0b" }}>{volatileBooths.length}</p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>neutral or insufficient lean</p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #ef444433" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>High-Priority Gaps</p>
          <p className="text-2xl font-bold" style={{ color: "#ef4444" }}>{highPrioritySchemes.length}</p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>scheme delivery gaps</p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #8b5cf633" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Swing Booths</p>
          <p className="text-2xl font-bold" style={{ color: "#8b5cf6" }}>{leanBooths.length}</p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>lean (not strong) lean</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main column */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Charts */}
          <TwinCharts booths={booths} narrativeTypes={narrativeTypes} />

          {/* TwinCell State Vectors */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Activity size={14} style={{ color: "#f59e0b" }} /> TwinCell State Vectors
              </h3>
            </div>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
                    {["Booth", "Voters", "Lean", "BJP Pulse", "Volatility", "Top Issue", "Confidence", "Events"].map((h) => (
                      <th key={h} className="px-3 py-2 text-left font-medium uppercase tracking-wider"
                        style={{ color: "#475569" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {twinCells.map((c, i) => (
                    <tr key={c.id}
                      style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4520" }}>
                      <td className="px-3 py-2 font-mono" style={{ color: "#94a3b8" }}>{c.number}</td>
                      <td className="px-3 py-2 text-white">{fmt(c.voters)}</td>
                      <td className="px-3 py-2" style={{
                        color: c.lean.includes("BJP") ? "#f97316" : c.lean.includes("OPP") ? "#3b82f6" : "#64748b"
                      }}>{c.lean}</td>
                      <td className="px-3 py-2" style={{ color: "#f97316" }}>
                        {c.bjpPulse != null ? c.bjpPulse.toFixed(2) : "—"}
                      </td>
                      <td className="px-3 py-2" style={{
                        color: c.volatility === "HIGH" ? "#ef4444" : c.volatility === "MEDIUM" ? "#f59e0b" : "#10b981"
                      }}>{c.volatility}</td>
                      <td className="px-3 py-2 capitalize" style={{ color: "#94a3b8" }}>
                        {c.issue?.replace(/_/g, " ") ?? "—"}
                      </td>
                      <td className="px-3 py-2" style={{
                        color: c.confidence === "HIGH" ? "#10b981" : c.confidence === "MEDIUM" ? "#f59e0b" : "#ef4444"
                      }}>{c.confidence}</td>
                      <td className="px-3 py-2 text-white">{c.eventCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-6">
          {/* Scenario Templates */}
          <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp size={14} style={{ color: "#f59e0b" }} /> Scenario Templates
            </h3>
            <div className="space-y-3">
              {scenarios.map((sc) => (
                <div key={sc.id} className="rounded-lg p-3"
                  style={{ background: "#0a0e1a", border: `1px solid ${sc.priority === "HIGH" ? "#ef444433" : "#f59e0b33"}` }}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-semibold text-white">{sc.name}</p>
                    <span className="text-xs px-2 py-0.5 rounded"
                      style={{
                        background: sc.priority === "HIGH" ? "#ef444422" : "#f59e0b22",
                        color: sc.priority === "HIGH" ? "#ef4444" : "#f59e0b"
                      }}>{sc.priority}</span>
                  </div>
                  <p className="text-xs mb-2" style={{ color: "#94a3b8" }}>{sc.desc}</p>
                  <div className="flex justify-between text-xs">
                    <span style={{ color: "#475569" }}>Target booths:</span>
                    <span className="text-white font-medium">{sc.targetBooths}</span>
                  </div>
                  <div className="mt-1 px-2 py-1.5 rounded text-xs"
                    style={{ background: "#10b98122", color: "#10b981" }}>
                    Projected: {sc.projectedLift}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Narratives */}
          <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
            <h3 className="text-sm font-semibold text-white mb-4">Dominant Narratives</h3>
            {topNarratives.length === 0 ? (
              <p className="text-sm" style={{ color: "#475569" }}>No narrative data.</p>
            ) : (
              <div className="space-y-2">
                {topNarratives.map(([type, count]) => (
                  <div key={type}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize text-white">{type.replace(/_/g, " ")}</span>
                      <span style={{ color: "#94a3b8" }}>{count} booths</span>
                    </div>
                    <div className="h-1.5 rounded-full" style={{ background: "#1e2d45" }}>
                      <div className="h-1.5 rounded-full" style={{
                        width: `${(count / (topNarratives[0]?.[1] || 1)) * 100}%`,
                        background: "#8b5cf6"
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Candidate results */}
          {candidates.length > 0 && (
            <div className="rounded-xl p-5" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
              <h3 className="text-sm font-semibold text-white mb-4">Historical Candidates</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {candidates.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs rounded p-2"
                    style={{ background: "#0a0e1a", border: "1px solid #1e2d45" }}>
                    <div>
                      <p className="font-medium text-white">{c.name}</p>
                      <p style={{ color: "#475569" }}>{c.party} · {c.election_year}</p>
                    </div>
                    <div className="text-right">
                      {c.vote_share != null && (
                        <p style={{ color: "#94a3b8" }}>{c.vote_share.toFixed(1)}%</p>
                      )}
                      {c.winner_flag && (
                        <span className="text-xs px-1 py-0.5 rounded" style={{ background: "#10b98122", color: "#10b981" }}>Won</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
