"use client";

import { useState, useEffect, useCallback } from "react";
import {
  api,
  type ConversionBoothSummary,
  type ConversionStats,
  type BeneficiaryRow,
  type PartyLean,
} from "@/lib/api";
import {
  Target, Users, Phone, MapPin, CheckCircle2, ChevronRight,
  RefreshCw, Upload, Loader, AlertCircle, TrendingUp,
  Filter, Search, Home, Zap, FileText,
} from "lucide-react";

const AC_ID = process.env.NEXT_PUBLIC_PILOT_AC ?? "GKP_URBAN";

// ── Party lean styling ────────────────────────────────────────────────────────

const LEAN_META: Record<PartyLean, { label: string; color: string; bg: string }> = {
  BJP:     { label: "BJP",     color: "#f97316", bg: "rgba(249,115,22,0.12)"  },
  SP:      { label: "SP",      color: "#ef4444", bg: "rgba(239,68,68,0.12)"   },
  BSP:     { label: "BSP",     color: "#a78bfa", bg: "rgba(167,139,250,0.12)" },
  INC:     { label: "INC",     color: "#60a5fa", bg: "rgba(96,165,250,0.12)"  },
  OTHERS:  { label: "OTHERS",  color: "var(--text-3)", bg: "rgba(148,163,184,0.12)" },
  UNKNOWN: { label: "?",       color: "#f59e0b", bg: "rgba(245,158,11,0.12)"  },
};

function LeanBadge({ lean }: { lean: PartyLean }) {
  const m = LEAN_META[lean] ?? LEAN_META.UNKNOWN;
  return (
    <span className="mono px-1.5 py-0.5 rounded text-xs font-bold"
      style={{ background: m.bg, color: m.color, fontSize: 9 }}>
      {m.label}
    </span>
  );
}

// ── Conversion script per scheme ──────────────────────────────────────────────

const SCHEME_SCRIPTS: Record<string, string> = {
  "PM Awas Yojana":        "PM Awas Yojana ke tahat aapko greh nirman sahayata mili. Yeh vartaman sarkar ke prayas se sambhav hua. Vikas jaari rakhne ke liye sahi pratinidhi ko samarthan den.",
  "PM Kisan Samman Nidhi": "PM Kisan ke antargat aapko ₹6,000 varshik sahayata milti hai. Iss yojana ko jaari rakhne ke liye uchit sarkar ka samarthan zaruri hai.",
  "Ujjwala Yojana":        "Ujjwala Yojana se aapko muft LPG connection mila. Mahilaon ke jeevan ko aasaan banane ki yeh pehel vartaman sarkaar ki hai.",
  "Ayushman Bharat":       "Ayushman Bharat se aapke parivar ko ₹5 lakh tak ka muft ilaj milta hai. Is suraksha kavach ko banaye rakhne ke liye sahi netatva zaruri hai.",
  "Jan Dhan Yojana":       "Jan Dhan ke zariye aapka bank account khula. Vittiya samaveshan ki is mahan yojana ke nirmata aapke saath hain.",
  "Swachh Bharat Mission": "Swachh Bharat ke antargat aapko shauchalaya banane mein madad mili. Swasthya aur swachhata ki yeh yojana aage bhi jaari rahegi.",
  "PM Mudra Yojana":       "PM Mudra Loan se aapke vyavsay ko sambal mila. Laghu udyog ko badhawa dene wali is sarkar ka samarthan karein.",
  "Kisan Credit Card":     "Kisan Credit Card se aapko sasta karz mila. Kisan hitaishi is sarkar ke saath khade rahen.",
  "Sukanya Samriddhi":     "Sukanya Samriddhi se aapki beti ka bhavishya surakshit hai. Betiyon ke liye kaam karne wali sarkar ko aage bhi mauka den.",
  "PM Garib Kalyan Anna":  "PM Garib Kalyan Anna Yojana se aapko muft rashan milta hai. Is sahayata ko jaari rakhne ke liye sahi sarkar chunna zaruri hai.",
};

