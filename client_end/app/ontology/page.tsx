import { BookOpen, CheckCircle, Circle } from "lucide-react";

const ENTITIES = [
  {
    name: "State",
    id: "state_id",
    example: "UP",
    desc: "Top-level administrative unit (Uttar Pradesh)",
    color: "#f97316",
  },
  {
    name: "District",
    id: "district_id",
    example: "GKP",
    desc: "District within a state (Gorakhpur)",
    color: "#fb923c",
  },
  {
    name: "AssemblyConstituency",
    id: "ac_id",
    example: "GKP_URBAN",
    desc: "Vidhan Sabha segment, the primary analysis unit",
    color: "#3b82f6",
  },
  {
    name: "Booth",
    id: "booth_id",
    example: "GKP_322_001",
    desc: "Individual polling booth — atomic unit of data",
    color: "#60a5fa",
  },
  {
    name: "Candidate",
    id: "candidate_id",
    example: "GKP_CAN_2022_001",
    desc: "Contesting candidate across election years",
    color: "#10b981",
  },
  {
    name: "Party",
    id: "party_id",
    example: "BJP",
    desc: "Political party (BJP, SP, BSP, INC, etc.)",
    color: "#8b5cf6",
  },
  {
    name: "Issue",
    id: "issue_code",
    example: "water_supply",
    desc: "Political/civic issue tracked across booths",
    color: "#ef4444",
  },
  {
    name: "Scheme",
    id: "scheme_id",
    example: "PM_UJJWALA",
    desc: "Government welfare scheme",
    color: "#f59e0b",
  },
  {
    name: "PulseEvent",
    id: "event_id",
    example: "PE_2024_001",
    desc: "Digitally-observed political event (social, news, grievance)",
    color: "#06b6d4",
  },
  {
    name: "Narrative",
    id: "(booth_id, narrative_type, computed_at)",
    example: "anti_incumbency @ B001",
    desc: "Detected narrative pattern at booth level",
    color: "#ec4899",
  },
  {
    name: "DataQuality",
    id: "(booth_id, computed_at)",
    example: "DQ_B001_2024",
    desc: "Confidence and quality metrics per booth window",
    color: "#84cc16",
  },
  {
    name: "SchemeGap",
    id: "(booth_id, scheme_name, computed_at)",
    example: "GAP_B001_UJJWALA",
    desc: "Delivery gap between scheme entitlement and actual coverage",
    color: "#f97316",
  },
  {
    name: "ContradictionFlag",
    id: "(booth_id, entity, source_a, source_b, computed_at)",
    example: "CF_B001_BJP_NEWS_SM",
    desc: "Cross-source signal conflict flagged for review",
    color: "#dc2626",
  },
  {
    name: "GovernanceAsset",
    id: "asset_id",
    example: "ROAD_001",
    desc: "Physical governance delivery (roads, schools, hospitals)",
    color: "#94a3b8",
  },
  {
    name: "TwinScenario",
    id: "scenario_id",
    example: "SCN_WATER_2024",
    desc: "Hypothetical intervention and projected directional effects",
    color: "#a78bfa",
  },
];

