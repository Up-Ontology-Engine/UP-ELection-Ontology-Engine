"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Network, Brain,
  MessageSquare, BookOpen, Users, Activity,
  ChevronDown, GitBranch, Database, Shield, Radio, Zap, Flame,
  AlertTriangle, ListChecks, Target,
} from "lucide-react";

interface SidebarProps {
  topOffset: number;
  sidebarWidth: number;
}

const SECTIONS = [
  {
    label: "Operations",
    labelHi: "संचालन",
    items: [
      { href: "/",          icon: LayoutDashboard, label: "Home",               labelHi: "मुख्य पृष्ठ",     badge: null },
      { href: "/dashboard", icon: Activity,        label: "Command Center",     labelHi: "कमांड सेंटर",     badge: null },
      { href: "/booths",    icon: Shield,          label: "Booth Intelligence", labelHi: "बूथ बुद्धिमत्ता", badge: null },
    ],
  },
  {
    label: "Decisions",
    labelHi: "निर्णय",
    items: [
      { href: "/pain-points", icon: AlertTriangle, label: "Pain Point Engine",      labelHi: "दर्द बिंदु इंजन",   badge: null },
      { href: "/actions",     icon: ListChecks,    label: "Action Recommendations", labelHi: "कार्य अनुशंसाएं",   badge: null },
      { href: "/drivers",     icon: Target,        label: "Candidate + Drivers",    labelHi: "उम्मीदवार विश्लेषण", badge: null },
    ],
  },
  {
    label: "Intelligence",
    labelHi: "आसूचना",
    items: [
      { href: "/heatmap",   icon: Flame,         label: "Constituency Heatmap", labelHi: "क्षेत्र हीटमैप", badge: null },
      { href: "/graph",     icon: Network,       label: "Knowledge Graph",      labelHi: "ज्ञान ग्राफ",    badge: null },
      { href: "/reasoning", icon: MessageSquare, label: "AI Reasoning",         labelHi: "AI तर्कशक्ति",   badge: null },
    ],
  },
  {
    label: "Analytics",
    labelHi: "विश्लेषण",
    items: [
      { href: "/demographics", icon: Users,    label: "Demographics",   labelHi: "जनसांख्यिकी", badge: null  },
      { href: "/ontology",     icon: BookOpen, label: "Ontology Layer", labelHi: "ऑन्टोलॉजी",   badge: "v1" },
    ],
  },
];

const PIPELINE = [
  { label: "PostgreSQL",   status: "LIVE", icon: Database,  color: "#138808", pulse: true  },
  { label: "Neo4j Graph",  status: "LIVE", icon: GitBranch, color: "#138808", pulse: true  },
  { label: "ETL Pipeline", status: "IDLE", icon: Radio,     color: "#d97706", pulse: false },
];

const NAVY = "#061225";
const NAVY_2 = "#0a1b35";
const NAVY_3 = "#10294d";
const LINE = "rgba(255,255,255,0.14)";
const TEXT = "#f3f7ff";
const MUTED = "rgba(243,247,255,0.62)";
const DIM = "rgba(243,247,255,0.42)";

