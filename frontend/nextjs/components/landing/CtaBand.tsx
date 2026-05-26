import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function CtaBand() {
  return (
    <section className="border-t" style={{ borderTopColor: "rgba(220,207,187,0.65)" }}>
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="rounded-[28px] bg-[rgb(23,45,82)] text-white px-10 py-14 flex flex-col md:flex-row md:items-center md:justify-between gap-6 shadow-[0_18px_50px_-25px_rgba(23,45,82,0.65)]">
          <div>
            <div className="text-xs font-mono tracking-widest text-white/70">BUILDING A MODEL?</div>
            <h2 className="mt-2 text-3xl font-semibold">Bring your district data into focus.</h2>
            <p className="mt-3 max-w-2xl text-white/80 leading-relaxed">Pull together booth trends, affidavit summaries, and constituency signals before the next campaign sprint.</p>
          </div>
          <Button asChild size="lg" className="gap-2 bg-[var(--saffron)] text-white hover:bg-[var(--saffron-dim)]">
            <Link href="/signup"><ArrowRight size={16} /> Start exploring</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
