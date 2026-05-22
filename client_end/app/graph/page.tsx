"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { GraphResult, GraphNode, BoothRow } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";
import {
  Network, Search, Layers, Database, RefreshCw,
  ChevronRight, Info, ZoomIn, ZoomOut, RotateCcw,
  History, Maximize2, ArrowLeft, GitBranch, Box, AlertTriangle
} from "lucide-react";
import GraphCanvas from "./GraphCanvas";

// ── Constants ──────────────────────────────────────────────────────────────────

// High-volume media nodes — hidden by default, togglable
const DEFAULT_EXCLUDED = ["YouTubeVideo", "Channel"];

// All node types that can be toggled for visibility
const ALL_FILTER_TYPES = [
  "YouTubeVideo", "Channel", "Candidate", "Booth",
  "Issue", "Party", "Narrative", "District", "Panchayat",
];

const NODE_COLORS: Record<string, string> = {
  AssemblyConstituency: "#f97316",
  Booth:                "#3b82f6",
  Issue:                "#ef4444",
  Candidate:            "#10b981",
  Party:                "#8b5cf6",
  Scheme:               "#f59e0b",
  Narrative:            "#ec4899",
  PulseEvent:           "#06b6d4",
  DataQuality:          "#84cc16",
  SchemeGap:            "#fb923c",
  ContradictionFlag:    "#dc2626",
  TwinScenario:         "#a78bfa",
  YouTubeVideo:         "#ff0000",
  Channel:              "#ff4444",
  Panchayat:            "#14b8a6",
  District:             "#f97316",
  State:                "#f97316",
};

// Map graph node types → API entity_type param
const NODE_TYPE_TO_ENTITY: Record<string, string> = {
  AssemblyConstituency: "AC",
  Booth:                "Booth",
  Issue:                "Issue",
  Candidate:            "Candidate",
  Party:                "Party",
  Scheme:               "Scheme",
  Narrative:            "Narrative",
  YouTubeVideo:         "YouTubeVideo",
  Channel:              "Channel",
  Panchayat:            "Panchayat",
  District:             "District",
  State:                "State",
};

const ENTITY_TYPES = ["AC", "Booth", "Issue", "Candidate", "Party", "Scheme", "Narrative"];

const QUICK_QUERIES = [
  { label: "Gorakhpur Urban AC",  type: "AC",        id: "GKP_322",              desc: "All AC connections" },
  { label: "BJP Party",           type: "Party",     id: "BJP",                  desc: "BJP party network" },
  { label: "SP Party",            type: "Party",     id: "SP",                   desc: "SP opposition network" },
  { label: "Water Issue",         type: "Issue",     id: "water",                desc: "Water issue network" },
  { label: "Education Issue",     type: "Issue",     id: "education",            desc: "Education issue" },
  { label: "Adityanath 2022",     type: "Candidate", id: "ADITYANATH_2022",      desc: "Incumbent candidate" },
  { label: "Booth 001",           type: "Booth",     id: "GKP_322_001",          desc: "Primary School Rampur" },
  { label: "Booth 010",           type: "Booth",     id: "GKP_322_010",          desc: "Anganwadi Center 1" },
];

// ── Types ──────────────────────────────────────────────────────────────────────

