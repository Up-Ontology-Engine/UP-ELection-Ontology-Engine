"use client";

import { useEffect } from "react";
import { Candidate } from "@/lib/api";
import {
  X, User, Users, TrendingUp, Vote, Wallet, Scale,
  Briefcase, Eye, Globe, BookOpen, Wifi, Award, AlertTriangle
} from "lucide-react";
import { hexToRgba } from "@/lib/colors";

function fmtRs(n: number | null | undefined): string {
  if (!n || n <= 0) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

export default function CandidateDialogue({
  electionYear,
  candidateData,
  onClose,
}: {
  electionYear: number;
  candidateData: Candidate | null;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  if (!candidateData) return null;

  const {
    name, party, candidate_id, is_winner,
    age, education, self_profession,
    total_assets, total_liabilities, net_worth_rs,
    criminal_cases, serious_cases,
    total_votes, vote_share_pct, rank,
    is_incumbent, is_primary_opp,
    sentiment_score, mention_count, history_json
  } = candidateData;

  const sections = [
    {
      id: "personal",
      title: "Personal Vitals",
      icon: User,
      color: "#3b82f6",
      items: [
        { label: "Age", value: age ? `${age} years` : "Unknown" },
        { label: "Education", value: education || "Not stated" },
        { label: "Profession", value: self_profession || "Not stated" },
      ]
    },
    {
      id: "electoral",
      title: "Electoral Record",
      icon: Vote,
      color: "#8b5cf6",
      items: [
        { label: "Total Votes", value: total_votes?.toLocaleString() || "—" },
        { label: "Vote Share", value: vote_share_pct != null ? `${(vote_share_pct * 100).toFixed(2)}%` : "—" },
        { label: "Rank", value: rank || "—" },
        { label: "Incumbent", value: is_incumbent ? "Yes" : "No" },
        { label: "Primary Opposition", value: is_primary_opp ? "Yes" : "No" },
      ]
    },
    {
      id: "financial",
      title: "Financial Profile",
      icon: Wallet,
      color: "#eab308",
      items: [
        { label: "Declared Assets", value: total_assets || fmtRs(net_worth_rs) || "—" },
        { label: "Declared Liabilities", value: total_liabilities || "—" },
        { label: "Net Worth (Est.)", value: fmtRs(net_worth_rs) },
      ]
    },
    {
      id: "legal",
      title: "Legal & Criminal Record",
      icon: Scale,
      color: (criminal_cases || 0) > 0 ? "#ef4444" : "#22c55e",
      items: [
        { label: "Total Criminal Cases", value: criminal_cases || 0 },
        { label: "Serious IPC Counts", value: serious_cases || 0 },
      ]
    },
    {
      id: "public",
      title: "Public Presence",
      icon: Eye,
      color: "#06b6d4",
      items: [
        { label: "Sentiment Score", value: sentiment_score != null ? sentiment_score.toFixed(2) : "—" },
        { label: "Media Mentions", value: mention_count || "—" },
      ]
    }
  ];

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.72)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 50, padding: "20px",
      }}
    >
      <div style={{
        background: "var(--bg-base)", borderRadius: "14px",
        border: "1px solid var(--border)",
        maxWidth: "960px", width: "100%", maxHeight: "90vh",
        display: "flex", flexDirection: "column",
        boxShadow: "0 30px 60px rgba(0,0,0,0.4)",
      }}>
        {/* ── Header ── */}
        <div style={{
          display: "flex", alignItems: "flex-start", justifyContent: "space-between",
          padding: "22px 24px", borderBottom: "1px solid var(--border)",
          background: "var(--bg-surface)", borderRadius: "14px 14px 0 0",
          position: "sticky", top: 0, zIndex: 10,
        }}>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "14px" }}>
            <div style={{
              width: "48px", height: "48px", borderRadius: "50%",
              background: "linear-gradient(135deg, var(--saffron), #3b82f6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontWeight: 700, fontSize: "20px", flexShrink: 0,
            }}>
              {name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ margin: "0 0 3px 0", fontSize: "18px", fontWeight: 700, color: "var(--text-1)", display: 'flex', alignItems: 'center', gap: '8px' }}>
                {name}
                {is_winner && <Award size={18} style={{ color: "var(--saffron)" }} />}
              </h2>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-3)" }}>
                <span style={{
                  display: "inline-block", padding: "1px 8px", borderRadius: "4px", marginRight: "6px",
                  background: "rgba(249,115,22,0.12)", color: "var(--saffron)", fontWeight: 600, fontSize: "11px",
                }}>{party}</span>
                Candidate ID: {candidate_id} · {electionYear}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", cursor: "pointer",
            padding: "6px", display: "flex", alignItems: "center", justifyContent: "center",
            color: "var(--text-3)", borderRadius: "6px",
          }}>
            <X size={20} />
          </button>
        </div>

        {/* ── Section tabs strip ── */}
        <div style={{
          display: "flex", overflowX: "auto", gap: "2px",
          padding: "8px 16px",
          background: "var(--bg-surface)", borderBottom: "1px solid var(--border)",
        }}>
          {sections.map((s) => (
            <a key={s.id} href={`#section-${s.id}`} style={{
              display: "flex", alignItems: "center", gap: "5px",
              padding: "5px 10px", borderRadius: "6px", whiteSpace: "nowrap",
              fontSize: "11px", fontWeight: 500, color: "var(--text-3)",
              textDecoration: "none", flexShrink: 0,
            }}>
              <s.icon size={11} style={{ color: s.color }} />
              {s.title}
            </a>
          ))}
        </div>

        {/* ── Content ── */}
        <div style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
          {sections.map((section) => (
            <div key={section.id} id={`section-${section.id}`} style={{
              marginBottom: "32px", paddingBottom: "28px",
              borderBottom: "1px solid var(--border)",
            }}>
              {/* Section header */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
                <div style={{
                  width: "32px", height: "32px", borderRadius: "7px",
                  background: hexToRgba(section.color, "10"),
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <section.icon size={15} style={{ color: section.color }} />
                </div>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-1)" }}>
                  {section.title}
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px 28px" }}>
                {section.items.map((item, idx) => (
                  <div key={idx}>
                    <p style={{
                      margin: "0 0 4px 0", fontSize: "11px", fontWeight: 600,
                      color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.5px",
                    }}>
                      {item.label}
                    </p>
                    <p style={{
                      margin: 0, fontSize: "13px", color: "var(--text-1)",
                      fontWeight: 500, lineHeight: 1.6, whiteSpace: "pre-wrap",
                    }}>
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {history_json && (
            <div id="section-history" style={{ marginBottom: "32px" }}>
               <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
                <div style={{
                  width: "32px", height: "32px", borderRadius: "7px",
                  background: hexToRgba("#64748b", "10"),
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Briefcase size={15} style={{ color: "#64748b" }} />
                </div>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-1)" }}>
                  Additional History
                </h3>
              </div>
              <pre style={{
                background: "var(--bg-surface)", padding: "16px", borderRadius: "8px",
                border: "1px solid var(--border)", fontSize: "12px", color: "var(--text-2)",
                overflowX: "auto"
              }}>
                {JSON.stringify(history_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

