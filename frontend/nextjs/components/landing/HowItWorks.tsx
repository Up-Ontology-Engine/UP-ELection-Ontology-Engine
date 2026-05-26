const steps = [
  { n: "01", title: "Ingest", body: "Pull Form 20 booth data, MyNeta affidavits, and constituency boundaries into one place." },
  { n: "02", title: "Map ontology", body: "Entities resolve into a knowledge graph — candidates, parties, booths, demographics, claims." },
  { n: "03", title: "Explore trends", body: "Query, visualize and compare. From a single booth to an entire state." },
];

export function HowItWorks() {
  return (
    <section id="how" className="border-t" style={{ borderTopColor: "rgba(220,207,187,0.65)" }}>
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-2xl">
          <div className="text-xs font-mono tracking-widest text-[var(--saffron)]">HOW IT WORKS</div>
          <h2 className="mt-2 text-3xl md:text-4xl font-semibold text-foreground">From raw PDFs to structured insight.</h2>
        </div>
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          {steps.map((s) => (
            <div key={s.n} className="rounded-3xl border border-[color:var(--border-bright)] bg-[var(--bg-card)] p-6 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="text-xs font-mono text-[var(--saffron)]">{s.n}</div>
              <div className="mt-3 text-lg font-semibold text-foreground">{s.title}</div>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
