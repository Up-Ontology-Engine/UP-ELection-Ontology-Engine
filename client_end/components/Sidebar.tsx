"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, MapPin, Network, BarChart3, Brain,
  MessageSquare, BookOpen, Users, Cpu, Activity,
  ChevronDown, GitBranch, Database, Shield, Radio
} from "lucide-react";

const SECTIONS = [
  {
    label: "Operations",
    items: [
      { href: "/", icon: LayoutDashboard, label: "Command Center", badge: null, dot: "green" },
      { href: "/booths", icon: Activity, label: "Booth Intelligence", badge: "247", dot: "green" },
      { href: "/heatmap", icon: MapPin, label: "Geospatial Command", badge: null, dot: "amber" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/graph", icon: Network, label: "Knowledge Graph", badge: null, dot: "blue" },
      { href: "/twin", icon: Cpu, label: "Digital Twin", badge: "BETA", dot: "purple" },
      { href: "/reasoning", icon: MessageSquare, label: "AI Reasoning", badge: null, dot: "pink" },
    ],
  },
  {
    label: "Analytics",
    items: [
      { href: "/demographics", icon: Users, label: "Demographics", badge: null, dot: "cyan" },
      { href: "/ontology", icon: BookOpen, label: "Ontology Layer", badge: "v1", dot: "slate" },
    ],
  },
];

const DOT_COLORS: Record<string, string> = {
  green: "#10b981", amber: "#f59e0b", blue: "#3b82f6",
  purple: "#8b5cf6", pink: "#ec4899", cyan: "#06b6d4", slate: "#64748b",
};

export default function Sidebar() {
  const path = usePathname();

  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <aside className="fixed top-0 left-0 h-full w-56 flex flex-col z-50 select-none"
      style={{ background: "#060b14", borderRight: "1px solid #1a2b44" }}>

      {/* Logo / Brand */}
      <div className="px-4 pt-4 pb-3" style={{ borderBottom: "1px solid #1a2b44" }}>
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #f97316 0%, #dc2626 100%)" }}>
            <BarChart3 size={14} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-xs leading-none tracking-wide">UP-EOM</p>
            <p className="text-xs leading-none mt-0.5" style={{ color: "#4d6480" }}>Election Ontology Engine</p>
          </div>
        </div>

        {/* AC Selector */}
        <button className="w-full flex items-center justify-between px-3 py-2 rounded-md text-xs transition-colors hover:bg-white/5"
          style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
          <div className="flex items-center gap-2">
            <Shield size={10} style={{ color: "#f97316" }} />
            <span className="font-medium" style={{ color: "#f97316" }}>Gorakhpur Urban</span>
          </div>
          <ChevronDown size={10} style={{ color: "#4d6480" }} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {SECTIONS.map((section) => (
          <div key={section.label} className="mb-1">
            <p className="px-4 py-2 label" style={{ color: "#2e4260" }}>{section.label}</p>
            {section.items.map(({ href, icon: Icon, label, badge, dot }) => {
              const active = isActive(href);
              return (
                <Link key={href} href={href}
                  className="flex items-center gap-2.5 mx-2 px-2.5 py-2 rounded-md mb-0.5 transition-all text-xs group relative"
                  style={{
                    background: active ? "rgba(249,115,22,0.1)" : "transparent",
                    color: active ? "#f97316" : "#8ba0bc",
                  }}>
                  {active && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full"
                      style={{ background: "#f97316" }} />
                  )}
                  {/* Status dot */}
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse-dot"
                    style={{ background: DOT_COLORS[dot] ?? "#64748b", opacity: active ? 1 : 0.5 }} />
                  <Icon size={13} className="flex-shrink-0" />
                  <span className="flex-1 font-medium leading-none">{label}</span>
                  {badge && (
                    <span className="text-xs px-1.5 py-0.5 rounded mono"
                      style={{
                        background: active ? "rgba(249,115,22,0.2)" : "#1a2b44",
                        color: active ? "#f97316" : "#4d6480",
                        fontSize: 9,
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
      <div className="px-3 py-3" style={{ borderTop: "1px solid #1a2b44" }}>
        <p className="label mb-2" style={{ color: "#2e4260" }}>Pipeline Status</p>
        {[
          { label: "PostgreSQL", status: "LIVE", color: "#10b981", icon: Database },
          { label: "Neo4j Graph", status: "LIVE", color: "#10b981", icon: GitBranch },
          { label: "ETL Pipeline", status: "IDLE", color: "#f59e0b", icon: Radio },
        ].map(({ label, status, color, icon: Icon }) => (
          <div key={label} className="flex items-center gap-2 py-1">
            <Icon size={10} style={{ color }} />
            <span className="flex-1 text-xs" style={{ color: "#4d6480" }}>{label}</span>
            <span className="mono text-xs" style={{ color, fontSize: 9 }}>{status}</span>
          </div>
        ))}
      </div>

      {/* Version */}
      <div className="px-4 py-2.5 flex items-center justify-between"
        style={{ borderTop: "1px solid #1a2b44" }}>
        <div className="flex items-center gap-1.5">
          <Brain size={10} style={{ color: "#2e4260" }} />
          <span className="mono text-xs" style={{ color: "#2e4260" }}>v1.0.0-ontology</span>
        </div>
        <span className="text-xs px-1.5 py-0.5 rounded mono"
          style={{ background: "#0b1220", color: "#2e4260", fontSize: 9 }}>PHASE 0</span>
      </div>
    </aside>
  );
}
