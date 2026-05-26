"use client";

import { useState, useEffect, useCallback, useMemo, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { hexToRgba } from "@/lib/colors";
import type { GraphResult, GraphNode, BoothRow, BoothSummary } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";
import {
  Network, Search, Layers, Database, RefreshCw,
  ChevronRight, RotateCcw,
  History, GitBranch, Box, AlertTriangle, Flame, MapPin,
  Users, Award, Activity, X, BookOpen, Shield, Target, Zap, Tag,
  BarChart2,
} from "lucide-react";
import GraphCanvas from "./GraphCanvas";

// ── Constants ──────────────────────────────────────────────────────────────────

const DEFAULT_EXCLUDED = ["YouTubeVideo", "Channel"];

const ALL_FILTER_TYPES = [
  "YouTubeVideo", "Channel", "Candidate", "Booth",
  "Issue", "Party", "Narrative", "District", "Panchayat",
];

const NODE_COLORS: Record<string, string> = {
  AC:                   "#f97316",
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

const PARTY_COLORS: Record<string, string> = {
  BJP: "#f97316",
  SP:  "#ef4444",
  BSP: "#3b82f6",
  INC: "#22c55e",
  AAP: "#06b6d4",
  AD:  "#8b5cf6",
};

const LEAN_CONFIG: Record<string, { label: string; color: string }> = {
  STRONG_BJP:   { label: "Strong BJP",  color: "#f97316" },
  LEAN_BJP:     { label: "Lean BJP",    color: "#fb923c" },
  NEUTRAL:      { label: "Neutral",     color: "#64748b" },
  LEAN_OPP:     { label: "Lean SP",    color: "#3b82f6" },
  STRONG_OPP:   { label: "Strong SP",  color: "#2563eb" },
  INSUFFICIENT: { label: "No Signal",  color: "#475569" },
};

const PRIORITY_CONFIG: Record<string, { color: string; bg: string }> = {
  HIGH:   { color: "#ef4444", bg: "rgba(239,68,68,0.12)"  },
  MEDIUM: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  LOW:    { color: "#22c55e", bg: "rgba(34,197,94,0.12)"  },
};

const NODE_TYPE_TO_ENTITY: Record<string, string> = {
  AC:                   "AC",
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
  { label: "Gorakhpur Urban AC",  type: "AC",        id: "GKP_322",         desc: "All AC connections" },
  { label: "BJP Party",           type: "Party",     id: "BJP",             desc: "BJP party network" },
  { label: "SP Party",            type: "Party",     id: "SP",              desc: "SP party network" },
  { label: "Water Issue",         type: "Issue",     id: "water",           desc: "Water issue network" },
  { label: "Education Issue",     type: "Issue",     id: "education",       desc: "Education issue" },
  { label: "Adityanath 2022",     type: "Candidate", id: "ADITYANATH_2022", desc: "Incumbent candidate" },
  { label: "Booth 001",           type: "Booth",     id: "GKP_322_001",     desc: "Primary School Rampur" },
  { label: "Booth 010",           type: "Booth",     id: "GKP_322_010",     desc: "Anganwadi Center 1" },
];

// ── Types ──────────────────────────────────────────────────────────────────────

interface HistoryEntry {
  type: string;
  id: string;
  nodeCount: number;
  edgeCount: number;
  graph: GraphResult;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString();
}

function issueTitle(code: string): string {
  return code.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── SVG Chart Helpers ──────────────────────────────────────────────────────────

function DonutRing({ segs, size = 72, sw = 10 }: {
  segs: { v: number; c: string }[];
  size?: number;
  sw?: number;
}) {
  const r = (size - sw) / 2;
  const cx = size / 2;
  const circ = 2 * Math.PI * r;
  const total = segs.reduce((s, x) => s + x.v, 0) || 1;
  const GAP = 1.5;
  const offsets = segs.reduce<number[]>((acc) => {
    acc.push(acc.length === 0 ? 0 : acc[acc.length - 1] + (segs[acc.length - 1]?.v ?? 0) / total * circ);
    return acc;
  }, []);
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={sw} />
      {segs.map((seg, i) => {
        const frac = seg.v / total;
        const dash = Math.max(0, frac * circ - GAP);
        const el = (
          <circle key={i} cx={cx} cy={cx} r={r} fill="none" stroke={seg.c}
            strokeWidth={sw} strokeDasharray={`${dash} ${circ - dash}`}
            strokeDashoffset={-(offsets[i] + GAP / 2)} strokeLinecap="butt" />
        );
        return el;
      })}
    </svg>
  );
}

function SemiGauge({ val, color, size = 88 }: { val: number; color: string; size?: number }) {
  const sw = 8;
  const r = (size - sw * 2 - 4) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const norm = Math.min(1, Math.max(0, (val + 1) / 2));
  const track = `M ${(cx - r).toFixed(1)} ${cy} A ${r} ${r} 0 0 1 ${(cx + r).toFixed(1)} ${cy}`;
  const fa = (180 + norm * 180) * (Math.PI / 180);
  const fx = (cx + r * Math.cos(fa)).toFixed(1);
  const fy = (cy + r * Math.sin(fa)).toFixed(1);
  const fill = norm > 0.005
    ? `M ${(cx - r).toFixed(1)} ${cy} A ${r} ${r} 0 ${norm > 0.5 ? 1 : 0} 1 ${fx} ${fy}`
    : "";
  const vbY = cy - r - sw;
  const vbH = r + sw * 2;
  return (
    <svg width={size} height={Math.ceil(vbH)} viewBox={`0 ${vbY} ${size} ${vbH}`}>
      <path d={track} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={sw} strokeLinecap="round" />
      {fill && <path d={fill} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" />}
    </svg>
  );
}

function SparkLine({ vals, color, w = 120, h = 28 }: {
  vals: number[]; color: string; w?: number; h?: number;
}) {
  if (!vals || vals.length < 2) return null;
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const rng = mx - mn || 1;
  const pad = 3;
  const pts = vals.map((v, i) =>
    `${(i / (vals.length - 1)) * w},${h - pad - ((v - mn) / rng) * (h - pad * 2)}`
  ).join(" ");
  const lastPt = pts.split(" ").at(-1)!.split(",");
  return (
    <svg width={w} height={h}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5}
        strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={parseFloat(lastPt[0])} cy={parseFloat(lastPt[1])} r={2.5} fill={color} />
    </svg>
  );
}

const SOURCE_COLORS: Record<string, string> = {
  youtube: "#ff4444", facebook: "#4267B2", twitter: "#1DA1F2",
  news: "#f59e0b", field_report: "#10b981", other: "#64748b",
};

// ── Component ──────────────────────────────────────────────────────────────────

function GraphPageInner() {
  const { theme } = useTheme();
  const searchParams = useSearchParams();

  const [entityType, setEntityType] = useState(() => searchParams.get("type") ?? "AC");
  const [entityId, setEntityId]     = useState(() => searchParams.get("id") ?? "GKP_322");
  const [graph, setGraph]           = useState<GraphResult | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [selected, setSelected]     = useState<GraphNode | null>(null);
  const [activeTab, setActiveTab]   = useState<"query" | "legend" | "stats" | "history">("query");
  const [history, setHistory]       = useState<HistoryEntry[]>([]);
  const [booths, setBooths]         = useState<BoothRow[]>([]);
  const [boothSearch, setBoothSearch] = useState("");
  const [canvasKey, setCanvasKey]   = useState(0);
  const [excludeTypes, setExcludeTypes] = useState<string[]>(DEFAULT_EXCLUDED);
  const [nodeDetail, setNodeDetail] = useState<BoothSummary | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailTab, setDetailTab] = useState<"analysis" | "connections" | "raw">("analysis");
  const initialGraphParamsRef = useRef({
    type: searchParams.get("type") ?? "AC",
    id: searchParams.get("id") ?? "GKP_322",
    excludeTypes: DEFAULT_EXCLUDED,
  });

  useEffect(() => {
    api.booths("GKP_URBAN").then((r) => setBooths(r.booths)).catch(() => {});
  }, []);

  // Fetch detailed booth data when a Booth node is selected
  useEffect(() => {
    if (!selected || selected.type !== "Booth") return;
    const boothId = (selected.properties.booth_id as string) ?? selected.id.replace("Booth:", "");
    let cancelled = false;

    void (async () => {
      setNodeDetail(null);
      setLoadingDetail(true);
      try {
        const d = await api.boothSummary(boothId, 365);
        if (!cancelled) setNodeDetail(d);
      } catch {
        if (!cancelled) setNodeDetail(null);
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selected]);

  const load = useCallback(async (
    type?: string, id?: string, excl?: string[], pushHistory = true,
  ) => {
    const t  = (type ?? entityType).trim();
    const i  = (id ?? entityId).trim();
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

  useEffect(() => {
    const { type, id, excludeTypes } = initialGraphParamsRef.current;
    let cancelled = false;

    void (async () => {
      if (!id) return;
      setLoading(true);
      setError("");
      setSelected(null);
      try {
        const result = await api.subgraph(type, id, excludeTypes);
        if (cancelled) return;
        if (result.nodes.length === 0) {
          setError(`No graph data found for ${type} "${id}". Try removing type filters or check the entity ID.`);
          return;
        }
        setGraph(result);
        setCanvasKey((k) => k + 1);
        setHistory((prev) => [
          ...prev.slice(-19),
          { type, id, nodeCount: result.nodes.length, edgeCount: result.edges.length, graph: result },
        ]);
      } catch {
        if (!cancelled) setError(`Failed to reach the API for ${type} "${id}". Ensure the backend is running on port 8000.`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  function selectNode(node: GraphNode) {
    setSelected(node);
    setDetailTab("analysis");
  }

  function toggleExclude(nodeType: string) {
    setExcludeTypes((prev) => {
      const next = prev.includes(nodeType) ? prev.filter((t) => t !== nodeType) : [...prev, nodeType];
      if (graph) setTimeout(() => load(entityType, entityId, next), 0);
      return next;
    });
  }

  async function expandNode(node: GraphNode) {
    const entityT = NODE_TYPE_TO_ENTITY[node.type];
    if (!entityT) { setError(`Cannot expand ${node.type} nodes — no direct API mapping.`); return; }
    setEntityType(entityT);
    setEntityId(node.id);
    setDetailTab("analysis");
    await load(entityT, node.id, excludeTypes);
  }

  function restoreHistory(entry: HistoryEntry) {
    setGraph(entry.graph);
    setEntityType(entry.type);
    setEntityId(entry.id);
    setSelected(null);
    setDetailTab("analysis");
    setError("");
    setCanvasKey((k) => k + 1);
  }

  // Derived stats
  const nodeCounts: Record<string, number> = {};
  graph?.nodes.forEach((n) => { nodeCounts[n.type] = (nodeCounts[n.type] ?? 0) + 1; });
  const edgeCounts: Record<string, number> = {};
  graph?.edges.forEach((e) => { edgeCounts[e.type] = (edgeCounts[e.type] ?? 0) + 1; });

  // Nodes connected to the selected node in the current graph
  const selectedConnections = useMemo<Record<string, GraphNode[]>>(() => {
    if (!selected || !graph) return {};
    const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));
    const groups: Record<string, GraphNode[]> = {};
    const seen = new Set<string>();
    graph.edges.forEach((e) => {
      let otherId: string | null = null;
      if (e.source === selected.id) otherId = e.target;
      else if (e.target === selected.id) otherId = e.source;
      if (!otherId || seen.has(otherId)) return;
      seen.add(otherId);
      const other = nodeById.get(otherId);
      if (!other) return;
      if (!groups[other.type]) groups[other.type] = [];
      groups[other.type].push(other);
    });
    return groups;
  }, [selected, graph]);

  const filteredBooths = booths
    .filter((b) => !boothSearch ||
      b.name.toLowerCase().includes(boothSearch.toLowerCase()) ||
      String(b.booth_number).includes(boothSearch))
    .slice(0, 25);

  const canExpand  = selected ? !!NODE_TYPE_TO_ENTITY[selected.type] : false;
  const nodeColor  = selected ? (NODE_COLORS[selected.type] ?? "#64748b") : "#64748b";

  // ── CSS var shortcuts ──────────────────────────────────────────────────────
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

  // ── Type-specific analysis sections ───────────────────────────────────────

  function renderAnalysis() {
    if (!selected) return null;
    const p = selected.properties;

    /* ── AC ── */
    if (selected.type === "AC" || selected.type === "AssemblyConstituency") {
      const totalBooths     = selectedConnections["Booth"]?.length     ?? 0;
      const totalCandidates = selectedConnections["Candidate"]?.length ?? 0;
      const totalIssues     = selectedConnections["Issue"]?.length     ?? 0;
      const totalParties    = selectedConnections["Party"]?.length     ?? 0;
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3 space-y-1.5"
            style={{ background: "rgba(249,115,22,0.07)", border: "1px solid rgba(249,115,22,0.25)" }}>
            <p className="text-xs font-semibold" style={{ color: S.saffron }}>Assembly Constituency</p>
            <p className="text-sm font-bold" style={{ color: S.t1 }}>Gorakhpur Urban</p>
            <p className="text-xs mono" style={{ color: S.t3 }}>Uttar Pradesh · 2022 Assembly Election</p>
          </div>
          <div>
            <p className="label mb-2" style={{ color: S.t4 }}>Graph Connections</p>
            <div className="grid grid-cols-2 gap-2">
              {([
                { icon: MapPin,  label: "Booths",     val: totalBooths,     color: NODE_COLORS.Booth },
                { icon: Users,   label: "Candidates", val: totalCandidates, color: NODE_COLORS.Candidate },
                { icon: Target,  label: "Issues",     val: totalIssues,     color: NODE_COLORS.Issue },
                { icon: Shield,  label: "Parties",    val: totalParties,    color: NODE_COLORS.Party },
              ] as const).map(({ icon: Icon, label, val, color }) => (
                <div key={label} className="rounded-md p-2.5 flex items-center gap-2"
                  style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                  <div className="w-6 h-6 rounded flex items-center justify-center shrink-0"
                    style={{ background: hexToRgba(color, "18") }}>
                    <Icon size={11} style={{ color }} />
                  </div>
                  <div>
                    <p className="mono text-base font-bold leading-none" style={{ color }}>{val}</p>
                    <p className="text-xs mt-0.5" style={{ color: S.t4, fontSize: 10 }}>{label}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {selectedConnections["Issue"]?.length > 0 && (
            <div>
              <p className="label mb-2" style={{ color: S.t4 }}>Active Issues</p>
              <div className="flex flex-wrap gap-1.5">
                {selectedConnections["Issue"].map((n) => (
                  <button key={n.id} onClick={() => selectNode(n)}
                    className="px-2 py-1 rounded text-xs transition-all"
                    style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: NODE_COLORS.Issue }}>
                    {issueTitle((n.properties.code as string) ?? n.label)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    /* ── Booth ── */
    if (selected.type === "Booth") {
      const leanKey = ((nodeDetail?.digital_pulse?.lean_label ?? "").toUpperCase().replace(/\s+/g, "_"));
      const leanCfg = LEAN_CONFIG[leanKey] ?? LEAN_CONFIG.INSUFFICIENT;
      const bjpPulse = nodeDetail?.digital_pulse?.bjp_pulse ?? null;
      const oppPulse = nodeDetail?.digital_pulse?.opp_pulse ?? null;
      const male    = nodeDetail?.male_voters ?? null;
      const female  = nodeDetail?.female_voters ?? null;
      const totalV  = nodeDetail?.total_voters ?? (p.total_voters as number | null);
      const bjpShares = nodeDetail?.historical?.bjp_vote_shares ?? [];
      const maxIssue  = nodeDetail?.top_issues?.[0]?.mention_count ?? 1;

      return (
        <div className="space-y-4">
          {/* Voter Demographics */}
          <div className="rounded-lg p-3" style={{ background: "rgba(59,130,246,0.07)", border: "1px solid rgba(59,130,246,0.25)" }}>
            <p className="text-xs font-semibold mb-3" style={{ color: NODE_COLORS.Booth }}>Voter Demographics</p>
            <div className="flex items-center gap-4">
              <div className="relative shrink-0" style={{ width: 72, height: 72 }}>
                {male != null && female != null ? (
                  <>
                    <DonutRing segs={[{ v: male, c: "#60a5fa" }, { v: female, c: "#f472b6" }]} size={72} sw={10} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="mono font-bold" style={{ color: S.t1, fontSize: 9 }}>{fmt(totalV)}</span>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-full rounded-full flex items-center justify-center"
                    style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)" }}>
                    <Users size={20} style={{ color: "rgba(59,130,246,0.4)" }} />
                  </div>
                )}
              </div>
              <div className="flex-1 space-y-2">
                {[
                  { label: "Total",  val: fmt(totalV),                     color: S.t1        },
                  { label: "Male",   val: male   != null ? fmt(male)   : "—", color: "#60a5fa" },
                  { label: "Female", val: female != null ? fmt(female) : "—", color: "#f472b6" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="flex justify-between items-center">
                    <span className="text-xs" style={{ color: S.t3 }}>{label}</span>
                    <span className="mono text-xs font-bold" style={{ color }}>{val}</span>
                  </div>
                ))}
                {male != null && female != null && (totalV ?? 0) > 0 && (
                  <div className="flex rounded-full overflow-hidden" style={{ height: 4 }}>
                    <div style={{ width: `${(male / (totalV ?? 1)) * 100}%`, background: "#60a5fa" }} />
                    <div style={{ width: `${(female / (totalV ?? 1)) * 100}%`, background: "#f472b6" }} />
                  </div>
                )}
              </div>
            </div>
          </div>

          {loadingDetail ? (
            <div className="flex items-center gap-2 px-3 py-2.5 rounded"
              style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <RefreshCw size={10} className="animate-spin" style={{ color: S.t4 }} />
              <span className="text-xs" style={{ color: S.t4 }}>Loading digital intelligence…</span>
            </div>
          ) : nodeDetail && (<>

            {/* Lean + Confidence row */}
            <div className="flex gap-2">
              <div className="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-lg"
                style={{ background: hexToRgba(leanCfg.color, "10"), border: `1px solid ${hexToRgba(leanCfg.color, "40")}` }}>
                <Activity size={12} style={{ color: leanCfg.color }} />
                <div>
                  <p className="text-xs font-bold" style={{ color: leanCfg.color }}>{leanCfg.label}</p>
                  <p style={{ color: S.t4, fontSize: 9 }}>Political lean</p>
                </div>
              </div>
              <div className="px-3 py-2.5 rounded-lg text-center shrink-0"
                style={{ background: S.surface, border: `1px solid ${S.border}`, minWidth: 72 }}>
                <p className="mono text-xs font-bold" style={{ color: S.t1 }}>{nodeDetail.confidence?.label ?? "—"}</p>
                <p style={{ color: S.t4, fontSize: 9 }}>Confidence</p>
              </div>
            </div>

            {/* Digital Pulse semi-gauges */}
            {(bjpPulse != null || oppPulse != null) && (
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Digital Pulse Scores</p>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "BJP Signal", val: bjpPulse, color: "#f97316" },
                    { label: "SP Signal",  val: oppPulse, color: "#3b82f6" },
                  ].map(({ label, val, color }) => (
                    <div key={label} className="rounded-lg p-3 text-center"
                      style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                      <div className="flex justify-center mb-1">
                        <SemiGauge val={val ?? 0} color={color} size={88} />
                      </div>
                      <p className="mono text-sm font-bold" style={{ color }}>
                        {val != null ? val.toFixed(2) : "—"}
                      </p>
                      <p style={{ color: S.t4, fontSize: 9 }}>{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Historical sparkline */}
            {bjpShares.length >= 2 && (
              <div className="rounded-lg p-3" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold" style={{ color: S.t3 }}>BJP Vote Share Trend</p>
                  <span className="mono text-xs font-bold" style={{ color: "#f97316" }}>
                    {bjpShares.at(-1)?.toFixed(1)}%
                  </span>
                </div>
                <SparkLine vals={bjpShares} color="#f97316" w={340} h={34} />
                <div className="flex justify-between mt-1">
                  <span style={{ color: S.t4, fontSize: 9 }}>Oldest</span>
                  <span style={{ color: S.t4, fontSize: 9 }}>Latest</span>
                </div>
              </div>
            )}

            {/* Top issues */}
            {nodeDetail.top_issues?.length > 0 && (
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Top Issues by Mention</p>
                <div className="space-y-2">
                  {nodeDetail.top_issues.slice(0, 6).map((iss) => {
                    const pct = (iss.mention_count / maxIssue) * 100;
                    const pol = iss.avg_polarity ?? 0;
                    const barColor = pol > 0.05 ? "#22c55e" : pol < -0.05 ? "#ef4444" : "#64748b";
                    return (
                      <div key={iss.issue}>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs truncate mr-2" style={{ color: S.t2 }}>{issueTitle(iss.issue)}</span>
                          <span className="mono text-xs shrink-0" style={{ color: barColor, fontSize: 10 }}>
                            {iss.mention_count}
                            <span style={{ color: S.t4, marginLeft: 3, fontSize: 9 }}>
                              {pol > 0.05 ? "+" : pol < -0.05 ? "−" : "~"}{Math.abs(pol).toFixed(2)}
                            </span>
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full" style={{ background: S.border }}>
                          <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: barColor }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Source breakdown */}
            {nodeDetail.source_breakdown?.length > 0 && (
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Source Breakdown</p>
                <div className="flex items-center gap-3">
                  <div className="shrink-0">
                    <DonutRing segs={nodeDetail.source_breakdown.map((s) => ({
                      v: s.event_count,
                      c: SOURCE_COLORS[s.source_type] ?? "#64748b",
                    }))} size={56} sw={8} />
                  </div>
                  <div className="flex-1 space-y-1.5">
                    {nodeDetail.source_breakdown.map((s) => {
                      const sc = SOURCE_COLORS[s.source_type] ?? "#64748b";
                      return (
                        <div key={s.source_type} className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: sc }} />
                            <span className="text-xs capitalize" style={{ color: S.t2 }}>
                              {s.source_type.replace(/_/g, " ")}
                            </span>
                          </div>
                          <span className="mono text-xs font-bold" style={{ color: sc, fontSize: 10 }}>
                            {s.event_count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Scheme gaps */}
            {nodeDetail.scheme_analysis?.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="label" style={{ color: S.t4 }}>Scheme Gaps</p>
                  <span className="mono text-xs font-bold px-2 py-0.5 rounded"
                    style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b", fontSize: 10 }}>
                    {nodeDetail.scheme_analysis.length}
                  </span>
                </div>
                <div className="space-y-1.5">
                  {nodeDetail.scheme_analysis.slice(0, 4).map((sg, i) => {
                    const priCfg = PRIORITY_CONFIG[(sg.priority ?? "MEDIUM").toUpperCase()] ?? PRIORITY_CONFIG.MEDIUM;
                    return (
                      <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md"
                        style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                        <Shield size={9} style={{ color: "#f59e0b", flexShrink: 0 }} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium truncate" style={{ color: S.t2 }}>{sg.scheme_name}</p>
                          <p style={{ color: S.t4, fontSize: 9 }}>{sg.gap_type.replace(/_/g, " ")}</p>
                        </div>
                        <span className="mono text-xs px-1.5 py-0.5 rounded shrink-0"
                          style={{ background: priCfg.bg, color: priCfg.color, border: `1px solid ${hexToRgba(priCfg.color, "40")}`, fontSize: 9 }}>
                          {sg.priority}
                        </span>
                      </div>
                    );
                  })}
                  {nodeDetail.scheme_analysis.length > 4 && (
                    <p className="text-xs px-1" style={{ color: S.t4 }}>+{nodeDetail.scheme_analysis.length - 4} more</p>
                  )}
                </div>
              </div>
            )}

            {/* Narratives */}
            {nodeDetail.narratives?.length > 0 && (
              <div>
                <p className="label mb-2" style={{ color: S.t4 }}>Active Narratives</p>
                <div className="space-y-2">
                  {nodeDetail.narratives.slice(0, 3).map((n, i) => (
                    <div key={i} className="rounded-md p-2.5"
                      style={{ background: "rgba(236,72,153,0.06)", border: "1px solid rgba(236,72,153,0.2)" }}>
                      <div className="flex items-center justify-between mb-1.5">
                        <p className="text-xs font-medium" style={{ color: NODE_COLORS.Narrative }}>
                          {(n.narrative_type ?? "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                        </p>
                        <span className="mono" style={{ color: S.t4, fontSize: 9 }}>
                          {n.strength != null ? `${(n.strength * 100).toFixed(0)}%` : "—"}
                        </span>
                      </div>
                      {n.strength != null && (
                        <div className="h-1 rounded-full" style={{ background: S.border }}>
                          <div className="h-1 rounded-full"
                            style={{ width: `${Math.min(100, n.strength * 100)}%`, background: NODE_COLORS.Narrative }} />
                        </div>
                      )}
                      {n.summary && (
                        <p className="mt-1.5 leading-relaxed" style={{ color: S.t3, fontSize: 10 }}>{n.summary}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key insight */}
            {nodeDetail.key_insight && (
              <div className="rounded-md px-3 py-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <p className="font-semibold mb-1.5" style={{ color: S.t4, fontSize: 9 }}>KEY INSIGHT</p>
                <p className="text-xs leading-relaxed" style={{ color: S.t2 }}>{nodeDetail.key_insight}</p>
              </div>
            )}

            {/* Recommendation */}
            {nodeDetail.recommendation && (
              <div className="rounded-md px-3 py-2.5"
                style={{ background: "rgba(249,115,22,0.05)", border: "1px solid rgba(249,115,22,0.2)" }}>
                <p className="font-semibold mb-1.5" style={{ color: S.saffron, fontSize: 9 }}>RECOMMENDATION</p>
                <p className="text-xs leading-relaxed" style={{ color: S.t2 }}>{nodeDetail.recommendation}</p>
              </div>
            )}
          </>)}
        </div>
      );
    }

    /* ── Candidate ── */
    if (selected.type === "Candidate") {
      const party      = p.party as string ?? "—";
      const partyColor = PARTY_COLORS[party] ?? "#64748b";
      const isIncumbent = p.is_incumbent as boolean;
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3 flex items-center gap-3"
            style={{ background: hexToRgba(partyColor, "10"), border: `1px solid ${hexToRgba(partyColor, "35")}` }}>
            <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
              style={{ background: partyColor, color: "#fff" }}>
              {party.slice(0, 3)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold" style={{ color: S.t1 }}>{party}</p>
              <p className="text-xs" style={{ color: S.t3 }}>Political Party</p>
            </div>
            {isIncumbent && (
              <div className="flex items-center gap-1 px-2 py-1 rounded shrink-0"
                style={{ background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)" }}>
                <Award size={9} style={{ color: S.saffron }} />
                <span className="text-xs mono" style={{ color: S.saffron, fontSize: 9 }}>Incumbent</span>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Election Year", val: String(p.election_year ?? "—") },
              { label: "Constituency",  val: String(p.ac_id ?? "—") },
            ].map(({ label, val }) => (
              <div key={label} className="rounded-md p-2.5 text-center"
                style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <p className="mono text-sm font-bold" style={{ color: S.t1 }}>{val}</p>
                <p className="text-xs mt-0.5" style={{ color: S.t4, fontSize: 10 }}>{label}</p>
              </div>
            ))}
          </div>
          <div className="rounded-md px-3 py-2" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <p className="text-xs" style={{ color: S.t4, fontSize: 10 }}>CANDIDATE ID</p>
            <p className="mono text-xs mt-0.5 break-all" style={{ color: S.t2 }}>{p.candidate_id as string ?? "—"}</p>
          </div>
        </div>
      );
    }

    /* ── Party ── */
    if (selected.type === "Party") {
      const party      = (p.name as string) ?? (p.party_id as string) ?? selected.label;
      const partyColor = PARTY_COLORS[party] ?? NODE_COLORS.Party;
      const candidates = selectedConnections["Candidate"] ?? [];
      const incumbent  = candidates.find((c) => c.properties.is_incumbent);
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3 text-center"
            style={{ background: hexToRgba(partyColor, "10"), border: `1px solid ${hexToRgba(partyColor, "35")}` }}>
            <div className="w-12 h-12 rounded-full flex items-center justify-center font-bold text-base mx-auto mb-2"
              style={{ background: partyColor, color: "#fff" }}>
              {party.slice(0, 3)}
            </div>
            <p className="font-bold text-sm" style={{ color: S.t1 }}>{party}</p>
            <p className="text-xs mt-0.5" style={{ color: S.t3 }}>
              {candidates.length} candidate{candidates.length !== 1 ? "s" : ""} in graph
            </p>
          </div>
          {incumbent && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-md"
              style={{ background: "rgba(249,115,22,0.08)", border: "1px solid rgba(249,115,22,0.25)" }}>
              <Award size={11} style={{ color: S.saffron }} />
              <div>
                <p className="text-xs font-semibold" style={{ color: S.saffron }}>Current Incumbent</p>
                <p className="text-xs" style={{ color: S.t2 }}>{incumbent.properties.name as string}</p>
              </div>
            </div>
          )}
          {candidates.length > 0 && (
            <div>
              <p className="label mb-2" style={{ color: S.t4 }}>Candidates</p>
              <div className="space-y-1">
                {candidates.map((c) => (
                  <button key={c.id} onClick={() => selectNode(c)}
                    className="w-full text-left px-3 py-2 rounded-md text-xs flex items-center gap-2 transition-all"
                    style={{ background: S.surface, border: `1px solid ${S.border}` }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = hexToRgba(partyColor, "50"); }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = S.surface; e.currentTarget.style.borderColor = S.border; }}>
                    <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: partyColor }} />
                    <span className="flex-1 truncate" style={{ color: S.t2 }}>{c.properties.name as string ?? c.label}</span>
                    <span className="mono" style={{ color: S.t4, fontSize: 10 }}>{c.properties.election_year as number}</span>
                    {!!c.properties.is_incumbent && <Award size={9} style={{ color: S.saffron }} />}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    /* ── Issue ── */
    if (selected.type === "Issue") {
      const code    = (p.code as string) ?? selected.label.toLowerCase();
      const booths  = selectedConnections["Booth"] ?? [];
      const acNodes = selectedConnections["AC"]    ?? [];
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3" style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.25)" }}>
            <div className="flex items-center gap-2 mb-1">
              <Tag size={11} style={{ color: NODE_COLORS.Issue }} />
              <p className="text-xs font-semibold" style={{ color: NODE_COLORS.Issue }}>Political Issue</p>
            </div>
            <p className="text-base font-bold" style={{ color: S.t1 }}>{issueTitle(code)}</p>
            <p className="text-xs mono mt-1" style={{ color: S.t4 }}>code: {code}</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md p-2.5 text-center" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <p className="mono text-lg font-bold" style={{ color: NODE_COLORS.Booth }}>{booths.length || "30"}</p>
              <p className="text-xs" style={{ color: S.t4, fontSize: 10 }}>Booths Affected</p>
            </div>
            <div className="rounded-md p-2.5 text-center" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <p className="mono text-lg font-bold" style={{ color: NODE_COLORS.Issue }}>{acNodes.length || "1"}</p>
              <p className="text-xs" style={{ color: S.t4, fontSize: 10 }}>Constituencies</p>
            </div>
          </div>
          <div className="rounded-md px-3 py-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <p className="text-xs leading-relaxed" style={{ color: S.t3 }}>
              Derived from AC-level digital signals (699 pulse events). All booths in the constituency share this issue signal.
            </p>
          </div>
          {booths.length > 0 && (
            <div>
              <p className="label mb-2" style={{ color: S.t4 }}>Affected Booths</p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {booths.slice(0, 10).map((b) => (
                  <button key={b.id} onClick={() => selectNode(b)}
                    className="w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center gap-2 transition-all"
                    style={{ background: S.surface, border: `1px solid ${S.border}` }}
                    onMouseEnter={(e) => e.currentTarget.style.background = S.hover}
                    onMouseLeave={(e) => e.currentTarget.style.background = S.surface}>
                    <MapPin size={8} style={{ color: NODE_COLORS.Booth, flexShrink: 0 }} />
                    <span style={{ color: S.t2 }}>{b.label}</span>
                  </button>
                ))}
                {booths.length > 10 && (
                  <p className="text-xs px-2.5 py-1" style={{ color: S.t4 }}>+{booths.length - 10} more…</p>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    /* ── Narrative ── */
    if (selected.type === "Narrative") {
      const strength      = (p.strength as number) ?? 0;
      const description   = (p.description as string) ?? "";
      const narrativeType = (p.narrative_type as string) ?? selected.label;
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3" style={{ background: "rgba(236,72,153,0.07)", border: "1px solid rgba(236,72,153,0.25)" }}>
            <div className="flex items-center gap-2 mb-1">
              <BookOpen size={11} style={{ color: NODE_COLORS.Narrative }} />
              <p className="text-xs font-semibold" style={{ color: NODE_COLORS.Narrative }}>Narrative Signal</p>
            </div>
            <p className="text-sm font-bold" style={{ color: S.t1 }}>
              {narrativeType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </p>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="label" style={{ color: S.t4 }}>Signal Strength</p>
              <span className="mono text-xs font-bold" style={{ color: NODE_COLORS.Narrative }}>
                {(strength * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-2 rounded-full" style={{ background: S.border }}>
              <div className="h-2 rounded-full transition-all"
                style={{ width: `${strength * 100}%`, background: `linear-gradient(90deg, ${NODE_COLORS.Narrative}80, ${NODE_COLORS.Narrative})` }} />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-xs" style={{ color: S.t4, fontSize: 9 }}>Weak</span>
              <span className="text-xs" style={{ color: S.t4, fontSize: 9 }}>Strong</span>
            </div>
          </div>
          {description && (
            <div className="rounded-md px-3 py-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <p className="text-xs font-semibold mb-1.5" style={{ color: S.t4, fontSize: 10 }}>DESCRIPTION</p>
              <p className="text-xs leading-relaxed" style={{ color: S.t2 }}>{description}</p>
            </div>
          )}
          {(selectedConnections["Booth"] ?? []).map((b) => (
            <button key={b.id} onClick={() => selectNode(b)}
              className="w-full text-left px-3 py-2 rounded-md flex items-center gap-2 transition-all"
              style={{ background: S.surface, border: `1px solid ${S.border}` }}
              onMouseEnter={(e) => e.currentTarget.style.background = S.hover}
              onMouseLeave={(e) => e.currentTarget.style.background = S.surface}>
              <MapPin size={10} style={{ color: NODE_COLORS.Booth }} />
              <span className="text-xs" style={{ color: S.t2 }}>{b.label}</span>
            </button>
          ))}
        </div>
      );
    }

    /* ── Scheme ── */
    if (selected.type === "Scheme") {
      const schemeName = (p.scheme_name as string) ?? selected.label;
      const issueTag   = (p.issue_tag as string)   ?? "—";
      const gapType    = ((p.gap_type as string)    ?? "").replace(/_/g, " ");
      const priority   = ((p.priority as string)    ?? "MEDIUM").toUpperCase();
      const priCfg     = PRIORITY_CONFIG[priority] ?? PRIORITY_CONFIG.MEDIUM;
      return (
        <div className="space-y-4">
          <div className="rounded-lg p-3" style={{ background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.25)" }}>
            <div className="flex items-center gap-2 mb-1">
              <Shield size={11} style={{ color: NODE_COLORS.Scheme }} />
              <p className="text-xs font-semibold" style={{ color: NODE_COLORS.Scheme }}>Government Scheme</p>
            </div>
            <p className="text-sm font-bold leading-tight" style={{ color: S.t1 }}>{schemeName}</p>
          </div>
          <div className="space-y-2">
            {[
              { label: "Issue Tag", content: (
                <span className="px-2 py-0.5 rounded text-xs mono"
                  style={{ background: "rgba(239,68,68,0.1)", color: NODE_COLORS.Issue }}>
                  {issueTitle(issueTag)}
                </span>
              )},
              { label: "Gap Type", content: (
                <span className="text-xs font-medium" style={{ color: S.t2 }}>
                  {gapType.replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
              )},
              { label: "Priority", content: (
                <span className="px-2 py-0.5 rounded mono text-xs font-bold"
                  style={{ background: priCfg.bg, color: priCfg.color, border: `1px solid ${priCfg.color}40` }}>
                  {priority}
                </span>
              )},
            ].map(({ label, content }) => (
              <div key={label} className="flex items-center justify-between px-3 py-2 rounded-md"
                style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <span className="text-xs" style={{ color: S.t3 }}>{label}</span>
                {content}
              </div>
            ))}
          </div>
          {(selectedConnections["Booth"] ?? []).map((b) => (
            <button key={b.id} onClick={() => selectNode(b)}
              className="w-full text-left px-3 py-2 rounded-md flex items-center gap-2 transition-all"
              style={{ background: S.surface, border: `1px solid ${S.border}` }}
              onMouseEnter={(e) => e.currentTarget.style.background = S.hover}
              onMouseLeave={(e) => e.currentTarget.style.background = S.surface}>
              <MapPin size={10} style={{ color: NODE_COLORS.Booth }} />
              <span className="text-xs flex-1" style={{ color: S.t2 }}>{b.label}</span>
              <ChevronRight size={10} style={{ color: S.t4 }} />
            </button>
          ))}
        </div>
      );
    }

    return null;
  }

  // ── JSX ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen" style={{ background: S.base }}>

      {/* ── Left panel ──────────────────────────────────────────────────────── */}
      <div className="w-72 shrink-0 flex flex-col" style={{ borderRight: `1px solid ${S.border}`, background: S.base }}>

        {/* Header */}
        <div className="px-4 py-3.5" style={{ borderBottom: `1px solid ${S.border}` }}>
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded flex items-center justify-center"
                style={{ background: "rgba(249,115,22,0.15)", border: "1px solid rgba(249,115,22,0.3)" }}>
                <Network size={12} style={{ color: S.saffron }} />
              </div>
              <h1 className="text-sm font-bold" style={{ color: S.t1 }}>Knowledge Graph</h1>
            </div>
            <a href="/heatmap"
              className="w-6 h-6 rounded flex items-center justify-center transition-all"
              style={{ background: "transparent", border: `1px solid ${S.border}`, color: S.t3 }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(249,115,22,0.1)"; e.currentTarget.style.borderColor = "rgba(249,115,22,0.4)"; e.currentTarget.style.color = S.saffron; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = S.border; e.currentTarget.style.color = S.t3; }}
              title="Go to Heatmap">
              <Flame size={11} />
            </a>
          </div>
          <p className="text-xs mono" style={{ color: S.t3 }}>PostgreSQL-backed graph explorer</p>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: `1px solid ${S.border}` }}>
          {[
            { id: "query",   label: "Query",   icon: Search   },
            { id: "legend",  label: "Schema",  icon: Layers   },
            { id: "stats",   label: "Stats",   icon: Database },
            { id: "history", label: "History", icon: History  },
          ].map(({ id, label, icon: Icon }) => {
            const isActive = activeTab === id;
            return (
              <button key={id} onClick={() => setActiveTab(id as typeof activeTab)}
                className="flex-1 flex items-center justify-center gap-1 py-2.5 text-xs transition-all"
                style={{
                  background:   isActive ? S.surface : "transparent",
                  borderBottom: isActive ? `2px solid ${S.saffron}` : "2px solid transparent",
                  color:        isActive ? S.saffron : S.t3,
                }}>
                <Icon size={10} /> {label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">

          {/* ── QUERY ── */}
          {activeTab === "query" && (
            <div className="p-4 space-y-4">
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

              {entityType === "Booth" && booths.length > 0 && (
                <div>
                  <p className="label mb-1.5" style={{ color: S.t4 }}>Search Booths</p>
                  <input value={boothSearch} onChange={(e) => setBoothSearch(e.target.value)}
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
                  {entityType === "Narrative" && "e.g. party_dominance"}
                </p>
              </div>

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
                  <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="label" style={{ color: S.t4 }}>Filter Node Types</p>
                  {excludeTypes.length > 0 && (
                    <button onClick={() => { setExcludeTypes([]); if (graph) setTimeout(() => load(entityType, entityId, []), 0); }}
                      className="text-xs mono transition-colors"
                      style={{ color: S.saffron, fontSize: 9 }}>show all</button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_FILTER_TYPES.map((type) => {
                    const color    = NODE_COLORS[type] ?? "#64748b";
                    const excluded = excludeTypes.includes(type);
                    return (
                      <button key={type} onClick={() => toggleExclude(type)}
                        className="flex items-center gap-1 px-2 py-1 rounded mono text-xs transition-all"
                        style={{
                          background: excluded ? S.surface : hexToRgba(color, "18"),
                          border:     `1px solid ${excluded ? S.border : hexToRgba(color, "60")}`,
                          color:      excluded ? S.t4 : color,
                          opacity:    excluded ? 0.55 : 1,
                          fontSize:   9,
                        }}>
                        <span style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: excluded ? S.t4 : color, flexShrink: 0 }} />
                        {type}
                      </button>
                    );
                  })}
                </div>
              </div>

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
                      <span className="mono font-semibold px-1.5 py-0.5 rounded shrink-0"
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

          {/* ── LEGEND ── */}
          {activeTab === "legend" && (
            <div className="p-4">
              <p className="label mb-3" style={{ color: S.t4 }}>Node Types</p>
              <div className="space-y-1">
                {Object.entries(NODE_COLORS)
                  .filter(([t]) => !["AssemblyConstituency", "State", "District"].includes(t))
                  .map(([type, color]) => (
                    <div key={type} className="flex items-center gap-2.5 py-1.5 px-2 rounded-md transition-all"
                      style={{ border: "1px solid transparent" }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = S.border; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "transparent"; }}>
                      <div className="w-3 h-3 rounded-full shrink-0" style={{ background: color, boxShadow: `0 0 6px ${hexToRgba(color, "60")}` }} />
                      <span className="text-xs mono flex-1" style={{ color: S.t2 }}>{type}</span>
                      <div className="flex-1 h-px" style={{ background: hexToRgba(color, "25") }} />
                      <span className="mono text-xs font-bold" style={{ color, fontSize: 10 }}>
                        {nodeCounts[type] ?? "—"}
                      </span>
                    </div>
                  ))}
              </div>
              <div className="mt-4 pt-3" style={{ borderTop: `1px solid ${S.border}` }}>
                <p className="label mb-2" style={{ color: S.t4 }}>Navigation</p>
                <div className="space-y-1.5 text-xs" style={{ color: S.t3 }}>
                  {[
                    "Click node → opens analysis panel",
                    "Expand → loads 1-hop subgraph",
                    "Drag nodes to reposition",
                    "Scroll to zoom, drag canvas to pan",
                    "Arrows show relationship direction",
                  ].map((tip, i) => (
                    <p key={i} className="flex items-center gap-2">
                      <span className="w-4 h-4 rounded flex items-center justify-center shrink-0"
                        style={{ background: "rgba(249,115,22,0.1)", color: S.saffron, fontSize: 9 }}>{i + 1}</span>
                      {tip}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── STATS ── */}
          {activeTab === "stats" && (
            <div className="p-4">
              {!graph ? (
                <div className="flex flex-col items-center justify-center h-32">
                  <Box size={24} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                  <p className="text-xs" style={{ color: S.t4 }}>Load a subgraph first</p>
                </div>
              ) : (
                <>
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
                      const pct   = (count / graph.nodes.length) * 100;
                      const color = NODE_COLORS[type] ?? "#64748b";
                      return (
                        <div key={type}>
                          <div className="flex items-center gap-2 mb-0.5">
                            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                            <span className="text-xs flex-1" style={{ color: S.t2 }}>{type}</span>
                            <span className="mono text-xs font-semibold" style={{ color }}>{count}</span>
                          </div>
                          <div className="h-1 rounded-full mx-4" style={{ background: S.border }}>
                            <div className="h-1 rounded-full" style={{ width: `${pct}%`, background: color }} />
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

          {/* ── HISTORY ── */}
          {activeTab === "history" && (
            <div className="p-4">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32">
                  <History size={24} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                  <p className="text-xs" style={{ color: S.t4 }}>No history yet</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {[...history].reverse().map((entry, i) => (
                    <button key={i} onClick={() => restoreHistory(entry)}
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
                        <span>{entry.nodeCount} nodes</span><span>·</span>
                        <span>{entry.edgeCount} edges</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Canvas ────────────────────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden">
        {!graph ? (
          <div className="w-full h-full flex flex-col items-center justify-center" style={{ background: S.base }}>
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
            onSelect={selectNode}
            selectedId={selected?.id}
            theme={theme}
          />
        )}

        {graph && graph.nodes.length > 0 && (
          <>
            <div className="absolute bottom-4 left-4 mono text-xs flex items-center gap-3"
              style={{ background: "rgba(6,11,20,0.88)", border: `1px solid ${S.border}`, borderRadius: 6, padding: "5px 10px", color: S.t3, backdropFilter: "blur(4px)" }}>
              <span style={{ color: S.saffron, fontWeight: 700 }}>{graph.nodes.length}</span> nodes
              <span style={{ color: S.t4 }}>·</span>
              <span style={{ color: "var(--cyan)", fontWeight: 700 }}>{graph.edges.length}</span> edges
              {excludeTypes.length > 0 && (
                <><span style={{ color: S.t4 }}>·</span>
                <span style={{ color: "var(--amber)" }}>{excludeTypes.length} filtered</span></>
              )}
              <span style={{ color: S.t4 }}>·</span>
              <span>scroll=zoom · drag=pan · click=inspect</span>
            </div>

            <div className="absolute bottom-4 right-4 flex flex-col gap-1.5">
              <button onClick={() => setCanvasKey((k) => k + 1)}
                className="w-8 h-8 rounded-md flex items-center justify-center transition-all"
                style={{ background: S.card, border: `1px solid ${S.border}`, color: S.t3 }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = S.saffron; e.currentTarget.style.color = S.saffron; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = S.border; e.currentTarget.style.color = S.t3; }}
                title="Re-run simulation">
                <RotateCcw size={12} />
              </button>
            </div>

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
              <div className="w-12 h-12 rounded-full border-2 animate-spin"
                style={{ borderColor: `rgba(249,115,22,0.3)`, borderTopColor: S.saffron }} />
              <p className="mono text-xs" style={{ color: S.t2 }}>Building graph…</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right analysis panel ───────────────────────────────────────────────── */}
      {selected && (
        <div className="w-110 shrink-0 flex flex-col"
          style={{ borderLeft: `1px solid ${S.border}`, background: S.base }}>

          {/* Header */}
          <div className="px-4 py-3 shrink-0"
            style={{ borderBottom: `1px solid ${S.border}`, background: S.surface }}>
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: nodeColor, boxShadow: `0 0 8px ${hexToRgba(nodeColor, "80")}` }} />
                  <span className="mono px-2 py-0.5 rounded text-xs font-semibold"
                    style={{ background: hexToRgba(nodeColor, "18"), color: nodeColor, border: `1px solid ${hexToRgba(nodeColor, "35")}`, fontSize: 10 }}>
                    {selected.type}
                  </span>
                </div>
                <h2 className="text-sm font-bold truncate" style={{ color: S.t1 }}>{selected.label}</h2>
                <p className="mono mt-0.5 truncate" style={{ color: S.t4, fontSize: 10 }}>{selected.id}</p>
              </div>
              <button onClick={() => setSelected(null)}
                className="w-7 h-7 shrink-0 flex items-center justify-center rounded-md transition-all"
                style={{ border: `1px solid ${S.border}`, color: S.t4, background: S.card }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = S.bright; e.currentTarget.style.color = S.t2; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = S.border; e.currentTarget.style.color = S.t4; }}>
                <X size={11} />
              </button>
            </div>
          </div>

          {/* Tab bar */}
          <div className="flex shrink-0" style={{ borderBottom: `1px solid ${S.border}` }}>
            {([
              { id: "analysis",    label: "Analysis",    icon: BarChart2 },
              { id: "connections", label: "Connections", icon: GitBranch },
              { id: "raw",         label: "Properties",  icon: Database  },
            ] as const).map(({ id, label, icon: Icon }) => {
              const isActive = detailTab === id;
              return (
                <button key={id} onClick={() => setDetailTab(id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs transition-all"
                  style={{
                    background:   isActive ? S.surface : "transparent",
                    borderBottom: isActive ? `2px solid ${nodeColor}` : "2px solid transparent",
                    color:        isActive ? nodeColor : S.t3,
                  }}>
                  <Icon size={10} /> {label}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">

            {/* Analysis */}
            {detailTab === "analysis" && (
              <div className="p-4 space-y-4">
                {renderAnalysis() ?? (
                  <div className="flex flex-col items-center justify-center h-32 text-center">
                    <BarChart2 size={20} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                    <p className="text-xs" style={{ color: S.t4 }}>No detailed analysis available for this node type</p>
                  </div>
                )}
              </div>
            )}

            {/* Connections */}
            {detailTab === "connections" && (
              <div className="p-4 space-y-4">
                {Object.keys(selectedConnections).length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-32 text-center">
                    <GitBranch size={20} style={{ color: S.t4 }} className="mb-2 opacity-40" />
                    <p className="text-xs" style={{ color: S.t4 }}>No connections visible in current subgraph</p>
                  </div>
                ) : (<>
                  {/* Badge summary */}
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(selectedConnections)
                      .sort((a, b) => b[1].length - a[1].length)
                      .map(([type, nodes]) => {
                        const color = NODE_COLORS[type] ?? "#64748b";
                        return (
                          <div key={type} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md"
                            style={{ background: hexToRgba(color, "12"), border: `1px solid ${hexToRgba(color, "35")}` }}>
                            <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
                            <span className="mono text-xs font-bold" style={{ color }}>{nodes.length}</span>
                            <span className="text-xs" style={{ color: S.t3 }}>{type}</span>
                          </div>
                        );
                      })}
                  </div>
                  {/* Grouped node lists */}
                  {Object.entries(selectedConnections)
                    .sort((a, b) => b[1].length - a[1].length)
                    .map(([type, nodes]) => {
                      const color = NODE_COLORS[type] ?? "#64748b";
                      const shown = nodes.length > 8 ? nodes.slice(0, 6) : nodes;
                      return (
                        <div key={type}>
                          <p className="font-semibold mb-1.5" style={{ color: S.t4, fontSize: 10 }}>{type.toUpperCase()}</p>
                          <div className="space-y-1">
                            {shown.map((n) => (
                              <button key={n.id} onClick={() => selectNode(n)}
                                className="w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center gap-2 transition-all"
                                style={{ background: S.surface, border: `1px solid ${S.border}` }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = S.hover; e.currentTarget.style.borderColor = hexToRgba(color, "50"); }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = S.surface; e.currentTarget.style.borderColor = S.border; }}>
                                <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
                                <span className="flex-1 truncate" style={{ color: S.t2 }}>{n.label}</span>
                                <ChevronRight size={9} style={{ color: S.t4, flexShrink: 0 }} />
                              </button>
                            ))}
                            {nodes.length > 6 && (
                              <p className="text-xs px-2.5 py-1" style={{ color: S.t4 }}>+{nodes.length - 6} more…</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                </>)}
              </div>
            )}

            {/* Raw properties */}
            {detailTab === "raw" && (
              <div className="p-4">
                <div className="rounded-md overflow-hidden" style={{ border: `1px solid ${S.border}` }}>
                  {Object.entries(selected.properties)
                    .filter(([k]) => !["_synthetic", "source"].includes(k))
                    .map(([k, v], i, arr) => (
                      <div key={k} className="flex gap-2 px-3 py-2"
                        style={{
                          borderBottom: i < arr.length - 1 ? `1px solid ${S.border}` : "none",
                          background: i % 2 === 0 ? "transparent" : `rgba(255,255,255,0.02)`,
                        }}>
                        <span className="mono shrink-0" style={{ color: S.t4, fontSize: 9, width: 90 }}>{k}</span>
                        <span className="text-xs break-all" style={{ color: S.t2 }}>
                          {v === null || v === undefined
                            ? <span style={{ color: S.t4 }}>null</span>
                            : typeof v === "boolean"
                              ? <span style={{ color: v ? "#22c55e" : "#ef4444" }}>{String(v)}</span>
                              : typeof v === "number"
                                ? <span style={{ color: "#06b6d4" }}>{String(v)}</span>
                                : String(v).length > 100 ? String(v).slice(0, 100) + "…" : String(v)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer actions */}
          <div className="px-4 py-3 shrink-0 space-y-2"
            style={{ borderTop: `1px solid ${S.border}`, background: S.surface }}>
            <button
              onClick={() => expandNode(selected)}
              disabled={loading || !canExpand}
              className="w-full py-2.5 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all"
              style={{
                background: canExpand ? "rgba(249,115,22,0.12)" : "transparent",
                border:     `1px solid ${canExpand ? "rgba(249,115,22,0.45)" : S.border}`,
                color:      canExpand ? S.saffron : S.t4,
                opacity:    loading ? 0.6 : 1,
                cursor:     canExpand ? "pointer" : "not-allowed",
              }}
              onMouseEnter={(e) => { if (canExpand) e.currentTarget.style.background = "rgba(249,115,22,0.2)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = canExpand ? "rgba(249,115,22,0.12)" : "transparent"; }}>
              {loading
                ? <><RefreshCw size={10} className="animate-spin" /> Loading…</>
                : <><Zap size={10} /> Expand 1-hop Subgraph</>}
            </button>
            {selected.type === "Booth" && (
              <a href={`/booths/${selected.id}`}
                className="w-full py-2 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all"
                style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.3)", color: NODE_COLORS.Booth }}>
                <MapPin size={10} /> Deep Booth Analysis
              </a>
            )}
            {selected.type === "Booth" && (
              <a href={`/heatmap?booth=${selected.id}`}
                className="w-full py-2 rounded-md text-xs mono font-semibold flex items-center justify-center gap-2 transition-all"
                style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.3)", color: S.saffron }}>
                <Flame size={10} /> View on Heatmap
              </a>
            )}
            {!canExpand && (
              <p className="text-xs text-center" style={{ color: S.t4, fontSize: 10 }}>
                {selected.type} nodes cannot be expanded
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "var(--text-3)", fontSize: 13 }}>Loading…</div>}>
      <GraphPageInner />
    </Suspense>
  );
}
