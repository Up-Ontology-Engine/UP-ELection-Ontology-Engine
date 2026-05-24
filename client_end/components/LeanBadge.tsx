interface Props { label: string | null; compact?: boolean }

const MAP: Record<string, { bg: string; text: string; short: string; display: string }> = {
  "STRONG_BJP":   { bg: "rgba(249,115,22,0.18)", text: "#f97316", short: "S.BJP",  display: "Strong BJP"  },
  "LEAN_BJP":     { bg: "rgba(249,115,22,0.1)",  text: "#fb923c", short: "L.BJP",  display: "Lean BJP"    },
  "NEUTRAL":      { bg: "rgba(100,116,139,0.18)", text: "#94a3b8", short: "NEUT",  display: "Neutral"     },
  "LEAN_OPP":     { bg: "rgba(59,130,246,0.1)",  text: "#60a5fa", short: "L.SP",   display: "Lean SP"     },
  "STRONG_OPP":   { bg: "rgba(59,130,246,0.18)", text: "#3b82f6", short: "S.SP",   display: "Strong SP"   },
  "INSUFFICIENT": { bg: "rgba(45,62,80,0.5)",    text: "#4d6480", short: "INSUF",  display: "Insufficient"},
};

export default function LeanBadge({ label, compact }: Props) {
  const key = label?.toUpperCase() ?? "INSUFFICIENT";
  const c = MAP[key] ?? MAP["INSUFFICIENT"];
  return (
    <span className="px-2 py-0.5 rounded mono text-xs font-semibold"
      style={{ background: c.bg, color: c.text, fontSize: 10, letterSpacing: "0.05em" }}>
      {compact ? c.short : c.display}
    </span>
  );
}
