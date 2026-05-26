import { Network, Map, FileText, Users } from "lucide-react";

const items = [
  { icon: Map, title: "Booth Intelligence", body: "Form 20 ingestion with polling-station turnout, age and gender breakdowns.", tone: "primary" },
  { icon: Network, title: "Knowledge Graph", body: "Parties, candidates, constituencies linked into a queryable ontology.", tone: "accent" },
  { icon: FileText, title: "MyNeta Report Card", body: "Affidavit-backed profiles: assets, liabilities, criminal records, profession.", tone: "mint" },
  { icon: Users, title: "Demographic Heatmaps", body: "Spot trends across age cohorts, gender splits, and constituency segments.", tone: "primary" },
];

const toneBg: Record<string, string> = {
  primary: "bg-(--saffron-subtle) text-(--saffron)",
  accent: "bg-[rgba(251,146,60,0.14)] text-(--saffron-dim)",
  mint: "bg-[oklch(0.72_0.10_165_/_0.18)] text-[oklch(0.42_0.08_165)]",
};

export function Features() {
  return (
    <section id="features" className="border-t" style={{ borderTopColor: "rgba(220,207,187,0.65)" }}>
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-2xl">
          <div className="text-xs font-mono tracking-widest text-(--saffron)">FEATURES</div>
          <h2 className="mt-2 text-3xl md:text-4xl font-semibold text-foreground">Everything you need to read an electorate.</h2>
        </div>
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((it) => (
            <div key={it.title} className="rounded-3xl border border-[color:var(--border-bright)] bg-(--bg-card) p-5 shadow-sm hover:shadow-md transition-all duration-200">
              <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${toneBg[it.tone]}`}>
                <it.icon size={20} />
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{it.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{it.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
