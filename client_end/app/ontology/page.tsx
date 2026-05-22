import { api, type OntologyStatus } from "@/lib/api";
import {
  BookOpen, CheckCircle, Circle, Database, GitBranch,
  Activity, Layers, Link2, AlertCircle, ChevronRight
} from "lucide-react";

// ── Static ontology definitions ───────────────────────────────────────────────

const ENTITIES = [
  { name: "State",               id: "state_id",                              example: "UP",                   color: "#f97316",  neo4j: "State" },
  { name: "District",            id: "district_id",                           example: "GKP",                  color: "#fb923c",  neo4j: "District" },
  { name: "AssemblyConstituency",id: "ac_id",                                 example: "GKP_322",              color: "#3b82f6",  neo4j: "AssemblyConstituency" },
  { name: "Booth",               id: "booth_id",                              example: "GKP_322_001",          color: "#60a5fa",  neo4j: "Booth" },
  { name: "Candidate",           id: "candidate_id",                          example: "GKP_CAN_2022_001",     color: "#10b981",  neo4j: "Candidate" },
  { name: "Party",               id: "party_id",                              example: "BJP",                  color: "#8b5cf6",  neo4j: "Party" },
  { name: "Issue",               id: "code",                                  example: "water",                color: "#ef4444",  neo4j: "Issue" },
  { name: "Scheme",              id: "name",                                  example: "PM_UJJWALA",           color: "#f59e0b",  neo4j: "Scheme" },
  { name: "PulseEvent",          id: "event_id",                              example: "PE_YT_abc123",         color: "#06b6d4",  neo4j: "PulseEvent" },
  { name: "YouTubeVideo",        id: "video_id",                              example: "dQw4w9WgXcQ",          color: "#ec4899",  neo4j: "YouTubeVideo" },
  { name: "Channel",             id: "channel_id",                            example: "UCxxx",                color: "#a78bfa",  neo4j: "Channel" },
  { name: "Panchayat",           id: "panchayat_id",                          example: "PAN_GKP_001",          color: "#84cc16",  neo4j: "Panchayat" },
  { name: "Narrative",           id: "(booth_id, narrative_type, computed_at)", example: "anti_incumbency@B001", color: "#e879f9", neo4j: "Narrative" },
  { name: "DataQuality",         id: "(booth_id, computed_at)",               example: "DQ_B001_2024",         color: "#22d3ee",  neo4j: "DataQuality" },
  { name: "SchemeGap",           id: "(booth_id, scheme_name, computed_at)", example: "GAP_B001_UJJWALA",     color: "#f97316",  neo4j: "SchemeGap" },
  { name: "ContradictionFlag",   id: "(booth_id, entity, source_a, …)",      example: "CF_B001_BJP_NEWS_SM",  color: "#dc2626",  neo4j: "ContradictionFlag" },
];

const RELATIONSHIPS = [
  { from: "State",              to: "District",             type: "HAS_DISTRICT" },
  { from: "District",          to: "AssemblyConstituency", type: "HAS_AC" },
  { from: "AssemblyConstituency", to: "Booth",             type: "HAS_BOOTH" },
  { from: "Candidate",         to: "Party",                type: "REPRESENTS" },
  { from: "Candidate",         to: "AssemblyConstituency", type: "CONTESTED_IN" },
  { from: "Candidate",         to: "CriminalRecord",       type: "HAS_CRIMINAL_RECORD" },
  { from: "Candidate",         to: "AssetDeclaration",     type: "HAS_ASSETS" },
  { from: "PulseEvent",        to: "Booth",                type: "AT_BOOTH (inv)" },
  { from: "PulseEvent",        to: "Issue",                type: "ABOUT_ISSUE" },
  { from: "PulseEvent",        to: "Party",                type: "MENTIONS" },
  { from: "YouTubeVideo",      to: "AssemblyConstituency", type: "ABOUT_AC" },
  { from: "YouTubeVideo",      to: "Channel",              type: "FROM_CHANNEL" },
  { from: "Panchayat",         to: "AssemblyConstituency", type: "WITHIN_AC" },
  { from: "Booth",             to: "DataQuality",          type: "HAS_QUALITY" },
  { from: "Booth",             to: "Narrative",            type: "HAS_NARRATIVE" },
  { from: "Narrative",         to: "Issue",                type: "ABOUT_ISSUE" },
  { from: "Narrative",         to: "Party",                type: "INVOLVES_PARTY" },
  { from: "Booth",             to: "SchemeGap",            type: "HAS_SCHEME_GAP" },
  { from: "SchemeGap",         to: "Scheme",               type: "FOR_SCHEME" },
  { from: "Booth",             to: "ContradictionFlag",    type: "HAS_CONTRADICTION" },
];

