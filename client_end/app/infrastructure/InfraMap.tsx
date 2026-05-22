"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { GraphCoverageBooth } from "@/lib/api";
import "leaflet/dist/leaflet.css";

export type InfraLayer = "graph_coverage" | "bjp_pulse" | "confidence";

interface LocatedBooth extends GraphCoverageBooth {
  lat: number;
  lon: number;
}

interface Props {
  booths: LocatedBooth[];
  layer: InfraLayer;
  onSelect: (b: GraphCoverageBooth) => void;
}

function getColor(b: LocatedBooth, layer: InfraLayer): string {
  if (layer === "graph_coverage") {
    return b.in_neo4j ? "#10b981" : "#1e3a5f";
  }
  if (layer === "bjp_pulse") {
    const s = b.bjp_pulse_score;
    if (s == null) return "#1e3a5f";
    if (s > 0.3) return "#f97316";
    if (s > 0.1) return "#fb923c";
    if (s > -0.1) return "#64748b";
    if (s > -0.3) return "#60a5fa";
    return "#3b82f6";
  }
  if (layer === "confidence") {
    const l = b.confidence_label?.toUpperCase() ?? "";
    if (l === "HIGH") return "#10b981";
    if (l === "MEDIUM") return "#f59e0b";
    if (l === "LOW") return "#ef4444";
    return "#1e3a5f";
  }
  return "#1e3a5f";
}

function getRadius(b: LocatedBooth): number {
  const v = b.total_voters ?? 500;
  return Math.max(5, Math.min(16, v / 150));
}

function FitBounds({ booths }: { booths: LocatedBooth[] }) {
  const map = useMap();
  useEffect(() => {
    if (booths.length === 0) return;
    const lats = booths.map((b) => b.lat);
    const lons = booths.map((b) => b.lon);
    map.fitBounds([
      [Math.min(...lats) - 0.005, Math.min(...lons) - 0.005],
      [Math.max(...lats) + 0.005, Math.max(...lons) + 0.005],
    ]);
  }, [booths, map]);
  return null;
}

export default function InfraMap({ booths, layer, onSelect }: Props) {
  const center: [number, number] = booths.length > 0
    ? [booths[0].lat, booths[0].lon]
    : [26.7606, 83.3732];

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ height: "100%", width: "100%", background: "#0a0e1a" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds booths={booths} />
      {booths.map((b) => (
        <CircleMarker
          key={b.booth_id}
          center={[b.lat, b.lon]}
          radius={getRadius(b)}
          pathOptions={{
            fillColor: getColor(b, layer),
            color: b.in_neo4j && layer === "graph_coverage" ? "#6ee7b7" : "#ffffff",
            weight: b.in_neo4j && layer === "graph_coverage" ? 1.5 : 0.5,
            opacity: 0.9,
            fillOpacity: b.in_neo4j ? 0.85 : 0.4,
          }}
          eventHandlers={{ click: () => onSelect(b) }}>
          <Popup>
            <div style={{ color: "#f1f5f9", fontSize: 12, minWidth: 170 }}>
              <p style={{ fontWeight: 600, marginBottom: 4 }}>Booth {b.booth_number}</p>
              <p style={{ color: "#94a3b8", marginBottom: 6, fontSize: 11 }}>{b.name}</p>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ color: "#94a3b8" }}>In KG:</span>
                <span style={{ color: b.in_neo4j ? "#10b981" : "#ef4444" }}>
                  {b.in_neo4j ? `Yes (deg ${b.neo4j_degree})` : "No"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ color: "#94a3b8" }}>Voters:</span>
                <span>{b.total_voters?.toLocaleString("en-IN") ?? "—"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ color: "#94a3b8" }}>BJP pulse:</span>
                <span style={{ color: "#f97316" }}>{b.bjp_pulse_score?.toFixed(3) ?? "—"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#94a3b8" }}>Confidence:</span>
                <span>{b.confidence_label ?? "—"}</span>
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
