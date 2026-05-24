"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { GraphCoverageResponse, GraphCoverageBooth } from "@/lib/api";
import { type PlottedBooth } from "./LeafletMap";
import {
  Flame, Layers, BarChart3, X, Users, GitBranch,
  TrendingUp, Network, Search, MapPin, Info
} from "lucide-react";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });

export type HeatLayer = "voters" | "kg_coverage" | "bjp_lean" | "confidence";

// BharatMaps (NIC, Govt. of India) — embedded official map portal.
// Gorakhpur district bounds (extracted from stategisportal.nic.in WMS).
const GKP_LAT = 26.6675;
const GKP_LON = 83.3694;
const BHARATMAPS_URL =
  process.env.NEXT_PUBLIC_BHARATMAPS_URL ?? "https://bharatmaps.gov.in/bharatmaps/";

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
      desc: "Party digital pulse signal — BJP · SP · BSP",
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
    { label: "High (2000+ voters)", color: "#ef4444" },
    { label: "Medium (1200–2000)", color: "#f97316" },
    { label: "Low (< 1200 voters)", color: "#3b82f6" },
  ],
  kg_coverage: [
    { label: "Present in Neo4j", color: "#10b981" },
    { label: "Not in graph", color: "var(--text-4)" },
  ],
  bjp_lean: [
    { label: "Strong BJP (+0.3+)", color: "#f97316" },
    { label: "Lean BJP", color: "#fb923c" },
    { label: "Neutral", color: "var(--text-3)" },
    { label: "Lean SP", color: "#60a5fa" },
    { label: "Strong SP", color: "#3b82f6" },
    { label: "No signal", color: "var(--text-4)" },
  ],
  confidence: [
    { label: "HIGH", color: "#10b981" },
    { label: "MEDIUM", color: "#f59e0b" },
    { label: "LOW", color: "#ef4444" },
    { label: "Unknown", color: "var(--text-4)" },
  ],
};

interface Props {
  coverage: GraphCoverageResponse | null;
}

export default function HeatMapClient({ coverage }: Props) {
  const [layer, setLayer] = useState<HeatLayer>("voters");
  const [selected, setSelected] = useState<any>(null);
  const [search, setSearch] = useState("");

  const booths: GraphCoverageBooth[] = useMemo(() => coverage?.booths ?? [], [coverage]);

  const total = booths.length;
  const inKg = booths.filter((b) => b.in_neo4j).length;
  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const maxVoters = Math.max(...booths.map((b) => b.total_voters ?? 0));
  const minVoters = Math.min(...booths.map((b) => b.total_voters ?? Infinity));
  const usingRealCoords = booths.length > 0 && booths.every((b) => b.lat && b.lon);

  // Add synthetic coordinates if not present (distribute within Gorakhpur bounds)
  const plotBooths = useMemo(() => {
    const gorakhpurBounds = {
      north: 27.116212,
      south: 26.218752,
      east: 83.671043,
      west: 83.067767,
    };

    return booths.map((b, idx) => ({
      ...b,
      lat: b.lat ?? (gorakhpurBounds.south + (idx % 13) * 0.068),
      lon: b.lon ?? (gorakhpurBounds.west + Math.floor(idx / 13) * 0.085),
    }));
  }, [booths]);

  const filteredBooths = plotBooths.filter((b) =>
    !search ||
    b.name?.toLowerCase().includes(search.toLowerCase()) ||
    String(b.booth_number).includes(search));

  return (
    <div className="flex" style={{ height: "calc(100vh - 56px)", background: "var(--bg-base)" }}>

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
          <div className="mt-1.5 inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
            style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)" }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--green)" }} />
            <span className="text-xs" style={{ color: "var(--green)", fontSize: 9.5 }}>
              Basemap: BharatMaps · NIC
            </span>
          </div>
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
              { label: "Booths", value: total, color: "var(--saffron)", icon: Flame },
              { label: "In KG", value: `${inKg}/${total}`, color: "#10b981", icon: GitBranch },
              { label: "Total voters", value: (totalVoters / 1000).toFixed(1) + "k", color: "var(--blue)", icon: Users },
              { label: "Max booth", value: `${maxVoters.toLocaleString("en-IN")}`, color: "#8b5cf6", icon: TrendingUp },
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
                    { label: "Booth ID", value: selected.booth_id, color: "var(--text-3)" },
                    { label: "Voters", value: selected.total_voters?.toLocaleString("en-IN") ?? "—", color: "var(--saffron)" },
                    { label: "BJP signal", value: selected.bjp_pulse_score?.toFixed(3) ?? "No data", color: "#f97316" },
                    { label: "SP signal",  value: selected.opp_pulse_score?.toFixed(3) ?? "No data", color: "#3b82f6" },
                    { label: "Confidence", value: selected.confidence_label ?? "No data", color: selected.confidence_label === "HIGH" ? "#10b981" : selected.confidence_label === "LOW" ? "#ef4444" : "var(--text-4)" },
                    { label: "KG degree", value: String(selected.neo4j_degree), color: "#10b981" },
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
            <div>
              <p className="label mb-2" style={{ color: "var(--text-4)" }}>Booths ({total})</p>
              <div className="relative mb-2">
                <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: "var(--text-4)" }} />
                <input value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search booth…"
                  className="w-full pl-7 pr-2 py-1.5 rounded-md text-xs outline-none"
                  style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-1)" }} />
              </div>
              <div className="space-y-1">
                {filteredBooths.map((b) => (
                  <button key={b.booth_id} onClick={() => setSelected(b)}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-all"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-surface)")}>
                    <MapPin size={9} style={{ color: "var(--saffron)", flexShrink: 0 }} />
                    <span className="flex-1 truncate" style={{ color: "var(--text-2)" }}>{b.name}</span>
                    <span className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>{b.total_voters?.toLocaleString("en-IN") ?? "—"}</span>
                  </button>
                ))}
                {filteredBooths.length === 0 && (
                  <p className="text-xs px-1 py-2" style={{ color: "var(--text-4)" }}>No booths match.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-3 py-2 mono text-xs flex items-center gap-1.5"
          style={{ borderTop: "1px solid var(--border)", color: "var(--text-4)" }}>
          <MapPin size={9} />
          <span style={{ fontSize: 9 }}>BharatMaps · NIC, Govt. of India</span>
        </div>
      </div>

      {/* ── Interactive Leaflet Map ── */}
      <div className="flex-1 relative" style={{ background: "var(--bg-base)" }}>
        <LeafletMap
          booths={filteredBooths}
          layer={layer}
          onSelect={setSelected}
          selected={selected}
        />

        {/* Context overlay — Gorakhpur + active layer */}
        <div className="absolute top-3 right-3 z-10 flex flex-col gap-2 pointer-events-none">
          <div className="rounded-md px-3 py-2"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", boxShadow: "var(--shadow-md)" }}>
            <p className="mono text-xs" style={{ color: "var(--text-2)" }}>
              <span style={{ color: "var(--saffron)" }}>●</span>{" "}
              Gorakhpur · {total} booths
            </p>
            <p className="mono" style={{ color: "var(--text-4)", fontSize: 9, marginTop: 2 }}>
              {GKP_LAT.toFixed(4)}, {GKP_LON.toFixed(4)} · {usingRealCoords ? "Real coords" : "Synthetic"} · {LAYERS.find((l) => l.id === layer)?.label}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
