"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Network, BarChart3, Brain,
  MessageSquare, BookOpen, Users, Activity,
  ChevronDown, GitBranch, Database, Shield, Radio, Zap, Flame
} from "lucide-react";

const SECTIONS = [
  {
    label: "Operations",
    items: [
      { href: "/",       icon: LayoutDashboard, label: "Command Center",     badge: null,  dot: "green" },
      { href: "/booths", icon: Activity,        label: "Booth Intelligence", badge: "30",  dot: "green" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/heatmap",   icon: Flame,         label: "Constituency Heatmap", badge: null, dot: "amber" },
      { href: "/graph",     icon: Network,       label: "Knowledge Graph",      badge: null, dot: "blue"  },
      { href: "/reasoning", icon: MessageSquare, label: "AI Reasoning",         badge: null, dot: "pink"  },
    ],
  },
  {
    label: "Analytics",
    items: [
      { href: "/demographics", icon: Users,    label: "Demographics",   badge: null, dot: "cyan"  },
      { href: "/ontology",     icon: BookOpen, label: "Ontology Layer", badge: "v1", dot: "slate" },
    ],
  },
];

const DOT_COLORS: Record<string, string> = {
  green:  "var(--green)",
  amber:  "var(--amber)",
  blue:   "var(--blue)",
  purple: "var(--purple)",
  pink:   "var(--pink)",
  cyan:   "var(--cyan)",
  slate:  "#64748b",
  orange: "var(--saffron)",
};

const PIPELINE = [
  { label: "PostgreSQL", status: "LIVE", icon: Database, color: "var(--green)", pulse: true  },
  { label: "Neo4j Graph", status: "LIVE", icon: GitBranch, color: "var(--green)", pulse: true  },
  { label: "ETL Pipeline", status: "IDLE", icon: Radio, color: "var(--amber)", pulse: false },
];

export default function Sidebar() {
  const path = usePathname();

  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <aside className="fixed top-0 left-0 h-full w-56 flex flex-col z-50 select-none"
      style={{ background: "var(--bg-base)", borderRight: "1px solid var(--border)" }}>

      {/* Top accent line */}
      <div className="h-0.5 w-full flex-shrink-0"
        style={{ background: "var(--sidebar-top-line)" }} />

      {/* Logo / Brand */}
      <div className="px-4 pt-4 pb-3.5" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2.5 mb-3.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #f97316 0%, #dc2626 100%)", boxShadow: "0 2px 8px rgba(249,115,22,0.3)" }}>
            <BarChart3 size={15} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-xs leading-none tracking-widest" style={{ color: "var(--text-1)" }}>UP-EOM</p>
            <p className="text-xs leading-none mt-1" style={{ color: "var(--text-3)", fontSize: 10 }}>Election Ontology Engine</p>
          </div>
        </div>

        {/* AC Selector */}
        <button className="w-full flex items-center justify-between px-2.5 py-2 rounded-md text-xs transition-all"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--saffron-dim)")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
          <div className="flex items-center gap-2">
            <Shield size={10} style={{ color: "var(--saffron)" }} />
            <span className="font-semibold" style={{ color: "var(--saffron)", fontSize: 11 }}>Gorakhpur Urban</span>
          </div>
          <ChevronDown size={10} style={{ color: "var(--text-4)" }} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {SECTIONS.map((section, si) => (
          <div key={section.label} className={si > 0 ? "mt-1" : ""}>
            {/* Section header */}
            <div className="flex items-center gap-2 px-4 pt-3 pb-1.5">
              <span className="label" style={{ color: "var(--text-4)", fontSize: 9, letterSpacing: "0.12em" }}>
                {section.label}
              </span>
              <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            </div>

            {section.items.map(({ href, icon: Icon, label, badge, dot }) => {
              const active = isActive(href);
              return (
                <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
                  {/* Status dot */}
                  <span
                    className={active ? "animate-pulse-dot" : ""}
                    style={{
                      display: "inline-block",
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background: DOT_COLORS[dot] ?? "#64748b",
                      opacity: active ? 1 : 0.4,
                      flexShrink: 0,
                    }} />
                  <Icon size={13} style={{ flexShrink: 0, opacity: active ? 1 : 0.7 }} />
                  <span className="flex-1 leading-none" style={{ fontSize: 12 }}>{label}</span>
                  {badge && (
                    <span className="mono px-1.5 py-0.5 rounded"
                      style={{
                        background: active ? "rgba(249,115,22,0.2)" : "var(--bg-surface)",
                        color: active ? "var(--saffron)" : "var(--text-4)",
                        fontSize: 9,
                        fontWeight: 600,
                        letterSpacing: "0.04em",
                        border: `1px solid ${active ? "rgba(249,115,22,0.3)" : "var(--border)"}`,
                      }}>
                      {badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Pipeline status */}
      <div className="px-3.5 py-3" style={{ borderTop: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 mb-2.5">
          <Zap size={9} style={{ color: "var(--text-4)" }} />
          <p className="label" style={{ color: "var(--text-4)", fontSize: 9 }}>Pipeline Status</p>
        </div>
        <div className="space-y-1.5">
          {PIPELINE.map(({ label, status, icon: Icon, color, pulse }) => (
            <div key={label} className="flex items-center gap-2 px-2.5 py-1.5 rounded-md"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
              <Icon size={10} style={{ color, flexShrink: 0 }} />
              <span className="flex-1 text-xs" style={{ color: "var(--text-3)", fontSize: 11 }}>{label}</span>
              <div className="flex items-center gap-1">
                <span className={pulse ? "animate-pulse-dot" : ""}
                  style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: color }} />
                <span className="mono" style={{ color, fontSize: 9, fontWeight: 700, letterSpacing: "0.05em" }}>{status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Version */}
      <div className="px-4 py-2.5 flex items-center justify-between"
        style={{ borderTop: "1px solid var(--border)" }}>
        <div className="flex items-center gap-1.5">
          <Brain size={9} style={{ color: "var(--text-4)" }} />
          <span className="mono" style={{ color: "var(--text-4)", fontSize: 10 }}>v1.0.0-ontology</span>
        </div>
        <span className="mono px-1.5 py-0.5 rounded"
          style={{ background: "var(--bg-surface)", color: "var(--text-4)", fontSize: 9, border: "1px solid var(--border)" }}>
          PHASE 0
        </span>
      </div>
    </aside>
  );
}
