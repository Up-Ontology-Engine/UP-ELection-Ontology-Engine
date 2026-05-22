"use client";

import { AlertTriangle, X, ChevronRight } from "lucide-react";
import { useState } from "react";

interface Alert {
  level: "critical" | "warning" | "info";
  message: string;
  booth?: string;
}

const LEVEL_COLORS = {
  critical: { bg: "rgba(239,68,68,0.08)", border: "#ef444430", text: "#ef4444", icon: "#ef4444" },
  warning:  { bg: "rgba(245,158,11,0.08)", border: "#f59e0b30", text: "#f59e0b", icon: "#f59e0b" },
  info:     { bg: "rgba(59,130,246,0.08)",  border: "#3b82f630", text: "#3b82f6", icon: "#3b82f6" },
};

interface Props { alerts: Alert[] }

export default function AlertStrip({ alerts }: Props) {
  const [dismissed, setDismissed] = useState<number[]>([]);
  const visible = alerts.filter((_, i) => !dismissed.includes(i));
  if (visible.length === 0) return null;

  return (
    <div className="space-y-1 mb-4">
      {visible.map((a, i) => {
        const c = LEVEL_COLORS[a.level];
        const realIdx = alerts.indexOf(a);
        return (
          <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-md text-xs"
            style={{ background: c.bg, border: `1px solid ${c.border}` }}>
            <AlertTriangle size={12} style={{ color: c.icon, flexShrink: 0 }} />
            <span className="font-semibold mono" style={{ color: c.text }}>{a.level.toUpperCase()}</span>
            <span style={{ color: "#8ba0bc" }} className="flex-1">{a.message}</span>
            {a.booth && (
              <a href={`/booths/${a.booth}`} className="flex items-center gap-1 hover:underline"
                style={{ color: c.text }}>
                View <ChevronRight size={10} />
              </a>
            )}
            <button onClick={() => setDismissed((d) => [...d, realIdx])}
              className="p-0.5 rounded hover:bg-white/10 transition-colors">
              <X size={10} style={{ color: "#4d6480" }} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
