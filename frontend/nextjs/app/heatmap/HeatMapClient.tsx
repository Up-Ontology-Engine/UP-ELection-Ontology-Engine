"use client";

import { hexToRgba } from "@/lib/colors";
import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { GraphCoverageResponse, GraphCoverageBooth } from "@/lib/api";
import { type PlottedBooth } from "./LeafletMap";
import {
  Flame, Layers, BarChart3, X, Users, GitBranch,
  TrendingUp, Network, Search, MapPin, Info,
  Activity, Zap, ShieldCheck, AlertTriangle,
  BarChart2, Target,
} from "lucide-react";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });

export type HeatLayer = "voters" | "kg_coverage" | "bjp_lean" | "confidence";

// Gorakhpur Urban AC-322 city bounds
const GKP_URBAN = {
  north: 26.800, south: 26.705,
  east:  83.425, west:  83.325,
};
const GKP_LAT = 26.755;
const GKP_LON = 83.375;

const LAYERS: { id: HeatLayer; label: string; desc: string; color: string }[] = [
  { id: "voters",      label: "Voter Density",  desc: "Heat by registered voter count",           color: "#f97316" },
  { id: "kg_coverage", label: "KG Coverage",    desc: "Knowledge Graph node presence per booth",  color: "#10b981" },
  { id: "bjp_lean",    label: "Political Lean", desc: "Party pulse signal — BJP · SP · BSP",      color: "#3b82f6" },
  { id: "confidence",  label: "Data Quality",   desc: "Data confidence score per booth",          color: "#8b5cf6" },
];

const LEGENDS: Record<HeatLayer, { label: string; color: string }[]> = {
  voters: [
    { label: "High (2000+ voters)", color: "#ef4444" },
    { label: "Medium (1000–2000)",  color: "#f97316" },
    { label: "Low (< 1000 voters)", color: "#3b82f6" },
  ],
  kg_coverage: [
    { label: "In Knowledge Graph",  color: "#10b981" },
    { label: "Not indexed",         color: "#475569" },
  ],
  bjp_lean: [
    { label: "Strong BJP",  color: "#f97316" },
    { label: "Lean BJP",    color: "#fb923c" },
    { label: "Neutral",     color: "#64748b" },
    { label: "Lean SP",     color: "#60a5fa" },
    { label: "Strong SP",   color: "#3b82f6" },
    { label: "No signal",   color: "#475569" },
  ],
  confidence: [
    { label: "HIGH",    color: "#10b981" },
    { label: "MEDIUM",  color: "#f59e0b" },
    { label: "LOW",     color: "#ef4444" },
    { label: "Unknown", color: "#475569" },
  ],
};

// Lean badge style
const LEAN_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  STRONG_BJP:   { bg: "rgba(249,115,22,0.18)", text: "#f97316", label: "Strong BJP"  },
  LEAN_BJP:     { bg: "rgba(249,115,22,0.1)",  text: "#fb923c", label: "Lean BJP"    },
  NEUTRAL:      { bg: "rgba(100,116,139,0.2)", text: "#94a3b8", label: "Neutral"     },
  LEAN_OPP:     { bg: "rgba(59,130,246,0.1)",  text: "#60a5fa", label: "Lean SP"     },
  STRONG_OPP:   { bg: "rgba(59,130,246,0.18)", text: "#3b82f6", label: "Strong SP"   },
  INSUFFICIENT: { bg: "rgba(45,62,80,0.5)",    text: "#4d6480", label: "Insufficient"},
};

interface Props {
  coverage: GraphCoverageResponse | null;
}

type PanelStyles = {
  border: string;
  t1: string;
  t2: string;
  t3: string;
  t4: string;
  surface: string;
};

function Divider({ S }: { S: PanelStyles }) {
  return <div style={{ height: 1, background: S.border, margin: "12px 0" }} />;
}

function StatRow({
  label,
  value,
  S,
  color = S.t2,
}: {
  label: string;
  value: string | number;
  S: PanelStyles;
  color?: string;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: `1px solid ${S.border}` }}>
      <span style={{ color: S.t4, fontSize: 11 }}>{label}</span>
      <span style={{ color, fontSize: 12, fontWeight: 600, fontFamily: "monospace" }}>{value}</span>
    </div>
  );
}

