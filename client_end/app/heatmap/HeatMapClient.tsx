"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { GraphCoverageResponse, GraphCoverageBooth } from "@/lib/api";
import type { HeatLayer, PlottedBooth } from "./LeafletMap";
import {
  Flame, Layers, BarChart3, X, Users, GitBranch,
  AlertCircle, Info, TrendingUp, Network
} from "lucide-react";

const Map = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center"
      style={{ background: "var(--bg-base)" }}>
      <div className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin mb-3" />
      <p className="text-xs mono" style={{ color: "var(--text-3)" }}>
        Initialising constituency heatmap…
      </p>
    </div>
  ),
});

// ── Synthetic coordinate generator ──────────────────────────────────────────
// Phyllotaxis (golden angle) spiral centred on Gorakhpur Urban
// Produces a natural, non-gridded scatter within ~2 km radius
const GKP_LAT = 26.7606;
const GKP_LON = 83.3732;
const GOLDEN_ANGLE = 2.39996; // radians (~137.5°)
const MAX_BOOTHS = 30;

function syntheticCoord(boothNum: number): [number, number] {
  const theta = (boothNum - 1) * GOLDEN_ANGLE;
  const r = 0.019 * Math.sqrt(boothNum / MAX_BOOTHS);
  return [
    GKP_LAT + r * Math.sin(theta),
    GKP_LON + r * 1.18 * Math.cos(theta), // slight E-W stretch for realistic shape
  ];
}

function addCoords(b: GraphCoverageBooth): PlottedBooth {
  const [lat, lon] = b.lat != null && b.lon != null
    ? [b.lat, b.lon]
    : syntheticCoord(b.booth_number);
  return { ...b, synthLat: lat, synthLon: lon };
}

// ── Layer config ─────────────────────────────────────────────────────────────
const LAYERS: {
  id: HeatLayer;
  label: string;
  desc: string;
  color: string;
  hasData: boolean;
}[] = [
  {
    id: "voters",
    label: "Voter Density",
    desc: "Heat intensity by registered voter count",
    color: "#f97316",
    hasData: true,
  },
  {
    id: "kg_coverage",
    label: "KG Coverage",
    desc: "Knowledge Graph node presence per booth",
    color: "#10b981",
    hasData: true,
  },
  {
    id: "bjp_lean",
    label: "Political Lean",
    desc: "BJP vs Opposition digital pulse signal",
    color: "#3b82f6",
    hasData: false,
  },
  {
    id: "confidence",
    label: "Data Quality",
    desc: "Data confidence score per booth",
    color: "#8b5cf6",
    hasData: false,
  },
];

const LEGENDS: Record<HeatLayer, { label: string; color: string }[]> = {
  voters: [
    { label: "High (2000+ voters)",  color: "#ef4444" },
    { label: "Medium (1200–2000)",   color: "#f97316" },
    { label: "Low (< 1200 voters)",  color: "#3b82f6" },
  ],
  kg_coverage: [
    { label: "Present in Neo4j",     color: "#10b981" },
    { label: "Not in graph",         color: "var(--text-4)" },
  ],
  bjp_lean: [
    { label: "Strong BJP (+0.3+)",   color: "#f97316" },
    { label: "Lean BJP",             color: "#fb923c" },
    { label: "Neutral",              color: "var(--text-3)" },
    { label: "Lean Opp",             color: "#60a5fa" },
    { label: "Strong Opp",           color: "#3b82f6" },
    { label: "No signal",            color: "var(--text-4)" },
  ],
  confidence: [
    { label: "HIGH",                 color: "#10b981" },
    { label: "MEDIUM",               color: "#f59e0b" },
    { label: "LOW",                  color: "#ef4444" },
    { label: "Unknown",              color: "var(--text-4)" },
  ],
};

interface Props {
  coverage: GraphCoverageResponse | null;
}

