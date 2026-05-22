"use client";

import { useState, useEffect } from "react";
import { Wifi, WifiOff, RefreshCw, ChevronRight, Home, Clock, Sun, Moon, Bell } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/components/ThemeProvider";

interface Props {
  topOffset: number;
  sidebarWidth: number;
  breadcrumbs?: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Map pathnames to human-readable breadcrumb labels (Hindi / English)
const CRUMB_MAP: Record<string, { en: string; hi: string }> = {
  "/":              { en: "Home",                  hi: "मुख्य पृष्ठ" },
  "/dashboard":     { en: "Overview Dashboard",    hi: "अवलोकन डैशबोर्ड" },
  "/pain-points":   { en: "Pain Point Engine",     hi: "समस्या इंजन" },
  "/booths":        { en: "Booth Intelligence",    hi: "बूथ बुद्धिमत्ता" },
  "/heatmap":       { en: "Constituency Heatmap",  hi: "क्षेत्र हीटमैप" },
  "/drivers":       { en: "Drivers Graph",         hi: "प्रभावक ग्राफ" },
  "/actions":       { en: "Action Engine",         hi: "कार्य योजना" },
  "/graph":         { en: "Knowledge Graph",       hi: "ज्ञान ग्राफ" },
  "/twin":          { en: "Digital Twin",          hi: "डिजिटल ट्विन" },
  "/reasoning":     { en: "AI Reasoning",          hi: "AI तर्कशक्ति" },
  "/demographics":  { en: "Demographics",          hi: "जनसांख्यिकी" },
  "/ontology":      { en: "Ontology Layer",        hi: "ऑन्टोलॉजी" },
  "/infrastructure":{ en: "Data Infrastructure",   hi: "डेटा अवसंरचना" },
};

export default function Header({ topOffset, sidebarWidth }: Props) {
  const [time, setTime] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname();

  // Resolve breadcrumb from current pathname
  const basePath = "/" + (pathname.split("/")[1] ?? "");
  const crumb = CRUMB_MAP[basePath] ?? { en: "Page", hi: "पृष्ठ" };

  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Asia/Kolkata",
        })
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => setApiOk(r.ok))
      .catch(() => setApiOk(false));
  }, []);

  return (
    <div
      role="navigation"
      aria-label="Breadcrumb and page controls"
      style={{
        position: "fixed",
        top: topOffset,
        left: sidebarWidth,
        right: 0,
        height: 44,
        background: "#f0f2f5",
        borderBottom: "1px solid #c0cfe0",
        zIndex: 45,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
      }}
    >
      {/* Breadcrumb */}
      <nav aria-label="You are here" style={{ display: "flex", alignItems: "center", gap: 0, fontSize: 12 }}>
        <Link href="/" aria-label="Home" style={{
          color: "#003380",
          textDecoration: "none",
          display: "flex",
          alignItems: "center",
          gap: 4,
          fontWeight: 500,
        }}>
          <Home size={11} />
          <span>Home</span>
        </Link>
        <ChevronRight size={10} style={{ color: "#a0b4c8", margin: "0 3px" }} />
        <span style={{ color: "#7890a8" }}>UP Vidhan Sabha</span>
        <ChevronRight size={10} style={{ color: "#a0b4c8", margin: "0 3px" }} />
        <span style={{ color: "#7890a8" }}>Gorakhpur Urban AC-322</span>
        <ChevronRight size={10} style={{ color: "#a0b4c8", margin: "0 3px" }} />
        <span style={{ color: "#002060", fontWeight: 600 }}>
          {crumb.en}
          <span style={{ fontSize: 10, color: "#7890a8", fontWeight: 400, marginLeft: 6 }} lang="hi">
            ({crumb.hi})
          </span>
        </span>
      </nav>

      {/* Right controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        {/* API status */}
        <div
          role="status"
          aria-live="polite"
          aria-label={`API status: ${apiOk === null ? "checking" : apiOk ? "live" : "down"}`}
          style={{ display: "flex", alignItems: "center", gap: 5 }}
        >
          {apiOk === null ? (
            <RefreshCw size={10} style={{ color: "#7890a8" }} className="animate-spin" />
          ) : apiOk ? (
            <Wifi size={10} style={{ color: "#138808" }} />
          ) : (
            <WifiOff size={10} style={{ color: "#cc2200" }} />
          )}
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            fontFamily: "monospace",
            letterSpacing: "0.04em",
            color: apiOk === null ? "#7890a8" : apiOk ? "#138808" : "#cc2200",
          }}>
            {apiOk === null ? "CHECKING" : apiOk ? "API LIVE" : "API DOWN"}
          </span>
        </div>

        <div style={{ width: 1, height: 16, background: "#c0cfe0" }} />

        {/* IST clock */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <Clock size={10} style={{ color: "#7890a8" }} />
          <span style={{ fontSize: 11, color: "#4a6280", fontFamily: "monospace" }}>{time}</span>
          <span style={{ fontSize: 9, color: "#a0b4c8", fontWeight: 600 }}>IST</span>
        </div>

        <div style={{ width: 1, height: 16, background: "#c0cfe0" }} />

        {/* Last updated — suppressHydrationWarning because date can differ between server/client */}
        <span style={{ fontSize: 10, color: "#7890a8" }}>
          Last Updated:{" "}
          <span suppressHydrationWarning style={{ fontWeight: 600, color: "#4a6280" }}>
            {new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
          </span>
        </span>

        <div style={{ width: 1, height: 16, background: "#c0cfe0" }} />

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="theme-toggle"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
        </button>

        {/* Alerts */}
        <button
          aria-label="Notifications"
          style={{
            position: "relative",
            padding: 5,
            borderRadius: 4,
            border: "1px solid #c0cfe0",
            background: "#ffffff",
            cursor: "pointer",
            color: "#4a6280",
            display: "flex",
            alignItems: "center",
          }}
        >
          <Bell size={13} />
          <span
            aria-label="1 new notification"
            style={{
              position: "absolute",
              top: 2,
              right: 2,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#cc2200",
            }}
          />
        </button>
      </div>
    </div>
  );
}
