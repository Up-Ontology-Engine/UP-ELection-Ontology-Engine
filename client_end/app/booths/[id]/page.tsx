import { api, type BoothActionItem } from "@/lib/api";
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

  let boothActions: BoothActionItem[] = [];
  try {
    const actResult = await api.boothActions(id);
    boothActions = actResult.actions;
  } catch {}

  const [segments, conversion] = await Promise.all([
    api.boothSegments(id),
    api.boothConversion(id),
  ]);

  if (!summary) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center" style={{ background: "var(--bg-base)" }}>
        <p className="mb-2" style={{ color: "var(--text-1)" }}>Booth not found: <span className="mono">{id}</span></p>
        <Link href="/booths" className="text-xs hover:underline" style={{ color: "#003380" }}>← Back</Link>
      </div>
    );
  }

  const femalePct = summary.total_voters && summary.female_voters
    ? ((summary.female_voters / summary.total_voters) * 100).toFixed(1)
    : null;

  return (
    <div className="p-5 min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 mono text-xs mb-4" style={{ color: "var(--text-4)" }}>
        <Link href="/booths" className="flex items-center gap-1 hover:underline" style={{ color: "var(--text-3)" }}>
          <ArrowLeft size={10} /> Booth Intelligence
        </Link>
        <ChevronRight size={10} />
        <span style={{ color: "var(--text-1)" }}>Booth {summary.booth_number}</span>
        <ChevronRight size={10} />
        <span className="truncate max-w-48" style={{ color: "var(--text-3)" }}>{summary.name}</span>
      </div>

      {/* Header bar */}
      <div className="card p-4 mb-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: "linear-gradient(90deg, #FF9933, #003380, transparent)" }} />
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <span className="mono text-xs px-2 py-0.5 rounded"
                style={{ background: "var(--bg-surface)", color: "#FF9933", border: "1px solid rgba(255,153,51,0.3)" }}>
                B-{String(summary.booth_number).padStart(3, "0")}
              </span>
              <h1 className="font-bold" style={{ fontSize: 16, color: "var(--text-1)" }}>{summary.name}</h1>
            </div>
            <p className="text-xs mono" style={{ color: "var(--text-4)" }}>
              {summary.ac_name} · AC-322 · ID: {id}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <LeanBadge label={summary.digital_pulse.lean_label} />
            <ConfidenceBadge label={summary.confidence.label} />
            <span className="flex items-center gap-1.5 text-xs mono"
              style={{ color: "var(--text-3)" }}>
              <Radio size={10} style={{ color: "#10b981" }} />
              {summary.confidence.event_count} events
            </span>
          </div>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 md:grid-cols-8 gap-3 mb-4">
        {[
          { label: "Total Voters",  value: fmt(summary.total_voters),                 color: "var(--text-1)", sub: null              },
          { label: "Male Voters",   value: fmt(summary.male_voters),                  color: "#003380",       sub: null              },
          { label: "Female Voters", value: fmt(summary.female_voters),                color: "#be185d",       sub: femalePct ? `${femalePct}%` : null },
          { label: "BJP Wins",      value: summary.historical.bjp_won_count,          color: "#FF9933",       sub: "historical"      },
          { label: "BJP Pulse",     value: fmt(summary.digital_pulse.bjp_pulse, 3),   color: "#FF9933",       sub: "digital score"   },
          { label: "Opp Pulse",     value: fmt(summary.digital_pulse.opp_pulse, 3),   color: "#003380",       sub: "digital score"   },
          { label: "Confidence",    value: fmt(summary.confidence.score, 2),
            color: summary.confidence.label === "HIGH" ? "#138808" : summary.confidence.label === "MEDIUM" ? "#d97706" : "#cc2200",
            sub: summary.confidence.label },
          { label: "Data Events",   value: summary.confidence.event_count,            color: "#138808",       sub: "raw signals"     },
        ].map(({ label, value, color, sub }) => (
          <div key={label} className="card px-3 py-2.5">
            <p className="label" style={{ color: "var(--text-4)" }}>{label}</p>
            <p className="mono font-bold mt-0.5 text-base" style={{ color }}>{value}</p>
            {sub && <p className="text-xs mt-0.5" style={{ color: "var(--text-4)" }}>{sub}</p>}
          </div>
        ))}
      </div>

      {/* Insight banners */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <div className="rounded-md px-4 py-3 flex items-start gap-3"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid #138808" }}>
          <Shield size={14} className="mt-0.5 flex-shrink-0" style={{ color: "#138808" }} />
          <div>
            <p className="label mb-1" style={{ color: "#138808" }}>Key Insight</p>
            <p className="text-xs" style={{ color: "var(--text-3)" }}>{summary.key_insight}</p>
          </div>
        </div>
        <div className="rounded-md px-4 py-3 flex items-start gap-3"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid #FF9933" }}>
          <TrendingUp size={14} className="mt-0.5 flex-shrink-0" style={{ color: "#FF9933" }} />
          <div>
            <p className="label mb-1" style={{ color: "#FF9933" }}>Recommendation</p>
            <p className="text-xs" style={{ color: "var(--text-3)" }}>{summary.recommendation}</p>
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
            <SectionHeader title="Issue Analysis" sub={`${summary.top_issues.length} tracked issues`} accent="#cc2200"
              right={
                <span className="mono text-xs" style={{ color: "var(--text-4)" }}>
                  {summary.top_issues.reduce((s, i) => s + i.mention_count, 0)} total mentions
                </span>
              }
            />
            {summary.top_issues.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--text-4)" }}>No verified issue data available.</p>
            ) : (
              <div className="space-y-3">
                {summary.top_issues.map((iss, i) => {
                  const maxMentions = summary.top_issues[0].mention_count;
                  const pct = (iss.mention_count / maxMentions) * 100;
                  const isNeg = iss.avg_polarity != null && iss.avg_polarity < -0.2;
                  const isPos = iss.avg_polarity != null && iss.avg_polarity > 0.2;
                  return (
                    <div key={iss.issue}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="mono text-xs w-4" style={{ color: "var(--text-4)" }}>{i + 1}</span>
                          <span className="text-xs font-medium capitalize" style={{ color: "var(--text-1)" }}>
                            {iss.issue.replace(/_/g, " ")}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs" style={{ color: "var(--text-4)" }}>
                            {iss.mention_count} mentions
                          </span>
                          {iss.avg_polarity != null && (
                            <span className="mono text-xs px-1.5 py-0.5 rounded"
                              style={{
                                background: isNeg ? "#fef2f2" : isPos ? "#f0fdf4" : "var(--bg-surface)",
                                color: isNeg ? "#cc2200" : isPos ? "#138808" : "var(--text-4)",
                                border: `1px solid ${isNeg ? "#fecaca" : isPos ? "#bbf7d0" : "var(--border)"}`,
                                fontSize: 9,
                              }}>
                              avg {iss.avg_polarity.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
                          <div className="h-1.5 rounded-full" style={{
                            width: `${pct}%`,
                            background: isNeg ? "#cc2200" : "#003380",
                          }} />
                        </div>
                        <div className="flex gap-2 text-xs mono" style={{ fontSize: 9 }}>
                          <span style={{ color: "#cc2200" }}>▼{iss.negative_count}</span>
                          <span style={{ color: "#138808" }}>▲{iss.positive_count}</span>
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
              <p className="text-xs" style={{ color: "var(--text-4)" }}>No narratives detected.</p>
            ) : summary.narratives.map((n, i) => (
              <div key={i} className="mb-2 last:mb-0 rounded-md p-3"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium capitalize" style={{ color: "var(--text-1)" }}>
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
                  <div className="h-1 rounded-full mb-1.5" style={{ background: "var(--bg-base)" }}>
                    <div className="h-1 rounded-full" style={{ width: `${n.strength * 100}%`, background: "#8b5cf6" }} />
                  </div>
                )}
                {n.summary && <p className="text-xs" style={{ color: "var(--text-3)" }}>{n.summary}</p>}
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
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium" style={{ color: "var(--text-1)" }}>{c.entity}</span>
                      {c.delta != null && (
                        <span className="mono text-xs" style={{ color: "#ef4444", fontSize: 9 }}>
                          Δ {c.delta.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="mono text-xs" style={{ color: "var(--text-3)", fontSize: 9 }}>
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

          {/* Recommended Actions */}
          {boothActions.length > 0 && (
            <div className="card p-4">
              <SectionHeader
                title="Recommended Actions"
                sub={`${boothActions.length} prioritised items`}
                accent="#f97316"
                right={
                  <span className="mono text-xs" style={{ color: "var(--text-4)" }}>
                    {boothActions.filter((a) => a.priority === "high").length} high priority
                  </span>
                }
              />
              <div className="space-y-2">
                {boothActions.map((action, i) => {
                  const isHigh = action.priority === "high";
                  const catColors: Record<string, string> = {
                    scheme:       "#f59e0b",
                    issue:        "#cc2200",
                    narrative:    "#8b5cf6",
                    mobilisation: "#003380",
                  };
                  const accent = catColors[action.category] ?? "#f97316";
                  return (
                    <div key={i} className="rounded-md p-3"
                      style={{
                        background: "var(--bg-surface)",
                        border: `1px solid ${isHigh ? `${accent}40` : "var(--border)"}`,
                        borderLeft: `3px solid ${accent}`,
                      }}>
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <p className="text-xs font-medium" style={{ color: "var(--text-1)" }}>{action.title}</p>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className="mono text-xs px-1.5 py-0.5 rounded capitalize"
                            style={{
                              background: `${accent}18`,
                              color: accent,
                              border: `1px solid ${accent}30`,
                              fontSize: 9,
                            }}>
                            {action.category}
                          </span>
                          <span className="mono text-xs px-1.5 py-0.5 rounded"
                            style={{
                              background: isHigh ? "#ef444420" : "#f9731618",
                              color: isHigh ? "#ef4444" : "#f97316",
                              fontSize: 9,
                            }}>
                            {action.priority}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs mb-1.5" style={{ color: "var(--text-3)" }}>{action.description}</p>
                      <p className="mono text-xs" style={{ color: "var(--text-4)", fontSize: 9 }}>
                        {action.rationale}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Voter Segments */}
          {segments && segments.segments.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Voter Segments" sub="aggregated · no PII" accent="#8b5cf6" />
              <div className="space-y-2">
                {segments.segments.map((seg) => {
                  const pct = seg.pct_of_voters ?? 0;
                  return (
                    <div key={seg.segment_type}>
                      <div className="flex justify-between mb-1">
                        <span className="text-xs capitalize" style={{ color: "var(--text-2)" }}>
                          {seg.segment_type.replace(/_/g, " ")}
                        </span>
                        <span className="mono text-xs" style={{ color: "var(--text-3)" }}>
                          {seg.count} · {pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: "#8b5cf6" }} />
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
              <SectionHeader
                title="Conversion Opportunity"
                sub={conversion.recommended_action?.replace(/_/g, " ") ?? ""}
                accent="#10b981"
              />
              {conversion.overall_conversion_score != null && (
                <div className="mb-3">
                  <div className="flex justify-between mb-1">
                    <span className="text-xs" style={{ color: "var(--text-3)" }}>Overall Score</span>
                    <span className="mono text-xs font-bold" style={{ color: "#10b981" }}>
                      {(conversion.overall_conversion_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: "var(--bg-base)" }}>
                    <div className="h-2 rounded-full" style={{ width: `${conversion.overall_conversion_score * 100}%`, background: "#10b981" }} />
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 mt-2">
                {([
                  { label: "Persuasion Room",      value: conversion.persuasion_room_score,      color: "#f97316" },
                  { label: "Beneficiary Density",  value: conversion.beneficiary_density_score,  color: "#8b5cf6" },
                  { label: "Turnout Mobilization", value: conversion.turnout_mobilization_score, color: "#3b82f6" },
                  { label: "Service Risk",          value: conversion.service_risk_score,         color: "#ef4444" },
                ] as { label: string; value: number | null | undefined; color: string }[]).map(({ label, value, color }) => value != null ? (
                  <div key={label} className="rounded-md p-2" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <p className="text-xs mb-1" style={{ color: "var(--text-4)", fontSize: 9 }}>{label}</p>
                    <p className="mono font-bold text-sm" style={{ color }}>{(value * 100).toFixed(0)}%</p>
                  </div>
                ) : null)}
              </div>
              {conversion.action_reason && (
                <div className="mt-2 rounded-md p-2.5" style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.2)" }}>
                  <span className="mono text-xs capitalize font-medium" style={{ color: "#10b981", fontSize: 9 }}>
                    {conversion.recommended_action?.replace(/_/g, " ")}
                  </span>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-3)" }}>{conversion.action_reason}</p>
                </div>
              )}
            </div>
          )}

          {/* Scheme gaps */}
          {summary.scheme_analysis.length > 0 && (
            <div className="card p-4">
              <SectionHeader title="Scheme Delivery Gaps" sub={`${summary.scheme_analysis.length} gaps identified`} accent="#f59e0b" />
              <div className="space-y-1.5">
                {summary.scheme_analysis.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 py-2 px-2.5 rounded-md"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: s.priority === "HIGH" ? "#ef4444" : "#f59e0b" }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate" style={{ color: "var(--text-1)" }}>{s.scheme_name}</p>
                      <p className="text-xs capitalize" style={{ color: "var(--text-3)", fontSize: 9 }}>
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
                  <div key={i} className="rounded-md p-2.5" style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <p className="text-xs line-clamp-2 mb-1.5" style={{ color: "var(--text-1)" }}>{c.content}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="mono text-xs px-1.5 py-0.5 rounded"
                        style={{ background: "var(--bg-card)", color: "#3b82f6", border: "1px solid var(--border)", fontSize: 9 }}>
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
