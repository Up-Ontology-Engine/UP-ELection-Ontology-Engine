import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t" style={{ borderTopColor: "rgba(220,207,187,0.65)" }}>
      <div className="mx-auto max-w-6xl px-6 py-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <Logo size="sm" />
        <div className="text-xs font-mono text-muted-foreground">© 2026 Election Ontology Engine</div>
        <div className="flex gap-6 text-sm text-muted-foreground">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Terms</a>
          <a href="#" className="hover:text-foreground">Contact</a>
        </div>
      </div>
    </footer>
  );
}