const RELATIONSHIPS = [
  { from: "State", to: "District", type: "HAS_DISTRICT", dir: "→" },
  { from: "District", to: "AssemblyConstituency", type: "HAS_AC", dir: "→" },
  { from: "AssemblyConstituency", to: "Booth", type: "HAS_BOOTH", dir: "→" },
  { from: "Booth", to: "PulseEvent", type: "AT_BOOTH", dir: "←" },
  { from: "Candidate", to: "Party", type: "MEMBER_OF", dir: "→" },
  { from: "Candidate", to: "AssemblyConstituency", type: "CONTESTED_IN", dir: "→" },
  { from: "Booth", to: "DataQuality", type: "HAS_QUALITY", dir: "→" },
  { from: "Booth", to: "Narrative", type: "HAS_NARRATIVE", dir: "→" },
  { from: "Narrative", to: "Issue", type: "ABOUT_ISSUE", dir: "→" },
  { from: "Narrative", to: "Party", type: "INVOLVES_PARTY", dir: "→" },
  { from: "Narrative", to: "Candidate", type: "INVOLVES_CANDIDATE", dir: "→" },
  { from: "Booth", to: "SchemeGap", type: "HAS_SCHEME_GAP", dir: "→" },
  { from: "SchemeGap", to: "Scheme", type: "FOR_SCHEME", dir: "→" },
  { from: "SchemeGap", to: "Issue", type: "TAGGED_ISSUE", dir: "→" },
  { from: "Booth", to: "ContradictionFlag", type: "HAS_CONTRADICTION", dir: "→" },
  { from: "ContradictionFlag", to: "Party", type: "ABOUT_ENTITY", dir: "→" },
  { from: "PulseEvent", to: "Issue", type: "ABOUT_ISSUE", dir: "→" },
  { from: "PulseEvent", to: "Party", type: "MENTIONS", dir: "→" },
  { from: "AssemblyConstituency", to: "TwinScenario", type: "HAS_SCENARIO", dir: "→" },
];

const CONSTRAINTS = [
  { label: "AssemblyConstituency(ac_id)", type: "UNIQUE", active: true },
  { label: "Booth(booth_id)", type: "UNIQUE", active: true },
  { label: "Party(party_id)", type: "UNIQUE", active: true },
  { label: "Candidate(candidate_id)", type: "UNIQUE", active: true },
  { label: "Issue(issue_code)", type: "UNIQUE", active: true },
  { label: "Scheme(scheme_id)", type: "UNIQUE", active: true },
  { label: "DataQuality(booth_id, computed_at)", type: "NODE KEY", active: false },
  { label: "Narrative(booth_id, narrative_type, computed_at)", type: "NODE KEY", active: false },
  { label: "SchemeGap(booth_id, scheme_name, computed_at)", type: "NODE KEY", active: false },
  { label: "ContradictionFlag(booth_id, entity, source_a, source_b, computed_at)", type: "NODE KEY", active: false },
];

const ID_FORMAT = [
  { entity: "State", format: "UP" },
  { entity: "District", format: "GKP" },
  { entity: "AC", format: "GKP_URBAN" },
  { entity: "Booth", format: "GKP_322_<booth_number_3digit>" },
  { entity: "Candidate", format: "GKP_CAN_<year>_<seq>" },
  { entity: "PulseEvent", format: "PE_<source>_<hash>" },
  { entity: "Scheme", format: "SCHEME_<scheme_name_upper>" },
  { entity: "TwinScenario", format: "SCN_<type>_<year>" },
];

