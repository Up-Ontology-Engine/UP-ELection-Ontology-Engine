"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, WMSTileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { GraphCoverageBooth } from "@/lib/api";
import "leaflet/dist/leaflet.css";

// ── BharatMaps (NIC, Govt. of India) WMS basemap ─────────────────────────────
// BharatMaps is an OGC WMS map service, not a JS map library — it's consumed
// *through* a renderer (Leaflet here). It is NOT a public/open API: NIC issues
// the WMS endpoint, layer name and access token only to departments under a
// formal agreement (see https://mapservice.gov.in). Configure via env so the
// real layer activates once NIC credentials are in hand; otherwise we fall back
// to an open basemap so the heatmap keeps working.
//   NEXT_PUBLIC_BHARATMAPS_WMS_URL     e.g. https://mapservice.gov.in/.../wms
//   NEXT_PUBLIC_BHARATMAPS_WMS_LAYERS  e.g. bharatmaps:india_base
//   NEXT_PUBLIC_BHARATMAPS_WMS_FORMAT  default image/png
//   NEXT_PUBLIC_BHARATMAPS_TOKEN       NIC-issued access token (optional)
const BHARATMAPS_WMS_URL    = process.env.NEXT_PUBLIC_BHARATMAPS_WMS_URL;
const BHARATMAPS_WMS_LAYERS = process.env.NEXT_PUBLIC_BHARATMAPS_WMS_LAYERS ?? "";
const BHARATMAPS_WMS_FORMAT = process.env.NEXT_PUBLIC_BHARATMAPS_WMS_FORMAT ?? "image/png";
const BHARATMAPS_TOKEN      = process.env.NEXT_PUBLIC_BHARATMAPS_TOKEN;
export const BHARATMAPS_ACTIVE = Boolean(BHARATMAPS_WMS_URL && BHARATMAPS_WMS_LAYERS);

export type HeatLayer = "voters" | "kg_coverage" | "bjp_lean" | "confidence";

export interface PlottedBooth extends GraphCoverageBooth {
  synthLat: number;
  synthLon: number;
}

interface Props {
  booths: PlottedBooth[];
  layer: HeatLayer;
  onSelect: (b: PlottedBooth) => void;
  selected: PlottedBooth | null;
}

// Voter count thresholds for normalised heat colour
const MAX_VOTERS = 3000;

function hsl(h: number, s: number, l: number) {
  return `hsl(${h},${s}%,${l}%)`;
}

function getHeatColor(b: PlottedBooth, layer: HeatLayer): { fill: string; glow: string } {
  if (layer === "voters") {
    const ratio = Math.min((b.total_voters ?? 0) / MAX_VOTERS, 1);
    // low → blue, mid → orange, high → red
    const h = 220 - ratio * 200;   // 220 (blue) → 20 (orange-red)
    const s = 70 + ratio * 25;
    const l = 45 + ratio * 10;
    const fill = hsl(h, s, l);
    return { fill, glow: fill };
  }

  if (layer === "kg_coverage") {
    return b.in_neo4j
      ? { fill: "#10b981", glow: "#10b981" }
      : { fill: "#94a3b8", glow: "#94a3b8" };
  }

  if (layer === "bjp_lean") {
    const s = b.bjp_pulse_score;
    if (s == null) return { fill: "#94a3b8", glow: "#94a3b8" };
    if (s > 0.3)  return { fill: "#f97316", glow: "#f97316" };
    if (s > 0.1)  return { fill: "#fb923c", glow: "#fb923c" };
    if (s > -0.1) return { fill: "#64748b", glow: "#64748b" };
    if (s > -0.3) return { fill: "#60a5fa", glow: "#60a5fa" };
    return { fill: "#3b82f6", glow: "#3b82f6" };
  }

  if (layer === "confidence") {
    const l = b.confidence_label?.toUpperCase() ?? "";
    if (l === "HIGH")   return { fill: "#10b981", glow: "#10b981" };
    if (l === "MEDIUM") return { fill: "#f59e0b", glow: "#f59e0b" };
    if (l === "LOW")    return { fill: "#ef4444", glow: "#ef4444" };
    return { fill: "#94a3b8", glow: "#94a3b8" };
  }

  return { fill: "#94a3b8", glow: "#94a3b8" };
}

