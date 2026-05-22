"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Network, BarChart3, Brain,
  MessageSquare, BookOpen, Users, Activity,
  ChevronDown, GitBranch, Database, Shield, Radio, Zap, Flame, Target,
  AlertTriangle, ListChecks,
} from "lucide-react";

const SECTIONS = [
  {
    label: "Operations",
    labelHi: "संचालन",
    items: [
      { href: "/",           icon: LayoutDashboard, label: "Home",               labelHi: "मुख्य पृष्ठ",       badge: null,  dot: "green"  },
      { href: "/dashboard",  icon: Activity,        label: "Command Center",     labelHi: "कमांड सेंटर",      badge: null,  dot: "green"  },
      { href: "/booths",     icon: Activity,        label: "Booth Intelligence", labelHi: "बूथ बुद्धिमत्ता",  badge: "30",  dot: "green"  },
      { href: "/conversion", icon: Target,          label: "Voter Conversion",   labelHi: "मतदाता रूपांतरण",   badge: "NEW", dot: "orange" },
    ],
  },
  {
    label: "Decisions",
    labelHi: "निर्णय",
    items: [
      { href: "/pain-points", icon: AlertTriangle, label: "Pain Point Engine",      labelHi: "दर्द बिंदु इंजन",    badge: null, dot: "amber"  },
      { href: "/actions",     icon: ListChecks,    label: "Action Recommendations", labelHi: "कार्य अनुशंसाएं",    badge: null, dot: "purple" },
      { href: "/drivers",     icon: Target,        label: "Candidate + Drivers",    labelHi: "उम्मीदवार विश्लेषण", badge: null, dot: "blue"   },
    ],
  },
  {
    label: "Intelligence",
    labelHi: "आसूचना",
    items: [
      { href: "/heatmap",   icon: Flame,         label: "Constituency Heatmap", labelHi: "क्षेत्र हीटमैप",  badge: null, dot: "amber" },
      { href: "/graph",     icon: Network,       label: "Knowledge Graph",      labelHi: "ज्ञान ग्राफ",     badge: null, dot: "blue"  },
      { href: "/reasoning", icon: MessageSquare, label: "AI Reasoning",         labelHi: "AI तर्कशक्ति",    badge: null, dot: "pink"  },
    ],
  },
  {
    label: "Analytics",
    labelHi: "विश्लेषण",
    items: [
      { href: "/demographics", icon: Users,    label: "Demographics",   labelHi: "जनसांख्यिकी", badge: null, dot: "cyan"  },
      { href: "/ontology",     icon: BookOpen, label: "Ontology Layer", labelHi: "ऑन्टोलॉजी",   badge: "v1", dot: "slate" },
    ],
  },
];

const DOT_COLORS: Record<string, string> = {
  green:  "#10b981",
  amber:  "#f59e0b",
  blue:   "#3b82f6",
  purple: "#8b5cf6",
  pink:   "#ec4899",
  cyan:   "#06b6d4",
  slate:  "#64748b",
  orange: "#f97316",
};

const PIPELINE = [
  { label: "PostgreSQL",   status: "LIVE", icon: Database,  color: "#10b981", pulse: true  },
  { label: "Neo4j Graph",  status: "LIVE", icon: GitBranch, color: "#10b981", pulse: true  },
  { label: "ETL Pipeline", status: "IDLE", icon: Radio,     color: "#f59e0b", pulse: false },
];

// Dark sidebar constants — always dark regardless of global theme
const S = {
  bg:       "#0b1220",
  surface:  "#111827",
  border:   "#1a2b44",
  text1:    "#f0f4fa",
  text3:    "#4a6280",
  text4:    "#2e4260",
};