const REQUIRED_CONSTRAINTS = [
  { label: "AssemblyConstituency", prop: "ac_id",        type: "UNIQUE" },
  { label: "Booth",               prop: "booth_id",      type: "UNIQUE" },
  { label: "Party",               prop: "party_id",      type: "UNIQUE" },
  { label: "Candidate",           prop: "candidate_id",  type: "UNIQUE" },
  { label: "Issue",               prop: "code",          type: "UNIQUE" },
  { label: "YouTubeVideo",        prop: "video_id",      type: "UNIQUE" },
  { label: "Channel",             prop: "channel_id",    type: "UNIQUE" },
  { label: "PulseEvent",          prop: "event_id",      type: "UNIQUE" },
];

const ID_FORMAT = [
  { entity: "State",     format: "UP" },
  { entity: "District",  format: "GKP" },
  { entity: "AC",        format: "GKP_322" },
  { entity: "Booth",     format: "GKP_322_<booth_num_3d>" },
  { entity: "Candidate", format: "GKP_CAN_<year>_<seq>" },
  { entity: "PulseEvent",format: "PE_<source>_<hash>" },
  { entity: "Scheme",    format: "SCHEME_<name_upper>" },
];

const PHASE_ITEMS = [
  { label: "Entity class definitions",     done: true },
  { label: "ID normalization rules",       done: true },
  { label: "Relationship taxonomy",        done: true },
  { label: "Ontology version field",       done: true },
  { label: "Constraints v1 applied",       done: true },
  { label: "Form-20 election data loaded", done: true },
  { label: "YouTube signal ingestion",     done: true },
  { label: "Constraint activation (v2)",   done: false },
  { label: "Graph hardening (loaders)",    done: false },
  { label: "HeatMap ≥85% coverage",        done: false },
  { label: "Twin snapshot endpoint",       done: false },
  { label: "Demographic segment API",      done: false },
];

// ── Helper ────────────────────────────────────────────────────────────────────

