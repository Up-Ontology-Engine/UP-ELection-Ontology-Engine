import { api } from "@/lib/api";
import {
  AlertCircle,
  Award,
  BarChart3,
  Briefcase,
  CheckCircle2,
  GitBranch,
  Network,
  Shield,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

function fmtCr(rs: number | null | undefined) {
  if (rs == null) return "—";
  const cr = rs / 1_00_00_000;
  return cr >= 1 ? `₹${cr.toFixed(2)} Cr` : `₹${(rs / 100000).toFixed(1)} L`;
}

function SentimentBar({ score }: { score: number }) {
  const pct   = Math.min(Math.abs(score) * 100, 100);
  const color = score < -0.02 ? "#cc2200" : score > 0.02 ? "#138808" : "#d97706";
  const label = score < -0.02 ? "Negative" : score > 0.02 ? "Positive" : "Neutral";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs" style={{ color: "var(--text-4)" }}>Digital Sentiment</span>
        <span className="mono text-xs font-bold" style={{ color }}>
          {score > 0 ? "+" : ""}{score.toFixed(3)} ({label})
        </span>
      </div>
      <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

const PARTY_COLORS: Record<string, string> = {
  BJP:  "#FF9933",
  SP:   "#EF0000",
  BSP:  "#0047AB",
  INC:  "#00BFFF",
  IND:  "#6b7280",
};

function partyColor(party: string) {
  return PARTY_COLORS[party.toUpperCase()] ?? "#003380";
}

export default async function DriversPage() {
  const [candidatesR, graphR] = await Promise.allSettled([
    api.candidates(AC_ID),
    api.subgraph("AssemblyConstituency", AC_ID, [], 80),
  ]);

  const candidates = candidatesR.status === "fulfilled" ? candidatesR.value.candidates : [];
  const graph      = graphR.status      === "fulfilled" ? graphR.value : null;

  const nodeTypes = new Map<string, number>();
  graph?.nodes.forEach((n) => nodeTypes.set(n.type, (nodeTypes.get(n.type) ?? 0) + 1));

  const winner   = candidates.find((c) => c.is_winner || c.winner_flag);
  const incumbent = candidates.find((c) => c.is_incumbent);
  const primaryOpp = candidates.find((c) => c.is_primary_opp);

  return (
    <div className="min-h-screen p-5" style={{ background: "var(--bg-base)" }}>

      {/* Page header */}
      <div className="mb-5">
        <p className="text-xs font-semibold" style={{ color: "#003380" }}>Who is driving it?</p>
        <h1 className="mt-1 text-xl font-bold" style={{ color: "var(--text-1)" }}>
          Candidate + Influencer Graph
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-3)" }}>
          Election-filed candidates with affidavit data, vote results, campaign spend, and live digital sentiment.
        </p>
      </div>

      {/* Summary strip */}
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "Total Candidates", value: fmt(candidates.length),                         icon: Users,    color: "#003380" },
          { label: "Incumbent",        value: incumbent?.name ?? "—",                          icon: Shield,   color: "#d97706" },
          { label: "Primary Opp.",     value: primaryOpp?.name ?? "—",                         icon: TrendingDown, color: "#cc2200" },
          { label: "Graph Nodes",      value: fmt(graph?.nodes.length),                        icon: Network,  color: "#6d28d9" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded p-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold" style={{ color: "var(--text-4)" }}>{label}</span>
              <Icon size={13} style={{ color }} />
            </div>
            <p className="text-sm font-bold truncate" style={{ color: "var(--text-1)" }}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">

        {/* ── Candidate cards ── */}
        <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
            <Users size={15} style={{ color: "#003380" }} />
            <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Candidate Profiles</h2>
            <span className="ml-auto mono text-xs font-bold px-2 py-0.5 rounded"
              style={{ background: "#eef3fb", color: "#003380" }}>
              {candidates.length}
            </span>
          </div>

          {candidates.length === 0 ? (
            <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>
              No candidate records. Run the ETL to ingest Form-20 affidavit data.
            </p>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--border)" }}>
              {candidates.map((c) => {
                const isWinner = c.is_winner || c.winner_flag;
                const pc = partyColor(c.party);
                return (
                  <div key={c.candidate_id} className="p-4" style={{ borderLeft: `3px solid ${pc}` }}>
                    {/* Top row */}
                    <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-0.5">
                          <span className="text-base font-bold" style={{ color: "var(--text-1)" }}>{c.name}</span>
                          {isWinner && (
                            <span className="inline-flex items-center gap-1 text-xs font-bold px-1.5 py-0.5 rounded"
                              style={{ background: "#eef7ef", color: "#138808", border: "1px solid #b7dfbc" }}>
                              <Award size={10} /> Winner
                            </span>
                          )}
                          {c.is_incumbent && (
                            <span className="text-xs font-bold px-1.5 py-0.5 rounded"
                              style={{ background: "#fff8e8", color: "#92400e", border: "1px solid #fcd9a0" }}>
                              Incumbent
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="mono text-xs font-bold px-2 py-0.5 rounded"
                            style={{ background: `${pc}18`, color: pc, border: `1px solid ${pc}40` }}>
                            {c.party}
                          </span>
                          {c.self_profession && (
                            <span className="text-xs" style={{ color: "var(--text-4)" }}>
                              <Briefcase size={10} className="inline mr-1" />{c.self_profession}
                            </span>
                          )}
                          {c.age && (
                            <span className="text-xs" style={{ color: "var(--text-4)" }}>Age {c.age}</span>
                          )}
                        </div>
                      </div>

                      {/* Vote result */}
                      <div className="text-right">
                        <p className="mono text-lg font-bold" style={{ color: "var(--text-1)" }}>
                          {fmt(c.total_votes ?? c.votes)}
                        </p>
                        <p className="text-xs" style={{ color: "var(--text-4)" }}>
                          {c.vote_share_pct?.toFixed(1) ?? c.vote_share?.toFixed(1) ?? "—"}% vote share
                          {c.rank != null && ` · Rank ${c.rank}`}
                        </p>
                        {c.victory_margin_votes != null && (
                          <p className="text-xs font-semibold" style={{ color: "#138808" }}>
                            +{fmt(c.victory_margin_votes)} margin
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Stats grid */}
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-3 sm:grid-cols-4">
                      <div>
                        <p className="text-xs" style={{ color: "var(--text-4)" }}>Net Worth</p>
                        <p className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>{fmtCr(c.net_worth_rs)}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: "var(--text-4)" }}>Total Assets</p>
                        <p className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>{fmtCr(c.total_assets)}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: "var(--text-4)" }}>Liabilities</p>
                        <p className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>{fmtCr(c.total_liabilities)}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: "var(--text-4)" }}>Campaign Spend</p>
                        <p className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>{fmtCr(c.total_election_expense_rs)}</p>
                      </div>
                    </div>

                    {/* Criminal cases */}
                    {c.criminal_cases != null && (
                      <div className="flex items-center gap-2 mb-3 text-xs">
                        {c.criminal_cases === 0 ? (
                          <span className="flex items-center gap-1" style={{ color: "#138808" }}>
                            <CheckCircle2 size={12} /> No criminal cases declared
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 font-semibold" style={{ color: "#cc2200" }}>
                            <AlertCircle size={12} />
                            {c.criminal_cases} criminal case{c.criminal_cases > 1 ? "s" : ""}
                            {c.serious_cases ? ` (${c.serious_cases} serious)` : ""}
                          </span>
                        )}
                        {c.source_affidavit_url && (
                          <a href={c.source_affidavit_url} target="_blank" rel="noopener noreferrer"
                            className="ml-auto underline" style={{ color: "#003380" }}>
                            Affidavit ↗
                          </a>
                        )}
                      </div>
                    )}

                    {/* Sentiment bar */}
                    <SentimentBar score={c.sentiment_score} />
                    {c.mention_count > 0 && (
                      <p className="text-xs mt-1" style={{ color: "var(--text-4)" }}>
                        {fmt(c.mention_count)} YouTube mentions (last 30 days)
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Right: graph coverage ── */}
        <div className="flex flex-col gap-4">
          <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <GitBranch size={15} style={{ color: "#003380" }} />
              <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Neo4j Graph Coverage</h2>
            </div>
            {nodeTypes.size === 0 ? (
              <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>
                Graph not connected. Check Neo4j pipeline status.
              </p>
            ) : (
              <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {Array.from(nodeTypes.entries())
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => {
                    const maxNodes = Math.max(...Array.from(nodeTypes.values()));
                    const pct = (count / maxNodes) * 100;
                    return (
                      <div key={type} className="px-4 py-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            {type.toLowerCase().includes("booth")
                              ? <Users size={12} style={{ color: "#138808" }} />
                              : type.toLowerCase().includes("candidate")
                                ? <Shield size={12} style={{ color: "#d97706" }} />
                                : <Network size={12} style={{ color: "#003380" }} />}
                            <span className="text-xs font-semibold" style={{ color: "var(--text-2)" }}>{type}</span>
                          </div>
                          <span className="mono text-sm font-bold" style={{ color: "var(--text-1)" }}>{fmt(count)}</span>
                        </div>
                        <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
                          <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: "#003380" }} />
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </section>

          {/* Edge summary */}
          {graph && graph.edges.length > 0 && (
            <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
                <BarChart3 size={15} style={{ color: "#6d28d9" }} />
                <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Graph Relationships</h2>
              </div>
              {(() => {
                const edgeTypes = new Map<string, number>();
                graph.edges.forEach((e) => edgeTypes.set(e.type, (edgeTypes.get(e.type) ?? 0) + 1));
                return (
                  <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {Array.from(edgeTypes.entries())
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <div key={type} className="px-4 py-2.5 flex items-center justify-between">
                          <span className="text-xs font-mono" style={{ color: "var(--text-3)" }}>
                            {type.replace(/_/g, " ")}
                          </span>
                          <span className="mono text-xs font-bold" style={{ color: "#6d28d9" }}>{count}</span>
                        </div>
                      ))}
                  </div>
                );
              })()}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
