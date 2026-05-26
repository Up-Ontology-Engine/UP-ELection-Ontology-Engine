"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { InfraOverview, GraphCoverageResponse, GraphCoverageBooth } from "@/lib/api";
import type { InfraLayer } from "./InfraMap";
import {
  Server, Database, GitBranch, Layers, AlertCircle,
  MapPin, X, Activity, Cpu, Info
} from "lucide-react";

const Map = dynamic(() => import("./InfraMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center"
      style={{ background: "var(--bg-base)" }}>
      <div className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin mb-3" />
      <p className="text-xs mono" style={{ color: "var(--text-3)" }}>Initialising map…</p>
    </div>
  )
});

interface Props {
  overview: InfraOverview | null;
  coverage: GraphCoverageResponse | null;
}

const LAYERS: { id: InfraLayer; label: string; desc: string }[] = [
  { id: "graph_coverage", label: "KG Coverage",   desc: "Which booths are in Neo4j" },
  { id: "bjp_pulse",      label: "Party Signal",   desc: "Digital party sentiment score" },
  { id: "confidence",     label: "Confidence",     desc: "Data quality per booth"    },
];

const PG_LABELS: Record<string, string> = {
  booth_master:        "Booths",
  booth_metrics:       "Booth Metrics",
  booth_results:       "Election Results",
  pulse_events:        "Pulse Events",
  booth_narratives:    "Narratives",
  scheme_gap_analysis: "Scheme Gaps",
  data_quality_metrics:"Quality Metrics",
};

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

