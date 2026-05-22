import { api } from "@/lib/api";
import Link from "next/link";
import LeanBadge from "@/components/LeanBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import SectionHeader from "@/components/SectionHeader";
import BoothDetailCharts from "./BoothDetailCharts";
import {
  ArrowLeft, Users, Shield, AlertTriangle, BookOpen,
  TrendingUp, ChevronRight, Radio, Eye, Zap, Database,
<<<<<<< HEAD
  Target, Activity, Wifi
=======
  Target, Activity
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
} from "lucide-react";

function fmt(n: number | null | undefined, dec = 0) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: dec });
}

interface Props { params: Promise<{ id: string }> }

export default async function BoothDetailPage({ params }: Props) {
  const { id } = await params;
<<<<<<< HEAD
  const DAYS_WINDOW = 365;
  let summary: Awaited<ReturnType<typeof api.boothSummary>> | null = null;
  try { summary = await api.boothSummary(id, DAYS_WINDOW); } catch {}
  const [segments, conversion, pulseResp, issuesResp] = await Promise.all([
    api.boothSegments(id),
    api.boothConversion(id),
    api.boothPulse(id, DAYS_WINDOW).catch(() => null),
    api.boothIssues(id).catch(() => null),
=======
  let summary: Awaited<ReturnType<typeof api.boothSummary>> | null = null;
  try { summary = await api.boothSummary(id); } catch {}
  const [segments, conversion] = await Promise.all([
    api.boothSegments(id),
    api.boothConversion(id),
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
  ]);

  if (!summary) {
    return (
<<<<<<< HEAD
      <div className="min-h-screen flex flex-col items-center justify-center" style={{ background: "var(--bg-base)" }}>
        <p className="mb-2" style={{ color: 'var(--text-1)' }}>Booth not found: <span className="mono">{id}</span></p>
=======
      <div className="min-h-screen flex flex-col items-center justify-center" style={{ background: "#060b14" }}>
        <p className="text-white mb-2">Booth not found: <span className="mono">{id}</span></p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
        <Link href="/booths" className="text-xs hover:underline" style={{ color: "#f97316" }}>← Back</Link>
      </div>
    );
  }

  const femalePct = summary.total_voters && summary.female_voters
    ? ((summary.female_voters / summary.total_voters) * 100).toFixed(1)
    : null;

<<<<<<< HEAD
  const pulseDetail = summary.digital_pulse.pulse_detail.length > 0
    ? summary.digital_pulse.pulse_detail
    : (pulseResp?.pulse ?? []);

  const topIssues = summary.top_issues.length > 0
    ? summary.top_issues
    : (issuesResp?.issues ?? []);

  const inferredEventCount = pulseDetail.reduce((s, p) => s + (p.event_count ?? 0), 0);

  const detailSummary = {
    ...summary,
    digital_pulse: {
      ...summary.digital_pulse,
      pulse_detail: pulseDetail,
    },
    top_issues: topIssues,
    confidence: {
      ...summary.confidence,
      event_count: summary.confidence.event_count > 0 ? summary.confidence.event_count : inferredEventCount,
    },
  };

  return (
    <div className="p-5 min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 mono text-xs mb-4" style={{ color: "var(--text-3)" }}>
=======
  return (
    <div className="p-5 min-h-screen" style={{ background: "#060b14" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 mono text-xs mb-4" style={{ color: "#4d6480" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
        <Link href="/booths" className="hover:text-orange-400 transition-colors flex items-center gap-1">
          <ArrowLeft size={10} /> Booth Intelligence
        </Link>
        <ChevronRight size={10} />
<<<<<<< HEAD
        <span style={{ color: "var(--text-1)" }}>Booth {summary.booth_number}</span>
        <ChevronRight size={10} />
        <span className="truncate max-w-48" style={{ color: "var(--text-3)" }}>{summary.name}</span>
=======
        <span style={{ color: "#f0f4fa" }}>Booth {summary.booth_number}</span>
        <ChevronRight size={10} />
        <span className="truncate max-w-48" style={{ color: "#8ba0bc" }}>{summary.name}</span>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
      </div>

      {/* Header bar */}
      <div className="card p-4 mb-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: "linear-gradient(90deg, #f97316, #3b82f6, transparent)" }} />
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <span className="mono text-xs px-2 py-0.5 rounded"
<<<<<<< HEAD
                style={{ background: "var(--bg-surface)", color: "#f97316", border: "1px solid #f9731630" }}>
                B-{String(summary.booth_number).padStart(3, "0")}
              </span>
              <h1 className="font-bold text-[var(--text-1)]" style={{ fontSize: 16 }}>{summary.name}</h1>
            </div>
            <p className="text-xs mono" style={{ color: "var(--text-3)" }}>
=======
                style={{ background: "#0b1220", color: "#f97316", border: "1px solid #f9731630" }}>
                B-{String(summary.booth_number).padStart(3, "0")}
              </span>
              <h1 className="font-bold text-white" style={{ fontSize: 16 }}>{summary.name}</h1>
            </div>
            <p className="text-xs mono" style={{ color: "#4d6480" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
              {summary.ac_name} · AC-322 · ID: {id}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <LeanBadge label={summary.digital_pulse.lean_label} />
            <ConfidenceBadge label={summary.confidence.label} />
            <span className="flex items-center gap-1.5 text-xs mono"
<<<<<<< HEAD
              style={{ color: "var(--text-3)" }}>
              <Radio size={10} style={{ color: "#10b981" }} />
              {detailSummary.confidence.event_count} events
=======
              style={{ color: "#4d6480" }}>
              <Radio size={10} style={{ color: "#10b981" }} />
              {summary.confidence.event_count} events
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
            </span>
          </div>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 md:grid-cols-8 gap-3 mb-4">
        {[
<<<<<<< HEAD
          { label: "Total Voters",   value: fmt(summary.total_voters),   color: "var(--text-1)", sub: null },
=======
          { label: "Total Voters",   value: fmt(summary.total_voters),   color: "#f0f4fa", sub: null },
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
          { label: "Male Voters",    value: fmt(summary.male_voters),    color: "#3b82f6", sub: null },
          { label: "Female Voters",  value: fmt(summary.female_voters),  color: "#ec4899", sub: femalePct ? `${femalePct}%` : null },
          { label: "BJP Wins",       value: summary.historical.bjp_won_count, color: "#f97316", sub: "historical" },
          { label: "BJP Pulse",      value: fmt(summary.digital_pulse.bjp_pulse, 3), color: "#f97316", sub: "digital score" },
          { label: "Opp Pulse",      value: fmt(summary.digital_pulse.opp_pulse, 3), color: "#3b82f6", sub: "digital score" },
          { label: "Confidence",     value: fmt(summary.confidence.score, 2), color: summary.confidence.label === "HIGH" ? "#10b981" : summary.confidence.label === "MEDIUM" ? "#f59e0b" : "#ef4444", sub: summary.confidence.label },
<<<<<<< HEAD
          { label: "Data Events",    value: detailSummary.confidence.event_count, color: "#10b981", sub: "raw signals" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="card px-3 py-2.5">
            <p className="label" style={{ color: "var(--text-4)" }}>{label}</p>
            <p className="mono font-bold mt-0.5 text-base" style={{ color }}>{value}</p>
            {sub && <p className="text-xs mt-0.5" style={{ color: "var(--text-4)" }}>{sub}</p>}
=======
          { label: "Data Events",    value: summary.confidence.event_count, color: "#10b981", sub: "raw signals" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="card px-3 py-2.5">
            <p className="label" style={{ color: "#2e4260" }}>{label}</p>
            <p className="mono font-bold mt-0.5 text-base" style={{ color }}>{value}</p>
            {sub && <p className="text-xs mt-0.5" style={{ color: "#2e4260" }}>{sub}</p>}
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
            <p className="text-xs" style={{ color: "var(--text-3)" }}>{summary.key_insight}</p>
=======
            <p className="text-xs" style={{ color: "#8ba0bc" }}>{summary.key_insight}</p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
          </div>
        </div>
        <div className="rounded-md px-4 py-3 flex items-start gap-3"
          style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)" }}>
          <TrendingUp size={14} className="mt-0.5 flex-shrink-0" style={{ color: "#f97316" }} />
          <div>
            <p className="label mb-1" style={{ color: "#f97316" }}>Recommendation</p>
<<<<<<< HEAD
            <p className="text-xs" style={{ color: "var(--text-3)" }}>{summary.recommendation}</p>
=======
            <p className="text-xs" style={{ color: "#8ba0bc" }}>{summary.recommendation}</p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
          {/* Charts */}
<<<<<<< HEAD
          <BoothDetailCharts summary={detailSummary} />

          {/* Issue Analysis */}
          <div className="card p-4">
            <SectionHeader title="Issue Analysis" sub={`${detailSummary.top_issues.length} tracked issues`} accent="#ef4444"
              right={
                <span className="mono text-xs" style={{ color: "var(--text-3)" }}>
                  {detailSummary.top_issues.reduce((s, i) => s + i.mention_count, 0)} total mentions
                </span>
              }
            />
            {detailSummary.top_issues.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--text-3)" }}>No issue data.</p>
            ) : (
              <div className="space-y-3">
                {detailSummary.top_issues.map((iss, i) => {
                  const maxMentions = detailSummary.top_issues[0].mention_count;
                  const pct = (iss.mention_count / maxMentions) * 100;
                  const sentiment = iss.avg_polarity ?? 0;
                  const barColor = sentiment < -0.15 ? "#ef4444" : sentiment > 0.15 ? "#10b981" : "#f97316";
=======
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
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                  return (
                    <div key={iss.issue}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
<<<<<<< HEAD
                          <span className="mono text-xs w-4" style={{ color: "var(--text-4)" }}>{i + 1}</span>
                          <span className="text-xs font-medium text-[var(--text-1)] capitalize">
=======
                          <span className="mono text-xs w-4" style={{ color: "#2e4260" }}>{i + 1}</span>
                          <span className="text-xs font-medium text-white capitalize">
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                            {iss.issue.replace(/_/g, " ")}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
<<<<<<< HEAD
                          <span className="text-xs" style={{ color: "var(--text-3)" }}>
=======
                          <span className="text-xs" style={{ color: "#4d6480" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                            {iss.mention_count} mentions
                          </span>
                          {iss.avg_polarity != null && (
                            <span className="mono text-xs px-1.5 py-0.5 rounded"
                              style={{
<<<<<<< HEAD
                                background: sentiment < -0.15 ? "#ef444420" : sentiment > 0.15 ? "#10b98120" : "var(--bg-surface)",
                                color: sentiment < -0.15 ? "#ef4444" : sentiment > 0.15 ? "#10b981" : "var(--text-4)",
                                fontSize: 9
                              }}>
                              {sentiment > 0 ? "+" : ""}{iss.avg_polarity.toFixed(2)}
=======
                                background: iss.avg_polarity < -0.2 ? "#ef444420" : iss.avg_polarity > 0.2 ? "#10b98120" : "#1a2b44",
                                color: iss.avg_polarity < -0.2 ? "#ef4444" : iss.avg_polarity > 0.2 ? "#10b981" : "#64748b",
                                fontSize: 9
                              }}>
                              avg {iss.avg_polarity.toFixed(2)}
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
<<<<<<< HEAD
                        <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg-surface)" }}>
                          <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: barColor }} />
                        </div>
                        <div className="flex gap-2 mono" style={{ fontSize: 9 }}>
=======
                        <div className="flex-1 h-1.5 rounded-full" style={{ background: "#0b1220" }}>
                          <div className="h-1.5 rounded-full" style={{
                            width: `${pct}%`,
                            background: iss.avg_polarity != null && iss.avg_polarity < -0.2 ? "#ef4444" : "#f97316"
                          }} />
                        </div>
                        <div className="flex gap-2 text-xs mono" style={{ fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD

          {/* Digital Pulse by Source */}
          {summary.source_breakdown && summary.source_breakdown.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Digital Pulse by Source" sub={`${summary.source_breakdown.reduce((s, r) => s + r.event_count, 0)} total signals`} accent="#3b82f6"
                right={<Wifi size={12} style={{ color: "#3b82f6" }} />}
              />
              <div className="space-y-4 mt-1">
                {summary.source_breakdown.map((src) => {
                  const total = src.event_count;
                  const posPct = total > 0 ? (src.positive / total) * 100 : 0;
                  const negPct = total > 0 ? (src.negative / total) * 100 : 0;
                  const neuPct = total > 0 ? (src.neutral / total) * 100 : 0;
                  const SOURCE_LABELS: Record<string, string> = {
                    youtube: "YouTube", news: "News Media", survey: "Field Survey",
                    whatsapp: "WhatsApp", twitter: "Twitter / X", facebook: "Facebook",
                  };
                  const SOURCE_COLORS: Record<string, string> = {
                    youtube: "#ef4444", news: "#3b82f6", survey: "#10b981",
                    whatsapp: "#22c55e", twitter: "#06b6d4", facebook: "#6366f1",
                  };
                  const color = SOURCE_COLORS[src.source_type] ?? "#8b5cf6";
                  const label = SOURCE_LABELS[src.source_type] ?? src.source_type;
                  return (
                    <div key={src.source_type}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                          <span className="text-xs font-medium text-[var(--text-1)]">{label}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="mono text-xs" style={{ color: "var(--text-3)" }}>{total.toLocaleString("en-IN")} signals</span>
                          {src.avg_pulse != null && (
                            <span className="mono text-xs px-1.5 py-0.5 rounded"
                              style={{
                                background: src.avg_pulse > 0.05 ? "#10b98120" : src.avg_pulse < -0.05 ? "#ef444420" : "var(--bg-surface)",
                                color: src.avg_pulse > 0.05 ? "#10b981" : src.avg_pulse < -0.05 ? "#ef4444" : "var(--text-4)",
                                fontSize: 9
                              }}>
                              pulse {src.avg_pulse > 0 ? "+" : ""}{src.avg_pulse.toFixed(3)}
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Segmented bar: positive / neutral / negative */}
                      <div className="flex h-2 rounded-full overflow-hidden gap-px mb-1.5" style={{ background: "var(--bg-surface)" }}>
                        <div style={{ width: `${posPct}%`, background: "#10b981" }} />
                        <div style={{ width: `${neuPct}%`, background: "var(--border)" }} />
                        <div style={{ width: `${negPct}%`, background: "#ef4444" }} />
                      </div>
                      <div className="flex gap-4" style={{ fontSize: 9 }}>
                        <span className="mono flex items-center gap-1" style={{ color: "#10b981" }}>
                          ▲ {src.positive} positive ({posPct.toFixed(0)}%)
                        </span>
                        <span className="mono flex items-center gap-1" style={{ color: "var(--text-4)" }}>
                          — {src.neutral} neutral
                        </span>
                        <span className="mono flex items-center gap-1" style={{ color: "#ef4444" }}>
                          ▼ {src.negative} negative ({negPct.toFixed(0)}%)
                        </span>
                      </div>
                    </div>
                  );
                })}

                {/* Entity pulse table */}
                {detailSummary.digital_pulse.pulse_detail.length > 0 && (
                  <div className="pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                    <p className="text-xs mb-2" style={{ color: "var(--text-3)" }}>Entity pulse scores</p>
                    <div className="space-y-1.5">
                      {detailSummary.digital_pulse.pulse_detail.map((p) => {
                        const score = p.pulse_score ?? 0;
                        const barPct = Math.min(Math.abs(score) * 200, 100);
                        const isParty = ["BJP", "SP", "BSP", "INC", "Congress"].includes(p.entity);
                        const entityColor = p.entity === "BJP" ? "#f97316"
                          : p.entity === "SP" ? "#3b82f6"
                          : p.entity === "BSP" ? "#8b5cf6"
                          : "#64748b";
                        return (
                          <div key={p.entity} className="flex items-center gap-2">
                            <span className="text-xs w-28 truncate" style={{ color: isParty ? entityColor : "var(--text-2)" }}>
                              {p.entity}
                            </span>
                            <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg-surface)" }}>
                              <div className="h-1.5 rounded-full" style={{ width: `${barPct}%`, background: entityColor }} />
                            </div>
                            <span className="mono text-xs w-14 text-right" style={{ color: entityColor, fontSize: 10 }}>
                              {score > 0 ? "+" : ""}{score.toFixed(3)}
                            </span>
                            <span className="mono text-xs w-12 text-right" style={{ color: "var(--text-4)", fontSize: 9 }}>
                              {p.event_count}ev
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
=======
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
        </div>

        {/* Right column */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
          {/* Narratives */}
          <div className="card p-4">
            <SectionHeader title="Narrative Patterns" sub={`${summary.narratives.length} detected`} accent="#8b5cf6" />
            {summary.narratives.length === 0 ? (
<<<<<<< HEAD
              <p className="text-xs" style={{ color: "var(--text-3)" }}>No narratives detected.</p>
            ) : summary.narratives.map((n, i) => (
              <div key={i} className="mb-2 last:mb-0 rounded-md p-3"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-[var(--text-1)] capitalize">
=======
              <p className="text-xs" style={{ color: "#4d6480" }}>No narratives detected.</p>
            ) : summary.narratives.map((n, i) => (
              <div key={i} className="mb-2 last:mb-0 rounded-md p-3"
                style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-white capitalize">
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
                  <div className="h-1 rounded-full mb-1.5" style={{ background: "var(--border)" }}>
                    <div className="h-1 rounded-full" style={{ width: `${n.strength * 100}%`, background: "#8b5cf6" }} />
                  </div>
                )}
                {n.summary && <p className="text-xs" style={{ color: "var(--text-3)" }}>{n.summary}</p>}
=======
                  <div className="h-1 rounded-full mb-1.5" style={{ background: "#1a2b44" }}>
                    <div className="h-1 rounded-full" style={{ width: `${n.strength * 100}%`, background: "#8b5cf6" }} />
                  </div>
                )}
                {n.summary && <p className="text-xs" style={{ color: "#4d6480" }}>{n.summary}</p>}
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-[var(--text-1)]">{c.entity}</span>
=======
                    style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-white">{c.entity}</span>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                      {c.delta != null && (
                        <span className="mono text-xs" style={{ color: "#ef4444", fontSize: 9 }}>
                          Δ {c.delta.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
<<<<<<< HEAD
                      <span className="mono text-xs" style={{ color: "var(--text-3)", fontSize: 9 }}>
=======
                      <span className="mono text-xs" style={{ color: "#4d6480", fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
<<<<<<< HEAD
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: s.priority === "HIGH" ? "#ef4444" : "#f59e0b" }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[var(--text-1)] truncate">{s.scheme_name}</p>
                      <p className="text-xs capitalize" style={{ color: "var(--text-3)", fontSize: 9 }}>
=======
                    style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: s.priority === "HIGH" ? "#ef4444" : "#f59e0b" }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-white truncate">{s.scheme_name}</p>
                      <p className="text-xs capitalize" style={{ color: "#4d6480", fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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

          {/* Voter Segments */}
          {segments && segments.segments.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Voter Segments" sub="aggregated · no PII" accent="#8b5cf6"
                right={<Users size={12} style={{ color: "#8b5cf6" }} />}
              />
              <div className="space-y-2 mt-1">
                {segments.segments.map((seg) => {
                  const labels: Record<string, string> = {
                    youth: "Youth (18–30)",
                    first_voter: "First-time Voters (18–21)",
                    women: "Women",
                    elderly: "Elderly (60+)",
                    working_age: "Working Age (25–55)",
                  };
                  const colors: Record<string, string> = {
                    youth: "#f97316", first_voter: "#facc15", women: "#ec4899",
                    elderly: "#06b6d4", working_age: "#10b981",
                  };
                  const color = colors[seg.segment_type] ?? "#8b5cf6";
                  const pct = seg.pct_of_voters != null ? (seg.pct_of_voters * 100).toFixed(1) : null;
                  return (
                    <div key={seg.segment_type} className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
<<<<<<< HEAD
                          <span className="text-xs text-[var(--text-1)]">{labels[seg.segment_type] ?? seg.segment_type}</span>
                          <div className="flex items-center gap-2">
                            <span className="mono text-xs" style={{ color, fontSize: 10 }}>{seg.count.toLocaleString("en-IN")}</span>
                            {pct && <span className="mono text-xs" style={{ color: "var(--text-3)", fontSize: 9 }}>{pct}%</span>}
                          </div>
                        </div>
                        {pct && (
                          <div className="h-1 rounded-full" style={{ background: "var(--bg-surface)" }}>
=======
                          <span className="text-xs text-white">{labels[seg.segment_type] ?? seg.segment_type}</span>
                          <div className="flex items-center gap-2">
                            <span className="mono text-xs" style={{ color, fontSize: 10 }}>{seg.count.toLocaleString("en-IN")}</span>
                            {pct && <span className="mono text-xs" style={{ color: "#4d6480", fontSize: 9 }}>{pct}%</span>}
                          </div>
                        </div>
                        {pct && (
                          <div className="h-1 rounded-full" style={{ background: "#0b1220" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                            <div className="h-1 rounded-full" style={{ width: `${Math.min(parseFloat(pct), 100)}%`, background: color, opacity: 0.7 }} />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Conversion Opportunity */}
          {conversion && (
            <div className="card p-4">
              <SectionHeader title="Conversion Opportunity" sub={conversion.recommended_action?.replace(/_/g, " ") ?? ""} accent="#10b981"
                right={<Target size={12} style={{ color: "#10b981" }} />}
              />
              {/* Overall score bar */}
              {conversion.overall_conversion_score != null && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
<<<<<<< HEAD
                    <span className="text-xs" style={{ color: "var(--text-3)" }}>Overall score</span>
=======
                    <span className="text-xs" style={{ color: "#4d6480" }}>Overall score</span>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                    <span className="mono text-xs font-bold" style={{ color: "#10b981" }}>
                      {(conversion.overall_conversion_score * 100).toFixed(0)}
                    </span>
                  </div>
<<<<<<< HEAD
                  <div className="h-2 rounded-full" style={{ background: "var(--bg-surface)" }}>
=======
                  <div className="h-2 rounded-full" style={{ background: "#0b1220" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                    <div className="h-2 rounded-full" style={{
                      width: `${conversion.overall_conversion_score * 100}%`,
                      background: "linear-gradient(90deg, #10b981, #3b82f6)"
                    }} />
                  </div>
                </div>
              )}
              {/* 4 sub-scores */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                {[
                  { label: "Persuasion Room", value: conversion.persuasion_room_score, color: "#f97316" },
                  { label: "Beneficiary Density", value: conversion.beneficiary_density_score, color: "#8b5cf6" },
                  { label: "Turnout Mobilization", value: conversion.turnout_mobilization_score, color: "#3b82f6" },
                  { label: "Service Risk", value: conversion.service_risk_score, color: "#ef4444", invert: true },
                ].map(({ label, value, color, invert }) => (
<<<<<<< HEAD
                  <div key={label} className="rounded-md p-2" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <p className="text-xs mb-1" style={{ color: "var(--text-3)", fontSize: 9 }}>{label}</p>
                    <div className="flex items-center gap-1.5">
                      <div className="flex-1 h-1 rounded-full" style={{ background: "var(--border)" }}>
=======
                  <div key={label} className="rounded-md p-2" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <p className="text-xs mb-1" style={{ color: "#4d6480", fontSize: 9 }}>{label}</p>
                    <div className="flex items-center gap-1.5">
                      <div className="flex-1 h-1 rounded-full" style={{ background: "#1a2b44" }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                        <div className="h-1 rounded-full" style={{
                          width: value != null ? `${value * 100}%` : "0%",
                          background: invert
                            ? (value != null && value > 0.6 ? "#ef4444" : "#f59e0b")
                            : color
                        }} />
                      </div>
                      <span className="mono" style={{ color, fontSize: 9 }}>
                        {value != null ? (value * 100).toFixed(0) : "—"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {/* Recommended action */}
              {conversion.action_reason && (
                <div className="rounded-md px-3 py-2" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Activity size={10} style={{ color: "#10b981" }} />
                    <span className="text-xs font-medium capitalize" style={{ color: "#10b981" }}>
                      {conversion.recommended_action?.replace(/_/g, " ")}
                    </span>
                  </div>
<<<<<<< HEAD
                  <p className="text-xs" style={{ color: "var(--text-3)" }}>{conversion.action_reason}</p>
=======
                  <p className="text-xs" style={{ color: "#8ba0bc" }}>{conversion.action_reason}</p>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
                </div>
              )}
            </div>
          )}

          {/* Evidence / comments */}
          {summary.backing_comments.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Source Evidence" sub={`${summary.backing_comments.length} signals`} accent="#06b6d4" />
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {summary.backing_comments.map((c, i) => (
<<<<<<< HEAD
                  <div key={i} className="rounded-md p-2.5" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <p className="text-xs text-[var(--text-1)] line-clamp-2 mb-1.5">{c.content}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "var(--bg-card)", color: "#3b82f6", border: "1px solid var(--border)", fontSize: 9 }}>
=======
                  <div key={i} className="rounded-md p-2.5" style={{ background: "#0b1220", border: "1px solid #1a2b44" }}>
                    <p className="text-xs text-white line-clamp-2 mb-1.5">{c.content}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "#0f1929", color: "#3b82f6", border: "1px solid #1a2b44", fontSize: 9 }}>
>>>>>>> 8048c7b85b6989f4e9cca6f842da79de367504f4
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
