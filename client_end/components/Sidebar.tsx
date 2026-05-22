"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Network, BarChart3,
  MessageSquare, BookOpen, Users, Activity,
  ChevronDown, GitBranch, Database, Shield, Radio, Zap, Flame, Target
} from "lucide-react";

const SECTIONS = [
  {
    label: "Operations",
    items: [
      { href: "/",           icon: LayoutDashboard, label: "Command Center",     badge: null,  dot: "green"  },
      { href: "/booths",     icon: Activity,        label: "Booth Intelligence", badge: "30",  dot: "green"  },
      { href: "/conversion", icon: Target,          label: "Voter Conversion",   badge: "NEW", dot: "orange" },
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
  { label: "Relational Store", status: "LIVE",   icon: Database,  color: "var(--green)", pulse: true },
  { label: "Knowledge Graph",  status: "LIVE",   icon: GitBranch, color: "var(--green)", pulse: true },
  { label: "Signal Ingestion", status: "SYNCED", icon: Radio,     color: "var(--green)", pulse: true },
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
        <div className="flex items-center gap-3 mb-3.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #fb923c 0%, #f97316 45%, #dc2626 100%)", boxShadow: "0 4px 14px rgba(249,115,22,0.35), inset 0 1px 0 rgba(255,255,255,0.25)" }}>
            <BarChart3 size={17} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="font-bold leading-none" style={{ color: "var(--text-1)", fontSize: 13.5, letterSpacing: "-0.01em" }}>
              Election Ontology Engine
            </p>
            <p className="leading-none mt-1.5 eyebrow" style={{ color: "var(--text-3)" }}>
              Booth-Level Intelligence
            </p>
          </div>
        </div>

        {/* AC Selector */}
        <button className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-all"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--saffron-dim)")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
          <div className="flex items-center gap-2">
            <Shield size={12} style={{ color: "var(--saffron)" }} />
            <div className="text-left leading-none">
              <span className="font-semibold block" style={{ color: "var(--saffron)", fontSize: 12 }}>Gorakhpur Urban</span>
              <span className="block mt-1" style={{ color: "var(--text-4)", fontSize: 9.5 }}>Assembly Constituency 322</span>
            </div>
          </div>
          <ChevronDown size={11} style={{ color: "var(--text-4)" }} />
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

      {/* System status */}
      <div className="px-3.5 py-3" style={{ borderTop: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 mb-2.5">
          <Zap size={10} style={{ color: "var(--text-4)" }} />
          <p className="eyebrow">System Status</p>
        </div>
        <div className="space-y-1.5">
          {PIPELINE.map(({ label, status, icon: Icon, color, pulse }) => (
            <div key={label} className="flex items-center gap-2 px-2.5 py-2 rounded-lg"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
              <Icon size={11} style={{ color, flexShrink: 0 }} />
              <span className="flex-1" style={{ color: "var(--text-2)", fontSize: 11 }}>{label}</span>
              <div className="flex items-center gap-1.5">
                <span className={pulse ? "animate-pulse-dot" : ""}
                  style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: color }} />
                <span className="mono" style={{ color, fontSize: 9, fontWeight: 700, letterSpacing: "0.05em" }}>{status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer — secure session */}
      <div className="px-4 py-2.5 flex items-center justify-between"
        style={{ borderTop: "1px solid var(--border)" }}>
        <div className="flex items-center gap-1.5">
          <Shield size={10} style={{ color: "var(--green)" }} />
          <span style={{ color: "var(--text-3)", fontSize: 10 }}>Secure Session</span>
        </div>
        <span className="pill-saffron pill" style={{ fontSize: 8.5, padding: "2px 7px" }}>
          OFFICIAL USE
        </span>
      </div>
    </aside>
  );
}
