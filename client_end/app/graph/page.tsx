"use client";

import { useState } from "react";
import { api, type GraphResult } from "@/lib/api";
import { Network, Search, Layers, Info, Database, GitBranch, RefreshCw } from "lucide-react";
import GraphCanvas from "./GraphCanvas";

const ENTITY_TYPES = ["AC", "Booth", "Issue", "Candidate", "Party", "Scheme"];

const NODE_COLORS: Record<string, string> = {
  AssemblyConstituency: "#f97316",
  Booth:        "#3b82f6",
  Issue:        "#ef4444",
  Candidate:    "#10b981",
  Party:        "#8b5cf6",
  Scheme:       "#f59e0b",
  Narrative:    "#ec4899",
  PulseEvent:   "#06b6d4",
  DataQuality:  "#84cc16",
  SchemeGap:    "#fb923c",
  ContradictionFlag: "#dc2626",
  TwinScenario: "#a78bfa",
};

const QUICK_QUERIES = [
  { label: "Gorakhpur Urban AC", type: "AC", id: "GKP_URBAN" },
  { label: "Booth 001",          type: "Booth", id: "GKP_322_001" },
  { label: "BJP Party",          type: "Party", id: "BJP" },
  { label: "Water Supply Issue", type: "Issue", id: "water_supply" },
];

