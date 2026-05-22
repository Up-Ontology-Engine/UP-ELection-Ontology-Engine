import Link from "next/link";

const QUICK_LINKS = [
  { href: "/",              label: "Home",                 labelHi: "मुख्य पृष्ठ" },
  { href: "/dashboard",     label: "Command Center",       labelHi: "कमांड सेंटर" },
  { href: "/booths",        label: "Booth Intelligence",   labelHi: "बूथ बुद्धिमत्ता" },
  { href: "/heatmap",       label: "Constituency Heatmap", labelHi: "क्षेत्र हीटमैप" },
  { href: "/graph",         label: "Knowledge Graph",      labelHi: "ज्ञान ग्राफ" },
  { href: "/reasoning",     label: "AI Reasoning",         labelHi: "AI तर्कशक्ति" },
  { href: "/demographics",  label: "Demographics",         labelHi: "जनसांख्यिकी" },
];

const HELP_LINKS = [
  { href: "/sitemap", label: "Sitemap" },
];

const LEGAL_LINKS = [
  { href: "/infrastructure", label: "Data Infrastructure" },
  { href: "/ontology", label: "Ontology Layer" },
];

const linkStyle: React.CSSProperties = {
  fontSize: 11.5,
  color: "rgba(255,255,255,0.7)",
  textDecoration: "none",
  lineHeight: "22px",
  display: "block",
};

export default function GovFooter() {
  const year = new Date().getFullYear();
  const lastUpdated = new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <footer style={{ background: "#002060", color: "#ffffff", marginTop: "auto" }} role="contentinfo">
      {/* Tricolor top bar */}
      <div style={{
        height: 5,
        background: "linear-gradient(90deg, #FF9933 0% 33.3%, #ffffff 33.3% 66.6%, #138808 66.6% 100%)",
      }} />

      {/* Main footer content */}
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "28px 24px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 32, marginBottom: 24 }}>

          {/* Column 1: About */}
          <div>
            <h3 style={{
              fontSize: 12,
              fontWeight: 700,
              color: "#FF9933",
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}>
              About This System
            </h3>
            <p style={{ fontSize: 11.5, color: "rgba(255,255,255,0.7)", lineHeight: 1.75, margin: 0 }}>
              Booth-Level Political Intelligence presents data-backed booth analytics
              for Gorakhpur Urban AC-322 using this project&apos;s PostgreSQL and Neo4j data.
            </p>
            <p style={{ fontSize: 10.5, color: "rgba(255,255,255,0.45)", marginTop: 10, lineHeight: 1.6 }} lang="hi">
              इस प्रणाली में केवल उपलब्ध परियोजना डेटा से निकले तथ्य और संकेत दिखाए जाते हैं।
            </p>
          </div>

          {/* Column 2: Quick Links */}
          <div>
            <h3 style={{ fontSize: 12, fontWeight: 700, color: "#FF9933", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Quick Links
            </h3>
            {QUICK_LINKS.map(({ href, label, labelHi }) => (
              <Link key={href} href={href} style={linkStyle}>
                <span style={{ color: "rgba(255,153,51,0.6)", marginRight: 6 }}>›</span>
                {label}
                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", marginLeft: 6 }} lang="hi">
                  {labelHi}
                </span>
              </Link>
            ))}
          </div>

          {/* Column 3: Help & Support */}
          <div>
            <h3 style={{ fontSize: 12, fontWeight: 700, color: "#FF9933", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              System Links
            </h3>
            {HELP_LINKS.map(({ href, label }) => (
              <a key={label} href={href} style={linkStyle}>
                <span style={{ color: "rgba(255,153,51,0.6)", marginRight: 6 }}>›</span>
                {label}
              </a>
            ))}
          </div>

          {/* Column 4: Policies */}
          <div>
            <h3 style={{ fontSize: 12, fontWeight: 700, color: "#FF9933", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Data &amp; Model
            </h3>
            {LEGAL_LINKS.map(({ href, label }) => (
              <a key={label} href={href} style={linkStyle}>
                <span style={{ color: "rgba(255,153,51,0.6)", marginRight: 6 }}>›</span>
                {label}
              </a>
            ))}
          </div>
        </div>

        {/* Bottom strip */}
        <div style={{
          borderTop: "1px solid rgba(255,255,255,0.15)",
          paddingTop: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)" }}>
            © {year} Booth-Level Political Intelligence.
            <span style={{ margin: "0 10px", color: "rgba(255,255,255,0.25)" }}>|</span>
            Last Updated:{" "}
            <span style={{ color: "rgba(255,255,255,0.75)", fontWeight: 600 }}>{lastUpdated}</span>
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)" }}>
            Ownership, hosting, and authority claims are intentionally not shown without project proof.
          </div>
        </div>
      </div>
    </footer>
  );
}
