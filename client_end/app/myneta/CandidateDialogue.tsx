"use client";

import { useEffect } from "react";
import {
  X, User, Users, MapPin, TrendingUp, Vote, Wallet, Scale,
  Briefcase, Eye, ExternalLink, Globe, BookOpen, Wifi, WifiOff,
} from "lucide-react";

interface IconProps extends React.SVGProps<SVGSVGElement> {
  size?: number;
}

const Twitter = ({ size = 24, ...props }: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z" />
  </svg>
);

const Facebook = ({ size = 24, ...props }: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
  </svg>
);

const Instagram = ({ size = 24, ...props }: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
  </svg>
);

const Youtube = ({ size = 24, ...props }: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z" />
    <polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" />
  </svg>
);

interface CandidateProfile {
  name: string;
  candidate_id: string;
  party: string;
  ac_name: string;
  election_year: number;
  profile: Record<string, Record<string, string>>;
}

const SECTION_ICONS: Record<string, React.ComponentType<any>> = {
  "1_PersonalVitals":      User,
  "2_FamilyEducation":     Users,
  "3_ConstituencyData":    MapPin,
  "4_PoliticalTrajectory": TrendingUp,
  "5_ElectoralRecord":     Vote,
  "6_FinancialProfile":    Wallet,
  "7_LegalCriminalRecord": Scale,
  "8_CareerProfession":    Briefcase,
  "9_PublicPresencePolicy":Eye,
  "10_DigitalPresence":    Wifi,
};

const SECTION_TITLES: Record<string, string> = {
  "1_PersonalVitals":      "Personal Vitals",
  "2_FamilyEducation":     "Family & Education",
  "3_ConstituencyData":    "Constituency Data",
  "4_PoliticalTrajectory": "Political Trajectory",
  "5_ElectoralRecord":     "Electoral Record",
  "6_FinancialProfile":    "Financial Profile",
  "7_LegalCriminalRecord": "Legal & Criminal Record",
  "8_CareerProfession":    "Career & Profession",
  "9_PublicPresencePolicy":"Public Presence & Policy",
  "10_DigitalPresence":    "Digital Presence & Social Media",
};

// ── Social-platform metadata ─────────────────────────────────────────────────
const PLATFORM_META: Record<string, { icon: React.ComponentType<any>; color: string; label: string }> = {
  "Twitter/X Handle":    { icon: Twitter,   color: "#1DA1F2", label: "X / Twitter" },
  "Facebook":            { icon: Facebook,  color: "#1877F2", label: "Facebook" },
  "Instagram":           { icon: Instagram, color: "#E1306C", label: "Instagram" },
  "YouTube":             { icon: Youtube,   color: "#FF0000", label: "YouTube" },
  "Website":             { icon: Globe,     color: "#f97316", label: "Website" },
  "Wikipedia":           { icon: BookOpen,  color: "#94a3b8", label: "Wikipedia" },
};

const FOLLOWER_KEYS: Record<string, string> = {
  "Twitter/X Handle":  "Twitter/X Followers",
  "Facebook":          "Facebook Followers",
  "Instagram":         "Instagram Followers",
  "YouTube":           "YouTube Subscribers",
};