export default function GraphPage() {
  const [entityType, setEntityType] = useState("AC");
  const [entityId, setEntityId] = useState("GKP_URBAN");
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<GraphResult["nodes"][number] | null>(null);
  const [activeTab, setActiveTab] = useState<"query"|"legend"|"stats">("query");

  async function load(type?: string, id?: string) {
    const t = type ?? entityType;
    const i = id ?? entityId;
    setLoading(true); setError(""); setSelected(null);
    try {
      const result = await api.subgraph(t, i);
      setGraph(result);
    } catch {
      setError("Failed to load subgraph. Check API and entity ID.");
    } finally { setLoading(false); }
  }

  // Node type counts
  const nodeCounts: Record<string, number> = {};
  graph?.nodes.forEach((n) => { nodeCounts[n.type] = (nodeCounts[n.type] ?? 0) + 1; });
  const edgeCounts: Record<string, number> = {};
  graph?.edges.forEach((e) => { edgeCounts[e.type] = (edgeCounts[e.type] ?? 0) + 1; });

  return (
    <div className="flex h-screen" style={{ background: "#060b14" }}>
      {/* Left panel */}
      <div className="w-72 flex-shrink-0 flex flex-col" style={{ borderRight: "1px solid #1a2b44" }}>
        {/* Header */}
        <div className="px-4 py-3.5" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-2 mb-0.5">
            <Network size={13} style={{ color: "#8b5cf6" }} />
            <h1 className="text-sm font-bold text-white">Knowledge Graph</h1>
          </div>
          <p className="text-xs mono" style={{ color: "#4d6480" }}>Neo4j 1-hop subgraph explorer</p>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: "1px solid #1a2b44" }}>
          {[
            { id: "query", label: "Query", icon: Search },
            { id: "legend", label: "Schema", icon: Layers },
            { id: "stats", label: "Stats", icon: Database },
          ].map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setActiveTab(id as typeof activeTab)}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs transition-all"
              style={{
                background: activeTab === id ? "#0f1929" : "transparent",
                borderBottom: activeTab === id ? "2px solid #8b5cf6" : "2px solid transparent",
                color: activeTab === id ? "#8b5cf6" : "#4d6480",
              }}>
              <Icon size={10} /> {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "query" && (
            <div className="p-4 space-y-3">
              <div>
                <p className="label mb-1.5" style={{ color: "#4d6480" }}>Entity Type</p>
                <div className="flex flex-wrap gap-1.5">
                  {ENTITY_TYPES.map((t) => (
                    <button key={t} onClick={() => setEntityType(t)}
                      className="px-2.5 py-1 rounded mono text-xs transition-all"
                      style={{
                        background: entityType === t ? "#8b5cf620" : "#0b1220",
                        border: `1px solid ${entityType === t ? "#8b5cf6" : "#1a2b44"}`,
                        color: entityType === t ? "#8b5cf6" : "#4d6480",
                        fontSize: 10
                      }}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="label mb-1.5" style={{ color: "#4d6480" }}>Entity ID</p>
                <input value={entityId} onChange={(e) => setEntityId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && load()}
                  placeholder="e.g. GKP_URBAN"
                  className="w-full px-3 py-2 rounded-md text-xs mono outline-none text-white"
                  style={{ background: "#0b1220", border: "1px solid #1a2b44" }} />
              </div>
              <button onClick={() => load()} disabled={loading}
                className="w-full py-2.5 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all hover:opacity-80 disabled:opacity-40"
                style={{ background: "#8b5cf6", color: "#fff" }}>
                {loading ? <><RefreshCw size={11} className="animate-spin" /> Loading…</> : <><Search size={11} /> Execute Query</>}
              </button>
              {error && (
                <div className="rounded-md px-3 py-2 text-xs" style={{ background: "#ef444415", border: "1px solid #ef444440", color: "#ef4444" }}>
                  {error}
                </div>
              )}

              {/* Quick queries */}
              <div>
                <p className="label mb-1.5" style={{ color: "#4d6480" }}>Quick Queries</p>
                <div className="space-y-1">
                  {QUICK_QUERIES.map((q) => (
                    <button key={q.id} onClick={() => { setEntityType(q.type); setEntityId(q.id); load(q.type, q.id); }}
                      className="w-full text-left px-3 py-2 rounded-md text-xs transition-all hover:bg-white/5"
                      style={{ border: "1px solid #1a2b44", color: "#4d6480" }}>
                      <span className="mono" style={{ color: "#8b5cf6" }}>{q.type}</span>
                      <span className="mx-1.5" style={{ color: "#2e4260" }}>·</span>
                      {q.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "legend" && (
            <div className="p-4">
              <p className="label mb-3" style={{ color: "#4d6480" }}>Node Types</p>
              <div className="space-y-1.5">
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-2.5 py-1">
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
                    <span className="text-xs mono text-white">{type}</span>
                    <div className="flex-1 h-px" style={{ background: `${color}30` }} />
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-3" style={{ borderTop: "1px solid #1a2b44" }}>
                <p className="label mb-2" style={{ color: "#4d6480" }}>Controls</p>
                <div className="space-y-1 text-xs" style={{ color: "#4d6480" }}>
                  <p>• Drag nodes to reposition</p>
                  <p>• Click node to inspect properties</p>
                  <p>• Scroll to zoom (Leaflet)</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "stats" && graph && (
            <div className="p-4">
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="rounded-md p-3" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                  <p className="label mb-1" style={{ color: "#2e4260" }}>Total Nodes</p>
                  <p className="mono text-xl font-bold" style={{ color: "#8b5cf6" }}>{graph.nodes.length}</p>
                </div>
                <div className="rounded-md p-3" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                  <p className="label mb-1" style={{ color: "#2e4260" }}>Total Edges</p>
                  <p className="mono text-xl font-bold" style={{ color: "#06b6d4" }}>{graph.edges.length}</p>
                </div>
              </div>

              {Object.keys(nodeCounts).length > 0 && (
                <>
                  <p className="label mb-2" style={{ color: "#4d6480" }}>Nodes by Type</p>
                  <div className="space-y-1.5 mb-4">
                    {Object.entries(nodeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                      <div key={type} className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ background: NODE_COLORS[type] ?? "#64748b" }} />
                        <span className="text-xs flex-1" style={{ color: "#8ba0bc" }}>{type}</span>
                        <span className="mono text-xs" style={{ color: NODE_COLORS[type] ?? "#64748b" }}>{count}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {Object.keys(edgeCounts).length > 0 && (
                <>
                  <p className="label mb-2" style={{ color: "#4d6480" }}>Edges by Type</p>
                  <div className="space-y-1">
                    {Object.entries(edgeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                      <div key={type} className="flex items-center gap-2">
                        <span className="text-xs flex-1 mono" style={{ color: "#4d6480" }}>{type}</span>
                        <span className="mono text-xs" style={{ color: "#8ba0bc" }}>{count}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === "stats" && !graph && (
            <div className="flex flex-col items-center justify-center h-32">
              <p className="text-xs" style={{ color: "#2e4260" }}>Load a subgraph first</p>
            </div>
          )}
        </div>

        {/* Node property inspector */}
        {selected && (
          <div className="px-4 py-3" style={{ borderTop: "1px solid #1a2b44", background: "#0b1220" }}>
            <div className="flex items-center gap-2 mb-2">
              <Info size={10} style={{ color: "#8b5cf6" }} />
              <p className="label" style={{ color: "#4d6480" }}>Node Inspector</p>
            </div>
            <div className="rounded-md p-2.5" style={{ background: "#060b14", border: "1px solid #1a2b44" }}>
              <div className="flex items-center gap-2 mb-2">
                <span className="mono text-xs font-bold text-white">{selected.label}</span>
                <span className="mono text-xs px-1.5 py-0.5 rounded"
                  style={{ background: `${NODE_COLORS[selected.type] ?? "#64748b"}20`, color: NODE_COLORS[selected.type] ?? "#64748b", fontSize: 9 }}>
                  {selected.type}
                </span>
              </div>
              <div className="space-y-0.5 max-h-32 overflow-y-auto">
                {Object.entries(selected.properties).map(([k, v]) => (
                  <div key={k} className="flex gap-2 text-xs py-0.5" style={{ borderBottom: "1px solid #0b1220" }}>
                    <span className="mono w-20 flex-shrink-0 truncate" style={{ color: "#2e4260", fontSize: 9 }}>{k}</span>
                    <span className="text-white truncate" style={{ fontSize: 10 }}>{String(v ?? "—")}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        {!graph ? (
          <div className="w-full h-full flex flex-col items-center justify-center">
            <div className="w-24 h-24 mb-6 opacity-20">
              <Network size={96} style={{ color: "#1a2b44" }} />
            </div>
            <p className="text-white mb-1 font-medium">Knowledge Graph Explorer</p>
            <p className="text-sm mb-6" style={{ color: "#4d6480" }}>Select an entity type and ID, then execute</p>
            <div className="grid grid-cols-2 gap-2 max-w-xs">
              {QUICK_QUERIES.map((q) => (
                <button key={q.id} onClick={() => { setEntityType(q.type); setEntityId(q.id); load(q.type, q.id); }}
                  className="px-3 py-2.5 rounded-md text-xs text-left transition-all hover:opacity-80"
                  style={{ background: "#0f1929", border: "1px solid #1a2b44", color: "#4d6480" }}>
                  <p className="mono" style={{ color: "#8b5cf6", fontSize: 9 }}>{q.type}</p>
                  <p className="text-white mt-0.5">{q.label}</p>
                </button>
              ))}
            </div>
          </div>
        ) : graph.nodes.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center">
            <p className="text-sm" style={{ color: "#4d6480" }}>No graph data returned for this entity.</p>
          </div>
        ) : (
          <GraphCanvas nodes={graph.nodes} edges={graph.edges} nodeColors={NODE_COLORS} onSelect={setSelected} />
        )}
        {/* Graph overlay */}
        {graph && graph.nodes.length > 0 && (
          <div className="absolute bottom-4 left-4 mono text-xs"
            style={{ background: "rgba(6,11,20,0.9)", border: "1px solid #1a2b44", borderRadius: 6, padding: "6px 10px", color: "#4d6480" }}>
            {graph.nodes.length} nodes · {graph.edges.length} edges · drag to move · click to inspect
          </div>
        )}
      </div>
    </div>
  );
}
