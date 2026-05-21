"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { GeoRow } from "@/lib/api";
import { MapPin, Layers, BarChart3, AlertTriangle, Filter, X } from "lucide-react";

const Map = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center" style={{ background: "#060b14" }}>
      <div className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin mb-3" />
      <p className="text-xs mono" style={{ color: "#4d6480" }}>Initialising geospatial engine…</p>
    </div>
  )
});

type Layer = "lean" | "issues" | "narrative_risk" | "scheme_gap" | "confidence" | "voters";

const LAYERS: { id: Layer; label: string; desc: string; color: string }[] = [
  { id: "lean",           label: "Political Lean",    desc: "BJP vs Opposition sentiment", color: "#f97316" },
  { id: "confidence",     label: "Data Quality",      desc: "Confidence level per booth",  color: "#10b981" },
  { id: "voters",         label: "Voter Density",     desc: "Relative voter volume",       color: "#3b82f6" },
  { id: "issues",         label: "Issue Intensity",   desc: "BJP pulse as issue proxy",    color: "#ef4444" },
  { id: "narrative_risk", label: "Narrative Risk",    desc: "Opposition pulse as risk",    color: "#8b5cf6" },
  { id: "scheme_gap",     label: "Scheme Gap",        desc: "Delivery gap proxy",          color: "#f59e0b" },
];

interface Props { geo: GeoRow[] }

