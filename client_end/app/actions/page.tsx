import { api } from "@/lib/api";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Lightbulb,
  ListChecks,
  Target,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";

const AC_ID = "GKP_URBAN";

const PRIORITY_COLOR: Record<string, string> = {
  high:   "#cc2200",
  medium: "#d97706",
  low:    "#138808",
};
const LEVEL_COLOR: Record<string, string> = {
  high:   "#cc2200",
  medium: "#d97706",
  low:    "#138808",
};

export default async function ActionsPage() {
  const [recsR] = await Promise.allSettled([api.recommendations(AC_ID)]);
  const recs = recsR.status === "fulfilled" ? recsR.value : null;

  const actions      = recs?.actions      ?? [];
  const risks        = recs?.risks        ?? [];
  const opportunities = recs?.opportunities ?? [];

  return (
    <div className="min-h-screen p-5" style={{ background: "var(--bg-base)" }}>

      {/* Page header */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold" style={{ color: "#003380" }}>What should we do?</p>
          <h1 className="mt-1 text-xl font-bold" style={{ color: "var(--text-1)" }}>
            Action Recommendation Engine
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-3)" }}>
            Prioritized actions derived from live booth signals, YouTube discourse, and narrative analysis.
          </p>
        </div>
        {recs && (
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded px-3 py-1" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-2)" }}>
              Lean: <span style={{ color: "#003380" }}>{recs.overall_lean}</span>
            </span>
            <span className="rounded px-3 py-1" style={{
              background: recs.confidence === "HIGH" ? "#eef7ef" : "#fff8e8",
              border: `1px solid ${recs.confidence === "HIGH" ? "#b7dfbc" : "#fcd9a0"}`,
              color: recs.confidence === "HIGH" ? "#0f6b18" : "#92400e",
            }}>
              Confidence: {recs.confidence}
            </span>
          </div>
        )}
      </div>

      {/* Verdict banner */}
      {recs?.verdict && (
        <div className="mb-5 rounded p-3 flex items-center gap-3"
          style={{ background: "#eef3fb", border: "1px solid #c0cfe0", borderLeft: "4px solid #003380" }}>
          <Zap size={14} style={{ color: "#003380", flexShrink: 0 }} />
          <p className="text-sm font-medium" style={{ color: "#002060" }}>{recs.verdict}</p>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">

        {/* ── Actions column ── */}
        <div className="flex flex-col gap-4">
          <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <ListChecks size={15} style={{ color: "#003380" }} />
              <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>
                Recommended Actions
              </h2>
              <span className="ml-auto mono text-xs font-bold px-2 py-0.5 rounded"
                style={{ background: "#eef3fb", color: "#003380" }}>
                {actions.length}
              </span>
            </div>
            <div className="divide-y" style={{ borderColor: "var(--border)" }}>
              {actions.length === 0 ? (
                <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>
                  No recommendations — insufficient booth data collected yet.
                </p>
              ) : actions.map((action, i) => (
                <div key={i} className="p-4 flex gap-4">
                  <div className="flex-none">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-sm text-xs font-bold"
                      style={{ background: PRIORITY_COLOR[action.priority] ?? "#003380", color: "#fff" }}>
                      {i + 1}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-sm font-bold" style={{ color: "var(--text-1)" }}>
                        {action.title}
                      </span>
                      <span className="mono text-xs font-bold px-1.5 py-0.5 rounded"
                        style={{
                          background: action.priority === "high" ? "#fef2f2" : action.priority === "medium" ? "#fffbeb" : "#f0fdf4",
                          color: PRIORITY_COLOR[action.priority] ?? "#003380",
                          border: `1px solid ${PRIORITY_COLOR[action.priority] ?? "#003380"}40`,
                        }}>
                        {action.priority.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm leading-6" style={{ color: "var(--text-3)" }}>
                      {action.description}
                    </p>
                    {action.target_segment && (
                      <div className="mt-2 flex items-center gap-1.5 text-xs" style={{ color: "var(--text-4)" }}>
                        <Users size={11} />
                        <span>Target: <strong style={{ color: "var(--text-2)" }}>{action.target_segment}</strong></span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* ── Risks + Opportunities column ── */}
        <div className="flex flex-col gap-4">

          {/* Risks */}
          <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <Target size={15} style={{ color: "#cc2200" }} />
              <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Risk Signals</h2>
              <span className="ml-auto mono text-xs font-bold px-2 py-0.5 rounded"
                style={{ background: "#fef2f2", color: "#cc2200" }}>
                {risks.length}
              </span>
            </div>
            <div className="divide-y" style={{ borderColor: "var(--border)" }}>
              {risks.length === 0 ? (
                <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>No risk signals detected.</p>
              ) : risks.map((risk, i) => (
                <div key={i} className="p-3 flex gap-3">
                  <div className="mt-0.5 flex-none">
                    <AlertTriangle size={13} style={{ color: LEVEL_COLOR[risk.level] ?? "#d97706" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="text-xs font-bold" style={{ color: "var(--text-1)" }}>{risk.title}</span>
                      <span className="mono text-xs font-bold" style={{ color: LEVEL_COLOR[risk.level] ?? "#d97706" }}>
                        U{risk.urgency_score}
                      </span>
                    </div>
                    <p className="text-xs leading-5" style={{ color: "var(--text-3)" }}>{risk.description}</p>
                    {/* Urgency bar */}
                    <div className="mt-1.5 h-1 rounded-full" style={{ background: "var(--bg-base)" }}>
                      <div className="h-1 rounded-full" style={{
                        width: `${(risk.urgency_score / 10) * 100}%`,
                        background: LEVEL_COLOR[risk.level] ?? "#d97706",
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Opportunities */}
          <section className="rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <TrendingUp size={15} style={{ color: "#138808" }} />
              <h2 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>Opportunities</h2>
            </div>
            <div className="divide-y" style={{ borderColor: "var(--border)" }}>
              {opportunities.length === 0 ? (
                <p className="p-4 text-sm" style={{ color: "var(--text-4)" }}>No opportunities identified.</p>
              ) : opportunities.map((opp, i) => (
                <div key={i} className="p-3 flex gap-3">
                  <div className="mt-0.5 flex-none">
                    <Lightbulb size={13} style={{ color: "#138808" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="text-xs font-bold" style={{ color: "var(--text-1)" }}>{opp.title}</span>
                      <div className="flex gap-1.5 text-xs mono font-bold">
                        <span style={{ color: "#003380" }} title="Impact">I{opp.impact_score}</span>
                        <span style={{ color: "var(--text-4)" }}>/</span>
                        <span style={{ color: "#d97706" }} title="Urgency">U{opp.urgency_score}</span>
                      </div>
                    </div>
                    <p className="text-xs leading-5" style={{ color: "var(--text-3)" }}>{opp.description}</p>
                    {/* Impact bar */}
                    <div className="mt-1.5 h-1 rounded-full" style={{ background: "var(--bg-base)" }}>
                      <div className="h-1 rounded-full" style={{
                        width: `${(opp.impact_score / 10) * 100}%`,
                        background: "#138808",
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Top risk / opportunity summary */}
          {recs && (
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded p-3" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
                <p className="text-xs font-semibold mb-1" style={{ color: "#cc2200" }}>Top Risk</p>
                <p className="text-xs leading-5" style={{ color: "#7f1d1d" }}>{recs.top_risk}</p>
              </div>
              <div className="rounded p-3" style={{ background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                <p className="text-xs font-semibold mb-1" style={{ color: "#138808" }}>Top Opportunity</p>
                <p className="text-xs leading-5" style={{ color: "#14532d" }}>{recs.top_opportunity}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
