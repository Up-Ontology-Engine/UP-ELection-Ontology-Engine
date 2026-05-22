import { api, type OntologyStatus, type TwinSnapshot, type HeatmapCoverage } from "@/lib/api";
import {
  BookOpen, CheckCircle, Circle, Database, GitBranch,
  Activity, Layers, Link2, AlertCircle, ChevronRight,
  Map, Users, Cpu, ShieldCheck, BarChart2, Zap,
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
<<<<<<< HEAD
];

const V2_CONSTRAINTS = [
  { label: "State",              prop: "state_id",    type: "UNIQUE v2" },
  { label: "District",           prop: "district_id", type: "UNIQUE v2" },
  { label: "DemographicSegment", prop: "segment_id",  type: "UNIQUE v2" },
  { label: "GovernanceAsset",    prop: "asset_id",    type: "UNIQUE v2" },
  { label: "TwinScenario",       prop: "scenario_id", type: "UNIQUE v2" },
=======
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
  { label: "Constraint activation (v2)",   done: true },
  { label: "Graph hardening (loaders)",    done: true },
  { label: "HeatMap ≥85% coverage",        done: true },
  { label: "Twin snapshot endpoint",       done: true },
  { label: "Demographic segment API",      done: true },
=======
  { label: "Constraint activation (v2)",   done: false },
  { label: "Graph hardening (loaders)",    done: false },
  { label: "HeatMap ≥85% coverage",        done: false },
  { label: "Twin snapshot endpoint",       done: false },
  { label: "Demographic segment API",      done: false },
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
];

// ── Helper ────────────────────────────────────────────────────────────────────

function fmtNum(n: number | null | undefined) {
  if (n == null || n < 0) return <span style={{ color: "#475569" }}>—</span>;
  return <span style={{ color: "#10b981" }}>{n.toLocaleString("en-IN")}</span>;
}

