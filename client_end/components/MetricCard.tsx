import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  delta?: number;
  deltaLabel?: string;
  accent?: string;
  icon?: React.ReactNode;
  mono?: boolean;
  size?: "sm" | "md" | "lg";
  alert?: boolean;
}

export default function MetricCard({ label, value, sub, delta, deltaLabel, accent = "#f97316", icon, mono, size = "md", alert }: Props) {
  const valSize = size === "lg" ? "text-3xl" : size === "sm" ? "text-xl" : "text-2xl";
  return (
    <div className="card p-4 flex flex-col gap-1.5 relative overflow-hidden transition-all hover:border-[var(--border-bright)]"
      style={alert ? { borderColor: "#ef444433", boxShadow: "inset 0 0 20px rgba(239,68,68,0.05)" } : {}}>
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px" style={{ background: `linear-gradient(90deg, ${accent}44, transparent)` }} />

      <div className="flex items-center justify-between">
        <span className="label" style={{ color: "var(--text-3)" }}>{label}</span>
        {icon && <span style={{ color: accent }}>{icon}</span>}
      </div>

      <div className={`${valSize} font-bold leading-none ${mono ? "mono" : ""}`} style={{ color: accent }}>
        {value}
      </div>

      <div className="flex items-center gap-2">
        {delta != null && (
          <span className="flex items-center gap-0.5 text-xs" style={{
            color: delta > 0 ? "#10b981" : delta < 0 ? "#ef4444" : "#64748b"
          }}>
            {delta > 0 ? <TrendingUp size={10} /> : delta < 0 ? <TrendingDown size={10} /> : <Minus size={10} />}
            {delta > 0 ? "+" : ""}{delta.toFixed(1)}%
          </span>
        )}
        {sub && <span className="text-xs" style={{ color: "var(--text-3)" }}>{sub}</span>}
        {deltaLabel && <span className="text-xs" style={{ color: "var(--text-4)" }}>{deltaLabel}</span>}
      </div>
    </div>
  );
}
