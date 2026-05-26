import Link from "next/link";
import { ArrowRight, PlayCircle } from "lucide-react";
import { GraphPreview } from "@/components/landing/GraphPreview";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-6xl px-6 pt-20 pb-24 grid lg:grid-cols-[1.05fr_1fr] gap-14 items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-(--border-bright) bg-(--saffron-subtle) px-3 py-1 text-xs font-mono text-(--saffron-dim)">
            <span className="h-1.5 w-1.5 rounded-full bg-(--saffron)" /> Gorakhpur Pilot
          </div>
          <h1 className="mt-6 text-5xl md:text-6xl font-semibold tracking-tight text-foreground leading-[1.05]">
            Turn election data <br />
            into <span className="text-(--saffron)">understanding.</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-xl leading-relaxed">
            Booth-level intelligence, candidate knowledge graphs, and demographic
            trends — all in one ontology engine built for serious electoral
            analysis.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg" className="gap-2 bg-(--saffron) text-white hover:bg-(--saffron-dim) shadow-none"><Link href="/signup"><ArrowRight size={16} /> Get started</Link></Button>
            <Button asChild size="lg" variant="outline" className="gap-2 border-(--border-bright) bg-white text-(--saffron-dim) hover:bg-(--saffron-subtle) shadow-none">
              <Link href="/dashboard">
                <PlayCircle size={18} /> See live demo
              </Link>
            </Button>
          </div>
          <div className="mt-10 flex items-center gap-10 text-xs font-mono text-(--text-3)">
            <Stat label="CONSTITUENCIES" value="3" />
            <Stat label="CANDIDATES" value="44" />
            <Stat label="PARTIES" value="23" />
          </div>
        </div>
        <GraphPreview />
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-2xl font-semibold text-foreground">{value}</div>
      <div className="text-[10px] tracking-widest mt-1 text-(--saffron-dim)">{label}</div>
    </div>
  );
}
