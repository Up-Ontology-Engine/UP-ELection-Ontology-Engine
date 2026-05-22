import Link from "next/link";
import Image from "next/image";
import {
  Activity,
  ArrowRight,
  Bot,
  Database,
  GitBranch,
  Landmark,
  Map,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined) {
  if (n == null) return "-";
  return n.toLocaleString("en-IN");
}

function IndianEmblemMark() {
  return (
    <Image
      src="/indian-national-emblem.png"
      alt="Indian national emblem"
      width={112}
      height={128}
      className="h-32 w-28 flex-none rounded-sm object-cover"
      style={{ border: "2px solid #003380", background: "#ffffff" }}
    />
  );
}

export default async function LandingPage() {
  const [boothsR, intelR, qualityR] = await Promise.allSettled([
    api.booths(AC_ID),
    api.intelSummary(AC_ID),
    api.quality(AC_ID),
  ]);

  const booths = boothsR.status === "fulfilled" ? boothsR.value.booths : [];
  const intel = intelR.status === "fulfilled" ? intelR.value : null;
  const quality = qualityR.status === "fulfilled" ? qualityR.value : null;
  const voterStats = intel?.voter_stats;
  const totalBooths = voterStats?.total ?? booths.length;
  const totalVoters = voterStats?.total_voters ?? booths.reduce((sum, booth) => sum + (booth.total_voters ?? 0), 0);
  const issueCount = intel?.issues?.length ?? 0;
  const youtubeCount = intel?.youtube_count ?? 0;
  const qualityScore = quality?.avg_confidence != null ? `${Math.round(quality.avg_confidence * 100)}%` : "Pending";
  const lastUpdated = new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const modules = [
    {
      href: "/dashboard",
      title: "Overview Dashboard",
      question: "What is happening?",
      body: "Signals, movement, risk alerts, booth volatility, and weekly leadership summary.",
      icon: Activity,
    },
    {
      href: "/pain-points",
      title: "Pain Point Engine",
      question: "Why is it happening?",
      body: "Booth-wise issues, severity, confidence, source count, and evidence trails.",
      icon: ShieldCheck,
    },
    {
      href: "/heatmap",
      title: "Heatmap + Booth Explorer",
      question: "Where is it happening?",
      body: "Geographic clusters by issue heat, turnout risk, scheme gaps, and booth lean.",
      icon: Map,
    },
    {
      href: "/drivers",
      title: "Candidate + Influencer Graph",
      question: "Who is driving it?",
      body: "Candidates, parties, local influencers, issue amplifiers, and graph relationships.",
      icon: GitBranch,
    },
    {
      href: "/actions",
      title: "Action Recommendation Engine",
      question: "What should we do?",
      body: "Prioritized field actions by booth or cluster with owners, timelines, and rationale.",
      icon: Bot,
    },
    {
      href: "/infrastructure",
      title: "Data Infrastructure",
      question: "Is the system healthy?",
      body: "PostgreSQL, Neo4j, ETL, ingestion coverage, and data pipeline health.",
      icon: Database,
    },
  ];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)", color: "var(--text-1)" }}>
      <section className="px-6 py-8 lg:px-10" style={{ background: "#ffffff", borderBottom: "1px solid var(--border)" }}>
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-semibold">
              <span className="rounded-sm px-2 py-1" style={{ background: "#fff4e8", border: "1px solid #ffd4ad", color: "#9a4b00" }}>
                <span lang="hi">उत्तर प्रदेश विधान सभा</span>
              </span>
              <span className="rounded-sm px-2 py-1" style={{ background: "#eef7ef", border: "1px solid #b7dfbc", color: "#0f6b18" }}>
                AC-322 Gorakhpur Urban
              </span>
            </div>

            <p className="mb-2 text-sm font-semibold" style={{ color: "#003380" }} lang="hi">
              गोरखपुर शहरी निर्वाचन विश्लेषण प्रणाली
            </p>
            <h1 className="max-w-4xl text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl" style={{ color: "#002060" }}>
              Booth-Level Political Intelligence
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 sm:text-base" style={{ color: "#4a6280" }}>
              A five-question decision system for understanding what is happening, why it is happening,
              where it is concentrated, who is driving it, and what action should follow.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/dashboard" className="inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold" style={{ background: "#003380", color: "#ffffff" }}>
                Open Overview <ArrowRight size={16} />
              </Link>
              <Link href="/booths" className="inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold" style={{ background: "#ffffff", color: "#003380", border: "1px solid #c0cfe0" }}>
                <Search size={16} /> Search Booths
              </Link>
            </div>
          </div>

          <div className="overflow-hidden rounded-md" style={{ border: "1px solid #c0cfe0", background: "#f8fafc", boxShadow: "0 10px 30px rgba(0,32,96,0.08)" }}>
            <div className="h-2" style={{ background: "linear-gradient(90deg, #FF9933 0% 33.33%, #ffffff 33.33% 66.66%, #138808 66.66% 100%)" }} />
            <div className="flex items-center gap-5 p-6">
              <IndianEmblemMark />
              <div>
                <p className="text-xs font-bold uppercase tracking-wide" style={{ color: "#003380" }}>
                  Gorakhpur Urban AC-322
                </p>
                <p className="mt-1 text-lg font-bold" style={{ color: "#002060" }} lang="hi">
                  बूथ-स्तरीय राजनीतिक बुद्धिमत्ता
                </p>
                <p className="mt-3 text-sm leading-6" style={{ color: "#4a6280" }}>
                  Data-backed booth intelligence
                  <br />
                  Last Updated: <strong>{lastUpdated}</strong>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-6 lg:px-10">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-3 md:grid-cols-5">
          {[
            { label: "Booths", value: fmt(totalBooths), icon: Landmark },
            { label: "Registered Voters", value: fmt(totalVoters), icon: Users },
            { label: "Issue Signals", value: fmt(issueCount), icon: Activity },
            { label: "Videos Analysed", value: fmt(youtubeCount), icon: Bot },
            { label: "Data Quality", value: qualityScore, icon: ShieldCheck },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-semibold" style={{ color: "var(--text-4)" }}>{label}</span>
                <Icon size={15} style={{ color: "#003380" }} />
              </div>
              <p className="font-bold" style={{ color: "var(--text-1)", fontSize: 22 }}>{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="px-6 pb-8 lg:px-10">
        <div className="mx-auto max-w-7xl">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Leadership Question Pages</p>
              <p className="text-xs" style={{ color: "var(--text-4)" }}>
                The real product is organized around five decisions, not technical modules.
              </p>
            </div>
            <Link href="/sitemap" className="text-xs font-semibold" style={{ color: "#003380" }}>
              View sitemap
            </Link>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {modules.map(({ href, title, question, body, icon: Icon }) => (
              <Link key={href} href={href} className="group rounded p-4 transition-colors" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", textDecoration: "none" }}>
                <div className="mb-4 flex items-center justify-between">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded" style={{ background: "#eef3fb", color: "#003380" }}>
                    <Icon size={18} />
                  </span>
                  <ArrowRight size={16} style={{ color: "var(--text-4)" }} />
                </div>
                <p className="text-xs font-semibold" style={{ color: "#003380" }}>{question}</p>
                <p className="mt-1 font-bold" style={{ color: "var(--text-1)" }}>{title}</p>
                <p className="mt-3 text-sm leading-6" style={{ color: "var(--text-3)" }}>{body}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
