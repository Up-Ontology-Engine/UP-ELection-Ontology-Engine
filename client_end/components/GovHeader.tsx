import Link from "next/link";
import Image from "next/image";

function IndianEmblem({ size = 58 }: { size?: number }) {
  return (
    <div
      aria-label="Indian national emblem"
      role="img"
      style={{
        width: size,
        height: size,
        borderRadius: 4,
        border: "2px solid #003380",
        background: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 1px 4px rgba(0,32,96,0.16)",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      <Image
        src="/indian-national-emblem.png"
        alt=""
        width={size}
        height={size}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
    </div>
  );
}

export default function GovHeader() {
  return (
    <header
      style={{
        position: "fixed",
        top: 36,
        left: 0,
        right: 0,
        height: 80,
        background: "#ffffff",
        borderBottom: "2px solid #003380",
        zIndex: 60,
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
        boxShadow: "0 2px 10px rgba(0,48,128,0.10)",
      }}
      aria-label="Site header"
    >
      {/* Tricolor bar at top of header */}
      <div style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 5,
        background: "linear-gradient(90deg, #FF9933 0% 33.3%, #ffffff 33.3% 66.6%, #138808 66.6% 100%)",
        borderBottom: "1px solid #c0cfe0",
      }} />

      {/* National emblem */}
      <Link href="/" aria-label="Go to homepage" style={{ textDecoration: "none", marginRight: 12, flexShrink: 0 }}>
        <IndianEmblem size={58} />
      </Link>

      {/* Vertical divider */}
      <div style={{ width: 1, height: 52, background: "#c0cfe0", marginRight: 20, marginLeft: 4, flexShrink: 0 }} />

      {/* Site identity */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 10,
          color: "#003380",
          fontWeight: 600,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          marginBottom: 3,
          opacity: 0.8,
        }}>
          Gorakhpur Urban AC-322
        </div>
        <div style={{ fontSize: 19, color: "#002060", fontWeight: 800, lineHeight: 1.15 }}>
          Booth-Level Political Intelligence
        </div>
        <div style={{ fontSize: 11.5, color: "#4a6280", marginTop: 2, lineHeight: 1.2 }}>
          Gorakhpur Urban Election Ontology Engine
          <span style={{ color: "#c0cfe0", margin: "0 6px" }}>·</span>
          <span style={{ color: "#003380", fontWeight: 600 }}>Data-backed booth intelligence</span>
        </div>
      </div>

      {/* Right: data provenance note */}
      <div style={{ flexShrink: 0, textAlign: "right", marginLeft: 24 }}>
        <div style={{
          fontSize: 9,
          color: "#7890a8",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: 2,
          fontWeight: 600,
        }}>
          Data Status
        </div>
        <div style={{
          fontSize: 13,
          fontWeight: 800,
          color: "#003380",
          fontFamily: "monospace",
          letterSpacing: "0.08em",
          lineHeight: 1,
        }}>
          VERIFIED SOURCES ONLY
        </div>
        <div style={{ fontSize: 9, color: "#138808", fontWeight: 700, marginTop: 2, letterSpacing: "0.04em" }}>
          No assumed ownership claims
        </div>
      </div>
    </header>
  );
}
