"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { GeoRow } from "@/lib/api";
import "leaflet/dist/leaflet.css";

type Layer = "lean" | "issues" | "narrative_risk" | "scheme_gap" | "confidence" | "voters";

interface Props {
  geo: GeoRow[];
  layer: Layer;
  onSelect: (g: GeoRow) => void;
}

function getColor(g: GeoRow, layer: Layer): string {
  if (layer === "lean") {
    const label = g.digital_lean_label?.toUpperCase() ?? "";
    if (label.includes("STRONG_BJP")) return "#f97316";
    if (label.includes("LEAN_BJP")) return "#fb923c";
    if (label.includes("NEUTRAL")) return "#64748b";
    if (label.includes("LEAN_OPP")) return "#60a5fa";
    if (label.includes("STRONG_OPP")) return "#3b82f6";
    if (label.includes("INSUFFICIENT")) return "#374151";
    return "#374151";
  }

  if (layer === "confidence") {
    const label = g.confidence_label?.toUpperCase() ?? "";
    if (label === "HIGH") return "#10b981";
    if (label === "MEDIUM") return "#f59e0b";
    if (label === "LOW") return "#ef4444";
    return "#374151";
  }

  if (layer === "voters") {
    const v = g.total_voters ?? 0;
    if (v > 1200) return "#3b82f6";
    if (v > 800)  return "#60a5fa";
    if (v > 500)  return "#93c5fd";
    return "#1e3a5f";
  }

  // For issue/narrative/scheme — use bjp pulse as proxy for now (will be enriched)
  const score = layer === "narrative_risk" ? g.opp_pulse_score : g.bjp_pulse_score;
  if (score == null) return "#374151";
  if (score > 0.3) return "#ef4444";
  if (score > 0) return "#f59e0b";
  return "#10b981";
}

function getRadius(g: GeoRow): number {
  const v = g.total_voters ?? 500;
  return Math.max(5, Math.min(16, v / 150));
}

function FitBounds({ geo }: { geo: GeoRow[] }) {
  const map = useMap();
  useEffect(() => {
    if (geo.length === 0) return;
    const lats = geo.map((g) => g.lat);
    const lons = geo.map((g) => g.lon);
    map.fitBounds([
      [Math.min(...lats) - 0.005, Math.min(...lons) - 0.005],
      [Math.max(...lats) + 0.005, Math.max(...lons) + 0.005],
    ]);
  }, [geo, map]);
  return null;
}

export default function LeafletMap({ geo, layer, onSelect }: Props) {
  const center: [number, number] = geo.length > 0
    ? [geo[0].lat, geo[0].lon]
    : [26.7606, 83.3732]; // Gorakhpur

  return (
    <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%", background: "#0a0e1a" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds geo={geo} />
      {geo.map((g) => (
        <CircleMarker
          key={g.booth_id}
          center={[g.lat, g.lon]}
          radius={getRadius(g)}
          pathOptions={{
            fillColor: getColor(g, layer),
            color: "#ffffff",
            weight: 0.5,
            opacity: 0.8,
            fillOpacity: 0.75,
          }}
          eventHandlers={{ click: () => onSelect(g) }}>
          <Popup>
            <div style={{ color: "#f1f5f9", fontSize: 12, minWidth: 160 }}>
              <p style={{ fontWeight: 600, marginBottom: 4 }}>Booth {g.booth_number}</p>
              <p style={{ color: "#94a3b8", marginBottom: 6, fontSize: 11 }}>{g.name}</p>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ color: "#94a3b8" }}>Voters:</span>
                <span>{g.total_voters?.toLocaleString("en-IN") ?? "—"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ color: "#94a3b8" }}>Lean:</span>
                <span style={{ color: "#f97316" }}>{g.digital_lean_label ?? "—"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#94a3b8" }}>Issue:</span>
                <span style={{ textTransform: "capitalize" }}>{g.top_issue?.replace(/_/g, " ") ?? "—"}</span>
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