export default function Sidebar({ topOffset, sidebarWidth }: SidebarProps) {
  const path = usePathname();
  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <aside
      aria-label="Main Navigation"
      style={{
        position: "fixed",
        top: topOffset,
        left: 0,
        width: sidebarWidth,
        height: `calc(100vh - ${topOffset}px)`,
        background: NAVY,
        borderRight: "1px solid rgba(255,153,51,0.35)",
        display: "flex",
        flexDirection: "column",
        zIndex: 50,
        overflowY: "auto",
        boxShadow: "4px 0 18px rgba(0,18,48,0.28)",
      }}
    >
      {/* AC selector */}
      <div style={{
        padding: "10px 10px 8px",
        borderBottom: `1px solid ${LINE}`,
        background: NAVY_2,
      }}>
        <button
          aria-label="Switch constituency"
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 10px",
            borderRadius: 4,
            border: `1px solid ${LINE}`,
            background: NAVY_3,
            cursor: "pointer",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Shield size={12} style={{ color: "#FF9933" }} />
            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: TEXT, lineHeight: 1.2 }}>
                Gorakhpur Urban
              </div>
              <div style={{ fontSize: 9, color: MUTED, lineHeight: 1.2, marginTop: 1 }} lang="hi">
                गोरखपुर शहरी · AC-322
              </div>
            </div>
          </div>
          <ChevronDown size={10} style={{ color: MUTED }} />
        </button>
      </div>

      {/* Navigation */}
      <nav aria-label="Site sections" style={{ flex: 1, paddingTop: 6, paddingBottom: 4 }}>
        {SECTIONS.map((section, si) => (
          <div key={section.label} style={{ marginTop: si > 0 ? 2 : 0 }}>
            {/* Section header */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 14px 5px",
            }}>
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                color: "#FF9933",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}>
                {section.label}
              </span>
              <span style={{ fontSize: 9, color: DIM }} lang="hi">
                / {section.labelHi}
              </span>
              <div style={{ flex: 1, height: 1, background: LINE }} />
            </div>

            {section.items.map(({ href, icon: Icon, label, labelHi, badge }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-label={label}
                  aria-current={active ? "page" : undefined}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 9,
                    margin: "1px 8px",
                    padding: "7px 10px",
                    borderRadius: 4,
                    textDecoration: "none",
                    background: active ? "rgba(255,153,51,0.14)" : "transparent",
                    borderLeft: active ? "3px solid #FF9933" : "3px solid transparent",
                    transition: "all 0.1s ease",
                  }}
                >
                  <Icon
                    size={14}
                    style={{
                      color: active ? "#FF9933" : MUTED,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 12,
                      fontWeight: active ? 700 : 500,
                      color: active ? "#ffffff" : "rgba(243,247,255,0.82)",
                      lineHeight: 1.2,
                    }}>
                      {label}
                    </div>
                    <div style={{
                      fontSize: 9,
                      color: active ? "rgba(255,255,255,0.68)" : DIM,
                      lineHeight: 1,
                      marginTop: 1.5,
                    }} lang="hi">
                      {labelHi}
                    </div>
                  </div>
                  {badge && (
                    <span style={{
                      padding: "1px 5px",
                      borderRadius: 3,
                      fontSize: 9,
                      fontWeight: 700,
                      background: active ? "rgba(255,153,51,0.18)" : NAVY_3,
                      color: active ? "#FF9933" : MUTED,
                      border: `1px solid ${active ? "rgba(255,153,51,0.35)" : LINE}`,
                      fontFamily: "monospace",
                      flexShrink: 0,
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
      <div style={{
        padding: "10px 10px 8px",
        borderTop: `1px solid ${LINE}`,
        background: NAVY_2,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 7 }}>
          <Zap size={9} style={{ color: "#FF9933" }} />
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            color: MUTED,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}>
            Data Pipeline
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {PIPELINE.map(({ label, status, icon: Icon, color, pulse }) => (
            <div key={label} style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 8px",
              borderRadius: 4,
              background: NAVY_3,
              border: `1px solid ${LINE}`,
            }}>
              <Icon size={10} style={{ color, flexShrink: 0 }} />
              <span style={{ flex: 1, fontSize: 10.5, color: MUTED }}>{label}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span
                  className={pulse ? "animate-pulse-dot" : ""}
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: color,
                    flexShrink: 0,
                  }}
                />
                <span style={{
                  fontSize: 9,
                  fontWeight: 700,
                  color,
                  fontFamily: "monospace",
                  letterSpacing: "0.04em",
                }}>
                  {status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Version footer */}
      <div style={{
        padding: "7px 12px",
        borderTop: `1px solid ${LINE}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "#041027",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <Brain size={9} style={{ color: DIM }} />
          <span style={{ fontSize: 9.5, color: DIM, fontFamily: "monospace" }}>
            v1.0.0-ontology
          </span>
        </div>
        <span style={{
          padding: "1px 6px",
          borderRadius: 3,
          background: NAVY_3,
          color: MUTED,
          fontSize: 9,
          border: `1px solid ${LINE}`,
          fontFamily: "monospace",
          fontWeight: 700,
        }}>
          PHASE 0
        </span>
      </div>
    </aside>
  );
}
