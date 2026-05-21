import { api } from "@/lib/api";
import Link from "next/link";
import LeanBadge from "@/components/LeanBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import SectionHeader from "@/components/SectionHeader";
import BoothDetailCharts from "./BoothDetailCharts";
import {
  ArrowLeft, Users, Shield, AlertTriangle, BookOpen,
  TrendingUp, ChevronRight, Radio, Eye, Zap, Database
} from "lucide-react";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

interface Props { params: Promise<{ id: string }> }

export default async function BoothDetailPage({ params }: Props) {
  const { id } = await params;
  let summary: Awaited<ReturnType<typeof api.boothSummary>> | null = null;
  try { summary = await api.boothSummary(id); } catch {}

  if (!summary) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center" style={{ background: "#060b14" }}>
        <p className="text-white mb-2">Booth not found: <span className="mono">{id}</span></p>
        <Link href="/booths" className="text-xs hover:underline" style={{ color: "#f97316" }}>← Back</Link>
      </div>
    );
  }

  const femalePct = summary.total_voters && summary.female_voters
    ? ((summary.female_voters / summary.total_voters) * 100).toFixed(1)
    : null;

  return (
    <div className="p-5 min-h-screen" style={{ background: "#060b14" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 mono text-xs mb-4" style={{ color: "#4d6480" }}>
        <Link href="/booths" className="hover:text-orange-400 transition-colors flex items-center gap-1">
          <ArrowLeft size={10} /> Booth Intelligence
        </Link>
        <ChevronRight size={10} />
        <span style={{ color: "#f0f4fa" }}>Booth {summary.booth_number}</span>
        <ChevronRight size={10} />
        <span className="truncate max-w-48" style={{ color: "#8ba0bc" }}>{summary.name}</span>
      </div>

      {/* Header bar */}
      <div className="card p-4 mb-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: "linear-gradient(90deg, #f97316, #3b82f6, transparent)" }} />
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <span className="mono text-xs px-2 py-0.5 rounded"
                style={{ background: "#0b1220", color: "#f97316", border: "1px solid #f9731630" }}>
                B-{String(summary.booth_number).padStart(3, "0")}
              </span>
              <h1 className="font-bold text-white" style={{ fontSize: 16 }}>{summary.name}</h1>
            </div>
            <p className="text-xs mono" style={{ color: "#4d6480" }}>
              {summary.ac_name} · AC-322 · ID: {id}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <LeanBadge label={summary.digital_pulse.lean_label} />
            <ConfidenceBadge label={summary.confidence.label} />
            <span className="flex items-center gap-1.5 text-xs mono"
              style={{ color: "#4d6480" }}>
              <Radio size={10} style={{ color: "#10b981" }} />
              {summary.confidence.event_count} events
            </span>
          </div>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 md:grid-cols-8 gap-3 mb-4">
        {[
          { label: "Total Voters",   value: fmt(summary.total_voters),   color: "#f0f4fa", sub: null },
          { label: "Male Voters",    value: fmt(summary.male_voters),    color: "#3b82f6", sub: null },
          { label: "Female Voters",  value: fmt(summary.female_voters),  color: "#ec4899", sub: femalePct ? `${femalePct}%` : null },
          { label: "BJP Wins",       value: summary.historical.bjp_won_count, color: "#f97316", sub: "historical" },
          { label: "BJP Pulse",      value: fmt(summary.digital_pulse.bjp_pulse, 3), color: "#f97316", sub: "digital score" },
          { label: "Opp Pulse",      value: fmt(summary.digital_pulse.opp_pulse, 3), color: "#3b82f6", sub: "digital score" },
          { label: "Confidence",     value: fmt(summary.confidence.score, 2), color: summary.confidence.label === "HIGH" ? "#10b981" : summary.confidence.label === "MEDIUM" ? "#f59e0b" : "#ef4444", sub: summary.confidence.label },
          { label: "Data Events",    value: summary.confidence.event_count, color: "#10b981", sub: "raw signals" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="card px-3 py-2.5">
            <p className="label" style={{ color: "#2e4260" }}>{label}</p>
            <p className="mono font-bold mt-0.5 text-base" style={{ color }}>{value}</p>
            {sub && <p className="text-xs mt-0.5" style={{ color: "#2e4260" }}>{sub}</p>}
          </div>
        ))}
      </div>

      {/* Insight banners */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <div className="rounded-md px-4 py-3 flex items-start gap-3"
          style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)" }}>
          <Shield size={14} className="mt-0.5 flex-shrink-0" style={{ color: "#10b981" }} />
          <div>
            <p className="label mb-1" style={{ color: "#10b981" }}>Key Insight</p>
            <p className="text-xs" style={{ color: "#8ba0bc" }}>{summary.key_insight}</p>
          </div>
        </div>
        <div className="rounded-md px-4 py-3 flex items-start gap-3"
          style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)" }}>
          <TrendingUp size={14} className="mt-0.5 flex-shrink-0" style={{ color: "#f97316" }} />
          <div>
            <p className="label mb-1" style={{ color: "#f97316" }}>Recommendation</p>
            <p className="text-xs" style={{ color: "#8ba0bc" }}>{summary.recommendation}</p>
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
          {/* Charts */}
          <BoothDetailCharts summary={summary} />

          {/* Issues detail */}
          <div className="card p-4">
            <SectionHeader title="Issue Analysis" sub={`${summary.top_issues.length} tracked issues`} accent="#ef4444"
              right={
                <span className="mono text-xs" style={{ color: "#4d6480" }}>
                  {summary.top_issues.reduce((s, i) => s + i.mention_count, 0)} total mentions
                </span>
              }
            />
            {summary.top_issues.length === 0 ? (
              <p className="text-xs" style={{ color: "#4d6480" }}>No issue data.</p>
            ) : (
              <div className="space-y-3">
                {summary.top_issues.map((iss, i) => {
                  const maxMentions = summary.top_issues[0].mention_count;
                  const pct = (iss.mention_count / maxMentions) * 100;
                  return (
                    <div key={iss.issue}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="mono text-xs w-4" style={{ color: "#2e4260" }}>{i + 1}</span>
                          <span className="text-xs font-medium text-white capitalize">
                            {iss.issue.replace(/_/g, " ")}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs" style={{ color: "#4d6480" }}>
                            {iss.mention_count} mentions
                          </span>
                          {iss.avg_polarity != null && (
                            <span className="mono text-xs px-1.5 py-0.5 rounded"
                              style={{
                                background: iss.avg_polarity < -0.2 ? "#ef444420" : iss.avg_polarity > 0.2 ? "#10b98120" : "#1a2b44",
                                color: iss.avg_polarity < -0.2 ? "#ef4444" : iss.avg_polarity > 0.2 ? "#10b981" : "#64748b",
                                fontSize: 9
                              }}>
                              avg {iss.avg_polarity.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full" style={{ background: "#0b1220" }}>
                          <div className="h-1.5 rounded-full" style={{
                            width: `${pct}%`,
                            background: iss.avg_polarity != null && iss.avg_polarity < -0.2 ? "#ef4444" : "#f97316"
                          }} />
                        </div>
                        <div className="flex gap-2 text-xs mono" style={{ fontSize: 9 }}>
                          <span style={{ color: "#ef4444" }}>▼{iss.negative_count}</span>
                          <span style={{ color: "#10b981" }}>▲{iss.positive_count}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
          {/* Narratives */}
          <div className="card p-4">
            <SectionHeader title="Narrative Patterns" sub={`${summary.narratives.length} detected`} accent="#8b5cf6" />
            {summary.narratives.length === 0 ? (
              <p className="text-xs" style={{ color: "#4d6480" }}>No narratives detected.</p>
            ) : summary.narratives.map((n, i) => (
              <div key={i} className="mb-2 last:mb-0 rounded-md p-3"
                style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-white capitalize">
                    {n.narrative_type?.replace(/_/g, " ")}
                  </span>
                  {n.strength != null && (
                    <span className="mono text-xs px-1.5 py-0.5 rounded"
                      style={{
                        background: n.strength > 0.6 ? "#ef444420" : "#f9731620",
                        color: n.strength > 0.6 ? "#ef4444" : "#f97316",
                        fontSize: 9
                      }}>
                      str: {n.strength.toFixed(2)}
                    </span>
                  )}
                </div>
                {n.strength != null && (
                  <div className="h-1 rounded-full mb-1.5" style={{ background: "#1a2b44" }}>
                    <div className="h-1 rounded-full" style={{ width: `${n.strength * 100}%`, background: "#8b5cf6" }} />
                  </div>
                )}
                {n.summary && <p className="text-xs" style={{ color: "#4d6480" }}>{n.summary}</p>}
              </div>
            ))}
          </div>

          {/* Contradictions */}
          {summary.contradictions.length > 0 && (
            <div className="rounded-md p-4"
              style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.2)" }}>
              <SectionHeader title={`Signal Contradictions (${summary.contradictions.length})`} accent="#ef4444" />
              <div className="space-y-2">
                {summary.contradictions.map((c, i) => (
                  <div key={i} className="rounded-md p-2.5"
                    style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-white">{c.entity}</span>
                      {c.delta != null && (
                        <span className="mono text-xs" style={{ color: "#ef4444", fontSize: 9 }}>
                          Δ {c.delta.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="mono text-xs" style={{ color: "#4d6480", fontSize: 9 }}>
                        {c.source_a} vs {c.source_b}
                      </span>
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "#ef444420", color: "#ef4444", fontSize: 9 }}>
                        {c.flag_label}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scheme gaps */}
          {summary.scheme_analysis.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Scheme Delivery Gaps" sub={`${summary.scheme_analysis.length} gaps identified`} accent="#f59e0b" />
              <div className="space-y-1.5">
                {summary.scheme_analysis.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 py-2 px-2.5 rounded-md"
                    style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: s.priority === "HIGH" ? "#ef4444" : "#f59e0b" }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-white truncate">{s.scheme_name}</p>
                      <p className="text-xs capitalize" style={{ color: "#4d6480", fontSize: 9 }}>
                        {s.gap_type?.replace(/_/g, " ")}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {s.severity_score != null && (
                        <span className="mono text-xs" style={{ color: "#f59e0b", fontSize: 9 }}>
                          {s.severity_score.toFixed(1)}
                        </span>
                      )}
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{
                          background: s.priority === "HIGH" ? "#ef444420" : "#f59e0b20",
                          color: s.priority === "HIGH" ? "#ef4444" : "#f59e0b",
                          fontSize: 9
                        }}>
                        {s.priority}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence / comments */}
          {summary.backing_comments.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Source Evidence" sub={`${summary.backing_comments.length} signals`} accent="#06b6d4" />
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {summary.backing_comments.map((c, i) => (
                  <div key={i} className="rounded-md p-2.5" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <p className="text-xs text-white line-clamp-2 mb-1.5">{c.content}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "#0f1929", color: "#3b82f6", border: "1px solid #1a2b44", fontSize: 9 }}>
                        {c.source}
                      </span>
                      {c.final_issue && (
                        <span className="text-xs capitalize" style={{ color: "#f97316", fontSize: 9 }}>
                          {c.final_issue.replace(/_/g, " ")}
                        </span>
                      )}
                      {c.final_polarity != null && (
                        <span className="text-xs" style={{ color: c.final_polarity < 0 ? "#ef4444" : "#10b981", fontSize: 9 }}>
                          {c.final_polarity < 0 ? "▼ neg" : "▲ pos"}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