interface HistoryEntry {
  type: string;
  id: string;
  nodeCount: number;
  edgeCount: number;
  graph: GraphResult;
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function GraphPage() {
  const { theme } = useTheme();
  const [entityType, setEntityType] = useState("AC");
  const [entityId, setEntityId] = useState("GKP_322");
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [activeTab, setActiveTab] = useState<"query" | "legend" | "stats" | "history">("query");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [booths, setBooths] = useState<BoothRow[]>([]);
  const [boothSearch, setBoothSearch] = useState("");
  const [canvasKey, setCanvasKey] = useState(0);
  const [excludeTypes, setExcludeTypes] = useState<string[]>(DEFAULT_EXCLUDED);

  useEffect(() => {
    api.booths("GKP_URBAN").then((r) => setBooths(r.booths)).catch(() => {});
  }, []);

  const load = useCallback(async (
    type?: string,
    id?: string,
    excl?: string[],
    pushHistory = true,
  ) => {
    const t = (type ?? entityType).trim();
    const i = (id ?? entityId).trim();
    const ex = excl ?? excludeTypes;
    if (!i) return;
    setLoading(true); setError(""); setSelected(null);
    try {
      const result = await api.subgraph(t, i, ex);
      if (result.nodes.length === 0) {
        setError(`No graph data found for ${t} "${i}". Try removing type filters or check the entity ID.`);
        return;
      }
      setGraph(result);
      setCanvasKey((k) => k + 1);
      if (pushHistory) {
        setHistory((prev) => [
          ...prev.slice(-19),
          { type: t, id: i, nodeCount: result.nodes.length, edgeCount: result.edges.length, graph: result },
        ]);
      }
    } catch {
      setError(`Failed to reach the API for ${t} "${i}". Ensure the backend is running on port 8000.`);
    } finally { setLoading(false); }
  }, [entityType, entityId, excludeTypes]);

  function toggleExclude(nodeType: string) {
    setExcludeTypes((prev) => {
      const next = prev.includes(nodeType)
        ? prev.filter((t) => t !== nodeType)
        : [...prev, nodeType];
      // Re-fetch with updated filter if graph is already loaded
      if (graph) {
        setTimeout(() => load(entityType, entityId, next), 0);
      }
      return next;
    });
  }

  async function expandNode(node: GraphNode) {
    const entityT = NODE_TYPE_TO_ENTITY[node.type];
    if (!entityT) {
      setError(`Cannot expand ${node.type} nodes — no direct API mapping.`);
      return;
    }
    setEntityType(entityT);
    setEntityId(node.id);
    await load(entityT, node.id, excludeTypes);
  }

  function restoreHistory(entry: HistoryEntry) {
    setGraph(entry.graph);
    setEntityType(entry.type);
    setEntityId(entry.id);
    setSelected(null);
    setError("");
    setCanvasKey((k) => k + 1);
  }

  function resetView() {
    setCanvasKey((k) => k + 1);
  }

  // Derived stats
  const nodeCounts: Record<string, number> = {};
  graph?.nodes.forEach((n) => { nodeCounts[n.type] = (nodeCounts[n.type] ?? 0) + 1; });
  const edgeCounts: Record<string, number> = {};
  graph?.edges.forEach((e) => { edgeCounts[e.type] = (edgeCounts[e.type] ?? 0) + 1; });

  const filteredBooths = booths
    .filter((b) => !boothSearch || b.name.toLowerCase().includes(boothSearch.toLowerCase()) ||
      String(b.booth_number).includes(boothSearch))
    .slice(0, 25);

  const canExpand = selected ? !!NODE_TYPE_TO_ENTITY[selected.type] : false;

  // ── Styles via CSS vars ────────────────────────────────────────────────────
  const S = {
    base:    "var(--bg-base)",
    surface: "var(--bg-surface)",
    card:    "var(--bg-card)",
    hover:   "var(--bg-hover)",
    border:  "var(--border)",
    bright:  "var(--border-bright)",
    t1:      "var(--text-1)",
    t2:      "var(--text-2)",
    t3:      "var(--text-3)",
    t4:      "var(--text-4)",
    saffron: "var(--saffron)",
  };

  return (
    <div className="flex h-screen" style={{ background: S.base }}>

      {/* ── Left panel ──────────────────────────────────────────────────────── */}
      <div className="w-72 flex-shrink-0 flex flex-col" style={{ borderRight: `1px solid ${S.border}`, background: S.base }}>

        {/* Header */}
        <div className="px-4 py-3.5" style={{ borderBottom: `1px solid ${S.border}` }}>
          <div className="flex items-center gap-2 mb-0.5">
            <div className="w-6 h-6 rounded flex items-center justify-center"
              style={{ background: "rgba(249,115,22,0.15)", border: "1px solid rgba(249,115,22,0.3)" }}>
              <Network size={12} style={{ color: S.saffron }} />
            </div>
            <h1 className="text-sm font-bold" style={{ color: S.t1 }}>Knowledge Graph</h1>
          </div>
          <p className="text-xs mono" style={{ color: S.t3 }}>Neo4j 1-hop subgraph explorer</p>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: `1px solid ${S.border}` }}>
          {[
            { id: "query",   label: "Query",   icon: Search  },
            { id: "legend",  label: "Schema",  icon: Layers  },
            { id: "stats",   label: "Stats",   icon: Database },
            { id: "history", label: "History", icon: History },
          ].map(({ id, label, icon: Icon }) => {
            const isActive = activeTab === id;
            return (
              <button key={id} onClick={() => setActiveTab(id as typeof activeTab)}
                className="flex-1 flex items-center justify-center gap-1 py-2.5 text-xs transition-all"
                style={{
                  background: isActive ? S.surface : "transparent",
                  borderBottom: isActive ? `2px solid ${S.saffron}` : "2px solid transparent",
                  color: isActive ? S.saffron : S.t3,
                }}>
                <Icon size={10} /> {label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">

          {/* ── QUERY TAB ── */}
          {activeTab === "query" && (
            <div className="p-4 space-y-4">
              {/* Entity type selector */}
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Entity Type</p>
                <div className="flex flex-wrap gap-1.5">
                  {ENTITY_TYPES.map((t) => (
                    <button key={t} onClick={() => { setEntityType(t); setBoothSearch(""); }}
                      className="px-2.5 py-1 rounded mono text-xs transition-all"
                      style={{
                        background: entityType === t ? "rgba(249,115,22,0.15)" : S.surface,
                        border: `1px solid ${entityType === t ? "rgba(249,115,22,0.5)" : S.border}`,
                        color: entityType === t ? S.saffron : S.t3,
                        fontSize: 10,
                      }}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Booth autocomplete */}
              {entityType === "Booth" && booths.length > 0 && (
                <div>
                  <p className="label mb-1.5" style={{ color: S.t4 }}>Search Booths</p>
                  <input
                    value={boothSearch}
                    onChange={(e) => setBoothSearch(e.target.value)}
                    placeholder="Booth name or number…"
                    className="w-full px-3 py-2 rounded-md text-xs outline-none mono"
                    style={{ background: S.surface, border: `1px solid ${S.border}`, color: S.t1 }} />
                  <div className="mt-1.5 max-h-40 overflow-y-auto rounded-md"
                    style={{ border: `1px solid ${S.border}`, background: S.card }}>
                    {filteredBooths.map((b) => (
                      <button key={b.booth_id}
                        onClick={() => { setEntityId(b.booth_id); setBoothSearch(b.name); }}
                        className="w-full text-left flex items-center gap-2 px-3 py-2 text-xs transition-all"
                        style={{
                          borderBottom: `1px solid ${S.border}`,
                          color: entityId === b.booth_id ? S.saffron : S.t2,
                          background: entityId === b.booth_id ? "rgba(249,115,22,0.08)" : "transparent",
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = S.hover}
                        onMouseLeave={(e) => e.currentTarget.style.background = entityId === b.booth_id ? "rgba(249,115,22,0.08)" : "transparent"}>
                        <span className="mono font-bold" style={{ color: S.saffron, fontSize: 9, minWidth: 24 }}>
                          {String(b.booth_number).padStart(3, "0")}
                        </span>
                        <span className="flex-1 truncate">{b.name}</span>
                        {b.digital_lean_label && (
                          <span className="mono text-xs" style={{ color: S.t4, fontSize: 8 }}>
                            {b.digital_lean_label.replace("_", " ")}
                          </span>
                        )}
                      </button>
                    ))}
                    {filteredBooths.length === 0 && (
                      <p className="text-xs px-3 py-2" style={{ color: S.t4 }}>No booths match.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Manual ID input */}
              <div>
                <p className="label mb-1.5" style={{ color: S.t4 }}>Entity ID</p>
                <input value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && load()}
                  placeholder={entityType === "AC" ? "e.g. GKP_URBAN" : entityType === "Booth" ? "e.g. GKP_322_001" : "entity ID…"}
                  className="w-full px-3 py-2 rounded-md text-xs mono outline-none"
                  style={{ background: S.surface, border: `1px solid ${S.border}`, color: S.t1 }} />
                <p className="text-xs mt-1" style={{ color: S.t4, fontSize: 10 }}>
                  {entityType === "AC" && "ID: GKP_322 (Gorakhpur Urban)"}
                  {entityType === "Booth" && "Format: GKP_322_001 … GKP_322_030"}
                  {entityType === "Party" && "IDs: BJP · SP · BSP · INC · AAP"}
                  {entityType === "Issue" && "IDs: water · roads · electricity · jobs · health"}
                  {entityType === "Candidate" && "e.g. ADITYANATH_2022"}
                  {entityType === "Narrative" && "e.g. anti_incumbency"}
                </p>
              </div>

              {/* Execute */}
              <button onClick={() => load()} disabled={loading || !entityId.trim()}
                className="w-full py-2.5 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all"
                style={{ background: S.saffron, color: "#fff", opacity: loading || !entityId.trim() ? 0.5 : 1 }}>
                {loading
                  ? <><RefreshCw size={11} className="animate-spin" /> Loading subgraph…</>
                  : <><Search size={11} /> Execute Query</>}
              </button>

              {error && (
                <div className="rounded-md px-3 py-2.5 text-xs flex gap-2"
                  style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", color: "var(--red)" }}>
                  <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              {/* Node type filter */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="label" style={{ color: S.t4 }}>Filter Node Types</p>
                  {excludeTypes.length > 0 && (
                    <button onClick={() => { setExcludeTypes([]); if (graph) setTimeout(() => load(entityType, entityId, []), 0); }}
                      className="text-xs mono transition-colors"
                      style={{ color: S.saffron, fontSize: 9 }}>
                      show all
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_FILTER_TYPES.map((type) => {
                    const color = NODE_COLORS[type] ?? "#64748b";
                    const excluded = excludeTypes.includes(type);
                    return (
                      <button key={type} onClick={() => toggleExclude(type)}
                        className="flex items-center gap-1 px-2 py-1 rounded mono text-xs transition-all"
                        style={{
                          background:  excluded ? S.surface : `${color}18`,
                          border:      `1px solid ${excluded ? S.border : color + "60"}`,
                          color:       excluded ? S.t4 : color,
                          opacity:     excluded ? 0.55 : 1,
                          fontSize:    9,
                        }}>
                        <span style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: excluded ? S.t4 : color, flexShrink: 0 }} />
                        {type}
                      </button>
                    );
                  })}
                </div>
                {excludeTypes.length > 0 && (
                  <p className="text-xs mt-1.5" style={{ color: S.t4, fontSize: 10 }}>
                    {excludeTypes.length} type{excludeTypes.length > 1 ? "s" : ""} hidden · click to toggle
                  </p>
                )}
              </div>

              {/* Quick queries */}
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Quick Queries</p>
                <div className="space-y-1">
                  {QUICK_QUERIES.map((q) => (
                    <button key={q.id}
                      onClick={() => { setEntityType(q.type); setEntityId(q.id); load(q.type, q.id); }}
                      className="w-full text-left px-3 py-2 rounded-md text-xs transition-all flex items-start gap-2"
                      style={{ border: `1px solid ${S.border}`, color: S.t3, background: S.surface }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = S.bright; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = S.surface; e.currentTarget.style.borderColor = S.border; }}>
                      <span className="mono font-semibold px-1.5 py-0.5 rounded flex-shrink-0"
                        style={{ background: "rgba(249,115,22,0.12)", color: S.saffron, fontSize: 9 }}>
                        {q.type}
                      </span>
                      <div className="min-w-0">
                        <p style={{ color: S.t2 }}>{q.label}</p>
                        <p style={{ color: S.t4, fontSize: 10 }}>{q.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── LEGEND TAB ── */}
          {activeTab === "legend" && (
            <div className="p-4">
              <p className="label mb-3" style={{ color: S.t4 }}>Node Types</p>
              <div className="space-y-1">
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-2.5 py-1.5 px-2 rounded-md transition-all"
                    style={{ border: "1px solid transparent" }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = S.border; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "transparent"; }}>
                    <div className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ background: color, boxShadow: `0 0 6px ${color}60` }} />
                    <span className="text-xs mono flex-1" style={{ color: S.t2 }}>{type}</span>
                    <div className="flex-1 h-px" style={{ background: `${color}25` }} />
                    <span className="mono text-xs font-bold" style={{ color, fontSize: 10 }}>
                      {nodeCounts[type] ?? "—"}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-3" style={{ borderTop: `1px solid ${S.border}` }}>
                <p className="label mb-2" style={{ color: S.t4 }}>Navigation</p>
                <div className="space-y-1.5 text-xs" style={{ color: S.t3 }}>
                  <p className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>1</span>
                    Click node to inspect properties
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>2</span>
                    Use "Expand" to load connected subgraph
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>3</span>
                    Drag nodes to reposition
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>4</span>
                    Scroll to zoom, drag canvas to pan
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>5</span>
                    Arrows show relationship direction
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── STATS TAB ── */}
          {activeTab === "stats" && (
            <div className="p-4">
              {!graph ? (
                <div className="flex flex-col items-center justify-center h-32">
                  <Box size={24} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                  <p className="text-xs" style={{ color: S.t4 }}>Load a subgraph first</p>
                </div>
              ) : (
                <>
                  {/* Summary stat cards */}
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    <div className="rounded-md p-3" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                      <p className="label mb-1" style={{ color: S.t4, fontSize: 9 }}>Nodes</p>
                      <p className="mono text-xl font-bold" style={{ color: S.saffron }}>{graph.nodes.length}</p>
                    </div>
                    <div className="rounded-md p-3" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                      <p className="label mb-1" style={{ color: S.t4, fontSize: 9 }}>Edges</p>
                      <p className="mono text-xl font-bold" style={{ color: "var(--cyan)" }}>{graph.edges.length}</p>
                    </div>
                  </div>

                  <p className="label mb-2" style={{ color: S.t4 }}>Nodes by Type</p>
                  <div className="space-y-1.5 mb-4">
                    {Object.entries(nodeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                      const pct = (count / graph.nodes.length) * 100;
                      const color = NODE_COLORS[type] ?? "#64748b";
                      return (
                        <div key={type}>
                          <div className="flex items-center gap-2 mb-0.5">
                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                            <span className="text-xs flex-1" style={{ color: S.t2 }}>{type}</span>
                            <span className="mono text-xs font-semibold" style={{ color }}>{count}</span>
                          </div>
                          <div className="h-1 rounded-full mx-4" style={{ background: S.border }}>
                            <div className="h-1 rounded-full transition-all"
                              style={{ width: `${pct}%`, background: color }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {Object.keys(edgeCounts).length > 0 && (
                    <>
                      <p className="label mb-2" style={{ color: S.t4 }}>Relationships</p>
                      <div className="space-y-1">
                        {Object.entries(edgeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                          <div key={type} className="flex items-center gap-2 px-2 py-1.5 rounded"
                            style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                            <GitBranch size={9} style={{ color: S.t4, flexShrink: 0 }} />
                            <span className="text-xs flex-1 mono" style={{ color: S.t3 }}>{type}</span>
                            <span className="mono text-xs font-semibold" style={{ color: S.saffron }}>{count}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── HISTORY TAB ── */}
          {activeTab === "history" && (
            <div className="p-4">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32">
                  <History size={24} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                  <p className="text-xs" style={{ color: S.t4 }}>No history yet</p>
                  <p className="text-xs mt-1" style={{ color: S.t4, fontSize: 10 }}>Execute a query to start</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {[...history].reverse().map((entry, i) => (
                    <button key={i}
                      onClick={() => restoreHistory(entry)}
                      className="w-full text-left px-3 py-2.5 rounded-md transition-all"
                      style={{ border: `1px solid ${S.border}`, background: S.surface }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = "rgba(249,115,22,0.4)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = S.surface; e.currentTarget.style.borderColor = S.border; }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="mono px-1.5 py-0.5 rounded text-xs"
                          style={{ background: "rgba(249,115,22,0.12)", color: S.saffron, fontSize: 9 }}>
                          {entry.type}
                        </span>
                        <span className="text-xs font-medium mono flex-1 truncate" style={{ color: S.t2 }}>{entry.id}</span>
                      </div>
                      <div className="flex gap-3 text-xs" style={{ color: S.t4 }}>
                        <span>{entry.nodeCount} nodes</span>
                        <span>·</span>
                        <span>{entry.edgeCount} edges</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Node inspector ── */}
        {selected && (
          <div className="px-4 py-3 flex-shrink-0" style={{ borderTop: `1px solid ${S.border}`, background: S.surface }}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Info size={10} style={{ color: S.saffron }} />
                <p className="label" style={{ color: S.t3, fontSize: 9 }}>Node Inspector</p>
              </div>
              <button onClick={() => setSelected(null)}
                className="text-xs px-1.5 py-0.5 rounded transition-colors"
                style={{ color: S.t4, border: `1px solid ${S.border}` }}
                onMouseEnter={(e) => e.currentTarget.style.color = S.t2}
                onMouseLeave={(e) => e.currentTarget.style.color = S.t4}>
                ✕
              </button>
            </div>
            <div className="rounded-md p-2.5 mb-2" style={{ background: S.card, border: `1px solid ${S.border}` }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full"
                  style={{ background: NODE_COLORS[selected.type] ?? "#64748b", boxShadow: `0 0 6px ${NODE_COLORS[selected.type] ?? "#64748b"}60` }} />
                <span className="mono text-xs font-bold" style={{ color: S.t1 }}>{selected.label}</span>
                <span className="mono px-1.5 py-0.5 rounded"
                  style={{ background: `${NODE_COLORS[selected.type] ?? "#64748b"}20`, color: NODE_COLORS[selected.type] ?? "#64748b", fontSize: 9 }}>
                  {selected.type}
                </span>
              </div>
              <div className="space-y-0.5 max-h-28 overflow-y-auto">
                {Object.entries(selected.properties).slice(0, 12).map(([k, v]) => (
                  <div key={k} className="flex gap-2 text-xs py-0.5" style={{ borderBottom: `1px solid ${S.border}` }}>
                    <span className="mono w-20 flex-shrink-0 truncate" style={{ color: S.t4, fontSize: 9 }}>{k}</span>
                    <span className="truncate" style={{ color: S.t2, fontSize: 10 }}>{String(v ?? "—")}</span>
                  </div>
                ))}
              </div>
            </div>
            <button
              onClick={() => expandNode(selected)}
              disabled={loading || !canExpand}
              className="w-full py-2 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all"
              style={{
                background: canExpand ? "rgba(249,115,22,0.12)" : S.surface,
                border: `1px solid ${canExpand ? "rgba(249,115,22,0.4)" : S.border}`,
                color: canExpand ? S.saffron : S.t4,
                opacity: loading ? 0.6 : 1,
                cursor: canExpand ? "pointer" : "not-allowed",
              }}>
              {loading ? <><RefreshCw size={10} className="animate-spin" /> Loading…</> : <><ChevronRight size={10} /> Expand 1-hop subgraph</>}
            </button>
            {!canExpand && (
              <p className="text-xs mt-1.5 text-center" style={{ color: S.t4, fontSize: 10 }}>
                {selected.type} nodes cannot be expanded
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Canvas area ───────────────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden">
        {!graph ? (
          <div className="w-full h-full flex flex-col items-center justify-center"
            style={{ background: S.base }}>
            <div className="w-20 h-20 mb-6 rounded-2xl flex items-center justify-center"
              style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.15)" }}>
              <Network size={40} style={{ color: "rgba(249,115,22,0.3)" }} />
            </div>
            <p className="font-semibold mb-1" style={{ color: S.t1 }}>Knowledge Graph Explorer</p>
            <p className="text-sm mb-6" style={{ color: S.t3 }}>Select an entity type and execute a query</p>
            <div className="grid grid-cols-2 gap-2 max-w-sm">
              {QUICK_QUERIES.slice(0, 6).map((q) => (
                <button key={q.id}
                  onClick={() => { setEntityType(q.type); setEntityId(q.id); load(q.type, q.id); }}
                  className="px-3 py-2.5 rounded-md text-xs text-left transition-all"
                  style={{ background: S.card, border: `1px solid ${S.border}`, color: S.t3 }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = "rgba(249,115,22,0.35)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = S.card; e.currentTarget.style.borderColor = S.border; }}>
                  <p className="mono font-semibold mb-0.5" style={{ color: S.saffron, fontSize: 9 }}>{q.type}</p>
                  <p style={{ color: S.t2 }}>{q.label}</p>
                </button>
              ))}
            </div>
          </div>
        ) : graph.nodes.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center" style={{ background: S.base }}>
            <p className="text-sm" style={{ color: S.t3 }}>No graph data returned for this entity.</p>
          </div>
        ) : (
          <GraphCanvas
            key={canvasKey}
            nodes={graph.nodes}
            edges={graph.edges}
            nodeColors={NODE_COLORS}
            onSelect={setSelected}
            selectedId={selected?.id}
            theme={theme}
          />
        )}

        {/* Canvas overlays */}
        {graph && graph.nodes.length > 0 && (
          <>
            {/* Bottom info bar */}
            <div className="absolute bottom-4 left-4 mono text-xs flex items-center gap-3"
              style={{ background: "rgba(6,11,20,0.88)", border: `1px solid ${S.border}`, borderRadius: 6, padding: "5px 10px", color: S.t3, backdropFilter: "blur(4px)" }}>
              <span style={{ color: S.saffron, fontWeight: 700 }}>{graph.nodes.length}</span> nodes
              <span style={{ color: S.t4 }}>·</span>
              <span style={{ color: "var(--cyan)", fontWeight: 700 }}>{graph.edges.length}</span> edges
              {excludeTypes.length > 0 && (
                <>
                  <span style={{ color: S.t4 }}>·</span>
                  <span style={{ color: "var(--amber)" }}>{excludeTypes.length} type{excludeTypes.length > 1 ? "s" : ""} filtered</span>
                </>
              )}
              <span style={{ color: S.t4 }}>·</span>
              <span>scroll=zoom · drag=pan · click=inspect</span>
            </div>

            {/* Zoom controls */}
            <div className="absolute bottom-4 right-4 flex flex-col gap-1.5">
              <button onClick={resetView}
                className="w-8 h-8 rounded-md flex items-center justify-center transition-all"
                style={{ background: S.card, border: `1px solid ${S.border}`, color: S.t3 }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = S.saffron; e.currentTarget.style.color = S.saffron; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = S.border; e.currentTarget.style.color = S.t3; }}
                title="Re-run simulation (reset layout)">
                <RotateCcw size={12} />
              </button>
            </div>

            {/* Entity trail */}
            {history.length > 0 && (
              <div className="absolute top-4 left-4 flex items-center gap-1.5 mono text-xs"
                style={{ background: "rgba(6,11,20,0.88)", border: `1px solid ${S.border}`, borderRadius: 6, padding: "4px 10px", color: S.t4, backdropFilter: "blur(4px)", maxWidth: "60%" }}>
                {history.slice(-4).map((h, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    {i > 0 && <ChevronRight size={9} style={{ color: S.t4 }} />}
                    <button onClick={() => restoreHistory(h)}
                      className="transition-colors"
                      style={{ color: i === history.slice(-4).length - 1 ? S.saffron : S.t3 }}
                      onMouseEnter={(e) => e.currentTarget.style.color = S.saffron}
                      onMouseLeave={(e) => e.currentTarget.style.color = i === history.slice(-4).length - 1 ? S.saffron : S.t3}>
                      {h.type}:{h.id}
                    </button>
                  </span>
                ))}
              </div>
            )}
          </>
        )}

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center"
            style={{ background: "rgba(6,11,20,0.6)", backdropFilter: "blur(2px)" }}>
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-full border-2 flex items-center justify-center animate-spin"
                style={{ borderColor: `rgba(249,115,22,0.3)`, borderTopColor: S.saffron }}>
              </div>
              <p className="mono text-xs" style={{ color: S.t2 }}>Querying Neo4j…</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
