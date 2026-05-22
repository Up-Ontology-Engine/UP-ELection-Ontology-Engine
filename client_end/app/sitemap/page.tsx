import Link from "next/link";
import { ArrowRight, Bot, Database, GitBranch, Home, Map, Network, Users } from "lucide-react";

const ROUTES = [
  { href: "/", label: "Home", hi: "मुख्य पृष्ठ", icon: Home },
  { href: "/dashboard", label: "Overview Dashboard", hi: "अवलोकन डैशबोर्ड", icon: Network },
  { href: "/pain-points", label: "Pain Point Engine", hi: "समस्या इंजन", icon: Network },
  { href: "/drivers", label: "Candidate + Influencer Graph", hi: "प्रभावक ग्राफ", icon: GitBranch },
  { href: "/actions", label: "Action Recommendation Engine", hi: "कार्य योजना", icon: Bot },
  { href: "/booths", label: "Booth Intelligence", hi: "बूथ बुद्धिमत्ता", icon: Users },
  { href: "/heatmap", label: "Constituency Heatmap", hi: "क्षेत्र हीटमैप", icon: Map },
  { href: "/graph", label: "Knowledge Graph", hi: "ज्ञान ग्राफ", icon: GitBranch },
  { href: "/reasoning", label: "AI Reasoning", hi: "AI तर्कशक्ति", icon: Bot },
  { href: "/demographics", label: "Demographics", hi: "जनसांख्यिकी", icon: Users },
  { href: "/ontology", label: "Ontology Layer", hi: "ऑन्टोलॉजी", icon: Network },
  { href: "/infrastructure", label: "Data Infrastructure", hi: "डेटा अवसंरचना", icon: Database },
];

export default function SitemapPage() {
  return (
    <div className="min-h-screen px-6 py-8 lg:px-10" style={{ background: "var(--bg-base)" }}>
      <div className="mx-auto max-w-5xl">
        <div className="mb-6">
          <p className="text-sm font-semibold" style={{ color: "#003380" }} lang="hi">
            साइट मानचित्र
          </p>
          <h1 className="mt-1 text-2xl font-bold" style={{ color: "var(--text-1)" }}>
            Sitemap
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6" style={{ color: "var(--text-3)" }}>
            Quick access to the main sections of the Gorakhpur Urban Election Intelligence System.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {ROUTES.map(({ href, label, hi, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-4 rounded p-4"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)", textDecoration: "none" }}
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded" style={{ background: "#eef3fb", color: "#003380" }}>
                <Icon size={18} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold" style={{ color: "var(--text-1)" }}>{label}</span>
                <span className="block text-xs" style={{ color: "var(--text-4)" }} lang="hi">{hi}</span>
              </span>
              <ArrowRight size={16} style={{ color: "var(--text-4)" }} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
