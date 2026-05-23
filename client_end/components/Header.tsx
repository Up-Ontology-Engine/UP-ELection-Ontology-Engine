"use client";

import { useState, useEffect } from "react";
import { ChevronRight } from "lucide-react";

interface Props {
  breadcrumbs?: string[];
}

export default function Header({ breadcrumbs = ["Command Center"] }: Props) {
  const [time, setTime] = useState("");
  const [date, setDate] = useState("");

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

  return (
    <header className="header-bar fixed top-0 left-56 right-0 z-40 flex items-center justify-between px-6 h-14">
      {/* Left — breadcrumb title */}
      <div className="flex items-center gap-1.5 text-sm min-w-0" style={{ color: "var(--text-3)" }}>
        <span style={{ color: "var(--text-2)", fontWeight: 600 }}>Gorakhpur Urban</span>
        {breadcrumbs.map((b, i) => (
          <span key={i} className="flex items-center gap-1.5 truncate">
            <ChevronRight size={13} style={{ color: "var(--text-4)" }} />
            <span style={{ color: i === breadcrumbs.length - 1 ? "var(--text-1)" : "var(--text-2)", fontWeight: i === breadcrumbs.length - 1 ? 600 : 400 }}>{b}</span>
          </span>
        ))}
      </div>

      {/* Right — date + time */}
      <div className="hidden md:flex items-center gap-2 text-xs" style={{ color: "var(--text-4)" }}>
        <span>{date}</span>
        <span style={{ color: "var(--border-bright)" }}>·</span>
        <span className="mono" style={{ color: "var(--text-2)" }}>{time}</span>
      </div>
    </header>
  );
}