export default function HeatMapClient({ coverage }: Props) {
  const [layer, setLayer] = useState<HeatLayer>("voters");
  const [selected, setSelected] = useState<PlottedBooth | null>(null);

  const booths: PlottedBooth[] = useMemo(
    () => (coverage?.booths ?? []).map(addCoords),
    [coverage]
  );

  const total      = booths.length;
  const inKg       = booths.filter((b) => b.in_neo4j).length;
  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const maxVoters  = Math.max(...booths.map((b) => b.total_voters ?? 0));
  const minVoters  = Math.min(...booths.map((b) => b.total_voters ?? Infinity));

  const usingRealCoords = booths.some((b) => b.lat != null);

  return (
    <div className="flex" style={{ height: "calc(100vh - 44px)", background: "var(--bg-base)" }}>

      {/* ── Left control panel ── */}
      <div className="w-64 flex-shrink-0 flex flex-col overflow-y-auto"
        style={{ borderRight: "1px solid var(--border)" }}>

        {/* Header */}
        <div className="px-4 py-3.5" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <div className="flex items-center gap-2">
              <Flame size={13} style={{ color: "var(--saffron)" }} />
              <h1 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>
                Constituency Heatmap
              </h1>
            </div>
            <a href="/graph"
              className="w-6 h-6 rounded flex items-center justify-center transition-all"
              style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--text-3)" }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(249,115,22,0.1)"; e.currentTarget.style.borderColor = "rgba(249,115,22,0.4)"; e.currentTarget.style.color = "var(--saffron)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--text-3)"; }}
              title="Go to Knowledge Graph">
              <Network size={11} />
            </a>
          </div>
          <p className="text-xs mono" style={{ color: "var(--text-4)" }}>
            {total} booths · Gorakhpur Urban AC
          </p>
        </div>

        {/* Synthetic coords notice */}
        {!usingRealCoords && (
          <div className="mx-3 mt-2 px-3 py-2 rounded-md flex items-start gap-2"
            style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)" }}>
            <Info size={11} style={{ color: "var(--saffron)", flexShrink: 0, marginTop: 1 }} />
            <p className="text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>
              Positions are estimated — run the geocoding ETL for precise coordinates.
            </p>
          </div>
        )}

        {/* Quick stats */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Booths",      value: total,                              color: "var(--saffron)",  icon: Flame   },
              { label: "In KG",       value: `${inKg}/${total}`,                  color: "#10b981",         icon: GitBranch },
              { label: "Total voters",value: (totalVoters / 1000).toFixed(1)+"k", color: "var(--blue)",     icon: Users   },
              { label: "Max booth",   value: `${maxVoters.toLocaleString("en-IN")}`, color: "#8b5cf6",     icon: TrendingUp },
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
                    background: active ? `${l.color}18` : "transparent",
                    border: active ? `1px solid ${l.color}45` : "1px solid transparent",
                    color: active ? l.color : "var(--text-3)",
                  }}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: active ? l.color : "var(--border)" }} />
                      <span className="font-medium">{l.label}</span>
                    </div>
                    {!l.hasData && (
                      <span className="mono px-1 py-0.5 rounded"
                        style={{ background: "var(--bg-surface)", color: "var(--text-4)", fontSize: 8, border: "1px solid var(--border)" }}>
                        AWAITING
                      </span>
                    )}
                  </div>
                  {active && (
                    <p className="mt-0.5 ml-4" style={{ color: `${l.color}99`, fontSize: 9 }}>
                      {l.desc}
                    </p>
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
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                <span className="text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>{label}</span>
              </div>
            ))}
          </div>
          {layer === "voters" && (
            <p className="text-xs mt-2" style={{ color: "var(--text-4)", fontSize: 9 }}>
              Range: {minVoters.toLocaleString("en-IN")} – {maxVoters.toLocaleString("en-IN")} voters
            </p>
          )}
        </div>

        {/* Selected booth */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {selected ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="label" style={{ color: "var(--text-4)" }}>Selected Booth</p>
                <button onClick={() => setSelected(null)}>
                  <X size={10} style={{ color: "var(--text-4)" }} />
                </button>
              </div>
              <div className="rounded-md p-3"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
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
                      background: "rgba(16,185,129,0.1)",
                      color: "#10b981",
                      border: "1px solid rgba(16,185,129,0.3)",
                      fontSize: 9,
                    }}>
                    IN GRAPH
                  </span>
                </div>
                <p className="text-xs font-semibold mb-3 leading-snug"
                  style={{ color: "var(--text-1)" }}>
                  {selected.name}
                </p>
                <div className="space-y-1.5">
                  {[
                    { label: "Booth ID",   value: selected.booth_id,                               color: "var(--text-3)" },
                    { label: "Voters",     value: selected.total_voters?.toLocaleString("en-IN") ?? "—", color: "var(--saffron)" },
                    { label: "BJP pulse",  value: selected.bjp_pulse_score?.toFixed(3) ?? "No data", color: "#f97316" },
                    { label: "Opp pulse",  value: selected.opp_pulse_score?.toFixed(3) ?? "No data", color: "#3b82f6" },
                    { label: "Confidence", value: selected.confidence_label ?? "No data",           color: selected.confidence_label === "HIGH" ? "#10b981" : selected.confidence_label === "LOW" ? "#ef4444" : "var(--text-4)" },
                    { label: "KG degree",  value: String(selected.neo4j_degree),                   color: "#10b981" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex justify-between py-0.5"
                      style={{ borderBottom: "1px solid var(--border)" }}>
                      <span className="text-xs" style={{ color: "var(--text-4)" }}>{label}</span>
                      <span className="mono text-xs font-medium" style={{ color, fontSize: 11 }}>{value}</span>
                    </div>
                  ))}
                </div>
                <a href={`/booths/${selected.booth_id}`}
                  className="mt-3 flex items-center justify-center py-2 rounded-md text-xs mono transition-all hover:opacity-80"
                  style={{
                    background: "rgba(249,115,22,0.1)",
                    color: "var(--saffron)",
                    border: "1px solid rgba(249,115,22,0.3)",
                  }}>
                  Full Intelligence Report →
                </a>
                {selected.in_neo4j && (
                  <a href={`/graph?type=Booth&id=${selected.booth_id}`}
                    className="mt-2 flex items-center justify-center py-2 rounded-md text-xs mono transition-all hover:opacity-80"
                    style={{
                      background: "rgba(16,185,129,0.1)",
                      color: "#10b981",
                      border: "1px solid rgba(16,185,129,0.3)",
                    }}>
                    <Network size={9} className="mr-1" /> View in Knowledge Graph
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-24 text-center">
              <Flame size={20} className="mb-2" style={{ color: "var(--border)" }} />
              <p className="text-xs" style={{ color: "var(--text-4)" }}>Click any booth marker</p>
              <p style={{ color: "var(--text-4)", fontSize: 9 }} className="mt-0.5 mono">
                to inspect intelligence data
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-3 py-2 mono text-xs flex items-center gap-1.5"
          style={{ borderTop: "1px solid var(--border)", color: "var(--text-4)" }}>
          <AlertCircle size={9} />
          <span style={{ fontSize: 9 }}>
            {usingRealCoords ? "Live coordinates" : "Estimated positions"}
          </span>
        </div>
      </div>

      {/* ── Map ── */}
      <div className="flex-1 relative">
        {booths.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-3"
            style={{ background: "var(--bg-base)" }}>
            <Flame size={40} style={{ color: "var(--border)" }} />
            <p className="text-sm" style={{ color: "var(--text-3)" }}>No booth data available</p>
            <p className="text-xs" style={{ color: "var(--text-4)" }}>
              Ensure the API is running at localhost:8000
            </p>
          </div>
        ) : (
          <Map
            booths={booths}
            layer={layer}
            onSelect={setSelected}
            selected={selected}
          />
        )}

        {/* Map overlay — booth count + layer name */}
        {booths.length > 0 && (
          <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
            <div className="rounded-md px-3 py-2"
              style={{
                background: "rgba(6,11,20,0.88)",
                border: "1px solid var(--border)",
                backdropFilter: "blur(8px)",
              }}>
              <p className="mono text-xs" style={{ color: "var(--text-3)" }}>
                <span style={{ color: "var(--saffron)" }}>●</span>{" "}
                {booths.length} booths · {LAYERS.find((l) => l.id === layer)?.label}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
