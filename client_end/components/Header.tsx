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
      {/* Left — title + breadcrumb */}
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: "var(--saffron)" }} />
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

      {/* Right — date + clock */}
      <div className="hidden md:flex flex-col items-end leading-none">
        <span className="mono" style={{ color: "var(--text-1)", fontSize: 12, fontWeight: 600 }}>{time}</span>
        <span className="mt-1" style={{ color: "var(--text-4)", fontSize: 9.5 }}>{date}</span>
      </div>
    </header>
  );
}
