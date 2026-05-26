"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Network, BarChart3,
  MessageSquare, BookOpen, Users, Activity,
  ChevronDown, Shield, Flame, Target, ScrollText
} from "lucide-react";

const SECTIONS = [
  {
    label: "Operations",
    items: [
      { href: "/dashboard",  icon: LayoutDashboard, label: "Command Center"     },
      { href: "/booths",     icon: Activity,        label: "Booth Intelligence" },
      { href: "/conversion", icon: Target,          label: "Voter Conversion"   },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/heatmap",   icon: Flame,         label: "Constituency Heatmap" },
      { href: "/graph",     icon: Network,       label: "Knowledge Graph"      },
      { href: "/reasoning", icon: MessageSquare, label: "AI Reasoning"         },
    ],
  },
  {
    label: "Analytics",
    items: [
      { href: "/demographics", icon: Users,       label: "Demographics"        },
      { href: "/myneta",       icon: ScrollText,  label: "My Neta Report Card" },
      { href: "/ontology",     icon: BookOpen,    label: "Ontology Layer"      },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();

  const isActive = (href: string) =>
    href === "/dashboard" ? path === "/dashboard" : path === href || path.startsWith(href + "/");

  return (
    <aside className="fixed top-0 left-0 h-full w-56 flex flex-col z-50 select-none"
      style={{ background: "var(--bg-base)", borderRight: "1px solid var(--border)" }}>

      {/* Logo / Brand */}
      <div className="px-4 pt-4 pb-3.5" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3 mb-3.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "var(--saffron)" }}>
            <BarChart3 size={17} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="font-bold leading-none" style={{ color: "var(--text-1)", fontSize: 13.5, letterSpacing: "-0.01em" }}>
              Election Ontology Engine
            </p>
            <p className="leading-none mt-1.5" style={{ color: "var(--text-3)", fontSize: 10.5 }}>
              Booth-Level Intelligence
            </p>
          </div>
        </div>

        {/* AC Selector */}
        <button className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-all"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-bright)")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
          <div className="flex items-center gap-2">
            <Shield size={12} style={{ color: "var(--saffron)" }} />
            <div className="text-left leading-none">
              <span className="font-semibold block" style={{ color: "var(--text-1)", fontSize: 12 }}>Gorakhpur Urban</span>
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
            <div className="px-5 pt-3 pb-1.5">
              <span className="label" style={{ color: "var(--text-4)", fontSize: 9, letterSpacing: "0.12em" }}>
                {section.label}
              </span>
            </div>

            {section.items.map(({ href, icon: Icon, label }) => {
              const active = isActive(href);
              return (
                <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
                  <Icon size={15} style={{ flexShrink: 0, opacity: active ? 1 : 0.75 }} />
                  <span className="flex-1 leading-none" style={{ fontSize: 12.5 }}>{label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 flex items-center justify-between"
        style={{ borderTop: "1px solid var(--border)" }}>
        <span style={{ color: "var(--text-4)", fontSize: 10 }}>Gorakhpur Pilot</span>
        <span style={{ color: "var(--text-4)", fontSize: 10 }}>Pilot</span>
      </div>
    </aside>
  );
}