function getCoreRadius(b: PlottedBooth): number {
  const v = b.total_voters ?? 1000;
  return Math.max(6, Math.min(18, v / 170));
}

function FitBounds({ booths }: { booths: PlottedBooth[] }) {
  const map = useMap();
  useEffect(() => {
    if (booths.length === 0) return;
    const lats = booths.map((b) => b.synthLat);
    const lons = booths.map((b) => b.synthLon);
    map.fitBounds([
      [Math.min(...lats) - 0.008, Math.min(...lons) - 0.008],
      [Math.max(...lats) + 0.008, Math.max(...lons) + 0.008],
    ]);
  }, [booths, map]);
  return null;
}

export default function LeafletMap({ booths, layer, onSelect, selected }: Props) {
  const center: [number, number] = [26.7606, 83.3732];

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ height: "100%", width: "100%", background: "var(--bg-base)" }}>
      {BHARATMAPS_ACTIVE ? (
        <WMSTileLayer
          url={BHARATMAPS_WMS_URL!}
          layers={BHARATMAPS_WMS_LAYERS}
          format={BHARATMAPS_WMS_FORMAT}
          transparent={false}
          version="1.3.0"
          attribution='BharatMaps &copy; NIC, Govt. of India'
          {...(BHARATMAPS_TOKEN ? { token: BHARATMAPS_TOKEN } : {})}
        />
      ) : (
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
      )}
      <FitBounds booths={booths} />

      {booths.map((b) => {
        const { fill } = getHeatColor(b, layer);
        const r = getCoreRadius(b);
        const isSelected = selected?.booth_id === b.booth_id;
        const pos: [number, number] = [b.synthLat, b.synthLon];

        return (
          <span key={b.booth_id}>
            {/* Outer heat glow — largest, most transparent */}
            <CircleMarker
              center={pos}
              radius={r * 5.5}
              interactive={false}
              pathOptions={{
                fillColor: fill,
                color: "transparent",
                fillOpacity: 0.04,
              }}
            />
            {/* Middle heat ring */}
            <CircleMarker
              center={pos}
              radius={r * 3}
              interactive={false}
              pathOptions={{
                fillColor: fill,
                color: "transparent",
                fillOpacity: 0.09,
              }}
            />
            {/* Inner glow */}
            <CircleMarker
              center={pos}
              radius={r * 1.7}
              interactive={false}
              pathOptions={{
                fillColor: fill,
                color: "transparent",
                fillOpacity: 0.18,
              }}
            />
            {/* Core marker — clickable */}
            <CircleMarker
              center={pos}
              radius={r}
              pathOptions={{
                fillColor: fill,
                color: isSelected ? "#ffffff" : fill,
                weight: isSelected ? 2.5 : 0.8,
                opacity: isSelected ? 1 : 0.6,
                fillOpacity: isSelected ? 1 : 0.88,
              }}
              eventHandlers={{ click: () => onSelect(b) }}>
              <Popup>
                <div style={{ color: "var(--text-1)", fontSize: 12, minWidth: 165, padding: "2px 0" }}>
                  <p style={{ fontWeight: 700, marginBottom: 3, color: "#f97316" }}>
                    Booth {b.booth_number}
                  </p>
                  <p style={{ color: "var(--text-3)", marginBottom: 8, fontSize: 11 }}>{b.name}</p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {[
                      ["Voters",    b.total_voters?.toLocaleString("en-IN") ?? "—"],
                      ["In KG",     b.in_neo4j ? "Yes" : "No"],
                      ["BJP pulse", b.bjp_pulse_score?.toFixed(3) ?? "No data"],
                      ["Quality",   b.confidence_label ?? "No data"],
                    ].map(([k, v]) => (
                      <div key={String(k)} style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-3)" }}>{k}</span>
                        <span style={{ color: "var(--text-1)", fontWeight: 600 }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          </span>
        );
      })}
    </MapContainer>
  );
}