function getScript(scheme: string, name: string): string {
  const base = SCHEME_SCRIPTS[scheme]
    ?? `${name} ji, aap sarkari yojana ke labhaarthi hain. Vikas ko jaari rakhne ke liye sahi pratinidhi ko samarthan den.`;
  return base;
}

// ── Booth card (left sidebar) ─────────────────────────────────────────────────

function BoothCard({
  booth, active, onClick,
}: {
  booth: ConversionBoothSummary;
  active: boolean;
  onClick: () => void;
}) {
  const pct = booth.total > 0 ? Math.round((booth.targets_contacted / Math.max(booth.targets, 1)) * 100) : 0;
  const remainingTargets = booth.targets - booth.targets_contacted;

  return (
    <button onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg mb-1.5 transition-all ${active ? "" : "hover:bg-white/3"}`}
      style={{
        background: active ? "var(--bg-surface)" : "transparent",
        border: active ? "1px solid #1a3a5c" : "1px solid transparent",
      }}>
      <div className="flex items-start justify-between gap-1 mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="mono font-bold" style={{ color: active ? "#60a5fa" : "var(--text-3)", fontSize: 11 }}>
            {booth.booth_number}
          </span>
          <span className="text-xs truncate max-w-28" style={{ color: active ? "var(--text-3)" : "var(--text-3)", fontSize: 10 }}>
            {booth.booth_name?.split(" ").slice(0, 3).join(" ")}
          </span>
        </div>
        {remainingTargets > 0 && (
          <span className="mono px-1.5 py-0.5 rounded flex-shrink-0"
            style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", fontSize: 8, border: "1px solid rgba(239,68,68,0.2)" }}>
            {remainingTargets} left
          </span>
        )}
      </div>

      {/* Funnel bar: BJP | UNKNOWN | OPP */}
      {booth.total > 0 && (
        <div className="flex rounded overflow-hidden h-1.5 mb-1.5" style={{ gap: 1 }}>
          <div style={{ width: `${(booth.supporters / booth.total) * 100}%`, background: "#f97316", minWidth: booth.supporters > 0 ? 2 : 0 }} />
          <div style={{ width: `${(booth.unknown_lean / booth.total) * 100}%`, background: "#f59e0b", minWidth: booth.unknown_lean > 0 ? 2 : 0 }} />
          <div style={{ width: `${(booth.opp_lean / booth.total) * 100}%`, background: "#ef4444", minWidth: booth.opp_lean > 0 ? 2 : 0 }} />
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>
          {booth.total} benef · {booth.targets} targets
        </span>
        <span className="mono" style={{ color: pct > 50 ? "#10b981" : "#2e4260", fontSize: 9 }}>
          {pct}% reached
        </span>
      </div>
    </button>
  );
}

// ── Beneficiary contact card (route map) ─────────────────────────────────────

function BeneficiaryCard({
  b, onContacted,
}: {
  b: BeneficiaryRow;
  onContacted: (id: string, notes: string) => void;
}) {
  const [expanded,  setExpanded]  = useState(false);
  const [showScript, setShowScript] = useState(false);
  const [notes,     setNotes]     = useState(b.contact_notes ?? "");
  const [saving,    setSaving]    = useState(false);

  const isTarget = b.party_lean !== "BJP";
  const borderColor = b.contacted ? "#10b981" : isTarget ? (b.party_lean === "UNKNOWN" ? "#f59e0b" : "#ef4444") : "#f97316";

  async function handleContact() {
    setSaving(true);
    await onContacted(b.beneficiary_id, notes);
    setSaving(false);
    setExpanded(false);
  }

  return (
    <div className="rounded-xl overflow-hidden transition-all"
      style={{ background: "var(--bg-card)", border: `1px solid ${b.contacted ? "#10b98130" : borderColor + "20"}` }}>
      {/* Main row */}
      <div className="px-4 py-3 flex items-start gap-3">
        {/* Priority indicator */}
        <div className="w-1 self-stretch rounded-full flex-shrink-0"
          style={{ background: b.contacted ? "#10b981" : borderColor }} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <p className="font-medium text-sm text-[var(--text-1)]">{b.name}</p>
            <LeanBadge lean={b.party_lean} />
            {b.contacted && (
              <span className="mono flex items-center gap-1 px-1.5 py-0.5 rounded"
                style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", fontSize: 9, border: "1px solid rgba(16,185,129,0.2)" }}>
                <CheckCircle2 size={8} /> Contacted {b.contact_date ?? ""}
              </span>
            )}
          </div>

          {b.father_name && (
            <p className="text-xs mb-1" style={{ color: "var(--text-3)" }}>{b.father_name}</p>
          )}

          <div className="flex items-center gap-3 flex-wrap">
            <span className="flex items-center gap-1 text-xs"
              style={{ background: "rgba(16,185,129,0.08)", color: "#10b981", border: "1px solid rgba(16,185,129,0.15)", borderRadius: 6, padding: "2px 6px", fontSize: 10 }}>
              <FileText size={9} /> {b.scheme_name}
            </span>
            {b.benefit_desc && (
              <span className="text-xs" style={{ color: "var(--text-4)", fontSize: 10 }}>{b.benefit_desc}</span>
            )}
          </div>

          {b.address && (
            <p className="flex items-center gap-1 mt-1 text-xs" style={{ color: "var(--text-4)" }}>
              <MapPin size={9} /> {b.address}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          {b.phone && (
            <a href={`tel:${b.phone}`}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs mono transition-all hover:opacity-80"
              style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.2)" }}>
              <Phone size={10} /> {b.phone}
            </a>
          )}
          {!b.contacted && (
            <button onClick={() => setExpanded((s) => !s)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs mono transition-all"
              style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.2)" }}>
              <CheckCircle2 size={10} /> Mark Contacted
            </button>
          )}
        </div>
      </div>

      {/* Conversion script */}
      {isTarget && (
        <div style={{ borderTop: "1px solid var(--border)" }}>
          <button onClick={() => setShowScript((s) => !s)}
            className="w-full flex items-center gap-2 px-4 py-1.5 text-xs hover:bg-white/3 transition-colors"
            style={{ color: "#a78bfa" }}>
            <Zap size={9} /> Conversion script
            <ChevronRight size={9} className={`ml-auto transition-transform ${showScript ? "rotate-90" : ""}`} />
          </button>
          {showScript && (
            <div className="px-4 pb-3">
              <div className="rounded-lg p-3 text-xs italic"
                style={{ background: "var(--bg-surface)", color: "var(--text-3)", border: "1px solid var(--border)", lineHeight: 1.7 }}>
                &ldquo;{getScript(b.scheme_name, b.name)}&rdquo;
              </div>
            </div>
          )}
        </div>
      )}

      {/* Contact form */}
      {expanded && !b.contacted && (
        <div className="px-4 pb-3" style={{ borderTop: "1px solid var(--border)" }}>
          <p className="text-xs mb-2 mt-2" style={{ color: "var(--text-3)" }}>
            Add notes (optional):
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Interested, will think about it…"
            rows={2}
            className="w-full rounded-lg px-3 py-2 text-xs resize-none outline-none"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-3)" }}
          />
          <div className="flex gap-2 mt-2">
            <button onClick={handleContact} disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-50 transition-all"
              style={{ background: "rgba(16,185,129,0.15)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)" }}>
              {saving ? <Loader size={10} className="animate-spin" /> : <CheckCircle2 size={10} />}
              Confirm Contact
            </button>
            <button onClick={() => setExpanded(false)}
              className="px-3 py-1.5 rounded-lg text-xs transition-all hover:bg-white/5"
              style={{ color: "var(--text-3)", border: "1px solid var(--border)" }}>
              Cancel
            </button>
          </div>
          {b.contact_notes && (
            <p className="text-xs mt-2" style={{ color: "var(--text-3)" }}>
              Previous: {b.contact_notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Stats KPI card ─────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="rounded-xl px-4 py-3 flex flex-col gap-1"
      style={{ background: "var(--bg-card)", border: `1px solid ${color}20` }}>
      <p className="mono text-xs" style={{ color, fontSize: 9, letterSpacing: "0.1em" }}>{label}</p>
      <p className="text-xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>{sub}</p>}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type FilterTab = "all" | "targets" | "contacted";

export default function ConversionPage() {
  const [stats,       setStats]       = useState<ConversionStats | null>(null);
  const [boothList,   setBoothList]   = useState<ConversionBoothSummary[]>([]);
  const [activeBooth, setActiveBooth] = useState<ConversionBoothSummary | null>(null);
  const [targets,     setTargets]     = useState<BeneficiaryRow[]>([]);
  const [filter,      setFilter]      = useState<FilterTab>("targets");
  const [search,      setSearch]      = useState("");
  const [schemeFilter, setSchemeFilter] = useState("ALL");
  const [loading,     setLoading]     = useState(true);
  const [targetsLoading, setTargetsLoading] = useState(false);
  const [seeding,     setSeeding]     = useState(false);
  const [seedDone,    setSeedDone]    = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, stRes] = await Promise.all([
        api.conversion.overview(AC_ID),
        api.conversion.stats(AC_ID),
      ]);
      setBoothList(ovRes.booths);
      setStats(stRes);
      if (ovRes.booths.length > 0 && !activeBooth) {
        setActiveBooth(ovRes.booths[0]);
      }
    } catch { /* offline */ }
    setLoading(false);
  }, [activeBooth]);

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!activeBooth) return;
    setTargetsLoading(true);
    const contacted = filter === "contacted" ? true : filter === "targets" ? false : undefined;
    api.conversion.targets(activeBooth.booth_id, contacted, 300)
      .then((r) => setTargets(r.targets))
      .catch(() => setTargets([]))
      .finally(() => setTargetsLoading(false));
  }, [activeBooth, filter]);

  async function handleContacted(id: string, notes: string) {
    try {
      await api.conversion.contact(id, notes || undefined);
      setTargets((prev) =>
        prev.map((b) =>
          b.beneficiary_id === id
            ? { ...b, contacted: true, contact_notes: notes || null, contact_date: new Date().toISOString().slice(0, 10) }
            : b
        )
      );
      // refresh booth stats
      setBoothList((prev) =>
        prev.map((b) =>
          b.booth_id === activeBooth?.booth_id
            ? { ...b, contacted: b.contacted + 1, targets_contacted: b.targets_contacted + 1 }
            : b
        )
      );
      if (stats) setStats({ ...stats, total_contacted: stats.total_contacted + 1, targets_contacted: stats.targets_contacted + 1 });
    } catch { /* ignore */ }
  }

  async function handleSeedDemo() {
    setSeeding(true);
    try {
      await api.conversion.seedDemo(AC_ID);
      setSeedDone(true);
      await load();
    } catch { /* ignore */ }
    setSeeding(false);
  }

  const schemes = ["ALL", ...Array.from(new Set(targets.map((t) => t.scheme_name)))];
  const filtered = targets.filter((t) => {
    if (schemeFilter !== "ALL" && t.scheme_name !== schemeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        t.name.toLowerCase().includes(q) ||
        (t.address ?? "").toLowerCase().includes(q) ||
        (t.ward ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const noData = !loading && boothList.length === 0;

  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 flex-shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg,rgba(239,68,68,0.2),rgba(249,115,22,0.2))", border: "1px solid rgba(239,68,68,0.3)" }}>
            <Target size={15} style={{ color: "#ef4444" }} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--text-1)]">Voter Conversion Engine</h1>
            <p className="mono text-xs" style={{ color: "var(--text-4)" }}>
              Beneficiary → Voter Mapping · Booth-Level Route Map
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs hover:bg-white/5 disabled:opacity-40"
            style={{ border: "1px solid var(--border)", color: "var(--text-3)" }}>
            <RefreshCw size={11} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
          {noData && (
            <button onClick={handleSeedDemo} disabled={seeding}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-50"
              style={{ background: "rgba(239,68,68,0.12)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.25)" }}>
              {seeding ? <Loader size={11} className="animate-spin" /> : <Upload size={11} />}
              Load Demo Data
            </button>
          )}
        </div>
      </div>

      {/* KPI bar */}
      {stats && stats.total_beneficiaries > 0 && (
        <div className="flex gap-3 px-5 py-3 flex-shrink-0 overflow-x-auto"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <KpiCard label="TOTAL BENEFICIARIES" value={stats.total_beneficiaries.toLocaleString()}
            sub={`${stats.booths_with_data} booths mapped`} color="#60a5fa" />
          <KpiCard label="CONVERSION TARGETS" value={stats.total_targets.toLocaleString()}
            sub="Non-BJP beneficiaries" color="#ef4444" />
          <KpiCard label="SUPPORTERS MAPPED" value={stats.total_supporters.toLocaleString()}
            sub="Confirmed BJP lean" color="#f97316" />
          <KpiCard label="TARGETS CONTACTED" value={`${stats.target_contact_pct}%`}
            sub={`${stats.targets_contacted} of ${stats.total_targets}`} color="#10b981" />
          <div className="rounded-xl px-4 py-3 flex flex-col gap-1 min-w-48"
            style={{ background: "var(--bg-card)", border: "1px solid #a78bfa20" }}>
            <p className="mono text-xs" style={{ color: "#a78bfa", fontSize: 9, letterSpacing: "0.1em" }}>TOP SCHEMES</p>
            <div className="space-y-1 mt-1">
              {stats.top_schemes.slice(0, 3).map((s) => (
                <div key={s.scheme} className="flex items-center justify-between gap-2">
                  <span className="text-xs truncate" style={{ color: "var(--text-3)", fontSize: 10 }}>{s.scheme}</span>
                  <span className="mono font-bold" style={{ color: "#a78bfa", fontSize: 10 }}>{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Body */}
      {noData ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-5">
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
            style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
            <Target size={36} style={{ color: "#ef444460" }} />
          </div>
          <div className="text-center max-w-sm">
            <p className="font-bold text-[var(--text-1)] mb-2">No Beneficiary Data</p>
            <p className="text-sm mb-4" style={{ color: "var(--text-3)" }}>
              Import real Electoral Roll / scheme data via the API, or load demo data to see the system in action.
            </p>
            <div className="flex gap-3 justify-center">
              <button onClick={handleSeedDemo} disabled={seeding}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
                style={{ background: "rgba(239,68,68,0.12)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.25)" }}>
                {seeding ? <Loader size={14} className="animate-spin" /> : <Upload size={14} />}
                {seeding ? "Seeding…" : "Load Demo Data"}
              </button>
            </div>
            {seedDone && (
              <p className="mono mt-3" style={{ color: "#10b981", fontSize: 11 }}>
                ✓ Demo data loaded! Refreshing…
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Booth sidebar */}
          <div className="w-60 flex-shrink-0 flex flex-col overflow-hidden"
            style={{ borderRight: "1px solid var(--border)", background: "var(--bg-base)" }}>
            <div className="px-3 pt-3 pb-2 flex-shrink-0">
              <p className="mono mb-2 px-1" style={{ color: "var(--text-4)", fontSize: 9, letterSpacing: "0.1em" }}>
                BOOTHS · SORTED BY OPPORTUNITY
              </p>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-3">
              {loading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-16 rounded-lg mb-1.5 animate-pulse"
                      style={{ background: "var(--bg-card)" }} />
                  ))
                : boothList.map((b) => (
                    <BoothCard key={b.booth_id} booth={b}
                      active={activeBooth?.booth_id === b.booth_id}
                      onClick={() => setActiveBooth(b)} />
                  ))
              }
            </div>
          </div>

          {/* Route map */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {activeBooth ? (
              <>
                {/* Route map header */}
                <div className="px-5 py-3 flex items-center gap-4 flex-shrink-0"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div className="flex items-center gap-2">
                      <Home size={13} style={{ color: "#60a5fa" }} />
                      <p className="font-bold text-sm text-[var(--text-1)]">
                        Booth {activeBooth.booth_number} — {activeBooth.booth_name}
                      </p>
                    </div>
                    <p className="mono text-xs mt-0.5" style={{ color: "var(--text-4)" }}>
                      {activeBooth.total} beneficiaries · {activeBooth.targets} targets ·
                      {" "}{activeBooth.targets_contacted} contacted
                    </p>
                  </div>

                  {/* Progress bar */}
                  <div className="flex-1 max-w-48">
                    <div className="flex justify-between mb-1">
                      <span className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>Target progress</span>
                      <span className="mono" style={{ color: "#10b981", fontSize: 9 }}>
                        {activeBooth.targets > 0
                          ? Math.round((activeBooth.targets_contacted / activeBooth.targets) * 100)
                          : 0}%
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-card)" }}>
                      <div className="h-full rounded-full transition-all"
                        style={{
                          width: activeBooth.targets > 0
                            ? `${Math.round((activeBooth.targets_contacted / activeBooth.targets) * 100)}%`
                            : "0%",
                          background: "linear-gradient(90deg,#10b981,#059669)",
                        }} />
                    </div>
                  </div>

                  {/* Lean breakdown */}
                  <div className="flex items-center gap-2">
                    {([["#f97316", "BJP", activeBooth.supporters], ["#f59e0b", "?", activeBooth.unknown_lean], ["#ef4444", "OPP", activeBooth.opp_lean]] as [string, string, number][]).map(([c, l, v]) => (
                      <div key={l} className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                        <span className="mono" style={{ color: "var(--text-4)", fontSize: 9 }}>{l} {v}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Filters */}
                <div className="px-5 py-2.5 flex items-center gap-3 flex-shrink-0"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  {/* Tab filters */}
                  <div className="flex rounded-lg overflow-hidden" style={{ border: "1px solid var(--border)" }}>
                    {([["all", "All"], ["targets", "Targets"], ["contacted", "Contacted"]] as [FilterTab, string][]).map(([v, label]) => (
                      <button key={v} onClick={() => setFilter(v)}
                        className="px-3 py-1.5 text-xs mono transition-colors"
                        style={{
                          background: filter === v ? "var(--bg-hover)" : "transparent",
                          color: filter === v ? "var(--text-1)" : "var(--text-3)",
                          borderRight: v !== "contacted" ? "1px solid var(--border)" : undefined,
                        }}>
                        {label}
                        {v === "targets" && activeBooth.targets > 0 && (
                          <span className="ml-1 px-1 rounded"
                            style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", fontSize: 8 }}>
                            {activeBooth.targets}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Scheme filter */}
                  <select value={schemeFilter} onChange={(e) => setSchemeFilter(e.target.value)}
                    className="text-xs rounded-lg px-2.5 py-1.5 outline-none"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-3)" }}>
                    {schemes.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>

                  {/* Search */}
                  <div className="flex items-center gap-2 rounded-lg px-3 py-1.5 flex-1 max-w-64"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
                    <Search size={11} style={{ color: "var(--text-4)" }} />
                    <input value={search} onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search name, ward, address…"
                      className="bg-transparent outline-none text-xs flex-1 text-[var(--text-1)]"
                      style={{ color: "var(--text-3)" }} />
                  </div>

                  <span className="mono ml-auto" style={{ color: "var(--text-4)", fontSize: 9 }}>
                    {filtered.length} records
                  </span>
                </div>

                {/* Household cards */}
                <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                  {targetsLoading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-24 rounded-xl animate-pulse" style={{ background: "var(--bg-card)" }} />
                      ))
                    : filtered.length === 0
                    ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-3">
                          <AlertCircle size={32} style={{ color: "var(--text-4)" }} />
                          <p className="text-sm" style={{ color: "var(--text-4)" }}>
                            {filter === "contacted" ? "No contacted beneficiaries yet." : "No targets match your filters."}
                          </p>
                        </div>
                      )
                    : filtered.map((b) => (
                        <BeneficiaryCard key={b.beneficiary_id} b={b} onContacted={handleContacted} />
                      ))
                  }
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <TrendingUp size={40} style={{ color: "var(--text-4)" }} />
                <p className="text-sm" style={{ color: "var(--text-4)" }}>Select a booth to open its route map</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
