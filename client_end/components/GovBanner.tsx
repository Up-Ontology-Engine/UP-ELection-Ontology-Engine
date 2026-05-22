"use client";

import { useState, useEffect } from "react";

export default function GovBanner() {
  const [lang, setLang] = useState<"en" | "hi">(() => {
    if (typeof window === "undefined") return "en";
    return (localStorage.getItem("gov-lang") as "en" | "hi" | null) ?? "en";
  });
  const [fs, setFs] = useState<"sm" | "md" | "lg">(() => {
    if (typeof window === "undefined") return "md";
    return (localStorage.getItem("gov-fontsize") as "sm" | "md" | "lg" | null) ?? "md";
  });

  function applyFs(size: "sm" | "md" | "lg") {
    const map = { sm: "12px", md: "13px", lg: "15px" };
    document.body.style.fontSize = map[size];
  }

  useEffect(() => {
    applyFs(fs);
  }, [fs]);

  function setFontSize(size: "sm" | "md" | "lg") {
    setFs(size);
    localStorage.setItem("gov-fontsize", size);
    applyFs(size);
  }

  function setLanguage(l: "en" | "hi") {
    setLang(l);
    localStorage.setItem("gov-lang", l);
  }

  const base: React.CSSProperties = {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    height: 36,
    background: "#002060",
    borderBottom: "2px solid #FF9933",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 20px",
    zIndex: 70,
    fontSize: 11,
  };

  const pill: React.CSSProperties = {
    background: "#07152c",
    color: "rgba(255,255,255,0.78)",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 2,
    padding: "1px 8px",
    cursor: "pointer",
    fontSize: 11,
    lineHeight: "18px",
  };

  const pillActive: React.CSSProperties = {
    ...pill,
    background: "#0b2a58",
    border: "1px solid #FF9933",
    color: "#ffffff",
    fontWeight: 700,
  };

  const sep = <span style={{ color: "rgba(255,255,255,0.25)", margin: "0 6px" }}>|</span>;
  const darkPanel: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 4,
    background: "#061225",
    border: "1px solid rgba(255,255,255,0.16)",
    borderRadius: 3,
    padding: "3px 5px",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
  };

  return (
    <div style={base} role="banner">
      {/* Left: accessibility controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <a href="#main-content" style={{
          color: "#ffffff",
          textDecoration: "none",
          fontSize: 11,
          padding: "1px 8px",
          border: "1px solid rgba(255,255,255,0.35)",
          borderRadius: 2,
          fontWeight: 500,
        }}>
          Skip to Main Content
        </a>
        {sep}
        <div style={darkPanel} aria-label="Text size controls">
          <span style={{ color: "rgba(255,255,255,0.58)", fontSize: 11, padding: "0 4px" }}>Text</span>
          {(["sm", "md", "lg"] as const).map((size, i) => (
            <button key={size} onClick={() => setFontSize(size)}
              style={fs === size ? pillActive : pill}
              aria-label={["Small", "Normal", "Large"][i] + " text"}>
              <span style={{ fontSize: [10, 11, 13][i] }}>A</span>
            </button>
          ))}
        </div>
        {sep}
        <button style={pill} aria-label="Screen Reader Access">
          Screen Reader Access
        </button>
      </div>

      {/* Right: language toggle */}
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <button onClick={() => setLanguage("en")}
          style={lang === "en" ? pillActive : pill}
          aria-label="Switch to English" aria-pressed={lang === "en"}>
          English
        </button>
        {sep}
        <button onClick={() => setLanguage("hi")}
          style={lang === "hi" ? pillActive : { ...pill, fontSize: 12 }}
          aria-label="हिंदी में बदलें" aria-pressed={lang === "hi"}>
          हिंदी
        </button>
      </div>
    </div>
  );
}