function PulseBar({
  label,
  pct,
  score,
  color,
  S,
}: {
  label: string;
  pct: number;
  score: number | null;
  color: string;
  S: PanelStyles;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ color: S.t4, fontSize: 11 }}>{label}</span>
        <span style={{ color, fontSize: 11, fontFamily: "monospace", fontWeight: 600 }}>
          {score != null ? score.toFixed(3) : "No data"}
        </span>
      </div>
      <div style={{ height: 5, borderRadius: 4, background: "var(--bg-base)" }}>
        <div style={{
          height: "100%", borderRadius: 4,
          width: `${pct}%`,
          background: score != null ? color : "var(--border)",
          transition: "width 0.4s ease",
        }} />
      </div>
    </div>
  );
}

// ── Seed synthetic coords within Gorakhpur Urban using a low-discrepancy spread ─
function spreadSynthetic(booths: GraphCoverageBooth[]): PlottedBooth[] {
  const { north, south, east, west } = GKP_URBAN;
  const latRange = north - south; // ~0.095
  const lonRange = east  - west;  // ~0.1

  // Split into a grid with slight jitter to avoid strict lines
  const cols = 14;
  let synIdx = 0;

  return booths.map((b) => {
    if (b.lat && b.lon) {
      return { ...b, lat: b.lat, lon: b.lon };
    }
    const col  = synIdx % cols;
    const row  = Math.floor(synIdx / cols);
    const jitterLat = ((synIdx * 7919) % 100) / 100 * 0.004 - 0.002;
    const jitterLon = ((synIdx * 6271) % 100) / 100 * 0.005 - 0.0025;
    synIdx++;
    return {
      ...b,
      lat: south + (row + 0.5) * (latRange / Math.ceil(booths.length / cols)) + jitterLat,
      lon: west  + (col + 0.5) * (lonRange / cols)                              + jitterLon,
    };
  });
}

