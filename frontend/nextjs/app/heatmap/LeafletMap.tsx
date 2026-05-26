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

// Gorakhpur Urban AC-322 center (city, not full district)
const GORAKHPUR_URBAN_CENTER: [number, number] = [26.755, 83.375];

const MAX_VOTERS = 3000;

function hsl(h: number, s: number, l: number) {
  return `hsl(${h},${s}%,${l}%)`;
}

function getHeatColor(b: PlottedBooth, layer: Props["layer"]): string {
  if (layer === "voters") {
    const ratio = Math.min((b.total_voters ?? 0) / MAX_VOTERS, 1);
    // Blue → Orange → Red (cool to hot)
    const h = 220 - ratio * 200;
    const s = 70 + ratio * 25;
    const l = 45 + ratio * 10;
    return hsl(h, s, l);
  }

  if (layer === "kg_coverage") {
    return b.in_neo4j ? "#10b981" : "#475569";
  }

  if (layer === "bjp_lean") {
    const lbl = b.digital_lean_label?.toUpperCase() ?? "";
    if (lbl === "STRONG_BJP") return "#f97316";
    if (lbl === "LEAN_BJP")   return "#fb923c";
    if (lbl === "NEUTRAL")    return "#64748b";
    if (lbl === "LEAN_OPP")   return "#60a5fa";
    if (lbl === "STRONG_OPP") return "#3b82f6";
    // fallback to pulse score
    const s = b.bjp_pulse_score;
    if (s == null) return "#475569";
    if (s > 0.3) return "#f97316";
    if (s > 0.1) return "#fb923c";
    if (s > -0.1) return "#64748b";
    if (s > -0.3) return "#60a5fa";
    return "#3b82f6";
  }

  if (layer === "confidence") {
    const l = b.confidence_label?.toUpperCase() ?? "";
    if (l === "HIGH")   return "#10b981";
    if (l === "MEDIUM") return "#f59e0b";
    if (l === "LOW")    return "#ef4444";
    return "#475569";
  }

  return "#475569";
}

function getCoreRadius(b: PlottedBooth): number {
  const v = b.total_voters ?? 800;
  return Math.max(7, Math.min(20, v / 140));
}

export default function LeafletMap({ booths, layer, onSelect, selected }: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef          = useRef<L.Map | null>(null);
  const markersRef      = useRef<L.Layer[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialise map once
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
      }).setView(GORAKHPUR_URBAN_CENTER, 13);

      // CartoDB Positron — clean light base
      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        {
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
          subdomains: "abcd",
          maxZoom: 19,
        }
      ).addTo(mapRef.current);


    }

    // Remove old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    booths.forEach((b) => {
      if (!b.lat || !b.lon || !mapRef.current) return;

      const fill       = getHeatColor(b, layer);
      const r          = getCoreRadius(b);
      const isSelected = selected?.booth_id === b.booth_id;
      const pos: L.LatLngExpression = [b.lat, b.lon];

      // Glow rings (non-interactive)
      const glow1 = L.circleMarker(pos, {
        radius: r * 5,
        color: "transparent",
        fillColor: fill,
        fillOpacity: 0.05,
        interactive: false,
      }).addTo(mapRef.current);

      const glow2 = L.circleMarker(pos, {
        radius: r * 2.8,
        color: "transparent",
        fillColor: fill,
        fillOpacity: 0.1,
        interactive: false,
      }).addTo(mapRef.current);

      // Core marker — no popup, panel handles display
      const core = L.circleMarker(pos, {
        radius: r,
        color: isSelected ? "#ffffff" : fill,
        fillColor: fill,
        fillOpacity: isSelected ? 1 : 0.82,
        weight: isSelected ? 3 : 1,
        opacity: isSelected ? 1 : 0.7,
        bubblingMouseEvents: false,
      })
        .on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          onSelect(b);
        })
        .on("mouseover", (e) => {
          const marker = e.target as L.CircleMarker;
          if (!isSelected) {
            marker.setStyle({ fillOpacity: 1, weight: 2, opacity: 1 });
          }
          marker.bindTooltip(
            `<strong style="color:#f97316">B-${String(b.booth_number).padStart(3, "0")}</strong>
             <br/><span style="color:#94a3b8;font-size:11px">${b.name ?? ""}</span>
             <br/><span style="font-size:11px">${(b.total_voters ?? 0).toLocaleString("en-IN")} voters</span>`,
            { permanent: false, direction: "top", className: "booth-tooltip" }
          ).openTooltip();
        })
        .on("mouseout", (e) => {
          const marker = e.target as L.CircleMarker;
          if (!isSelected) {
            marker.setStyle({ fillOpacity: 0.82, weight: 1, opacity: 0.7 });
          }
          marker.unbindTooltip();
        })
        .addTo(mapRef.current);

      markersRef.current.push(glow1, glow2, core);
    });

    // Fit to booth bounds
    const validBooths = booths.filter((b) => b.lat && b.lon);
    if (validBooths.length > 0) {
      const bounds = L.latLngBounds(
        validBooths.map((b) => [b.lat, b.lon] as L.LatLngTuple)
      );
      mapRef.current.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
  }, [booths, layer, selected, onSelect]);

  return (
    <>
      <style>{`
        .booth-tooltip {
          background: #0f1c2e;
          border: 1px solid #1e3a5f;
          border-radius: 6px;
          color: #e2e8f0;
          font-family: monospace;
          font-size: 12px;
          padding: 6px 10px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
          white-space: nowrap;
        }
        .booth-tooltip::before { display: none; }
        .leaflet-tooltip-top.booth-tooltip::before { display: none; }
      `}</style>
      <div
        ref={mapContainerRef}
        style={{ height: "100%", width: "100%", background: "#0f1c2e" }}
      />
    </>
  );
}