export default function InfraClient({ overview, coverage }: Props) {
  const [layer, setLayer] = useState<InfraLayer>("graph_coverage");
  const [selected, setSelected] = useState<GraphCoverageBooth | null>(null);

  const allBooths = coverage?.booths ?? [];
  const booths = allBooths.filter((b): b is typeof b & { lat: number; lon: number } =>
    b.lat != null && b.lon != null
  );
  const hasGeo  = booths.length > 0;
  const inKg    = coverage?.in_neo4j ?? 0;
  const total   = coverage?.total ?? 0;

  const neo4j = overview?.neo4j;
  const pg    = overview?.postgresql ?? {};

  const pgTotal = Object.values(pg).reduce<number>((s, v) => s + (v ?? 0), 0);

  const coveragePct = total > 0 ? ((inKg / total) * 100).toFixed(1) : "0";

  // Top-level stat cards
  const stats = [
    {
      label: "PostgreSQL Records",
      value: fmt(pgTotal),
      sub: `${Object.keys(pg).length} tables`,
      icon: Database,
      color: "#f97316",
    },
    {
      label: "Neo4j Nodes",
      value: fmt(neo4j?.total_nodes ?? null),
      sub: `${Object.keys(neo4j?.nodes_by_type ?? {}).length} types`,
      icon: GitBranch,
      color: "#10b981",
    },
    {
      label: "Neo4j Relationships",
      value: fmt(neo4j?.total_edges ?? null),
      sub: `${Object.keys(neo4j?.edges_by_type ?? {}).length} types`,
      icon: Activity,
      color: "#3b82f6",
    },
    {
      label: "Graph Coverage",
      value: `${inKg}/${total}`,
      sub: `${coveragePct}% booths in KG`,
      icon: Cpu,
      color: inKg > 0 ? "#10b981" : "#ef4444",
    },
  ];

  const COVERAGE_LEGEND = [
    { label: "In Knowledge Graph", color: "#10b981" },
    { label: "Not in graph",       color: "var(--text-4)" },
  ];
  const PULSE_LEGEND = [
    { label: "Strong BJP (+0.3+)",   color: "#f97316" },
    { label: "Lean BJP (+0.1–0.3)",  color: "#fb923c" },
    { label: "Neutral",              color: "var(--text-3)" },
    { label: "Lean SP (−0.1–−0.3)", color: "#60a5fa" },
    { label: "Strong SP (< −0.3)",  color: "#3b82f6" },
    { label: "No data",              color: "var(--text-4)" },
  ];
  const CONF_LEGEND = [
    { label: "HIGH",    color: "#10b981" },
    { label: "MEDIUM",  color: "#f59e0b" },
    { label: "LOW",     color: "#ef4444" },
    { label: "Unknown", color: "var(--text-4)" },
  ];
  const legend =
    layer === "graph_coverage" ? COVERAGE_LEGEND :
    layer === "bjp_pulse"      ? PULSE_LEGEND :
                                  CONF_LEGEND;

  return (
    <div className="flex flex-col" style={{ minHeight: "calc(100vh - 56px)", background: "var(--bg-base)" }}>

      {/* ── Title strip ── */}
      <div className="px-6 py-4 flex items-center gap-3"
        style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: "linear-gradient(135deg, #f97316 0%, #dc2626 100%)", boxShadow: "0 2px 8px rgba(249,115,22,0.25)" }}>
          <Server size={15} className="text-[var(--text-1)]" />
        </div>
        <div>
          <h1 className="font-bold text-sm" style={{ color: "var(--text-1)" }}>Data Infrastructure</h1>
          <p className="text-xs mono" style={{ color: "var(--text-4)" }}>
            PostgreSQL · Neo4j · Knowledge Graph Coverage · Gorakhpur Urban
          </p>
        </div>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-4 gap-3 px-6 py-4"
        style={{ borderBottom: "1px solid var(--border)" }}>
        {stats.map(({ label, value, sub, icon: Icon, color }) => (
          <div key={label} className="rounded-lg px-4 py-3"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Icon size={12} style={{ color }} />
              <span className="text-xs" style={{ color: "var(--text-4)" }}>{label}</span>
            </div>
            <p className="mono font-bold text-xl" style={{ color }}>{value}</p>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-4)" }}>{sub}</p>
          </div>
        ))}
      </div>

      {/* ── Main content: left panel + map ── */}
      <div className="flex flex-1" style={{ minHeight: 0 }}>

        {/* Left panel */}
        <div className="w-72 flex-shrink-0 flex flex-col overflow-y-auto"
          style={{ borderRight: "1px solid var(--border)" }}>

          {/* Map layer selector */}
          <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-1.5 mb-2">
              <Layers size={11} style={{ color: "var(--text-4)" }} />
              <p className="label" style={{ color: "var(--text-4)" }}>Map Layer</p>
            </div>
            <div className="space-y-1">
              {LAYERS.map((l) => {
                const active = layer === l.id;
                return (
                  <button key={l.id} onClick={() => setLayer(l.id)}
                    className="w-full text-left px-3 py-2 rounded-md text-xs transition-all"
                    style={{
                      background: active ? "rgba(249,115,22,0.1)" : "transparent",
                      border: active ? "1px solid rgba(249,115,22,0.35)" : "1px solid transparent",
                      color: active ? "var(--saffron)" : "var(--text-3)",
                    }}>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: active ? "var(--saffron)" : "var(--border)" }} />
                      <span className="font-medium">{l.label}</span>
                    </div>
                    {active && (
                      <p className="text-xs mt-0.5 ml-4" style={{ color: "var(--text-4)", fontSize: 9 }}>{l.desc}</p>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="mt-3 space-y-1">
              {legend.map(({ label: ll, color }) => (
                <div key={ll} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>{ll}</span>
                </div>
              ))}
            </div>
          </div>

          {/* PostgreSQL tables */}
          {overview && (
            <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-1.5 mb-2">
                <Database size={11} style={{ color: "var(--text-4)" }} />
                <p className="label" style={{ color: "var(--text-4)" }}>PostgreSQL Tables</p>
              </div>
              <div className="space-y-1">
                {Object.entries(pg).map(([table, count]) => (
                  <div key={table} className="flex items-center justify-between px-2 py-1.5 rounded-md"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <span className="text-xs" style={{ color: "var(--text-3)", fontSize: 11 }}>
                      {PG_LABELS[table] ?? table}
                    </span>
                    <span className="mono font-bold text-xs" style={{ color: "var(--saffron)" }}>
                      {fmt(count)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Neo4j node types */}
          {neo4j && Object.keys(neo4j.nodes_by_type).length > 0 && (
            <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-1.5 mb-2">
                <GitBranch size={11} style={{ color: "var(--text-4)" }} />
                <p className="label" style={{ color: "var(--text-4)" }}>Neo4j Node Types</p>
              </div>
              <div className="space-y-1">
                {Object.entries(neo4j.nodes_by_type).map(([type, count]) => {
                  const pct = neo4j.total_nodes > 0 ? (count / neo4j.total_nodes) * 100 : 0;
                  return (
                    <div key={type} className="px-2 py-1.5 rounded-md"
                      style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs" style={{ color: "var(--text-3)", fontSize: 11 }}>{type}</span>
                        <span className="mono text-xs font-bold" style={{ color: "var(--saffron)" }}>{fmt(count)}</span>
                      </div>
                      <div className="h-0.5 rounded-full" style={{ background: "var(--border)" }}>
                        <div className="h-0.5 rounded-full" style={{
                          width: `${Math.min(pct, 100)}%`,
                          background: "var(--saffron)",
                          opacity: 0.7,
                        }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Neo4j relationship types */}
          {neo4j && Object.keys(neo4j.edges_by_type).length > 0 && (
            <div className="px-4 py-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Activity size={11} style={{ color: "var(--text-4)" }} />
                <p className="label" style={{ color: "var(--text-4)" }}>Relationship Types</p>
              </div>
              <div className="space-y-1">
                {Object.entries(neo4j.edges_by_type).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between px-2 py-1.5 rounded-md"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <span className="mono text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>{type}</span>
                    <span className="mono text-xs font-bold" style={{ color: "#3b82f6" }}>{fmt(count)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!overview && (
            <div className="flex flex-col items-center justify-center flex-1 gap-2 p-6">
              <AlertCircle size={24} style={{ color: "var(--text-4)" }} />
              <p className="text-xs text-center" style={{ color: "var(--text-4)" }}>
                Could not load infrastructure stats. Ensure the API is running.
              </p>
            </div>
          )}
        </div>

        {/* Map + selected booth panel */}
        <div className="flex flex-1 min-h-0">

          {/* Map / Coverage table */}
          <div className="flex-1 relative overflow-auto" style={{ minHeight: 480 }}>
            {!hasGeo ? (
              <div className="p-5">
                {/* No-geo notice */}
                <div className="flex items-start gap-3 mb-4 px-4 py-3 rounded-lg"
                  style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)" }}>
                  <Info size={13} style={{ color: "var(--saffron)", flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <p className="text-xs font-semibold mb-0.5" style={{ color: "var(--saffron)" }}>
                      Spatial heatmap unavailable
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-4)" }}>
                      Booth lat/lon coordinates are not yet geocoded. Run the geocoding
                      ETL to enable the geographic heatmap. KG membership is shown below.
                    </p>
                  </div>
                </div>

                {/* Coverage summary bar */}
                <div className="flex items-center gap-3 mb-4">
                  <p className="text-xs" style={{ color: "var(--text-3)" }}>
                    Knowledge Graph coverage:
                  </p>
                  <div className="flex-1 h-2 rounded-full overflow-hidden"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <div className="h-full rounded-full transition-all"
                      style={{
                        width: `${total > 0 ? (inKg / total) * 100 : 0}%`,
                        background: "linear-gradient(90deg, #10b981, #059669)",
                      }} />
                  </div>
                  <span className="mono text-xs font-bold" style={{ color: "#10b981" }}>
                    {inKg}/{total}
                  </span>
                </div>

                {/* Booth coverage grid */}
                {allBooths.length > 0 && (
                  <div className="grid grid-cols-3 gap-2">
                    {allBooths.map((b) => (
                      <button key={b.booth_id}
                        onClick={() => setSelected(selected?.booth_id === b.booth_id ? null : b)}
                        className="text-left px-3 py-2.5 rounded-md transition-all"
                        style={{
                          background: selected?.booth_id === b.booth_id
                            ? (b.in_neo4j ? "rgba(16,185,129,0.12)" : "rgba(249,115,22,0.08)")
                            : "var(--bg-surface)",
                          border: selected?.booth_id === b.booth_id
                            ? `1px solid ${b.in_neo4j ? "#10b981" : "var(--saffron)"}40`
                            : "1px solid var(--border)",
                        }}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="w-2 h-2 rounded-full flex-shrink-0"
                            style={{ background: b.in_neo4j ? "#10b981" : "#374151" }} />
                          <span className="mono text-xs font-bold" style={{ color: "var(--saffron)", fontSize: 10 }}>
                            B-{String(b.booth_number).padStart(3, "0")}
                          </span>
                        </div>
                        <p className="text-xs leading-tight" style={{ color: "var(--text-3)", fontSize: 10 }}>
                          {b.name && b.name.length > 28 ? b.name.slice(0, 26) + "…" : b.name}
                        </p>
                        <p className="mono mt-1" style={{ color: b.in_neo4j ? "#10b981" : "var(--text-4)", fontSize: 9 }}>
                          {b.in_neo4j ? `KG: deg ${b.neo4j_degree}` : "NOT IN KG"}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                <Map booths={booths} layer={layer} onSelect={setSelected} />
                {/* Overlay: coverage badge */}
                <div className="absolute top-3 right-3 z-10">
                  <div className="rounded-md px-3 py-2"
                    style={{ background: "rgba(6,11,20,0.9)", border: "1px solid var(--border)", backdropFilter: "blur(8px)" }}>
                    <p className="mono text-xs" style={{ color: "var(--text-4)" }}>
                      <span style={{ color: "#10b981" }}>●</span>&nbsp;
                      {inKg} in KG &nbsp;/&nbsp;
                      <span style={{ color: "var(--text-4)" }}>●</span>&nbsp;
                      {total - inKg} not mapped
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Selected booth detail */}
          {selected && (
            <div className="w-60 flex-shrink-0 overflow-y-auto"
              style={{ borderLeft: "1px solid var(--border)", background: "var(--bg-base)" }}>
              <div className="flex items-center justify-between px-4 py-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <p className="text-xs font-semibold" style={{ color: "var(--text-1)" }}>Selected Booth</p>
                <button onClick={() => setSelected(null)}>
                  <X size={12} style={{ color: "var(--text-4)" }} />
                </button>
              </div>

              <div className="px-4 py-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="mono text-xs px-1.5 py-0.5 rounded"
                    style={{
                      background: "rgba(249,115,22,0.12)",
                      color: "var(--saffron)",
                      border: "1px solid rgba(249,115,22,0.3)",
                      fontSize: 9,
                    }}>
                    B-{String(selected.booth_number).padStart(3, "0")}
                  </span>
                  <span className="mono text-xs px-1.5 py-0.5 rounded"
                    style={{
                      background: selected.in_neo4j ? "rgba(16,185,129,0.1)" : "rgba(30,58,95,0.4)",
                      color: selected.in_neo4j ? "#10b981" : "var(--text-3)",
                      border: `1px solid ${selected.in_neo4j ? "rgba(16,185,129,0.3)" : "var(--border)"}`,
                      fontSize: 9,
                    }}>
                    {selected.in_neo4j ? "IN GRAPH" : "NOT IN GRAPH"}
                  </span>
                </div>

                <p className="text-xs font-medium mb-3" style={{ color: "var(--text-1)" }}>
                  {selected.name}
                </p>

                <div className="space-y-1.5">
                  {[
                    { label: "Booth ID",    value: selected.booth_id,                                      color: "var(--text-3)" },
                    { label: "KG Degree",   value: selected.in_neo4j ? String(selected.neo4j_degree) : "—", color: selected.in_neo4j ? "#10b981" : "var(--text-4)" },
                    { label: "Voters",      value: fmt(selected.total_voters),                              color: "var(--text-2)" },
                    { label: "BJP signal",  value: selected.bjp_pulse_score?.toFixed(3) ?? "—",            color: "#f97316" },
                    { label: "SP signal",   value: selected.opp_pulse_score?.toFixed(3) ?? "—",            color: "#3b82f6" },
                    { label: "Confidence",  value: selected.confidence_label ?? "—",                       color: selected.confidence_label === "HIGH" ? "#10b981" : selected.confidence_label === "LOW" ? "#ef4444" : "#f59e0b" },
                    { label: "Events",      value: String(selected.event_count ?? "—"),                     color: "var(--text-3)" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex justify-between py-1"
                      style={{ borderBottom: "1px solid var(--border)" }}>
                      <span className="text-xs" style={{ color: "var(--text-4)" }}>{label}</span>
                      <span className="mono text-xs font-medium" style={{ color, fontSize: 11 }}>{value}</span>
                    </div>
                  ))}
                </div>

                <a href={`/booths/${selected.booth_id}`}
                  className="mt-4 flex items-center justify-center py-2 rounded-md text-xs mono transition-all hover:opacity-80"
                  style={{
                    background: "rgba(249,115,22,0.1)",
                    color: "var(--saffron)",
                    border: "1px solid rgba(249,115,22,0.3)",
                  }}>
                  Full Report →
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