// ── Booth analysis panel ──────────────────────────────────────────────────────
function BoothAnalysisPanel({
  booth,
  onClose,
}: {
  booth: PlottedBooth;
  onClose: () => void;
}) {
  const total   = booth.total_voters  ?? 0;
  const male    = booth.male_voters   ?? 0;
  const female  = booth.female_voters ?? 0;
  const other   = booth.other_voters  ?? 0;
  const malePct   = total > 0 ? (male / total) * 100 : 0;
  const femalePct = total > 0 ? (female / total) * 100 : 0;
  const genderRatio = male > 0 ? Math.round((female / male) * 1000) : null;

  const bjpScore = booth.bjp_pulse_score;
  const spScore  = booth.opp_pulse_score;
  const bjpBar   = bjpScore != null ? Math.round(((bjpScore + 1) / 2) * 100) : 50;
  const spBar    = spScore  != null ? Math.round(((spScore  + 1) / 2) * 100) : 50;

  const leanKey  = booth.digital_lean_label?.toUpperCase() ?? "INSUFFICIENT";
  const lean     = LEAN_STYLE[leanKey] ?? LEAN_STYLE.INSUFFICIENT;

  const confColor =
    booth.confidence_label === "HIGH"   ? "#10b981" :
    booth.confidence_label === "MEDIUM" ? "#f59e0b" : "#ef4444";

  const confBg =
    booth.confidence_label === "HIGH"   ? "rgba(16,185,129,0.12)" :
    booth.confidence_label === "MEDIUM" ? "rgba(245,158,11,0.12)" : "rgba(239,68,68,0.12)";

  const S = {
    border: "var(--border)",
    t1: "var(--text-1)", t2: "var(--text-2)", t3: "var(--text-3)", t4: "var(--text-4)",
    surface: "var(--bg-surface)",
  };

  return (
    <div style={{
      position: "absolute", top: 0, right: 0, bottom: 0,
      width: 340,
      background: "var(--bg-card)",
      borderLeft: "1px solid var(--border)",
      zIndex: 1000,
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
      boxShadow: "-8px 0 32px rgba(0,0,0,0.35)",
      animation: "slideInRight 0.22s ease",
    }}>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>

      {/* ── Header ── */}
      <div style={{
        padding: "14px 16px 12px",
        borderBottom: `1px solid ${S.border}`,
        background: "var(--bg-surface)",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
              <span style={{
                fontFamily: "monospace", fontSize: 10, fontWeight: 700,
                padding: "2px 7px", borderRadius: 4,
                background: "rgba(249,115,22,0.15)", color: "var(--saffron)",
                border: "1px solid rgba(249,115,22,0.35)",
              }}>
                B-{String(booth.booth_number).padStart(3, "0")}
              </span>
              <span style={{
                fontFamily: "monospace", fontSize: 10,
                padding: "2px 7px", borderRadius: 4,
                background: lean.bg, color: lean.text,
              }}>
                {lean.label}
              </span>
              {booth.in_neo4j && (
                <span style={{
                  fontFamily: "monospace", fontSize: 10,
                  padding: "2px 7px", borderRadius: 4,
                  background: "rgba(16,185,129,0.12)", color: "#10b981",
                  border: "1px solid rgba(16,185,129,0.25)",
                }}>
                  IN KG
                </span>
              )}
            </div>
            <p style={{ color: S.t1, fontSize: 13, fontWeight: 600, margin: 0, lineHeight: 1.35 }}>
              {booth.name}
            </p>
            {(booth.locality_hint || booth.ward_name) && (
              <p style={{ color: S.t4, fontSize: 10, margin: "3px 0 0", display: "flex", alignItems: "center", gap: 4 }}>
                <MapPin size={9} />
                {booth.locality_hint ?? booth.ward_name}
                {booth.ward_name && booth.locality_hint && ` · ${booth.ward_name}`}
              </p>
            )}
          </div>
          <button onClick={onClose} style={{
            background: "transparent", border: "none", cursor: "pointer",
            color: S.t4, padding: 4, borderRadius: 4, flexShrink: 0,
          }}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, padding: "14px 16px", overflowY: "auto" }}>

        {/* Voter demographics */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <div style={{ width: 24, height: 24, borderRadius: 6, background: "rgba(59,130,246,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Users size={13} style={{ color: "#3b82f6" }} />
            </div>
            <span style={{ color: S.t2, fontSize: 12, fontWeight: 600 }}>Voter Demographics</span>
          </div>

          {/* Total voter stat */}
          <div style={{
            display: "flex", alignItems: "baseline", justifyContent: "space-between",
            padding: "8px 12px", borderRadius: 8,
            background: S.surface, border: `1px solid ${S.border}`,
            marginBottom: 10,
          }}>
            <span style={{ color: S.t4, fontSize: 11 }}>Total Registered</span>
            <span style={{ color: S.t1, fontSize: 20, fontWeight: 700, fontFamily: "monospace" }}>
              {total.toLocaleString("en-IN")}
            </span>
          </div>

          {/* M / F / O breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 10 }}>
            {[
              { label: "Male", value: male, pct: malePct, color: "#3b82f6" },
              { label: "Female", value: female, pct: femalePct, color: "#ec4899" },
              { label: "Other", value: other, pct: total > 0 ? (other / total) * 100 : 0, color: "#8b5cf6" },
            ].map(({ label, value, pct, color }) => (
              <div key={label} style={{
                padding: "8px 10px", borderRadius: 8,
                background: S.surface, border: `1px solid ${S.border}`,
                textAlign: "center",
              }}>
                <p style={{ color: S.t4, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 3px" }}>{label}</p>
                <p style={{ color, fontSize: 14, fontWeight: 700, fontFamily: "monospace", margin: "0 0 2px" }}>{value.toLocaleString("en-IN")}</p>
                <p style={{ color: S.t4, fontSize: 10, margin: 0 }}>{pct.toFixed(1)}%</p>
              </div>
            ))}
          </div>

          {/* Gender bar */}
          {total > 0 && (
            <div>
              <div style={{ display: "flex", height: 6, borderRadius: 4, overflow: "hidden", gap: 1 }}>
                <div style={{ width: `${malePct}%`, background: "#3b82f6" }} />
                <div style={{ width: `${femalePct}%`, background: "#ec4899" }} />
                {other > 0 && <div style={{ flex: 1, background: "#8b5cf6" }} />}
              </div>
              {genderRatio != null && (
                <p style={{ color: S.t4, fontSize: 9, margin: "4px 0 0", textAlign: "right" }}>
                  Gender ratio: {genderRatio} F per 1,000 M
                </p>
              )}
            </div>
          )}
        </div>

        <Divider S={S} />

        {/* Party signals */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <div style={{ width: 24, height: 24, borderRadius: 6, background: "rgba(249,115,22,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Activity size={13} style={{ color: "var(--saffron)" }} />
            </div>
            <span style={{ color: S.t2, fontSize: 12, fontWeight: 600 }}>Party Pulse Signals</span>
          </div>
          <PulseBar label="BJP Signal" pct={bjpBar} score={bjpScore} color="#f97316" S={S} />
          <PulseBar label="SP Signal"  pct={spBar}  score={spScore}  color="#3b82f6" S={S} />
          {booth.digital_lean != null && (
            <StatRow label="Net Lean Score" value={booth.digital_lean.toFixed(3)} S={S}
              color={booth.digital_lean > 0 ? "#f97316" : booth.digital_lean < 0 ? "#3b82f6" : "#64748b"} />
          )}
        </div>

        <Divider S={S} />

        {/* Data intelligence */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <div style={{ width: 24, height: 24, borderRadius: 6, background: "rgba(139,92,246,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap size={13} style={{ color: "#8b5cf6" }} />
            </div>
            <span style={{ color: S.t2, fontSize: 12, fontWeight: 600 }}>Data Intelligence</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
            {/* Confidence */}
            <div style={{
              padding: "10px 12px", borderRadius: 8,
              background: confBg, border: `1px solid ${confColor}30`,
              textAlign: "center",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 4, marginBottom: 4 }}>
                {booth.confidence_label === "HIGH" ?
                  <ShieldCheck size={12} style={{ color: confColor }} /> :
                  <AlertTriangle size={12} style={{ color: confColor }} />}
                <span style={{ color: S.t4, fontSize: 9, textTransform: "uppercase" }}>Confidence</span>
              </div>
              <span style={{ color: confColor, fontSize: 15, fontWeight: 700, fontFamily: "monospace" }}>
                {booth.confidence_label ?? "—"}
              </span>
            </div>

            {/* Events */}
            <div style={{
              padding: "10px 12px", borderRadius: 8,
              background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
              textAlign: "center",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 4, marginBottom: 4 }}>
                <BarChart2 size={12} style={{ color: "#10b981" }} />
                <span style={{ color: S.t4, fontSize: 9, textTransform: "uppercase" }}>Events</span>
              </div>
              <span style={{ color: "#10b981", fontSize: 15, fontWeight: 700, fontFamily: "monospace" }}>
                {(booth.event_count ?? 0).toLocaleString("en-IN")}
              </span>
            </div>
          </div>

          <StatRow label="KG Connections" value={booth.neo4j_degree} S={S} color="#10b981" />
          <StatRow label="Knowledge Graph" value={booth.in_neo4j ? "Indexed" : "Not indexed"} S={S}
            color={booth.in_neo4j ? "#10b981" : "#ef4444"} />
          <StatRow label="Booth ID" value={booth.booth_id} S={S} color={S.t3} />
          {booth.lat && (
            <StatRow label="Coordinates" S={S}
              value={`${Number(booth.lat).toFixed(4)}, ${Number(booth.lon).toFixed(4)}`}
              color={S.t4} />
          )}
        </div>

        {/* Top issue */}
        {booth.top_issue && (
          <>
            <Divider S={S} />
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                <div style={{ width: 24, height: 24, borderRadius: 6, background: "rgba(245,158,11,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Target size={13} style={{ color: "#f59e0b" }} />
                </div>
                <span style={{ color: S.t2, fontSize: 12, fontWeight: 600 }}>Top Issue</span>
              </div>
              <div style={{
                padding: "10px 14px", borderRadius: 8,
                background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)",
              }}>
                <span style={{
                  color: "#f59e0b", fontSize: 13, fontWeight: 600,
                  textTransform: "capitalize",
                }}>
                  {booth.top_issue.replace(/_/g, " ")}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Actions ── */}
      <div style={{
        padding: "12px 16px",
        borderTop: `1px solid ${S.border}`,
        display: "flex", flexDirection: "column", gap: 8,
        background: "var(--bg-surface)",
      }}>
        <a href={`/booths/${booth.booth_id}`}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            padding: "9px 0", borderRadius: 8, fontSize: 12, fontWeight: 600,
            background: "rgba(249,115,22,0.12)", color: "var(--saffron)",
            border: "1px solid rgba(249,115,22,0.3)",
            textDecoration: "none",
          }}>
          <BarChart3 size={12} /> Full Intelligence Report
        </a>
        {booth.in_neo4j && (
          <a href={`/graph?type=Booth&id=${booth.booth_id}`}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "9px 0", borderRadius: 8, fontSize: 12,
              background: "rgba(16,185,129,0.08)", color: "#10b981",
              border: "1px solid rgba(16,185,129,0.25)",
              textDecoration: "none",
            }}>
            <Network size={12} /> View in Knowledge Graph
          </a>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function HeatMapClient({ coverage }: Props) {
  const [layer,    setLayer]    = useState<HeatLayer>("voters");
  const [selected, setSelected] = useState<PlottedBooth | null>(null);
  const [search,   setSearch]   = useState("");

  const booths: GraphCoverageBooth[] = useMemo(() => {
    const raw = coverage?.booths ?? [];
    return raw.filter((b) => b.lat !== null && b.lon !== null);
  }, [coverage]);

  const total       = booths.length;
  const inKg        = booths.filter((b) => b.in_neo4j).length;
  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const maxVoters   = booths.length > 0 ? Math.max(...booths.map((b) => b.total_voters ?? 0)) : 0;
  const minVoters   = booths.length > 0 ? Math.min(...booths.map((b) => b.total_voters ?? Infinity)) : 0;
  const realCoordCount = booths.filter((b) => b.lat && b.lon).length;
  const usingRealCoords = realCoordCount === total;

  const plotBooths = useMemo(() => spreadSynthetic(booths), [booths]);

  const filteredBooths = useMemo(() =>
    plotBooths.filter((b) =>
      !search ||
      b.name?.toLowerCase().includes(search.toLowerCase()) ||
      b.locality_hint?.toLowerCase().includes(search.toLowerCase()) ||
      String(b.booth_number).includes(search)
    ), [plotBooths, search]);

  return (
    <div className="flex" style={{ height: "calc(100vh - 56px)", background: "var(--bg-base)" }}>

      {/* ── Left control panel ── */}
      <div className="w-60 shrink-0 flex flex-col overflow-y-auto"
        style={{ borderRight: "1px solid var(--border)" }}>

        {/* Header */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <div className="flex items-center gap-2">
              <Flame size={13} style={{ color: "var(--saffron)" }} />
              <h1 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Constituency Heatmap</h1>
            </div>
            <a href="/graph"
              className="w-6 h-6 rounded flex items-center justify-center"
              style={{ border: "1px solid var(--border)", color: "var(--text-3)" }}
              title="Knowledge Graph">
              <Network size={11} />
            </a>
          </div>
          <p className="text-xs mono" style={{ color: "var(--text-4)" }}>
            Gorakhpur Urban · AC-322
          </p>
          <div className="mt-1.5 inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
            style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)" }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#10b981" }} />
            <span style={{ color: "#10b981", fontSize: 9 }}>
              {realCoordCount} accurate coordinates
            </span>
          </div>
        </div>

        {/* Coords notice */}
        {!usingRealCoords && (
          <div className="mx-3 mt-2 px-3 py-2 rounded-md flex items-start gap-2"
            style={{ background: "rgba(249,115,22,0.05)", border: "1px solid rgba(249,115,22,0.2)" }}>
            <Info size={11} style={{ color: "var(--saffron)", flexShrink: 0, marginTop: 1 }} />
            <p style={{ color: "var(--text-4)", fontSize: 10 }}>
              {total - realCoordCount} booths use estimated positions. Run ETL geocoding for precise coordinates.
            </p>
          </div>
        )}

        {/* Quick stats */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Booths",   value: total,                               color: "var(--saffron)", icon: Flame      },
              { label: "In KG",    value: `${inKg}/${total}`,                  color: "#10b981",        icon: GitBranch  },
              { label: "Voters",   value: (totalVoters / 1000).toFixed(1) + "k", color: "#3b82f6",    icon: Users      },
              { label: "Max/booth",value: maxVoters.toLocaleString("en-IN"),   color: "#8b5cf6",        icon: TrendingUp },
            ].map(({ label, value, color, icon: Icon }) => (
              <div key={label} className="rounded-md px-2 py-2"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                <div className="flex items-center gap-1 mb-0.5">
                  <Icon size={9} style={{ color }} />
                  <p className="label" style={{ color: "var(--text-4)", fontSize: 8 }}>{label}</p>
                </div>
                <p className="mono font-bold text-sm" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Layer selector */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-1.5 mb-2">
            <Layers size={11} style={{ color: "var(--text-4)" }} />
            <p className="label" style={{ color: "var(--text-4)" }}>Heat Layer</p>
          </div>
          <div className="space-y-1">
            {LAYERS.map((l) => {
              const active = layer === l.id;
              return (
                <button key={l.id} onClick={() => setLayer(l.id)}
                  className="w-full text-left px-3 py-2 rounded-md text-xs transition-all"
                  style={{
                    background: active ? hexToRgba(l.color, "18") : "transparent",
                    border: active ? `1px solid ${hexToRgba(l.color, "45")}` : "1px solid transparent",
                    color: active ? l.color : "var(--text-3)",
                  }}>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shrink-0"
                      style={{ background: active ? l.color : "var(--border)" }} />
                    <span className="font-medium">{l.label}</span>
                  </div>
                  {active && (
                    <p className="mt-0.5 ml-4" style={{ color: hexToRgba(l.color, "99"), fontSize: 9 }}>{l.desc}</p>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 size={11} style={{ color: "var(--text-4)" }} />
            <p className="label" style={{ color: "var(--text-4)" }}>Legend</p>
          </div>
          <div className="space-y-1.5">
            {LEGENDS[layer].map(({ label, color }) => (
              <div key={label} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                <span style={{ color: "var(--text-4)", fontSize: 10 }}>{label}</span>
              </div>
            ))}
          </div>
          {layer === "voters" && (
            <p style={{ color: "var(--text-4)", fontSize: 9, marginTop: 8 }}>
              Range: {minVoters.toLocaleString("en-IN")} – {maxVoters.toLocaleString("en-IN")}
            </p>
          )}
        </div>

        {/* Search + booth list */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <p className="label mb-2" style={{ color: "var(--text-4)" }}>Booths ({filteredBooths.length})</p>
          <div className="relative mb-2">
            <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: "var(--text-4)" }} />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Name, locality, number…"
              className="w-full pl-7 pr-2 py-1.5 rounded-md text-xs outline-none"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-1)" }} />
          </div>
          <div className="space-y-1">
            {filteredBooths.slice(0, 80).map((b) => (
              <button key={b.booth_id}
                onClick={() => setSelected(b)}
                className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-all"
                style={{
                  background: selected?.booth_id === b.booth_id ? "rgba(249,115,22,0.08)" : "var(--bg-surface)",
                  border: selected?.booth_id === b.booth_id ? "1px solid rgba(249,115,22,0.3)" : "1px solid var(--border)",
                }}>
                <MapPin size={9} style={{ color: "var(--saffron)", flexShrink: 0 }} />
                <span className="flex-1 truncate" style={{ color: "var(--text-2)" }}>{b.name}</span>
                <span className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>
                  {b.total_voters?.toLocaleString("en-IN") ?? "—"}
                </span>
              </button>
            ))}
            {filteredBooths.length === 0 && (
              <p className="text-xs px-1 py-2" style={{ color: "var(--text-4)" }}>No booths match.</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-3 py-2 mono text-xs flex items-center gap-1.5"
          style={{ borderTop: "1px solid var(--border)", color: "var(--text-4)" }}>
          <MapPin size={9} />
          <span style={{ fontSize: 9 }}>
            {GKP_LAT.toFixed(4)}, {GKP_LON.toFixed(4)} · Gorakhpur Urban
          </span>
        </div>
      </div>

      {/* ── Map area (with analysis panel overlay) ── */}
      <div className="flex-1 relative" style={{ overflow: "hidden" }}>
        <LeafletMap
          booths={filteredBooths}
          layer={layer}
          onSelect={setSelected}
          selected={selected}
        />

        {/* Top-right info chip */}
        <div style={{
          position: "absolute", top: 12, right: selected ? 352 : 12,
          zIndex: 10, transition: "right 0.22s ease",
          pointerEvents: "none",
        }}>
          <div className="rounded-md px-3 py-2"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", boxShadow: "var(--shadow-md)" }}>
            <p className="mono text-xs" style={{ color: "var(--text-2)" }}>
              <span style={{ color: "var(--saffron)" }}>●</span>{" "}
              {total} booths · {LAYERS.find((l) => l.id === layer)?.label}
            </p>
            <p className="mono" style={{ color: "var(--text-4)", fontSize: 9, marginTop: 2 }}>
              Click a booth to analyse
            </p>
          </div>
        </div>

        {/* Slide-in analysis panel */}
        {selected && (
          <BoothAnalysisPanel booth={selected} onClose={() => setSelected(null)} />
        )}
      </div>
    </div>
  );
}