export default function Sidebar() {
  const path = usePathname();

  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <aside className="fixed top-0 left-0 h-full w-56 flex flex-col z-50 select-none"
      style={{ background: S.bg, borderRight: `1px solid ${S.border}` }}>

      {/* Top accent line */}
      <div className="h-0.5 w-full flex-shrink-0"
        style={{ background: "linear-gradient(90deg, #FF9933, #003380, #138808)" }} />

      {/* Logo / Brand */}
      <div className="px-4 pt-4 pb-3.5" style={{ borderBottom: `1px solid ${S.border}` }}>
        <div className="flex items-center gap-2.5 mb-3.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #f97316 0%, #dc2626 100%)", boxShadow: "0 2px 8px rgba(249,115,22,0.3)" }}>
            <BarChart3 size={15} style={{ color: "#fff" }} />
          </div>
          <div>
            <p className="font-bold text-xs leading-none tracking-widest" style={{ color: S.text1 }}>UP-EOM</p>
            <p className="text-xs leading-none mt-1" style={{ color: S.text3, fontSize: 10 }}>Election Ontology Engine</p>
          </div>
        </div>

        {/* AC Selector */}
        <button className="w-full flex items-center justify-between px-2.5 py-2 rounded-md text-xs transition-all"
          style={{ background: S.surface, border: `1px solid ${S.border}` }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(255,153,51,0.5)")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = S.border)}>
          <div className="flex items-center gap-2">
            <Shield size={10} style={{ color: "#FF9933" }} />
            <span className="font-semibold" style={{ color: "#FF9933", fontSize: 11 }}>Gorakhpur Urban</span>
          </div>
          <ChevronDown size={10} style={{ color: S.text4 }} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {SECTIONS.map((section, si) => (
          <div key={section.label} className={si > 0 ? "mt-1" : ""}>
            {/* Section header */}
            <div className="flex items-center gap-2 px-4 pt-3 pb-1.5">
              <div>
                <span className="label" style={{ color: S.text4, fontSize: 9, letterSpacing: "0.12em" }}>
                  {section.label}
                </span>
                {section.labelHi && (
                  <span className="ml-1.5" style={{ color: S.text4, fontSize: 9, opacity: 0.6 }}>
                    · {section.labelHi}
                  </span>
                )}
              </div>
              <div className="flex-1 h-px" style={{ background: S.border }} />
            </div>

            {section.items.map(({ href, icon: Icon, label, labelHi, badge, dot }) => {
              const active = isActive(href);
              const dotColor = DOT_COLORS[dot] ?? "#64748b";
              const activeColor = "#f97316"; // always orange when active
              return (
                <Link key={href} href={href}
                  className="flex items-center gap-2.5 px-3.5 py-2 mx-1.5 rounded-md text-xs transition-all"
                  style={{
                    background: active ? "rgba(249,115,22,0.1)" : "transparent",
                    border: active ? "1px solid rgba(249,115,22,0.25)" : "1px solid transparent",
                    color: active ? S.text1 : S.text3,
                    textDecoration: "none",
                  }}>
                  {/* Status dot */}
                  <span
                    className={active ? "animate-pulse-dot" : ""}
                    style={{
                      display: "inline-block",
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background: active ? activeColor : dotColor,
                      opacity: active ? 1 : 0.4,
                      flexShrink: 0,
                    }} />
                  <Icon size={13} style={{ flexShrink: 0, color: active ? activeColor : S.text3, opacity: active ? 1 : 0.7 }} />
                  <div className="flex-1 min-w-0">
                    <p className="leading-none" style={{ fontSize: 12, color: active ? activeColor : S.text3 }}>{label}</p>
                    <p className="leading-none mt-0.5 truncate" style={{ fontSize: 9, color: active ? "rgba(249,115,22,0.6)" : S.text4 }}>{labelHi}</p>
                  </div>
                  {badge && (
                    <span className="mono px-1.5 py-0.5 rounded flex-shrink-0"
                      style={{
                        background: active ? "rgba(249,115,22,0.2)" : S.surface,
                        color: active ? activeColor : S.text4,
                        fontSize: 9,
                        fontWeight: 600,
                        letterSpacing: "0.04em",
                        border: `1px solid ${active ? "rgba(249,115,22,0.35)" : S.border}`,
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
      <div className="px-3.5 py-3" style={{ borderTop: `1px solid ${S.border}` }}>
        <div className="flex items-center gap-2 mb-2.5">
          <Zap size={9} style={{ color: S.text4 }} />
          <p className="label" style={{ color: S.text4, fontSize: 9 }}>Pipeline Status</p>
        </div>
        <div className="space-y-1.5">
          {PIPELINE.map(({ label, status, icon: Icon, color, pulse }) => (
            <div key={label} className="flex items-center gap-2 px-2.5 py-1.5 rounded-md"
              style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <Icon size={10} style={{ color, flexShrink: 0 }} />
              <span className="flex-1 text-xs" style={{ color: S.text3, fontSize: 11 }}>{label}</span>
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
        style={{ borderTop: `1px solid ${S.border}` }}>
        <div className="flex items-center gap-1.5">
          <Brain size={9} style={{ color: S.text4 }} />
          <span className="mono" style={{ color: S.text4, fontSize: 10 }}>v1.0.0-ontology</span>
        </div>
        <span className="mono px-1.5 py-0.5 rounded"
          style={{ background: S.surface, color: S.text4, fontSize: 9, border: `1px solid ${S.border}` }}>
          PHASE 0
        </span>
      </div>
    </aside>
  );
}
