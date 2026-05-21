import { api } from "@/lib/api";
import type { IssueBreakdownItem } from "@/lib/api";
import {
  AlertTriangle,
  BarChart3,
  Brain,
  ChevronRight,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

const SEVERITY_STYLE = {
  high:   { bg: "#fef2f2", border: "#fecaca", color: "#cc2200", label: "HIGH" },
  medium: { bg: "#fffbeb", border: "#fcd9a0", color: "#d97706", label: "MED"  },
  low:    { bg: "#f0fdf4", border: "#bbf7d0", color: "#138808", label: "LOW"  },
};

const NARRATIVE_LABELS: Record<string, string> = {
  anti_incumbency:     "Anti-incumbency",
  employment_crisis:   "Employment Crisis",
  youth_frustration:   "Youth Frustration",
  development_promise: "Development Promise",
  welfare_delivery:    "Welfare Delivery",
  law_order:           "Law & Order",
  communal_tension:    "Communal Tension",
  price_rise:          "Price Rise Anger",
};

function TrendChip({ trend, delta }: { trend: string; delta: number | null }) {
  if (trend === "rising")
    return (
      <span className="inline-flex items-center gap-1 text-xs font-bold" style={{ color: "#cc2200" }}>
        <TrendingUp size={11} /> {delta != null ? `+${delta}%` : "↑"}
      </span>
    );
  if (trend === "falling")
    return (
      <span className="inline-flex items-center gap-1 text-xs font-bold" style={{ color: "#138808" }}>
        <TrendingDown size={11} /> {delta != null ? `${delta}%` : "↓"}
      </span>
    );
  return <span className="text-xs" style={{ color: "var(--text-4)" }}>Stable</span>;
}

function PolarityBar({ neg, pos, total }: { neg: number; pos: number; total: number }) {
  const negPct = total > 0 ? (neg / total) * 100 : 0;
  const posPct = total > 0 ? (pos / total) * 100 : 0;
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-base)" }}>
      <div style={{ width: `${negPct}%`, background: "#cc2200" }} />
      <div style={{ width: `${posPct}%`, background: "#138808" }} />
    </div>
  );
}

