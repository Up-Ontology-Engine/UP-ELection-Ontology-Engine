import { BarChart3 } from "lucide-react";

export function Logo({ size = "md" }: { size?: "sm" | "md" }) {
  const s = size === "sm" ? "h-8 w-8" : "h-10 w-10";
  const icon = size === "sm" ? 18 : 22;
  return (
    <div className="flex items-center gap-3">
      <div className={`${s} rounded-lg bg-[var(--saffron)] flex items-center justify-center text-white shadow-sm`}>
        <BarChart3 size={icon} strokeWidth={2.25} />
      </div>
      <div className="leading-tight">
        <div className="font-semibold text-foreground">Election Ontology Engine</div>
        <div className="text-[11px] text-[var(--saffron-dim)] font-mono">Booth-Level Intelligence</div>
      </div>
    </div>
  );
}
