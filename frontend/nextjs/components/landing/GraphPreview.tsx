export function GraphPreview() {
  return (
    <div className="relative">
      <div className="rounded-3xl border border-border bg-card shadow-[0_10px_40px_-15px_rgba(0,0,0,0.12)] overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-4 h-10 bg-[rgb(23,45,82)] text-white">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
          </div>
          <div className="text-[11px] font-mono text-white/75">command-center · gorakhpur urban</div>
          <div className="text-[11px] font-mono text-white/75">16:18</div>
        </div>
        <div className="p-5 grid grid-cols-3 gap-3">
          <Tile label="Candidates" value="44" tone="primary" />
          <Tile label="Parties" value="23" tone="accent" />
          <Tile label="Flagged" value="7" tone="warn" />
        </div>
        <div className="px-5 pb-5">
          <svg viewBox="0 0 400 220" className="w-full h-auto">
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="oklch(0.94 0.006 80)" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="400" height="220" fill="url(#grid)" />
            {edges.map((e, i) => (
              <line key={i} x1={nodes[e[0]].x} y1={nodes[e[0]].y} x2={nodes[e[1]].x} y2={nodes[e[1]].y}
                stroke="oklch(0.85 0.02 80)" strokeWidth="1" />
            ))}
            {nodes.map((n, i) => (
              <circle key={i} cx={n.x} cy={n.y} r={n.r}
                fill={n.t === "p" ? "oklch(0.85 0.10 295 / 0.35)" : "oklch(0.85 0.08 165 / 0.35)"}
                stroke={n.t === "p" ? "oklch(0.65 0.12 295)" : "oklch(0.55 0.10 165)"} strokeWidth="1" />
            ))}
          </svg>
        </div>
      </div>
      <div className="absolute -bottom-4 -right-4 hidden md:block">
        <div className="rounded-2xl border border-border bg-card px-3 py-2 text-[11px] font-mono shadow-sm">
          <span className="text-muted-foreground">node:</span>{" "}
          <span className="text-foreground">BJP → Kajal Nishad</span>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value, tone }: { label: string; value: string; tone: "primary" | "accent" | "warn" }) {
  const dot = tone === "primary" ? "bg-primary" : tone === "accent" ? "bg-accent" : "bg-destructive";
  return (
    <div className="rounded-2xl border border-border bg-background/60 p-3">
      <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground tracking-wider">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} /> {label.toUpperCase()}
      </div>
      <div className="mt-1.5 text-2xl font-semibold text-foreground">{value}</div>
    </div>
  );
}

const nodes = [
  { x: 200, y: 110, r: 18, t: "p" as const },
  { x: 110, y: 60, r: 12, t: "c" as const },
  { x: 90, y: 140, r: 12, t: "c" as const },
  { x: 160, y: 180, r: 11, t: "c" as const },
  { x: 290, y: 70, r: 14, t: "p" as const },
  { x: 310, y: 150, r: 12, t: "c" as const },
  { x: 250, y: 180, r: 11, t: "c" as const },
  { x: 350, y: 110, r: 11, t: "c" as const },
  { x: 60, y: 95, r: 10, t: "c" as const },
];

const edges: [number, number][] = [
  [0, 1], [0, 2], [0, 3], [0, 4],
  [4, 5], [4, 7], [0, 5], [0, 6],
  [1, 8], [2, 8], [3, 6],
];
