import Link from "next/link";
import { Logo } from "./Logo";
import { Button } from "@/components/ui/button";

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b" style={{ borderBottomColor: "rgba(220,207,187,0.65)", background: "color-mix(in srgb, var(--bg-base) 75%, transparent)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
      <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
        <Link href="/"><Logo size="sm" /></Link>
        <nav className="hidden md:flex items-center gap-8 text-sm text-[var(--text-3)]">
          <a href="#features" className="hover:text-[var(--saffron)] transition-colors">Features</a>
          <a href="#how" className="hover:text-[var(--saffron)] transition-colors">How it works</a>
          <a href="#insights" className="hover:text-[var(--saffron)] transition-colors">Insights</a>
          <Link href="/login" className="hover:text-[var(--saffron)] transition-colors">Login</Link>
        </nav>
        <Button asChild className="bg-[var(--saffron)] text-white hover:bg-[var(--saffron-dim)] shadow-none"><Link href="/signup">Sign up</Link></Button>
      </div>
    </header>
  );
}