function fmtNum(n: number | null | undefined) {
  if (n == null || n < 0) return <span style={{ color: "#475569" }}>—</span>;
  return <span style={{ color: "#10b981" }}>{n.toLocaleString("en-IN")}</span>;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function OntologyPage() {
  const status: OntologyStatus | null = await api.ontologyStatus();

  const liveNodes   = status?.neo4j.nodes ?? {};
  const liveConstr  = status?.neo4j.constraints ?? [];
  const liveConstrSet = new Set(
    liveConstr.flatMap((c) => c.labels.map((lbl) => `${lbl}::${c.properties[0] ?? ""}`))
  );
  const pgTables    = status?.postgresql.tables ?? {};
  const neo4jOnline = status?.neo4j.online ?? false;
  const pgOnline    = status?.postgresql.online ?? false;

  const donePct = Math.round(
    (PHASE_ITEMS.filter((x) => x.done).length / PHASE_ITEMS.length) * 100
  );

  return (
    <div className="min-h-screen p-5" style={{ background: "#0a0e1a" }}>

      {/* ── Breadcrumb + Header ── */}
      <div className="mb-5">
        <div className="flex items-center gap-2 text-xs mono mb-2" style={{ color: "#475569" }}>
          <span>Gorakhpur Urban</span>
          <ChevronRight size={10} />
          <span style={{ color: "#94a3b8" }}>Ontology Layer</span>
        </div>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-8 rounded-full" style={{ background: "linear-gradient(180deg,#3b82f6,#8b5cf6)" }} />
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <BookOpen size={18} style={{ color: "#3b82f6" }} />
                Ontology Layer
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "#475569" }}>
                v1.0.0-ontology-phase · Entity classes · Relationships · Live graph stats
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
              style={{ background: neo4jOnline ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
                       border: `1px solid ${neo4jOnline ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}` }}>
              <span className="w-1.5 h-1.5 rounded-full"
                style={{ background: neo4jOnline ? "#10b981" : "#ef4444", display: "inline-block" }} />
              <span className="mono text-xs" style={{ color: neo4jOnline ? "#10b981" : "#ef4444" }}>
                Neo4j {neo4jOnline ? "LIVE" : "OFFLINE"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
              style={{ background: pgOnline ? "rgba(59,130,246,0.08)" : "rgba(239,68,68,0.08)",
                       border: `1px solid ${pgOnline ? "rgba(59,130,246,0.25)" : "rgba(239,68,68,0.25)"}` }}>
              <span className="w-1.5 h-1.5 rounded-full"
                style={{ background: pgOnline ? "#3b82f6" : "#ef4444", display: "inline-block" }} />
              <span className="mono text-xs" style={{ color: pgOnline ? "#3b82f6" : "#ef4444" }}>
                PostgreSQL {pgOnline ? "LIVE" : "OFFLINE"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Live summary strip ── */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          {
            label: "Total Nodes",
            value: status?.neo4j.total_nodes ?? null,
            icon:  GitBranch,
            color: "#10b981",
          },
          {
            label: "Total Edges",
            value: status?.neo4j.total_edges ?? null,
            icon:  Link2,
            color: "#3b82f6",
          },
          {
            label: "Active Constraints",
            value: liveConstr.length || null,
            icon:  Activity,
            color: "#8b5cf6",
          },
          {
            label: "Phase Progress",
            value: null,
            icon:  Layers,
            color: "#f59e0b",
            pct:   donePct,
          },
        ].map(({ label, value, icon: Icon, color, pct }) => (
          <div key={label} className="rounded-xl p-4"
            style={{ background: "#111827", border: "1px solid #1e2d45" }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: `${color}18` }}>
                <Icon size={13} style={{ color }} />
              </div>
              <span className="text-xs" style={{ color: "#64748b" }}>{label}</span>
            </div>
            {pct != null ? (
              <>
                <p className="text-2xl font-bold text-white">{pct}%</p>
                <div className="mt-2 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                  <div className="h-1 rounded-full transition-all"
                    style={{ width: `${pct}%`, background: color }} />
                </div>
              </>
            ) : (
              <p className="text-2xl font-bold" style={{ color: value != null ? "#f1f5f9" : "#475569" }}>
                {value != null ? value.toLocaleString("en-IN") : "—"}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Left: Entities + Relationships ── */}
        <div className="lg:col-span-2 flex flex-col gap-5">

          {/* Entity Classes */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">
                Entity Classes <span className="text-xs font-normal" style={{ color: "#475569" }}>({ENTITIES.length})</span>
              </h2>
              <span className="mono text-xs px-2 py-0.5 rounded"
                style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6",
                         border: "1px solid rgba(59,130,246,0.2)", fontSize: 9 }}>
                LIVE COUNTS
              </span>
            </div>
            <div className="divide-y" style={{ borderColor: "#1e2d4515" }}>
              {ENTITIES.map((e) => {
                const count = liveNodes[e.neo4j];
                return (
                  <div key={e.name}
                    className="px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.015] transition-colors"
                    style={{ background: "#111827" }}>
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: e.color }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold" style={{ color: e.color }}>{e.name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded font-mono"
                          style={{ background: "#1e2d45", color: "#64748b", fontSize: 9 }}>
                          {e.id}
                        </span>
                      </div>
                      <p className="text-xs mt-0.5 font-mono" style={{ color: "#334155", fontSize: 10 }}>
                        e.g. {e.example}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {count != null ? (
                        <span className="mono text-xs font-semibold" style={{ color: "#10b981" }}>
                          {count.toLocaleString("en-IN")}
                        </span>
                      ) : (
                        <span className="mono text-xs" style={{ color: "#1e3a5f" }}>—</span>
                      )}
                      <p className="text-xs" style={{ color: "#1e3a5f", fontSize: 9 }}>nodes</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Relationships */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">
                Relationship Taxonomy <span className="text-xs font-normal" style={{ color: "#475569" }}>({RELATIONSHIPS.length})</span>
              </h2>
              <span className="mono text-xs" style={{ color: "#475569", fontSize: 10 }}>
                {status?.neo4j.total_edges.toLocaleString("en-IN") ?? "—"} total edges
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
                    {["From", "Type", "To", "Count"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium uppercase tracking-wider"
                        style={{ color: "#334155", fontSize: 9 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {RELATIONSHIPS.map((r, i) => {
                    const cnt = status?.neo4j.relationships[r.type.replace(" (inv)", "")] ?? null;
                    return (
                      <tr key={i}
                        style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4514" }}>
                        <td className="px-4 py-2 font-mono font-bold" style={{ color: "#3b82f6", fontSize: 10 }}>{r.from}</td>
                        <td className="px-4 py-2 font-mono text-white" style={{ fontSize: 10 }}>[:{r.type}]</td>
                        <td className="px-4 py-2 font-mono font-bold" style={{ color: "#10b981", fontSize: 10 }}>{r.to}</td>
                        <td className="px-4 py-2 mono" style={{ color: cnt != null ? "#64748b" : "#1e3a5f", fontSize: 10 }}>
                          {cnt != null ? cnt.toLocaleString("en-IN") : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── Right: Constraints + PG Tables + Phase ── */}
        <div className="flex flex-col gap-5">

          {/* Constraints */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <Activity size={11} style={{ color: "#8b5cf6" }} />
              <h2 className="text-sm font-semibold text-white">Neo4j Constraints</h2>
              <span className="ml-auto mono text-xs"
                style={{ color: "#475569", fontSize: 9 }}>
                {liveConstr.length} active
              </span>
            </div>
            <div className="p-3 space-y-1.5">
              {REQUIRED_CONSTRAINTS.map((c) => {
                const key = `${c.label}::${c.prop}`;
                const active = liveConstrSet.has(key);
                return (
                  <div key={key} className="flex items-start gap-2 rounded-lg p-2"
                    style={{ background: "#0a0e1a", border: `1px solid ${active ? "#10b98130" : "#1e2d45"}` }}>
                    {active
                      ? <CheckCircle size={12} style={{ color: "#10b981", marginTop: 1, flexShrink: 0 }} />
                      : <AlertCircle size={12} style={{ color: "#f59e0b", marginTop: 1, flexShrink: 0 }} />}
                    <div>
                      <p className="text-xs font-mono text-white">{c.label}({c.prop})</p>
                      <p className="text-xs" style={{ color: active ? "#10b981" : "#f59e0b", fontSize: 9 }}>
                        {c.type} · {active ? "Active" : "Missing"}
                      </p>
                    </div>
                  </div>
                );
              })}
              {!neo4jOnline && (
                <div className="rounded-lg p-2 text-xs"
                  style={{ background: "#1a1500", border: "1px solid #f59e0b33", color: "#f59e0b" }}>
                  ! Neo4j offline — constraint status unavailable
                </div>
              )}
            </div>
          </div>

          {/* PostgreSQL table counts */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <Database size={11} style={{ color: "#3b82f6" }} />
              <h2 className="text-sm font-semibold text-white">PostgreSQL Tables</h2>
            </div>
            <div className="p-3 space-y-1">
              {Object.entries(pgTables).map(([tbl, cnt]) => (
                <div key={tbl} className="flex items-center justify-between py-1 border-b"
                  style={{ borderColor: "#1e2d4520" }}>
                  <span className="mono text-xs" style={{ color: "#475569", fontSize: 10 }}>{tbl}</span>
                  {fmtNum(cnt)}
                </div>
              ))}
              {Object.keys(pgTables).length === 0 && (
                <p className="text-xs py-2" style={{ color: "#334155" }}>
                  {pgOnline ? "No tables found" : "PostgreSQL offline"}
                </p>
              )}
            </div>
          </div>

          {/* ID Format */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">ID Normalization</h2>
            </div>
            <div className="p-3 space-y-1.5">
              {ID_FORMAT.map((f) => (
                <div key={f.entity} className="rounded-lg px-3 py-2"
                  style={{ background: "#0a0e1a", border: "1px solid #1e2d45" }}>
                  <p className="text-xs font-bold text-white">{f.entity}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: "#475569", fontSize: 10 }}>{f.format}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Phase Progress */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Phase Progress</h2>
              <span className="mono text-xs px-2 py-0.5 rounded"
                style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b",
                         border: "1px solid rgba(245,158,11,0.2)", fontSize: 9 }}>
                {donePct}%
              </span>
            </div>
            <div className="p-3 space-y-1.5">
              {PHASE_ITEMS.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {item.done
                    ? <CheckCircle size={11} style={{ color: "#10b981", flexShrink: 0 }} />
                    : <Circle     size={11} style={{ color: "#334155",  flexShrink: 0 }} />}
                  <span style={{ color: item.done ? "#cbd5e1" : "#475569" }}>{item.label}</span>
                </div>
              ))}
              <div className="mt-3 h-1.5 rounded-full" style={{ background: "#1e2d45" }}>
                <div className="h-1.5 rounded-full transition-all"
                  style={{ width: `${donePct}%`, background: "linear-gradient(90deg,#10b981,#3b82f6)" }} />
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