function DigitalPresenceSection({ fields }: { fields: Record<string, string> }) {
  const totalReach = fields["Total Digital Reach"] || fields["Digital Footprint"] || "";
  const footprint  = fields["Digital Footprint"]   || "";

  const platforms = Object.entries(PLATFORM_META)
    .map(([key, meta]) => ({
      key,
      meta,
      handle:    fields[key]            || "",
      followers: fields[FOLLOWER_KEYS[key] ?? ""] || "",
    }))
    .filter((p) => p.handle && p.handle !== "Not found" && p.handle !== "Not publicly available");

  const noPlatforms = platforms.length === 0;

  return (
    <div>
      {/* Platform cards */}
      {noPlatforms ? (
        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          padding: "16px", borderRadius: "8px",
          background: "var(--bg-surface)", border: "1px solid var(--border)",
          color: "var(--text-3)", fontSize: "13px",
        }}>
          <WifiOff size={16} />
          <span>No public social media presence found for this candidate.</span>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "12px", marginBottom: "16px" }}>
          {platforms.map(({ key, meta, handle, followers }) => {
            const Icon = meta.icon;
            const isUrl = handle.startsWith("http") || handle.startsWith("@") === false && handle.includes(".");
            return (
              <div key={key} style={{
                borderRadius: "10px", padding: "14px",
                background: "var(--bg-surface)",
                border: `1px solid ${meta.color}30`,
                boxShadow: `0 0 12px ${meta.color}10`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                  <div style={{
                    width: "30px", height: "30px", borderRadius: "6px",
                    background: `${meta.color}18`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Icon size={15} style={{ color: meta.color }} />
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    {meta.label}
                  </span>
                </div>
                <p style={{ margin: "0 0 4px 0", fontSize: "13px", fontWeight: 600, color: meta.color, wordBreak: "break-all" }}>
                  {isUrl ? (
                    <a href={handle.startsWith("http") ? handle : `https://${handle}`}
                      target="_blank" rel="noopener noreferrer"
                      style={{ color: meta.color, textDecoration: "none" }}>
                      {handle}
                    </a>
                  ) : handle}
                </p>
                {followers && followers !== "Not publicly available" && (
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-4)", fontFamily: "monospace" }}>
                    {followers} followers
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Digital reach summary */}
      {(totalReach || footprint) && (
        <div style={{
          padding: "12px 14px", borderRadius: "8px",
          background: "rgba(249,115,22,0.05)",
          border: "1px solid rgba(249,115,22,0.2)",
        }}>
          <p style={{ margin: "0 0 2px", fontSize: "10px", fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Digital Reach Summary
          </p>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--text-1)", lineHeight: 1.5 }}>
            {totalReach || footprint}
          </p>
        </div>
      )}

      {/* Other fields not already rendered */}
      {Object.entries(fields)
        .filter(([k]) =>
          !Object.keys(PLATFORM_META).includes(k) &&
          !Object.values(FOLLOWER_KEYS).includes(k) &&
          k !== "Total Digital Reach" && k !== "Digital Footprint"
        )
        .map(([k, v]) => (
          <div key={k} style={{ marginTop: "10px" }}>
            <p style={{ margin: "0 0 3px", fontSize: "11px", fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.5px" }}>{k}</p>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--text-1)" }}>{v}</p>
          </div>
        ))}
    </div>
  );
}

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

  if (!candidateData) return null;

  const { name, party, ac_name, profile } = candidateData;
  const sections = Object.entries(profile).sort(
    ([a], [b]) => parseInt(a.split("_")[0]) - parseInt(b.split("_")[0])
  );

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
              <h2 style={{ margin: "0 0 3px 0", fontSize: "18px", fontWeight: 700, color: "var(--text-1)" }}>
                {name}
              </h2>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-3)" }}>
                <span style={{
                  display: "inline-block", padding: "1px 8px", borderRadius: "4px", marginRight: "6px",
                  background: "rgba(249,115,22,0.12)", color: "var(--saffron)", fontWeight: 600, fontSize: "11px",
                }}>{party}</span>
                {ac_name} · {electionYear}
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
          {sections.map(([sectionKey]) => {
            const Icon = SECTION_ICONS[sectionKey] || User;
            const title = SECTION_TITLES[sectionKey] || sectionKey;
            const isDigital = sectionKey === "10_DigitalPresence";
            return (
              <a key={sectionKey} href={`#section-${sectionKey}`} style={{
                display: "flex", alignItems: "center", gap: "5px",
                padding: "5px 10px", borderRadius: "6px", whiteSpace: "nowrap",
                fontSize: "11px", fontWeight: 500, color: isDigital ? "#1DA1F2" : "var(--text-3)",
                background: isDigital ? "rgba(29,161,242,0.08)" : "transparent",
                textDecoration: "none", flexShrink: 0,
              }}>
                <Icon size={11} />
                {title}
              </a>
            );
          })}
        </div>

        {/* ── Content ── */}
        <div style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
          {sections.map(([sectionKey, fields]) => {
            const Icon = SECTION_ICONS[sectionKey] || User;
            const title = SECTION_TITLES[sectionKey] || sectionKey;
            const isDigital = sectionKey === "10_DigitalPresence";
            const isLegal   = sectionKey === "7_LegalCriminalRecord";

            const hasCriminal = isLegal &&
              Object.values(fields).some((v) => {
                const n = parseInt(String(v));
                return !isNaN(n) && n > 0;
              });

            return (
              <div key={sectionKey} id={`section-${sectionKey}`} style={{
                marginBottom: "32px", paddingBottom: "28px",
                borderBottom: "1px solid var(--border)",
              }}>
                {/* Section header */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
                  <div style={{
                    width: "32px", height: "32px", borderRadius: "7px",
                    background: isDigital ? "rgba(29,161,242,0.1)"
                              : hasCriminal ? "rgba(239,68,68,0.1)"
                              : "rgba(249,115,22,0.1)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Icon size={15} style={{
                      color: isDigital ? "#1DA1F2"
                           : hasCriminal ? "#ef4444"
                           : "var(--saffron)"
                    }} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-1)" }}>
                    {title}
                  </h3>
                  {hasCriminal && (
                    <span style={{
                      fontSize: "10px", padding: "2px 8px", borderRadius: "4px", fontWeight: 600,
                      background: "rgba(239,68,68,0.1)", color: "#ef4444",
                      border: "1px solid rgba(239,68,68,0.25)", marginLeft: "auto",
                    }}>
                      CASES DECLARED
                    </span>
                  )}
                </div>

                {/* Digital section: custom layout */}
                {isDigital ? (
                  <DigitalPresenceSection fields={fields} />
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px 28px" }}>
                    {Object.entries(fields).map(([fieldName, fieldValue]) => {
                      const isLong = String(fieldValue).length > 80;
                      return (
                        <div key={fieldName} style={isLong ? { gridColumn: "1 / -1" } : {}}>
                          <p style={{
                            margin: "0 0 4px 0", fontSize: "11px", fontWeight: 600,
                            color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.5px",
                          }}>
                            {fieldName}
                          </p>
                          <p style={{
                            margin: 0, fontSize: "13px", color: "var(--text-1)",
                            fontWeight: 500, lineHeight: 1.6, whiteSpace: "pre-wrap",
                          }}>
                            {String(fieldValue).split("\n").map((line, idx, arr) => (
                              <span key={idx}>{line}{idx < arr.length - 1 && <br />}</span>
                            ))}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