<<<<<<< HEAD
function Stat({ label, value, sub, color = "#10b981" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-xs" style={{ color: "var(--text-4)" }}>{label}</p>
      <p className="text-lg font-bold mono" style={{ color }}>{typeof value === "number" ? value.toLocaleString("en-IN") : value}</p>
      {sub && <p className="text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>{sub}</p>}
    </div>
  );
}

const SEGMENT_COLORS: Record<string, string> = {
  women_skewed_booths: "#ec4899",
  high_turnout_potential: "#3b82f6",
  bjp_stronghold: "#f97316",
  opp_stronghold: "#ef4444",
  swing_booths: "#f59e0b",
  low_confidence: "#64748b",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function OntologyPage() {
  const [status, twin, coverage] = await Promise.all([
    api.ontologyStatus(),
    api.twinSnapshot("GKP_322"),
    api.heatmapCoverage("GKP_322"),
  ]);

=======
// ── Page ──────────────────────────────────────────────────────────────────────

export default async function OntologyPage() {
  const status: OntologyStatus | null = await api.ontologyStatus();

>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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

  const coveragePct = Math.round((coverage?.coverage_pct ?? 0) * 100);
  const segments = twin?.demographic_segments ?? [];

  return (
    <div className="min-h-screen p-5" style={{ background: "#0a0e1a" }}>

<<<<<<< HEAD
      {/* ── Header ── */}
=======
      {/* ── Breadcrumb + Header ── */}
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
      <div className="mb-5">
        <div className="flex items-center gap-2 text-xs mono mb-2" style={{ color: "#475569" }}>
          <span>Gorakhpur Urban</span>
          <ChevronRight size={10} />
          <span style={{ color: "#94a3b8" }}>Ontology Layer</span>
        </div>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-8 rounded-full" style={{ background: "linear-gradient(180deg,#3b82f6,#8b5cf6)" }} />
            <div>
<<<<<<< HEAD
              <h1 className="text-xl font-bold text-[var(--text-1)] flex items-center gap-2">
=======
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                <BookOpen size={18} style={{ color: "#3b82f6" }} />
                Ontology Layer
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "#475569" }}>
                v1.0.0-ontology-phase · Entity classes · Relationships · Live graph stats
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { online: neo4jOnline, label: "Neo4j", color: "#10b981" },
              { online: pgOnline,    label: "PostgreSQL", color: "#3b82f6" },
            ].map(({ online, label, color }) => (
              <div key={label} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
                style={{ background: online ? `${color}14` : "rgba(239,68,68,0.08)",
                         border: `1px solid ${online ? `${color}40` : "rgba(239,68,68,0.25)"}` }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: online ? color : "#ef4444", display: "inline-block" }} />
                <span className="mono text-xs" style={{ color: online ? color : "#ef4444" }}>
                  {label} {online ? "LIVE" : "OFFLINE"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

<<<<<<< HEAD
      {/* ── Summary strip ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {[
          { label: "Total Nodes",       value: status?.neo4j.total_nodes ?? null, icon: GitBranch, color: "#10b981", sub: "in Neo4j" },
          { label: "Total Edges",       value: status?.neo4j.total_edges ?? null, icon: Link2,     color: "#3b82f6", sub: "relationships" },
          { label: "Active Constraints",value: liveConstr.length || null,          icon: Activity,  color: "#8b5cf6", sub: `${V2_CONSTRAINTS.length} v2 added` },
          { label: "HeatMap Coverage",  value: null,                               icon: Map,       color: "#f59e0b", pct: coveragePct },
        ].map(({ label, value, icon: Icon, color, sub, pct }) => (
          <div key={label} className="rounded-xl p-4"
            style={{ background: "var(--bg-card-2)", border: "1px solid var(--border)" }}>
=======
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
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={13} style={{ color }} />
              </div>
<<<<<<< HEAD
              <span className="text-xs" style={{ color: "var(--text-3)" }}>{label}</span>
            </div>
            {pct != null ? (
              <>
                <p className="text-2xl font-bold" style={{ color: pct >= 85 ? "#10b981" : "#f59e0b" }}>{pct}%</p>
                <div className="mt-2 h-1 rounded-full" style={{ background: "var(--border)" }}>
                  <div className="h-1 rounded-full transition-all"
                    style={{ width: `${Math.min(pct, 100)}%`, background: pct >= 85 ? "#10b981" : color }} />
=======
              <span className="text-xs" style={{ color: "#64748b" }}>{label}</span>
            </div>
            {pct != null ? (
              <>
                <p className="text-2xl font-bold text-white">{pct}%</p>
                <div className="mt-2 h-1 rounded-full" style={{ background: "#1e2d45" }}>
                  <div className="h-1 rounded-full transition-all"
                    style={{ width: `${pct}%`, background: color }} />
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                </div>
                <p className="text-xs mt-1" style={{ color: "var(--text-4)", fontSize: 9 }}>
                  {coverage?.geocoded_booths ?? 0}/{coverage?.total_booths ?? 0} booths geocoded
                </p>
              </>
            ) : (
<<<<<<< HEAD
              <>
                <p className="text-2xl font-bold" style={{ color: value != null ? "var(--text-1)" : "var(--text-4)" }}>
                  {value != null ? value.toLocaleString("en-IN") : "—"}
                </p>
                {sub && <p className="text-xs mt-1" style={{ color: "var(--text-4)", fontSize: 9 }}>{sub}</p>}
              </>
=======
              <p className="text-2xl font-bold" style={{ color: value != null ? "#f1f5f9" : "#475569" }}>
                {value != null ? value.toLocaleString("en-IN") : "—"}
              </p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
            )}
          </div>
        ))}
      </div>

      {/* ── Twin Snapshot + Demographics banner ── */}
      {twin && (
        <div className="rounded-xl p-4 mb-5"
          style={{ background: "linear-gradient(135deg,rgba(59,130,246,0.06),rgba(139,92,246,0.06))",
                   border: "1px solid rgba(139,92,246,0.2)" }}>
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={14} style={{ color: "#8b5cf6" }} />
            <h2 className="text-sm font-semibold text-[var(--text-1)]">Digital Twin Snapshot</h2>
            <span className="ml-auto mono text-xs" style={{ color: "var(--text-4)", fontSize: 9 }}>
              GKP_322 · {new Date(twin.snapshot_generated_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <Stat label="Graph Nodes"       value={twin.ontology.total_nodes}       color="#10b981" />
            <Stat label="Graph Edges"       value={twin.ontology.total_edges}       color="#3b82f6" />
            <Stat label="Constraints"       value={twin.ontology.active_constraints} color="#8b5cf6" />
            <Stat label="Total Voters"      value={twin.demographics_summary?.total_voters ?? "—"} color="#f59e0b" />
            <Stat label="Male / Female"
              value={`${twin.demographics_summary?.male_voters?.toLocaleString("en-IN") ?? "—"} / ${twin.demographics_summary?.female_voters?.toLocaleString("en-IN") ?? "—"}`}
              color="#ec4899" sub="voters" />
            <Stat label="HeatMap"
              value={`${Math.round((twin.heatmap.coverage_pct) * 100)}%`}
              sub={twin.heatmap.target_met ? "✓ target met" : "below target"}
              color={twin.heatmap.target_met ? "#10b981" : "#f59e0b"} />
          </div>

          {/* Demographic Segments */}
          {segments.length > 0 && (
            <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2 mb-3">
                <Users size={11} style={{ color: "#06b6d4" }} />
                <p className="text-xs font-semibold text-[var(--text-1)]">
                  Demographic Segments <span style={{ color: "var(--text-4)", fontWeight: 400 }}>({segments.length})</span>
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {segments.map((seg) => {
                  const color = SEGMENT_COLORS[seg.name] ?? "#64748b";
                  return (
                    <div key={seg.name} className="flex items-center gap-2 rounded-lg px-3 py-2"
                      style={{ background: `${color}12`, border: `1px solid ${color}30` }}>
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                      <div>
                        <p className="text-xs font-mono font-semibold" style={{ color }}>
                          {seg.name.replace(/_/g, " ")}
                        </p>
                        <p className="text-xs" style={{ color: "var(--text-4)", fontSize: 9 }}>
                          {seg.booth_count} booths · {seg.description.slice(0, 55)}{seg.description.length > 55 ? "…" : ""}
                        </p>
                      </div>
                      <span className="ml-2 font-bold mono text-sm" style={{ color }}>{seg.booth_count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Left: Entities + Relationships ── */}
        <div className="lg:col-span-2 flex flex-col gap-5">

          {/* Entity Classes */}
<<<<<<< HEAD
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <h2 className="text-sm font-semibold text-[var(--text-1)]">
                Entity Classes <span className="text-xs font-normal" style={{ color: "var(--text-4)" }}>({ENTITIES.length})</span>
=======
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">
                Entity Classes <span className="text-xs font-normal" style={{ color: "#475569" }}>({ENTITIES.length})</span>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
                    style={{ background: "var(--bg-card-2)" }}>
=======
                    style={{ background: "#111827" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: e.color }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold" style={{ color: e.color }}>{e.name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded font-mono"
<<<<<<< HEAD
                          style={{ background: "var(--border)", color: "var(--text-3)", fontSize: 9 }}>
=======
                          style={{ background: "#1e2d45", color: "#64748b", fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <h2 className="text-sm font-semibold text-[var(--text-1)]">
                Relationship Taxonomy <span className="text-xs font-normal" style={{ color: "var(--text-4)" }}>({RELATIONSHIPS.length})</span>
=======
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">
                Relationship Taxonomy <span className="text-xs font-normal" style={{ color: "#475569" }}>({RELATIONSHIPS.length})</span>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
              </h2>
              <span className="mono text-xs" style={{ color: "#475569", fontSize: 10 }}>
                {status?.neo4j.total_edges.toLocaleString("en-IN") ?? "—"} total edges
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
<<<<<<< HEAD
                  <tr style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)" }}>
                    {["From", "Type", "To", "Count"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium uppercase tracking-wider"
                        style={{ color: "var(--text-4)", fontSize: 9 }}>{h}</th>
=======
                  <tr style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
                    {["From", "Type", "To", "Count"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium uppercase tracking-wider"
                        style={{ color: "#334155", fontSize: 9 }}>{h}</th>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {RELATIONSHIPS.map((r, i) => {
                    const cnt = status?.neo4j.relationships[r.type.replace(" (inv)", "")] ?? null;
                    return (
                      <tr key={i}
<<<<<<< HEAD
                        style={{ background: i % 2 === 0 ? "var(--bg-card)" : "var(--bg-card-2)", borderBottom: "1px solid var(--border)" }}>
                        <td className="px-4 py-2 font-mono font-bold" style={{ color: "#3b82f6", fontSize: 10 }}>{r.from}</td>
                        <td className="px-4 py-2 font-mono text-[var(--text-1)]" style={{ fontSize: 10 }}>[:{r.type}]</td>
=======
                        style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4514" }}>
                        <td className="px-4 py-2 font-mono font-bold" style={{ color: "#3b82f6", fontSize: 10 }}>{r.from}</td>
                        <td className="px-4 py-2 font-mono text-white" style={{ fontSize: 10 }}>[:{r.type}]</td>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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

          {/* Live Relationship Counts */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <BarChart2 size={11} style={{ color: "#06b6d4" }} />
              <h2 className="text-sm font-semibold text-[var(--text-1)]">Live Edge Distribution</h2>
            </div>
            <div className="p-4 space-y-2">
              {Object.entries(status?.neo4j.relationships ?? {})
                .sort((a, b) => b[1] - a[1])
                .map(([rel, cnt]) => {
                  const max = Math.max(...Object.values(status?.neo4j.relationships ?? {}));
                  const pct = max > 0 ? (cnt / max) * 100 : 0;
                  return (
                    <div key={rel} className="flex items-center gap-3">
                      <span className="font-mono text-xs w-40 flex-shrink-0" style={{ color: "var(--text-3)", fontSize: 10 }}>
                        :{rel}
                      </span>
                      <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--border)" }}>
                        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: "#3b82f6" }} />
                      </div>
                      <span className="mono text-xs font-semibold w-12 text-right" style={{ color: "#10b981" }}>
                        {cnt.toLocaleString("en-IN")}
                      </span>
                    </div>
                  );
                })}
              {Object.keys(status?.neo4j.relationships ?? {}).length === 0 && (
                <p className="text-xs py-2" style={{ color: "var(--text-4)" }}>No edge data</p>
              )}
            </div>
          </div>
        </div>

        {/* ── Right: Constraints + PG Tables + Phase ── */}
        <div className="flex flex-col gap-5">

<<<<<<< HEAD
          {/* v1 Constraints */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <ShieldCheck size={11} style={{ color: "#10b981" }} />
              <h2 className="text-sm font-semibold text-[var(--text-1)]">Constraints v1</h2>
              <span className="ml-auto mono text-xs" style={{ color: "var(--text-4)", fontSize: 9 }}>
=======
          {/* Constraints */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <Activity size={11} style={{ color: "#8b5cf6" }} />
              <h2 className="text-sm font-semibold text-white">Neo4j Constraints</h2>
              <span className="ml-auto mono text-xs"
                style={{ color: "#475569", fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
                      <p className="text-xs font-mono text-[var(--text-1)]">{c.label}({c.prop})</p>
=======
                      <p className="text-xs font-mono text-white">{c.label}({c.prop})</p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                      <p className="text-xs" style={{ color: active ? "#10b981" : "#f59e0b", fontSize: 9 }}>
                        {c.type} · {active ? "Active" : "Missing"}
                      </p>
                    </div>
                  </div>
                );
              })}
<<<<<<< HEAD
            </div>
          </div>

          {/* v2 Constraints */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(139,92,246,0.3)" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "rgba(139,92,246,0.05)", borderBottom: "1px solid rgba(139,92,246,0.2)" }}>
              <Zap size={11} style={{ color: "#8b5cf6" }} />
              <h2 className="text-sm font-semibold text-[var(--text-1)]">Constraints v2</h2>
              <span className="ml-2 px-1.5 py-0.5 rounded text-xs mono"
                style={{ background: "rgba(139,92,246,0.15)", color: "#8b5cf6", fontSize: 9, border: "1px solid rgba(139,92,246,0.3)" }}>
                ACTIVATED
              </span>
            </div>
            <div className="p-3 space-y-1.5">
              {V2_CONSTRAINTS.map((c) => (
                <div key={c.label} className="flex items-start gap-2 rounded-lg p-2"
                  style={{ background: "var(--bg-base)", border: "1px solid rgba(139,92,246,0.2)" }}>
                  <CheckCircle size={12} style={{ color: "#8b5cf6", marginTop: 1, flexShrink: 0 }} />
                  <div>
                    <p className="text-xs font-mono text-[var(--text-1)]">{c.label}({c.prop})</p>
                    <p className="text-xs" style={{ color: "#8b5cf6", fontSize: 9 }}>{c.type} · Active</p>
                  </div>
=======
              {!neo4jOnline && (
                <div className="rounded-lg p-2 text-xs"
                  style={{ background: "#1a1500", border: "1px solid #f59e0b33", color: "#f59e0b" }}>
                  ! Neo4j offline — constraint status unavailable
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                </div>
              ))}
              <div className="rounded-lg p-2 text-xs"
                style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.2)", color: "#8b5cf6" }}>
                NODE KEY constraints require Neo4j Enterprise (skipped on Community)
              </div>
            </div>
          </div>

          {/* PostgreSQL table counts */}
<<<<<<< HEAD
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <Database size={11} style={{ color: "#3b82f6" }} />
              <h2 className="text-sm font-semibold text-[var(--text-1)]">PostgreSQL Tables</h2>
=======
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center gap-2"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <Database size={11} style={{ color: "#3b82f6" }} />
              <h2 className="text-sm font-semibold text-white">PostgreSQL Tables</h2>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3" style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <h2 className="text-sm font-semibold text-[var(--text-1)]">ID Normalization</h2>
=======
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">ID Normalization</h2>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
            </div>
            <div className="p-3 space-y-1.5">
              {ID_FORMAT.map((f) => (
                <div key={f.entity} className="rounded-lg px-3 py-2"
<<<<<<< HEAD
                  style={{ background: "var(--bg-base)", border: "1px solid var(--border)" }}>
                  <p className="text-xs font-bold text-[var(--text-1)]">{f.entity}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: "var(--text-4)", fontSize: 10 }}>{f.format}</p>
=======
                  style={{ background: "#0a0e1a", border: "1px solid #1e2d45" }}>
                  <p className="text-xs font-bold text-white">{f.entity}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: "#475569", fontSize: 10 }}>{f.format}</p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                </div>
              ))}
            </div>
          </div>

          {/* Phase Progress */}
<<<<<<< HEAD
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "var(--bg-base)", borderBottom: "1px solid var(--border)" }}>
              <h2 className="text-sm font-semibold text-[var(--text-1)]">Phase Progress</h2>
=======
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3 flex items-center justify-between"
              style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Phase Progress</h2>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
              <span className="mono text-xs px-2 py-0.5 rounded"
                style={{ background: donePct === 100 ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
                         color: donePct === 100 ? "#10b981" : "#f59e0b",
                         border: `1px solid ${donePct === 100 ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.2)"}`,
                         fontSize: 9 }}>
                {donePct}%
              </span>
            </div>
            <div className="p-3 space-y-1.5">
              {PHASE_ITEMS.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {item.done
                    ? <CheckCircle size={11} style={{ color: "#10b981", flexShrink: 0 }} />
<<<<<<< HEAD
                    : <Circle     size={11} style={{ color: "var(--text-4)",  flexShrink: 0 }} />}
                  <span style={{ color: item.done ? "var(--text-1)" : "var(--text-4)" }}>{item.label}</span>
                </div>
              ))}
              <div className="mt-3 h-1.5 rounded-full" style={{ background: "var(--border)" }}>
=======
                    : <Circle     size={11} style={{ color: "#334155",  flexShrink: 0 }} />}
                  <span style={{ color: item.done ? "#cbd5e1" : "#475569" }}>{item.label}</span>
                </div>
              ))}
              <div className="mt-3 h-1.5 rounded-full" style={{ background: "#1e2d45" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                <div className="h-1.5 rounded-full transition-all"
                  style={{ width: `${donePct}%`, background: donePct === 100 ? "#10b981" : "linear-gradient(90deg,#10b981,#3b82f6)" }} />
              </div>
              {donePct === 100 && (
                <p className="text-xs text-center pt-1" style={{ color: "#10b981" }}>
                  All phases complete ✓
                </p>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
