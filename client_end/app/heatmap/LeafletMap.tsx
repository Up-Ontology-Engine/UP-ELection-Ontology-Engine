"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GraphCoverageBooth } from "@/lib/api";

export interface PlottedBooth extends GraphCoverageBooth {
  lat: number;
  lon: number;
}

interface Props {
  booths: PlottedBooth[];
  layer: "voters" | "kg_coverage" | "bjp_lean" | "confidence";
  onSelect: (b: PlottedBooth) => void;
  selected: PlottedBooth | null;
}

// Gorakhpur district bounds from stategisportal.nic.in WMS
const GORAKHPUR_BOUNDS = {
  north: 27.116212,
  south: 26.218752,
  east: 83.671043,
  west: 83.067767,
};

const GORAKHPUR_CENTER: [number, number] = [26.6675, 83.3694];

const MAX_VOTERS = 3000;

function hsl(h: number, s: number, l: number) {
  return `hsl(${h},${s}%,${l}%)`;
}

function getHeatColor(b: PlottedBooth, layer: Props["layer"]): string {
  if (layer === "voters") {
    const ratio = Math.min((b.total_voters ?? 0) / MAX_VOTERS, 1);
    const h = 220 - ratio * 200;
    const s = 70 + ratio * 25;
    const l = 45 + ratio * 10;
    return hsl(h, s, l);
  }

  if (layer === "kg_coverage") {
    return b.in_neo4j ? "#10b981" : "#94a3b8";
  }

  if (layer === "bjp_lean") {
    const s = b.bjp_pulse_score;
    if (s == null) return "#94a3b8";
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
    return "#94a3b8";
  }

  return "#94a3b8";
}

function getCoreRadius(b: PlottedBooth): number {
  const v = b.total_voters ?? 1000;
  return Math.max(6, Math.min(18, v / 170));
}

export default function LeafletMap({ booths, layer, onSelect, selected }: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.CircleMarker[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize map
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current).setView(GORAKHPUR_CENTER, 11);

      // BharatMaps WMS layer (if configured)
      const wmsUrl = process.env.NEXT_PUBLIC_BHARATMAPS_WMS_URL;
      const wmsLayers = process.env.NEXT_PUBLIC_BHARATMAPS_WMS_LAYERS;
      const wmsToken = process.env.NEXT_PUBLIC_BHARATMAPS_TOKEN;

      if (wmsUrl && wmsLayers) {
        L.tileLayer.wms(wmsUrl, {
          layers: wmsLayers,
          format: "image/png",
          transparent: true,
          version: "1.3.0",
          attribution: "BharatMaps © NIC, Govt. of India",
          ...(wmsToken ? { token: wmsToken } : {}),
        }).addTo(mapRef.current);
      } else {
        // Fallback to OpenStreetMap
        L.tileLayer(
          "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
          {
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          }
        ).addTo(mapRef.current);
      }
    }

    // Clear previous markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Add booth markers
    booths.forEach((b) => {
      if (!b.lat || !b.lon || !mapRef.current) return;

      const fill = getHeatColor(b, layer);
      const r = getCoreRadius(b);
      const isSelected = selected?.booth_id === b.booth_id;
      const pos: L.LatLngExpression = [b.lat, b.lon];

      // Outer glow
      const glow1 = L.circleMarker(pos, {
        radius: r * 5.5,
        color: "transparent",
        fillColor: fill,
        fillOpacity: 0.04,
        interactive: false,
      }).addTo(mapRef.current);
      markersRef.current.push(glow1);

      // Middle ring
      const glow2 = L.circleMarker(pos, {
        radius: r * 3,
        color: "transparent",
        fillColor: fill,
        fillOpacity: 0.09,
        interactive: false,
      }).addTo(mapRef.current);
      markersRef.current.push(glow2);

      // Inner glow
      const glow3 = L.circleMarker(pos, {
        radius: r * 1.7,
        color: "transparent",
        fillColor: fill,
        fillOpacity: 0.18,
        interactive: false,
      }).addTo(mapRef.current);
      markersRef.current.push(glow3);

      // Core marker
      const core = L.circleMarker(pos, {
        radius: r,
        color: isSelected ? "#ffffff" : fill,
        fillColor: fill,
        fillOpacity: isSelected ? 1 : 0.88,
        weight: isSelected ? 2.5 : 0.8,
        opacity: isSelected ? 1 : 0.6,
      })
        .bindPopup(
          `
          <div style="color: var(--text-1); font-size: 12px; min-width: 165px; padding: 2px 0;">
            <p style="font-weight: 700; margin-bottom: 3px; color: #f97316;">Booth ${b.booth_number}</p>
            <p style="color: var(--text-3); margin-bottom: 8px; font-size: 11px;">${b.name}</p>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-3);">Voters</span>
                <span style="color: var(--text-1); font-weight: 600;">${(b.total_voters ?? 0).toLocaleString("en-IN")}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-3);">In KG</span>
                <span style="color: var(--text-1); font-weight: 600;">${b.in_neo4j ? "Yes" : "No"}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-3);">BJP pulse</span>
                <span style="color: var(--text-1); font-weight: 600;">${(b.bjp_pulse_score?.toFixed(3) ?? "No data")}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-3);">Quality</span>
                <span style="color: var(--text-1); font-weight: 600;">${b.confidence_label ?? "No data"}</span>
              </div>
            </div>
          </div>
        `
        )
        .on("click", () => onSelect(b))
        .addTo(mapRef.current);
      markersRef.current.push(core);
    });

    // Fit bounds to booths
    if (booths.length > 0) {
      const bounds = L.latLngBounds(
        booths
          .filter((b) => b.lat && b.lon)
          .map((b) => [b.lat, b.lon] as L.LatLngTuple)
      );
      mapRef.current.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [booths, layer, selected, onSelect]);

  return (
    <div
      ref={mapContainerRef}
      style={{
        height: "100%",
        width: "100%",
        background: "var(--bg-base)",
      }}
    />
  );
}
