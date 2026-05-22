interface Props { label: string | null }

const MAP: Record<string, { color: string; dot: string }> = {
  HIGH:    { color: "#10b981", dot: "#10b981" },
  MEDIUM:  { color: "#f59e0b", dot: "#f59e0b" },
  LOW:     { color: "#ef4444", dot: "#ef4444" },
  UNKNOWN: { color: "#4d6480", dot: "#4d6480" },
};

export default function ConfidenceBadge({ label }: Props) {
  const key = label?.toUpperCase() ?? "UNKNOWN";
  const c = MAP[key] ?? MAP["UNKNOWN"];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded mono text-xs"
      style={{ background: `${c.color}18`, color: c.color, fontSize: 10 }}>
      <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: c.dot }} />
      {label ?? "UNKNOWN"}
    </span>
  );
}
