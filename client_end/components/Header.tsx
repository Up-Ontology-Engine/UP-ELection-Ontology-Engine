"use client";

import { useState, useEffect } from "react";
import { Search, Bell, Wifi, WifiOff, RefreshCw, ChevronRight, Terminal, Sun, Moon } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

interface Props {
  breadcrumbs?: string[];
}

export default function Header({ breadcrumbs = ["Gorakhpur Urban AC"] }: Props) {
  const [time, setTime] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch("http://localhost:8000/health").then((r) => setApiOk(r.ok)).catch(() => setApiOk(false));
  }, []);

  return (
    <header className="header-bar fixed top-0 left-56 right-0 z-40 flex items-center justify-between px-5 h-11">
      {/* Left — breadcrumb */}
      <div className="flex items-center gap-1.5 mono text-xs" style={{ color: "var(--text-3)" }}>
        <Terminal size={11} style={{ color: "var(--saffron)" }} />
        <span style={{ color: "var(--text-2)" }}>UP-EOM</span>
        {breadcrumbs.map((b, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <ChevronRight size={10} style={{ color: "var(--text-4)" }} />
            <span style={{ color: i === breadcrumbs.length - 1 ? "var(--text-1)" : "var(--text-2)" }}>{b}</span>
          </span>
        ))}
      </div>

      {/* Center — live ticker */}
      <div className="hidden md:flex items-center gap-3 overflow-hidden max-w-sm">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--green)" }} />
          <span className="mono text-xs" style={{ color: "var(--text-3)" }}>LIVE</span>
        </div>
        <div className="text-xs mono truncate" style={{ color: "var(--text-3)" }}>
          Gorakhpur Urban AC · 247 booths · Last sync: {time}
        </div>
      </div>

      {/* Right — status controls */}
      <div className="flex items-center gap-3">
        {/* API status */}
        <div className="flex items-center gap-1.5">
          {apiOk === null ? (
            <RefreshCw size={11} className="animate-spin" style={{ color: "var(--text-3)" }} />
          ) : apiOk ? (
            <Wifi size={11} style={{ color: "var(--green)" }} />
          ) : (
            <WifiOff size={11} style={{ color: "var(--red)" }} />
          )}
          <span className="mono text-xs hidden lg:inline"
            style={{ color: apiOk === null ? "var(--text-3)" : apiOk ? "var(--green)" : "var(--red)" }}>
            {apiOk === null ? "CHECKING" : apiOk ? "API LIVE" : "API DOWN"}
          </span>
        </div>

        <div className="w-px h-4" style={{ background: "var(--border)" }} />

        {/* Clock */}
        <span className="mono text-xs hidden lg:inline" style={{ color: "var(--text-3)" }}>{time}</span>

        <div className="w-px h-4" style={{ background: "var(--border)" }} />

        {/* Search hint */}
        <button className="flex items-center gap-2 px-2 py-1 rounded text-xs mono transition-colors"
          style={{ color: "var(--text-3)", border: "1px solid var(--border)", background: "transparent" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
          <Search size={10} />
          <span className="hidden lg:inline">Search</span>
          <span className="hidden lg:inline px-1 rounded text-xs mono"
            style={{ background: "var(--bg-surface)", color: "var(--text-4)" }}>⌘K</span>
        </button>

        {/* Theme toggle */}
        <button onClick={toggleTheme} className="theme-toggle" title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
          {theme === "dark"
            ? <Sun size={13} />
            : <Moon size={13} />}
        </button>

        {/* Alerts */}
        <button className="relative p-1.5 rounded transition-colors"
          style={{ color: "var(--text-3)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
          <Bell size={13} />
          <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full" style={{ background: "var(--red)" }} />
        </button>
      </div>
    </header>
  );
}
