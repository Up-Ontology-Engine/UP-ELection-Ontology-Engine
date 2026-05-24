"use client";

import { useEffect } from "react";
import {
  X, User, Users, MapPin, TrendingUp, Vote, Wallet, Scale,
  Briefcase, Eye, ExternalLink
} from "lucide-react";

interface CandidateProfile {
  name: string;
  candidate_id: string;
  party: string;
  ac_name: string;
  election_year: number;
  profile: Record<string, Record<string, string>>;
}

const SECTION_ICONS: Record<string, React.ComponentType<any>> = {
  "1_PersonalVitals": User,
  "2_FamilyEducation": Users,
  "3_ConstituencyData": MapPin,
  "4_PoliticalTrajectory": TrendingUp,
  "5_ElectoralRecord": Vote,
  "6_FinancialProfile": Wallet,
  "7_LegalCriminalRecord": Scale,
  "8_CareerProfession": Briefcase,
  "9_PublicPresencePolicy": Eye,
};

const SECTION_TITLES: Record<string, string> = {
  "1_PersonalVitals": "Personal Vitals",
  "2_FamilyEducation": "Family & Education",
  "3_ConstituencyData": "Constituency Data",
  "4_PoliticalTrajectory": "Political Trajectory",
  "5_ElectoralRecord": "Electoral Record",
  "6_FinancialProfile": "Financial Profile",
  "7_LegalCriminalRecord": "Legal & Criminal Record",
  "8_CareerProfession": "Career & Profession",
  "9_PublicPresencePolicy": "Public Presence & Policy",
};

export default function CandidateDialogue({
  candidateId,
  electionYear,
  candidateData,
  onClose,
}: {
  candidateId: string;
  electionYear: number;
  candidateData: CandidateProfile | null;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  if (!candidateData) {
    return null;
  }

  const { name, party, ac_name, profile } = candidateData;
  const sections = Object.entries(profile).sort(
    ([a], [b]) => parseInt(a.split("_")[0]) - parseInt(b.split("_")[0])
  );

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: "20px",
        overflowY: "auto",
      }}
    >
      <div
        style={{
          background: "var(--bg-base)",
          borderRadius: "12px",
          border: "1px solid var(--border)",
          maxWidth: "900px",
          width: "100%",
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 25px 50px rgba(0, 0, 0, 0.3)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            padding: "24px",
            borderBottom: "1px solid var(--border)",
            background: "var(--bg-surface)",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, var(--saffron), var(--blue))",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "white",
                  fontWeight: "bold",
                  fontSize: "18px",
                }}
              >
                {name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 style={{ margin: "0 0 2px 0", fontSize: "18px", fontWeight: "600", color: "var(--text-1)" }}>
                  {name}
                </h2>
                <p style={{ margin: 0, fontSize: "12px", color: "var(--text-3)" }}>
                  {party} • {ac_name} • {electionYear}
                </p>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-3)",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Sections */}
        <div style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
          {sections.map(([sectionKey, fields]) => {
            const Icon = SECTION_ICONS[sectionKey] || User;
            const title = SECTION_TITLES[sectionKey] || sectionKey;

            return (
              <div
                key={sectionKey}
                style={{
                  marginBottom: "28px",
                  paddingBottom: "24px",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "6px",
                      background: "rgba(249, 115, 22, 0.1)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Icon size={16} style={{ color: "var(--saffron)" }} />
                  </div>
                  <h3
                    style={{
                      margin: 0,
                      fontSize: "14px",
                      fontWeight: "600",
                      color: "var(--text-1)",
                    }}
                  >
                    {title}
                  </h3>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px 24px" }}>
                  {Object.entries(fields).map(([fieldName, fieldValue]) => (
                    <div key={fieldName}>
                      <p
                        style={{
                          margin: "0 0 6px 0",
                          fontSize: "12px",
                          fontWeight: "500",
                          color: "var(--text-3)",
                          textTransform: "uppercase",
                          letterSpacing: "0.5px",
                        }}
                      >
                        {fieldName}
                      </p>
                      <p
                        style={{
                          margin: 0,
                          fontSize: "13px",
                          color: "var(--text-1)",
                          fontWeight: "500",
                          lineHeight: "1.5",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {String(fieldValue).split("\n").map((line, idx) => (
                          <span key={idx}>
                            {line}
                            {idx < String(fieldValue).split("\n").length - 1 && <br />}
                          </span>
                        ))}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border)",
            background: "var(--bg-surface)",
            fontSize: "12px",
            color: "var(--text-4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>Data sourced from MyNeta affidavits & Election Commission records</span>
          <a
            href={`https://www.myneta.info/LokSabha${electionYear}/candidate.php?candidate_id=${candidateId}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              color: "var(--saffron)",
              textDecoration: "none",
              fontSize: "12px",
              fontWeight: "500",
            }}
          >
            View on MyNeta <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
}