export default function HeatMapClient({ geo }: Props) {
  const [layer, setLayer] = useState<Layer>("lean");
  const [selected, setSelected] = useState<GeoRow | null>(null);
  const [filterLean, setFilterLean] = useState<string | null>(null);

  const geocoded = geo.filter((g) => g.lat && g.lon);
  const displayed = filterLean
    ? geocoded.filter((g) => g.digital_lean_label?.toUpperCase().includes(filterLean))
    : geocoded;

  // Stats
  const bjpCount = geocoded.filter((g) => g.digital_lean_label?.includes("BJP")).length;
  const oppCount = geocoded.filter((g) => g.digital_lean_label?.includes("OPP")).length;
  const neutralCount = geocoded.filter((g) => g.digital_lean_label?.includes("NEUTRAL")).length;
  const avgBjp = geocoded.filter((g) => g.bjp_pulse_score != null).length > 0
    ? geocoded.reduce((s, g) => s + (g.bjp_pulse_score ?? 0), 0) / geocoded.filter((g) => g.bjp_pulse_score != null).length
    : null;
  const totalVoters = geocoded.reduce((s, g) => s + (g.total_voters ?? 0), 0);

  return (
    <div className="flex h-screen" style={{ background: "#060b14" }}>
      {/* Left control panel */}
      <div className="w-64 flex-shrink-0 flex flex-col" style={{ borderRight: "1px solid #1a2b44" }}>
        {/* Header */}
        <div className="px-4 py-3.5" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-2 mb-0.5">
            <MapPin size={13} style={{ color: "#f97316" }} />
            <h1 className="text-sm font-bold text-white">Geospatial Command</h1>
          </div>
          <p className="text-xs mono" style={{ color: "#4d6480" }}>
            {geocoded.length}/{geo.length} booths geocoded
          </p>
        </div>

        {/* Coverage warning */}
        {geo.length > 0 && geocoded.length / geo.length < 0.85 && (
          <div className="mx-3 mt-2 px-3 py-2 rounded-md flex items-start gap-2"
            style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)" }}>
            <AlertTriangle size={11} style={{ color: "#f59e0b", flexShrink: 0, marginTop: 1 }} />
            <p className="text-xs" style={{ color: "#f59e0b" }}>
              Coverage {((geocoded.length / geo.length) * 100).toFixed(0)}% — target ≥85%
            </p>
          </div>
        )}

        {/* Quick stats */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "BJP Lean", value: bjpCount, color: "#f97316" },
              { label: "Opp Lean", value: oppCount, color: "#3b82f6" },
              { label: "Neutral",  value: neutralCount, color: "#64748b" },
              { label: "Avg BJP",  value: avgBjp != null ? avgBjp.toFixed(2) : "—", color: "#f97316" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-md px-2 py-2" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                <p className="label mb-0.5" style={{ color: "#2e4260" }}>{label}</p>
                <p className="mono font-bold text-sm" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Layer selector */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-1.5 mb-2">
            <Layers size={11} style={{ color: "#4d6480" }} />
            <p className="label" style={{ color: "#4d6480" }}>Intelligence Layer</p>
          </div>
          <div className="space-y-1">
            {LAYERS.map((l) => (
              <button key={l.id} onClick={() => setLayer(l.id)}
                className="w-full text-left px-3 py-2 rounded-md text-xs transition-all"
                style={{
                  background: layer === l.id ? `${l.color}15` : "transparent",
                  border: layer === l.id ? `1px solid ${l.color}40` : "1px solid transparent",
                  color: layer === l.id ? l.color : "#4d6480",
                }}>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: layer === l.id ? l.color : "#1a2b44" }} />
                  <span className="font-medium">{l.label}</span>
                </div>
                {layer === l.id && (
                  <p className="text-xs mt-0.5 ml-4" style={{ color: `${l.color}99`, fontSize: 9 }}>{l.desc}</p>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Quick filter */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-1.5 mb-2">
            <Filter size={11} style={{ color: "#4d6480" }} />
            <p className="label" style={{ color: "#4d6480" }}>Filter by Lean</p>
            {filterLean && (
              <button onClick={() => setFilterLean(null)} className="ml-auto">
                <X size={10} style={{ color: "#4d6480" }} />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1">
            {["BJP", "OPP", "NEUTRAL"].map((f) => (
              <button key={f} onClick={() => setFilterLean(filterLean === f ? null : f)}
                className="px-2 py-1 rounded mono transition-all"
                style={{
                  background: filterLean === f ? (f === "BJP" ? "#f9731620" : f === "OPP" ? "#3b82f620" : "#64748b20") : "#0b1220",
                  border: `1px solid ${filterLean === f ? (f === "BJP" ? "#f97316" : f === "OPP" ? "#3b82f6" : "#64748b") : "#1a2b44"}`,
                  color: filterLean === f ? (f === "BJP" ? "#f97316" : f === "OPP" ? "#3b82f6" : "#94a3b8") : "#4d6480",
                  fontSize: 9
                }}>
                {f}
              </button>
            ))}
          </div>
          <p className="text-xs mono mt-1.5" style={{ color: "#2e4260" }}>
            Showing {displayed.length} of {geocoded.length}
          </p>
        </div>

        {/* Legend */}
        <div className="px-3 py-3" style={{ borderBottom: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 size={11} style={{ color: "#4d6480" }} />
            <p className="label" style={{ color: "#4d6480" }}>Legend</p>
          </div>
          {layer === "lean" && (
            <div className="space-y-1">
              {[
                { label: "Strong BJP",  color: "#f97316" },
                { label: "Lean BJP",    color: "#fb923c" },
                { label: "Neutral",     color: "#64748b" },
                { label: "Lean Opp",    color: "#60a5fa" },
                { label: "Strong Opp",  color: "#3b82f6" },
                { label: "No signal",   color: "#1a2b44" },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-xs" style={{ color: "#4d6480" }}>{label}</span>
                </div>
              ))}
            </div>
          )}
          {layer === "confidence" && (
            <div className="space-y-1">
              {[
                { label: "HIGH",    color: "#10b981" },
                { label: "MEDIUM",  color: "#f59e0b" },
                { label: "LOW",     color: "#ef4444" },
                { label: "Unknown", color: "#374151" },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-xs" style={{ color: "#4d6480" }}>{label}</span>
                </div>
              ))}
            </div>
          )}
          {layer === "voters" && (
            <div>
              <p className="text-xs mb-1" style={{ color: "#4d6480" }}>Marker radius ∝ voter count</p>
              <div className="flex items-end gap-3">
                {[["Small", 6], ["Medium", 10], ["Large", 15]].map(([l, s]) => (
                  <div key={String(l)} className="flex flex-col items-center gap-1">
                    <div className="rounded-full" style={{ width: Number(s), height: Number(s), background: "#3b82f6", opacity: 0.7 }} />
                    <span className="text-xs" style={{ color: "#4d6480", fontSize: 9 }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!["lean", "confidence", "voters"].includes(layer) && (
            <div className="space-y-1">
              {[
                { label: "High intensity", color: "#ef4444" },
                { label: "Medium",         color: "#f59e0b" },
                { label: "Low",            color: "#10b981" },
                { label: "No data",        color: "#374151" },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-xs" style={{ color: "#4d6480" }}>{label}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected booth */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {selected ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="label" style={{ color: "#4d6480" }}>Selected Booth</p>
                <button onClick={() => setSelected(null)}><X size={10} style={{ color: "#4d6480" }} /></button>
              </div>
              <div className="rounded-md p-3" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="mono text-xs px-1.5 py-0.5 rounded"
                    style={{ background: "#060b14", color: "#f97316", border: "1px solid #f9731630", fontSize: 9 }}>
                    B-{String(selected.booth_number).padStart(3, "0")}
                  </span>
                </div>
                <p className="text-xs font-medium text-white mb-0.5">{selected.name}</p>
                {selected.locality_hint && (
                  <p className="text-xs mb-2" style={{ color: "#4d6480" }}>{selected.locality_hint}</p>
                )}
                <div className="space-y-1 text-xs">
                  {[
                    { label: "Total voters", value: selected.total_voters?.toLocaleString("en-IN") ?? "—", color: "#f0f4fa" },
                    { label: "BJP pulse",    value: selected.bjp_pulse_score?.toFixed(3) ?? "—",         color: "#f97316" },
                    { label: "Opp pulse",    value: selected.opp_pulse_score?.toFixed(3) ?? "—",         color: "#3b82f6" },
                    { label: "Lean",         value: selected.digital_lean_label ?? "—",                  color: "#8ba0bc" },
                    { label: "Top issue",    value: selected.top_issue?.replace(/_/g, " ") ?? "—",       color: "#8ba0bc" },
                    { label: "Confidence",   value: selected.confidence_label ?? "—",                    color: selected.confidence_label === "HIGH" ? "#10b981" : selected.confidence_label === "LOW" ? "#ef4444" : "#f59e0b" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex justify-between py-0.5"
                      style={{ borderBottom: "1px solid #1a2b44" }}>
                      <span style={{ color: "#4d6480" }}>{label}</span>
                      <span className="mono font-medium capitalize" style={{ color, fontSize: 11 }}>{value}</span>
                    </div>
                  ))}
                </div>
                <a href={`/booths/${selected.booth_id}`}
                  className="mt-3 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs mono transition-all hover:opacity-80"
                  style={{ background: "rgba(249,115,22,0.12)", color: "#f97316", border: "1px solid rgba(249,115,22,0.3)" }}>
                  Full Intelligence Report →
                </a>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-24 text-center">
              <MapPin size={20} className="mb-2" style={{ color: "#1a2b44" }} />
              <p className="text-xs" style={{ color: "#2e4260" }}>Click a booth marker</p>
              <p className="text-xs mt-0.5" style={{ color: "#1a2b44", fontSize: 9 }}>to see intelligence data</p>
            </div>
          )}
        </div>

        {/* Total voters */}
        <div className="px-3 py-2.5 mono text-xs" style={{ borderTop: "1px solid #1a2b44", color: "#2e4260" }}>
          Geocoded voters: {totalVoters.toLocaleString("en-IN")}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {geocoded.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center">
            <MapPin size={40} className="mb-3" style={{ color: "#1a2b44" }} />
            <p className="text-white text-sm">No geocoded booth data</p>
            <p className="text-xs mt-1" style={{ color: "#4d6480" }}>Run etl/geocode_booths.py to add coordinates</p>
          </div>
        ) : (
          <Map geo={displayed} layer={layer} onSelect={setSelected} />
        )}
        {/* Map overlay stats */}
        <div className="absolute top-3 right-3 flex flex-col gap-2 z-10">
          <div className="rounded-md px-3 py-2" style={{ background: "rgba(6,11,20,0.92)", border: "1px solid #1a2b44", backdropFilter: "blur(8px)" }}>
            <p className="mono text-xs" style={{ color: "#4d6480" }}>
              <span style={{ color: "#10b981" }}>●</span> {displayed.length} booths displayed
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