export default function OntologyPage() {
  return (
    <div className="min-h-screen p-6" style={{ background: "#0a0e1a" }}>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-2 h-6 rounded-full" style={{ background: "#3b82f6" }} />
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen size={20} style={{ color: "#3b82f6" }} /> Ontology Specification
          </h1>
        </div>
        <p className="text-sm ml-5" style={{ color: "#94a3b8" }}>
          Domain model · Entity classes · Relationship taxonomy · Constraints · ID conventions
        </p>
      </div>

      {/* Version banner */}
      <div className="rounded-xl p-4 mb-6 flex items-center justify-between"
        style={{ background: "#0f1e30", border: "1px solid #3b82f633" }}>
        <div>
          <p className="text-xs font-semibold" style={{ color: "#3b82f6" }}>ONTOLOGY VERSION</p>
          <p className="text-sm text-white font-medium">v1.0.0-ontology-phase · UP Election Ontology Engine (Gorakhpur)</p>
        </div>
        <div className="text-right">
          <p className="text-xs" style={{ color: "#475569" }}>Status</p>
          <p className="text-xs font-medium" style={{ color: "#f59e0b" }}>Phase 0 — Freeze in progress</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Entity Classes */}
        <div className="lg:col-span-2">
          <div className="rounded-xl overflow-hidden mb-6" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Entity Classes ({ENTITIES.length})</h2>
            </div>
            <div className="divide-y" style={{ borderColor: "#1e2d4520" }}>
              {ENTITIES.map((e) => (
                <div key={e.name} className="px-4 py-3 flex items-start gap-3 hover:bg-white/[0.02] transition-colors"
                  style={{ background: "#111827" }}>
                  <div className="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: e.color }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm font-bold" style={{ color: e.color }}>{e.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded font-mono"
                        style={{ background: "#1e2d45", color: "#94a3b8" }}>
                        ID: {e.id}
                      </span>
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: "#94a3b8" }}>{e.desc}</p>
                    <p className="text-xs mt-0.5 font-mono" style={{ color: "#475569" }}>e.g. {e.example}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Relationship Taxonomy */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Relationship Taxonomy ({RELATIONSHIPS.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
                    {["From", "Direction", "Type", "To"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium uppercase tracking-wider"
                        style={{ color: "#475569" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {RELATIONSHIPS.map((r, i) => (
                    <tr key={i}
                      style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4520" }}>
                      <td className="px-4 py-2 font-mono font-bold" style={{ color: "#3b82f6" }}>{r.from}</td>
                      <td className="px-4 py-2 text-center" style={{ color: "#475569" }}>{r.dir}</td>
                      <td className="px-4 py-2 font-mono text-white">[:{r.type}]</td>
                      <td className="px-4 py-2 font-mono font-bold" style={{ color: "#10b981" }}>{r.to}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-6">
          {/* Constraints */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Neo4j Constraints</h2>
            </div>
            <div className="p-3 space-y-2">
              {CONSTRAINTS.map((c, i) => (
                <div key={i} className="flex items-start gap-2 rounded-lg p-2"
                  style={{ background: "#0a0e1a", border: "1px solid #1e2d45" }}>
                  {c.active
                    ? <CheckCircle size={13} style={{ color: "#10b981", marginTop: 1, flexShrink: 0 }} />
                    : <Circle size={13} style={{ color: "#475569", marginTop: 1, flexShrink: 0 }} />}
                  <div>
                    <p className="text-xs font-mono text-white">{c.label}</p>
                    <p className="text-xs" style={{ color: c.active ? "#10b981" : "#475569" }}>
                      {c.type} · {c.active ? "Active" : "Commented out"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-4 pb-3">
              <div className="rounded-lg p-2 text-xs" style={{ background: "#1a0f00", border: "1px solid #f9731633", color: "#f97316" }}>
                ⚠ NODE KEY constraints require Neo4j Enterprise or AuraDB. Activate uniqueness constraints first.
              </div>
            </div>
          </div>

          {/* ID Format */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">ID Normalization Standard</h2>
            </div>
            <div className="p-3 space-y-2">
              {ID_FORMAT.map((f) => (
                <div key={f.entity} className="rounded-lg p-2"
                  style={{ background: "#0a0e1a", border: "1px solid #1e2d45" }}>
                  <p className="text-xs font-bold text-white">{f.entity}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: "#94a3b8" }}>{f.format}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Checklist progress */}
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #1e2d45" }}>
            <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
              <h2 className="text-sm font-semibold text-white">Ontology Phase Progress</h2>
            </div>
            <div className="p-3 space-y-2">
              {[
                { label: "Entity class definitions", done: true },
                { label: "ID normalization rules", done: true },
                { label: "Relationship taxonomy", done: true },
                { label: "Ontology version field", done: true },
                { label: "Constraint activation (v2)", done: false },
                { label: "Sign-off with team", done: false },
                { label: "Graph hardening (loaders)", done: false },
                { label: "HeatMap multi-layer (>=85%)", done: false },
                { label: "Twin snapshot endpoint", done: false },
                { label: "Demographic segment API", done: false },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {item.done
                    ? <CheckCircle size={12} style={{ color: "#10b981", flexShrink: 0 }} />
                    : <Circle size={12} style={{ color: "#475569", flexShrink: 0 }} />}
                  <span style={{ color: item.done ? "#f1f5f9" : "#64748b" }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
