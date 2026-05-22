"use client";

import { useState, useEffect } from "react";
import { Bell, Wifi, WifiOff, RefreshCw, ChevronRight, Sun, Moon, ShieldCheck } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

interface Props {
  breadcrumbs?: string[];
}

export default function Header({ breadcrumbs = ["Command Center"] }: Props) {
  const [time, setTime] = useState("");
  const [date, setDate] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false }));
      setDate(now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch("http://localhost:8000/health").then((r) => setApiOk(r.ok)).catch(() => setApiOk(false));
  }, []);

  return (
    <header className="header-bar fixed top-0 left-56 right-0 z-40 flex items-center justify-between px-6 h-14">
      {/* Left — title + breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full animate-pulse-dot flex-shrink-0" style={{ background: "var(--green)" }} />
          <div className="leading-none min-w-0">
            <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-3)" }}>
              <span style={{ color: "var(--text-2)", fontWeight: 600 }}>Gorakhpur Urban</span>
              {breadcrumbs.map((b, i) => (
                <span key={i} className="flex items-center gap-1.5 truncate">
                  <ChevronRight size={11} style={{ color: "var(--text-4)" }} />
                  <span style={{ color: i === breadcrumbs.length - 1 ? "var(--text-1)" : "var(--text-2)" }}>{b}</span>
                </span>
              ))}
            </div>
            <p className="mt-1.5" style={{ color: "var(--text-4)", fontSize: 10 }}>
              Booth-Level Political Intelligence Platform
            </p>
          </div>
        </div>
      </div>

      {/* Center — live feed indicator */}
      <div className="hidden lg:flex items-center gap-2 absolute left-1/2 -translate-x-1/2">
        <span className="pill pill-live">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--green)" }} />
          LIVE INTELLIGENCE FEED
        </span>
      </div>

      {/* Right — status controls */}
      <div className="flex items-center gap-3.5">
        {/* Date + clock */}
        <div className="hidden md:flex flex-col items-end leading-none">
          <span className="mono" style={{ color: "var(--text-1)", fontSize: 12, fontWeight: 600 }}>{time}</span>
          <span className="mt-1" style={{ color: "var(--text-4)", fontSize: 9.5 }}>{date}</span>
        </div>

        <div className="w-px h-6" style={{ background: "var(--border)" }} />

        {/* Connection status */}
        <div className="flex items-center gap-1.5" title="Backend connection">
          {apiOk === null ? (
            <RefreshCw size={12} className="animate-spin" style={{ color: "var(--text-3)" }} />
          ) : apiOk ? (
            <Wifi size={12} style={{ color: "var(--green)" }} />
          ) : (
            <WifiOff size={12} style={{ color: "var(--text-4)" }} />
          )}
          <span className="mono hidden xl:inline" style={{
            color: apiOk ? "var(--green)" : "var(--text-4)", fontSize: 10, fontWeight: 600,
          }}>
            {apiOk === null ? "CONNECTING" : apiOk ? "CONNECTED" : "OFFLINE"}
          </span>
        </div>

        {/* Theme toggle */}
        <button onClick={toggleTheme} className="theme-toggle" title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        {/* Alerts */}
        <button className="relative p-1.5 rounded-md transition-colors"
          style={{ color: "var(--text-3)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
          <Bell size={14} />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--red)" }} />
        </button>

        <div className="w-px h-6" style={{ background: "var(--border)" }} />

        {/* Verified badge */}
        <div className="hidden sm:flex items-center gap-1.5 pill" style={{ borderColor: "rgba(16,185,129,0.3)", background: "rgba(16,185,129,0.08)" }}>
          <ShieldCheck size={11} style={{ color: "var(--green)" }} />
          <span style={{ color: "var(--green)", fontSize: 10 }}>Verified Data</span>
        </div>
      </div>
    </header>
  );
}
