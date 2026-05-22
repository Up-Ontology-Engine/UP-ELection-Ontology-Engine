interface Props {
  bjp: number | null;
  opp: number | null;
  size?: "sm" | "md";
}

export default function PulseBar({ bjp, opp, size = "sm" }: Props) {
  const h = size === "sm" ? "h-1.5" : "h-2.5";
  const bjpPct = bjp != null ? Math.round(((bjp + 1) / 2) * 100) : 50;
  const oppPct = opp != null ? Math.round(((opp + 1) / 2) * 100) : 50;

  return (
    <div className="flex flex-col gap-1 w-full">
      <div className="flex items-center gap-2">
        <span className="text-xs w-8" style={{ color: "#f97316" }}>BJP</span>
        <div className={`flex-1 rounded-full ${h}`} style={{ background: "#1e2d45" }}>
          <div className={`${h} rounded-full transition-all`}
            style={{ width: `${bjpPct}%`, background: "#f97316" }} />
        </div>
        <span className="text-xs w-8 text-right" style={{ color: "#94a3b8" }}>{bjpPct}%</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs w-8" style={{ color: "#3b82f6" }}>OPP</span>
        <div className={`flex-1 rounded-full ${h}`} style={{ background: "#1e2d45" }}>
          <div className={`${h} rounded-full transition-all`}
            style={{ width: `${oppPct}%`, background: "#3b82f6" }} />
        </div>
        <span className="text-xs w-8 text-right" style={{ color: "#94a3b8" }}>{oppPct}%</span>
      </div>
    </div>
  );
}