function IssueRow({
  item,
  rank,
  maxSignals,
  expanded,
  onToggle,
}: {
  item: IssueBreakdownItem;
  rank: number;
  maxSignals: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const sev   = SEVERITY_STYLE[item.severity];
  const label = item.issue.replace(/_/g, " ");
  const pct   = (item.total_signals / maxSignals) * 100;

  return (
    <div style={{ borderBottom: "1px solid var(--border)" }}>
      {/* Main row */}
      <div className="px-4 py-3 grid items-center gap-3"
        style={{ gridTemplateColumns: "24px 1fr 120px 60px 60px 24px" }}>
        {/* Rank */}
        <span className="mono text-xs font-bold" style={{ color: "var(--text-4)" }}>{rank}</span>

        {/* Label + bar */}
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className="text-sm font-semibold capitalize" style={{ color: "var(--text-1)" }}>{label}</span>
            <span className="mono text-xs font-bold px-1.5 rounded"
              style={{ background: sev.bg, color: sev.color, border: `1px solid ${sev.border}` }}>
              {sev.label}
            </span>
            <TrendChip trend={item.trend} delta={item.trend_delta_pct} />
          </div>
          <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
            <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: sev.color }} />
          </div>
          <PolarityBar neg={item.negative_count} pos={item.positive_count} total={item.total_signals} />
        </div>

        {/* Booth count */}
        <div className="text-center">
          <p className="mono text-sm font-bold" style={{ color: "var(--text-1)" }}>{item.affected_booth_count}</p>
          <p className="text-xs" style={{ color: "var(--text-4)" }}>booths</p>
        </div>

        {/* Total signals */}
        <div className="text-center">
          <p className="mono text-sm font-bold" style={{ color: sev.color }}>{fmt(item.total_signals)}</p>
          <p className="text-xs" style={{ color: "var(--text-4)" }}>signals</p>
        </div>

        {/* Confidence */}
        <div className="text-center">
          <p className="mono text-sm font-bold" style={{ color: "var(--text-2)" }}>
            {(item.avg_confidence * 100).toFixed(0)}%
          </p>
          <p className="text-xs" style={{ color: "var(--text-4)" }}>conf</p>
        </div>

        {/* Expand toggle */}
        {(item.top_booths.length > 0 || item.evidence.length > 0) && (
          <button onClick={onToggle} aria-label="Toggle detail"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0, color: "var(--text-4)" }}>
            <ChevronRight size={14} style={{ transform: expanded ? "rotate(90deg)" : "none", transition: "transform 0.15s" }} />
          </button>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 grid gap-4 md:grid-cols-2" style={{ background: "var(--bg-card-2)" }}>

          {/* Top booths */}
          {item.top_booths.length > 0 && (
            <div>
              <p className="text-xs font-bold mb-2" style={{ color: "var(--text-3)" }}>
                Top Affected Booths
              </p>
              <div className="flex flex-col gap-1.5">
                {item.top_booths.map((b) => {
                  const bPct = (b.signals / item.top_booths[0].signals) * 100;
                  const neg  = b.avg_polarity < -0.05;
                  return (
                    <div key={b.booth_id}>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span style={{ color: "var(--text-2)" }}>
                          {b.booth_name || b.booth_id}
                          {b.locality_hint && (
                            <span style={{ color: "var(--text-4)" }}> · {b.locality_hint}</span>
                          )}
                        </span>
                        <span className="mono font-bold" style={{ color: neg ? "#cc2200" : "var(--text-2)" }}>
                          {b.signals}
                        </span>
                      </div>
                      <div className="h-1 rounded-full" style={{ background: "var(--bg-base)" }}>
                        <div className="h-1 rounded-full"
                          style={{ width: `${bPct}%`, background: neg ? "#cc2200" : "#003380" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Evidence snippets */}
          {item.evidence.length > 0 && (
            <div>
              <p className="text-xs font-bold mb-2" style={{ color: "var(--text-3)" }}>
                Source Evidence
              </p>
              <div className="flex flex-col gap-2">
                {item.evidence.map((e, i) => (
                  <div key={i} className="rounded p-2.5"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                    <p className="text-xs leading-5" style={{ color: "var(--text-2)" }}>
                      &ldquo;{e.text}&rdquo;
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="mono text-xs" style={{ color: "var(--text-4)" }}>{e.source}</span>
                      <span style={{ color: "var(--text-4)", fontSize: 10 }}>·</span>
                      {e.polarity < 0
                        ? <ThumbsDown size={10} style={{ color: "#cc2200" }} />
                        : <ThumbsUp size={10} style={{ color: "#138808" }} />}
                      <span className="mono text-xs" style={{ color: "var(--text-4)" }}>
                        conf {(e.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default async function PainPointsPage() {
  const [breakdownR, narrativesR] = await Promise.allSettled([
    api.issueBreakdown(AC_ID),
    api.narratives(AC_ID),
  ]);

  const breakdown  = breakdownR.status  === "fulfilled" ? breakdownR.value.issues : [];
  const narratives = narrativesR.status === "fulfilled" ? narrativesR.value.narratives : [];

  const totalSignals  = breakdown.reduce((s, i) => s + i.total_signals, 0);
  const totalBooths   = breakdown.reduce((s, i) => s + i.affected_booth_count, 0);
  const highCount     = breakdown.filter((i) => i.severity === "high").length;
  const risingCount   = breakdown.filter((i) => i.trend === "rising").length;

  return (
    <div className="min-h-screen p-5" style={{ background: "var(--bg-base)" }}>

      {/* Page header */}
      <div className="mb-5">
        <p className="text-xs font-semibold" style={{ color: "#003380" }}>Why is it happening?</p>
        <h1 className="mt-1 text-xl font-bold" style={{ color: "var(--text-1)" }}>Pain Point Engine</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-3)" }}>
          Voter issues extracted from YouTube discourse and booth pulse events — ranked by signal volume,
          with affected booths, evidence snippets, and 7-day trend.
        </p>
      </div>

      {/* Summary strip */}
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "Distinct Issues",    value: fmt(breakdown.length),  icon: BarChart3,  color: "#003380" },
          { label: "Total Signals",      value: fmt(totalSignals),       icon: MessageSquare, color: "#6d28d9" },
          { label: "High Severity",      value: fmt(highCount),          icon: AlertTriangle, color: "#cc2200" },
          { label: "Rising Trends",      value: fmt(risingCount),        icon: TrendingUp,    color: "#d97706" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded p-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold" style={{ color: "var(--text-4)" }}>{label}</span>
              <Icon size={13} style={{ color }} />
            </div>
            <p className="mono text-xl font-bold" style={{ color: "var(--text-1)" }}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">

        {/* ── Issue table ── */}
        <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          {/* Table header */}
          <div className="border-b px-4 py-3" style={{ borderColor: "var(--border)", background: "var(--bg-card-2)" }}>
            <div className="grid items-center gap-3 text-xs font-bold uppercase tracking-wide"
              style={{ gridTemplateColumns: "24px 1fr 120px 60px 60px 24px", color: "var(--text-4)" }}>
              <span>#</span>
              <span>Issue · Severity · Trend</span>
              <span className="text-center">Booths</span>
              <span className="text-center">Signals</span>
              <span className="text-center">Conf</span>
              <span />
            </div>
          </div>

          {breakdown.length === 0 ? (
            <div className="p-8 text-center">
              <AlertTriangle size={24} style={{ color: "var(--text-4)", margin: "0 auto 8px" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>
                No verified issue data available
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-4)" }}>
                Connect the ETL pipeline to populate pulse_events.
              </p>
            </div>
          ) : (
            // Client component needed for expand/collapse — render server-side with no expand
            breakdown.map((item, idx) => (
              <div key={item.issue} style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="px-4 py-3 grid items-center gap-3"
                  style={{ gridTemplateColumns: "24px 1fr 120px 60px 60px 24px" }}>
                  <span className="mono text-xs font-bold" style={{ color: "var(--text-4)" }}>{idx + 1}</span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-sm font-semibold capitalize" style={{ color: "var(--text-1)" }}>
                        {item.issue.replace(/_/g, " ")}
                      </span>
                      <span className="mono text-xs font-bold px-1.5 rounded"
                        style={{
                          background: SEVERITY_STYLE[item.severity].bg,
                          color: SEVERITY_STYLE[item.severity].color,
                          border: `1px solid ${SEVERITY_STYLE[item.severity].border}`,
                        }}>
                        {SEVERITY_STYLE[item.severity].label}
                      </span>
                      <TrendChip trend={item.trend} delta={item.trend_delta_pct} />
                    </div>
                    <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
                      <div className="h-1.5 rounded-full"
                        style={{
                          width: `${(item.total_signals / Math.max(...breakdown.map((i) => i.total_signals))) * 100}%`,
                          background: SEVERITY_STYLE[item.severity].color,
                        }} />
                    </div>
                    <div className="flex h-1 rounded-full overflow-hidden mt-0.5" style={{ background: "var(--bg-base)" }}>
                      <div style={{
                        width: `${item.total_signals > 0 ? (item.negative_count / item.total_signals) * 100 : 0}%`,
                        background: "#cc2200",
                      }} />
                      <div style={{
                        width: `${item.total_signals > 0 ? (item.positive_count / item.total_signals) * 100 : 0}%`,
                        background: "#138808",
                      }} />
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="mono text-sm font-bold" style={{ color: "var(--text-1)" }}>{item.affected_booth_count}</p>
                    <p className="text-xs" style={{ color: "var(--text-4)" }}>booths</p>
                  </div>
                  <div className="text-center">
                    <p className="mono text-sm font-bold" style={{ color: SEVERITY_STYLE[item.severity].color }}>
                      {fmt(item.total_signals)}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-4)" }}>signals</p>
                  </div>
                  <div className="text-center">
                    <p className="mono text-sm font-bold" style={{ color: "var(--text-2)" }}>
                      {(item.avg_confidence * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-4)" }}>conf</p>
                  </div>
                </div>

                {/* Top booths + evidence — always shown on server render */}
                {(item.top_booths.length > 0 || item.evidence.length > 0) && (
                  <div className="px-4 pb-4 grid gap-4 md:grid-cols-2"
                    style={{ background: "var(--bg-card-2)", borderTop: "1px solid var(--border)" }}>
                    {item.top_booths.length > 0 && (
                      <div className="pt-3">
                        <p className="text-xs font-bold mb-2" style={{ color: "var(--text-3)" }}>Top Affected Booths</p>
                        <div className="flex flex-col gap-1.5">
                          {item.top_booths.map((b) => {
                            const bPct = (b.signals / item.top_booths[0].signals) * 100;
                            return (
                              <div key={b.booth_id}>
                                <div className="flex justify-between text-xs mb-0.5">
                                  <span style={{ color: "var(--text-2)" }}>
                                    {b.booth_name || b.booth_id}
                                    {b.locality_hint && (
                                      <span style={{ color: "var(--text-4)" }}> · {b.locality_hint}</span>
                                    )}
                                  </span>
                                  <span className="mono font-bold" style={{ color: b.avg_polarity < -0.05 ? "#cc2200" : "var(--text-2)" }}>
                                    {b.signals}
                                  </span>
                                </div>
                                <div className="h-1 rounded-full" style={{ background: "var(--bg-base)" }}>
                                  <div className="h-1 rounded-full"
                                    style={{ width: `${bPct}%`, background: b.avg_polarity < -0.05 ? "#cc2200" : "#003380" }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                    {item.evidence.length > 0 && (
                      <div className="pt-3">
                        <p className="text-xs font-bold mb-2" style={{ color: "var(--text-3)" }}>Source Evidence</p>
                        <div className="flex flex-col gap-2">
                          {item.evidence.map((e, i) => (
                            <div key={i} className="rounded p-2.5"
                              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                              <p className="text-xs leading-5" style={{ color: "var(--text-2)" }}>
                                &ldquo;{e.text.slice(0, 160)}{e.text.length > 160 ? "…" : ""}&rdquo;
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="mono text-xs" style={{ color: "var(--text-4)" }}>{e.source}</span>
                                <span style={{ color: "var(--text-4)", fontSize: 10 }}>·</span>
                                {e.polarity < 0
                                  ? <ThumbsDown size={10} style={{ color: "#cc2200" }} />
                                  : <ThumbsUp size={10} style={{ color: "#138808" }} />}
                                <span className="mono text-xs" style={{ color: "var(--text-4)" }}>
                                  {(e.confidence * 100).toFixed(0)}% conf
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </section>

        {/* ── Right: narrative analysis ── */}
        <div className="flex flex-col gap-4">
          <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <Brain size={15} style={{ color: "#6d28d9" }} />
              <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Narrative Detection</h2>
            </div>
            {narratives.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>
                No verified narrative data available.
              </p>
            ) : (
              <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {narratives.map((n, i) => {
                  const label    = NARRATIVE_LABELS[n.narrative_type] ?? n.narrative_type.replace(/_/g, " ");
                  const strength = (n as { strength?: number; avg_strength?: number }).strength
                    ?? (n as { strength?: number; avg_strength?: number }).avg_strength
                    ?? 0;
                  const boothCount = (n as { booth_count?: number }).booth_count;
                  const evidence   = (n as { total_evidence?: number }).total_evidence;
                  const isHot = strength > 0.65;
                  return (
                    <div key={i} className="px-4 py-3">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-bold capitalize" style={{ color: "var(--text-1)" }}>{label}</span>
                        <span className="mono text-xs font-bold" style={{ color: isHot ? "#cc2200" : "#6d28d9" }}>
                          {(strength * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="flex gap-3 text-xs mb-1.5" style={{ color: "var(--text-4)" }}>
                        {boothCount != null && <span>{boothCount} booths</span>}
                        {evidence   != null && <span>{evidence} evidence</span>}
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "var(--bg-base)" }}>
                        <div className="h-1.5 rounded-full"
                          style={{ width: `${strength * 100}%`, background: isHot ? "#cc2200" : "#6d28d9" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Issue → action quick link */}
          {breakdown.filter((i) => i.severity === "high").length > 0 && (
            <div className="rounded p-4" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
              <p className="text-xs font-bold mb-2" style={{ color: "#cc2200" }}>High-Severity Issues</p>
              <div className="flex flex-col gap-1.5">
                {breakdown.filter((i) => i.severity === "high").map((i) => (
                  <div key={i.issue} className="flex items-center justify-between text-xs">
                    <span className="capitalize font-semibold" style={{ color: "#7f1d1d" }}>
                      {i.issue.replace(/_/g, " ")}
                    </span>
                    <span className="mono font-bold" style={{ color: "#cc2200" }}>
                      {fmt(i.total_signals)} · {i.affected_booth_count}B
                    </span>
                  </div>
                ))}
              </div>
              <a href="/actions"
                className="mt-3 inline-flex items-center gap-1 text-xs font-bold"
                style={{ color: "#cc2200" }}>
                → View recommended actions
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
