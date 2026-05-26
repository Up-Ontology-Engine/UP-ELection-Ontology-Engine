const parties = [
  { label: "IND", value: 16, color: "oklch(0.55 0.05 260)" },
  { label: "SP", value: 5, color: "oklch(0.65 0.20 25)" },
  { label: "BJP", value: 3, color: "oklch(0.72 0.17 55)" },
  { label: "INC", value: 2, color: "oklch(0.65 0.12 195)" },
  { label: "SARVO", value: 1, color: "oklch(0.55 0.05 260)" },
];

export function Insights() {
  return (
    <section id="insights" className="border-t" style={{ borderTopColor: "rgba(220,207,187,0.65)" }}>
      <div className="mx-auto max-w-6xl px-6 py-20 grid lg:grid-cols-2 gap-6 items-stretch">
        <div className="rounded-3xl border border-(--border-bright) bg-(--bg-card) p-6 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-mono tracking-widest text-(--saffron)">CANDIDATES BY PARTY</div>
          <div className="mt-5 space-y-3">
            {parties.map((p) => (
              <div key={p.label} className="grid grid-cols-[60px_1fr_30px] items-center gap-3">
                <div className="text-sm font-mono text-foreground">{p.label}</div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(p.value / 16) * 100}%`, background: p.color }} />
                </div>
                <div className="text-sm font-mono text-muted-foreground text-right">{p.value}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-3xl border border-(--border-bright) bg-(--bg-card) p-6 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-mono tracking-widest text-(--saffron)">AGE DISTRIBUTION · 18–80+</div>
          <div className="mt-6 flex items-end gap-3 h-44">
            {[42, 78, 96, 60, 32, 14].map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full rounded-md bg-(--saffron)" style={{ height: `${h}%` }} />
                <div className="text-[10px] font-mono text-muted-foreground">{["18", "25", "35", "45", "60", "80"][i]}</div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex items-center gap-6 text-xs font-mono text-muted-foreground">
            <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-(--saffron)" /> Male 41,608</span>
            <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-accent" /> Female 38,620</span>
          </div>
        </div>
      </div>
    </section>
  );
}
