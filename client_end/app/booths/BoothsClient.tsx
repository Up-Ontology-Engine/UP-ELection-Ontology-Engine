"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { BoothRow } from "@/lib/api";
import LeanBadge from "@/components/LeanBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import SectionHeader from "@/components/SectionHeader";
import {
  Search, Filter, Download, ArrowUpDown, ArrowUp, ArrowDown,
  Activity, Users, ChevronLeft, ChevronRight, X
} from "lucide-react";

type SortKey = keyof BoothRow;
type SortDir = "asc" | "desc";

const LEAN_OPTIONS = ["STRONG_BJP", "LEAN_BJP", "NEUTRAL", "LEAN_OPP", "STRONG_OPP", "INSUFFICIENT"];
const CONF_OPTIONS = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"];

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

interface Props { booths: BoothRow[] }

export default function BoothsClient({ booths }: Props) {
  const [search, setSearch]       = useState("");
  const [leanFilter, setLean]     = useState<string[]>([]);
  const [confFilter, setConf]     = useState<string[]>([]);
  const [sortKey, setSortKey]     = useState<SortKey>("booth_number");
  const [sortDir, setSortDir]     = useState<SortDir>("asc");
  const [page, setPage]           = useState(1);
  const [showFilters, setFilters] = useState(false);
  const [minVoters, setMin]       = useState("");
  const [maxVoters, setMax]       = useState("");
  const PAGE_SIZE = 30;

  const filtered = useMemo(() => {
    let data = [...booths];
    if (search) {
      const q = search.toLowerCase();
      data = data.filter((b) =>
        b.name?.toLowerCase().includes(q) ||
        String(b.booth_number).includes(q) ||
        b.locality_hint?.toLowerCase().includes(q) ||
        b.top_issue?.toLowerCase().includes(q)
      );
    }
    if (leanFilter.length > 0) data = data.filter((b) => leanFilter.includes(b.digital_lean_label?.toUpperCase() ?? ""));
    if (confFilter.length > 0) data = data.filter((b) => confFilter.includes(b.confidence_label?.toUpperCase() ?? ""));
    if (minVoters) data = data.filter((b) => (b.total_voters ?? 0) >= parseInt(minVoters));
    if (maxVoters) data = data.filter((b) => (b.total_voters ?? 0) <= parseInt(maxVoters));

    data.sort((a, b) => {
      const av = a[sortKey] as number | string | null;
      const bv = b[sortKey] as number | string | null;
      if (av == null) return 1; if (bv == null) return -1;
      return sortDir === "asc" ? (av < bv ? -1 : av > bv ? 1 : 0) : (av > bv ? -1 : av < bv ? 1 : 0);
    });
    return data;
  }, [booths, search, leanFilter, confFilter, sortKey, sortDir, minVoters, maxVoters]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const pageData = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function sort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
    setPage(1);
  }

  function toggleLean(v: string) {
    setLean((f) => f.includes(v) ? f.filter((x) => x !== v) : [...f, v]);
    setPage(1);
  }
  function toggleConf(v: string) {
    setConf((f) => f.includes(v) ? f.filter((x) => x !== v) : [...f, v]);
    setPage(1);
  }

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey !== k ? <ArrowUpDown size={9} style={{ color: "var(--text-4)" }} />
      : sortDir === "asc" ? <ArrowUp size={9} style={{ color: "#f97316" }} />
        : <ArrowDown size={9} style={{ color: "#f97316" }} />;

  // Summary stats
  const total = booths.length;
  const bjpCount = booths.filter((b) => b.digital_lean_label?.includes("BJP")).length;
  const oppCount = booths.filter((b) => b.digital_lean_label?.includes("OPP")).length;
  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);

  return (
    <div className="p-5 min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <Activity size={15} style={{ color: "#f97316" }} />
            <h1 className="font-bold text-[var(--text-1)]" style={{ fontSize: 15 }}>Booth Intelligence</h1>
            <span className="mono text-xs px-2 py-0.5 rounded"
              style={{ background: "#f9731618", color: "#f97316", border: "1px solid #f9731630" }}>
              {filtered.length}/{total}
            </span>
          </div>
          <p className="text-xs mono" style={{ color: "var(--text-3)" }}>
            AC-322 · {fmt(totalVoters)} registered voters · {bjpCount} BJP-leaning · {oppCount} Opp-leaning
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setFilters((f) => !f)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all"
            style={{
              background: showFilters ? "rgba(249,115,22,0.1)" : "transparent",
              border: `1px solid ${showFilters ? "rgba(249,115,22,0.3)" : "var(--border)"}`,
              color: showFilters ? "#f97316" : "var(--text-2)"
            }}>
            <Filter size={11} />
            Filters {(leanFilter.length + confFilter.length) > 0 ? `(${leanFilter.length + confFilter.length})` : ""}
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs"
            style={{ border: "1px solid var(--border)", color: "var(--text-3)" }}>
            <Download size={11} /> Export
          </button>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-4 md:grid-cols-8 gap-3 mb-4">
        {[
          { label: "Total Booths",  value: total,                      color: "var(--text-1)" },
          { label: "With Pulse",    value: booths.filter((b) => b.bjp_pulse_score != null).length, color: "#10b981" },
          { label: "BJP Lean",      value: bjpCount,                   color: "#f97316" },
          { label: "Opp Lean",      value: oppCount,                   color: "#3b82f6" },
          { label: "Neutral",       value: booths.filter((b) => b.digital_lean_label?.includes("NEUTRAL")).length, color: "#64748b" },
          { label: "High Conf.",    value: booths.filter((b) => b.confidence_label?.toUpperCase() === "HIGH").length, color: "#10b981" },
          { label: "Low Conf.",     value: booths.filter((b) => b.confidence_label?.toUpperCase() === "LOW").length, color: "#ef4444" },
          { label: "Total Voters",  value: fmt(totalVoters),           color: "var(--text-3)" },
        ].map(({ label, value, color }) => (
          <div key={label} className="card px-3 py-2.5">
            <p className="label" style={{ color: "var(--text-4)" }}>{label}</p>
            <p className="mono font-bold mt-0.5" style={{ color, fontSize: 15 }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Search + filters row */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1 relative">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search booth name, number, locality, issue…"
            className="w-full pl-8 pr-4 py-2 rounded-md text-xs text-[var(--text-1)] outline-none"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }} />
          {search && (
            <button onClick={() => { setSearch(""); setPage(1); }}
              className="absolute right-3 top-1/2 -translate-y-1/2">
              <X size={10} style={{ color: "var(--text-3)" }} />
            </button>
          )}
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="card p-4 mb-3 animate-fade-up">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="label mb-2" style={{ color: "var(--text-3)" }}>Political Lean</p>
              <div className="flex flex-wrap gap-1.5">
                {LEAN_OPTIONS.map((opt) => (
                  <button key={opt} onClick={() => toggleLean(opt)}
                    className="px-2 py-1 rounded text-xs mono transition-all"
                    style={{
                      background: leanFilter.includes(opt) ? "rgba(249,115,22,0.15)" : "var(--bg-surface)",
                      border: leanFilter.includes(opt) ? "1px solid rgba(249,115,22,0.4)" : "1px solid var(--border)",
                      color: leanFilter.includes(opt) ? "#f97316" : "var(--text-3)",
                      fontSize: 10
                    }}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="label mb-2" style={{ color: "var(--text-3)" }}>Data Confidence</p>
              <div className="flex flex-wrap gap-1.5">
                {CONF_OPTIONS.map((opt) => (
                  <button key={opt} onClick={() => toggleConf(opt)}
                    className="px-2 py-1 rounded text-xs mono transition-all"
                    style={{
                      background: confFilter.includes(opt) ? "rgba(16,185,129,0.1)" : "var(--bg-surface)",
                      border: confFilter.includes(opt) ? "1px solid rgba(16,185,129,0.3)" : "1px solid var(--border)",
                      color: confFilter.includes(opt) ? "#10b981" : "var(--text-3)",
                      fontSize: 10
                    }}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="label mb-2" style={{ color: "var(--text-3)" }}>Voter Count Range</p>
              <div className="flex gap-2">
                <input value={minVoters} onChange={(e) => { setMin(e.target.value); setPage(1); }}
                  placeholder="Min" className="w-20 px-2 py-1 rounded text-xs mono outline-none"
                  style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-1)" }} />
                <span className="text-xs" style={{ color: "var(--text-3)" }}>—</span>
                <input value={maxVoters} onChange={(e) => { setMax(e.target.value); setPage(1); }}
                  placeholder="Max" className="w-20 px-2 py-1 rounded text-xs mono outline-none"
                  style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", color: "var(--text-1)" }} />
              </div>
              {(leanFilter.length > 0 || confFilter.length > 0 || minVoters || maxVoters) && (
                <button onClick={() => { setLean([]); setConf([]); setMin(""); setMax(""); setPage(1); }}
                  className="mt-2 text-xs hover:underline" style={{ color: "#ef4444" }}>
                  Clear all filters
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full data-table">
            <thead>
              <tr>
                {[
                  { key: "booth_number", label: "#" },
                  { key: "name",         label: "Polling Station" },
                  { key: "locality_hint",label: "Locality" },
                  { key: "total_voters", label: "Voters" },
                  { key: null,           label: "M / F Split" },
                  { key: "bjp_pulse_score", label: "BJP Pulse" },
                  { key: "opp_pulse_score", label: "Opp Pulse" },
                  { key: "digital_lean_label", label: "Lean" },
                  { key: "top_issue",    label: "Top Issue" },
                  { key: "event_count",  label: "Events" },
                  { key: "confidence_label", label: "Confidence" },
                  { key: null,           label: "" },
                ].map(({ key, label }, i) => (
                  <th key={i}>
                    {key ? (
                      <button onClick={() => sort(key as SortKey)} className="flex items-center gap-1 hover:text-[var(--text-1)] transition-colors group">
                        {label} <SortIcon k={key as SortKey} />
                      </button>
                    ) : label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageData.length === 0 ? (
                <tr>
                  <td colSpan={12} className="text-center py-12 text-xs" style={{ color: "var(--text-3)" }}>
                    No booths match your filters.
                  </td>
                </tr>
              ) : pageData.map((b) => {
                const femalePct = (b.total_voters && b.female_voters)
                  ? (b.female_voters / b.total_voters) * 100 : null;
                return (
                  <tr key={b.booth_id}>
                    <td className="mono" style={{ color: "var(--text-3)" }}>{b.booth_number}</td>
                    <td>
                      <Link href={`/booths/${b.booth_id}`}
                        className="text-xs font-medium text-[var(--text-1)] hover:text-orange-400 transition-colors line-clamp-1 max-w-40 block">
                        {b.name}
                      </Link>
                    </td>
                    <td className="text-xs max-w-28 truncate" style={{ color: "var(--text-3)" }}>
                      {b.locality_hint ?? "—"}
                    </td>
                    <td className="mono text-xs" style={{ color: "var(--text-3)" }}>{fmt(b.total_voters)}</td>
                    <td>
                      {femalePct != null ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-14 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-surface)" }}>
                            <div className="h-full" style={{ width: `${100 - femalePct}%`, background: "#3b82f6", display: "inline-block" }} />
                            <div className="h-full" style={{ width: `${femalePct}%`, background: "#ec4899", display: "inline-block" }} />
                          </div>
                          <span className="mono text-xs" style={{ color: "var(--text-3)", fontSize: 9 }}>{femalePct.toFixed(0)}%F</span>
                        </div>
                      ) : <span style={{ color: "var(--text-4)" }}>—</span>}
                    </td>
                    <td>
                      {b.bjp_pulse_score != null ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-10 h-1 rounded-full" style={{ background: "var(--bg-surface)" }}>
                            <div className="h-1 rounded-full" style={{
                              width: `${Math.round(((b.bjp_pulse_score + 1) / 2) * 100)}%`,
                              background: b.bjp_pulse_score > 0 ? "#f97316" : "#ef4444"
                            }} />
                          </div>
                          <span className="mono text-xs" style={{ color: "#f97316" }}>{b.bjp_pulse_score.toFixed(2)}</span>
                        </div>
                      ) : <span className="text-xs" style={{ color: "var(--text-4)" }}>—</span>}
                    </td>
                    <td>
                      {b.opp_pulse_score != null ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-10 h-1 rounded-full" style={{ background: "var(--bg-surface)" }}>
                            <div className="h-1 rounded-full" style={{
                              width: `${Math.round(((b.opp_pulse_score + 1) / 2) * 100)}%`,
                              background: "#3b82f6"
                            }} />
                          </div>
                          <span className="mono text-xs" style={{ color: "#3b82f6" }}>{b.opp_pulse_score.toFixed(2)}</span>
                        </div>
                      ) : <span className="text-xs" style={{ color: "var(--text-4)" }}>—</span>}
                    </td>
                    <td><LeanBadge label={b.digital_lean_label} compact /></td>
                    <td>
                      {b.top_issue ? (
                        <span className="text-xs px-1.5 py-0.5 rounded mono capitalize"
                          style={{ background: "var(--bg-surface)", color: "var(--text-3)", fontSize: 9 }}>
                          {b.top_issue.replace(/_/g, " ")}
                        </span>
                      ) : <span style={{ color: "var(--text-4)" }}>—</span>}
                    </td>
                    <td className="mono text-xs" style={{ color: "var(--text-3)" }}>
                      {b.event_count ?? 0}
                    </td>
                    <td><ConfidenceBadge label={b.confidence_label} /></td>
                    <td>
                      <Link href={`/booths/${b.booth_id}`}
                        className="text-xs px-2 py-1 rounded mono transition-all hover:opacity-80"
                        style={{ background: "var(--bg-surface)", color: "var(--text-3)", border: "1px solid var(--border)", fontSize: 9 }}>
                        DETAIL →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3"
            style={{ borderTop: "1px solid var(--border)", background: "var(--bg-surface)" }}>
            <p className="mono text-xs" style={{ color: "var(--text-3)" }}>
              {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} booths
            </p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="p-1.5 rounded transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-30">
                <ChevronLeft size={12} style={{ color: "var(--text-3)" }} />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p = Math.max(1, Math.min(totalPages - 4, page - 2)) + i;
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className="w-7 h-7 rounded mono text-xs transition-all"
                    style={{
                      background: page === p ? "rgba(249,115,22,0.15)" : "transparent",
                      color: page === p ? "#f97316" : "var(--text-3)",
                      border: page === p ? "1px solid rgba(249,115,22,0.3)" : "1px solid transparent",
                    }}>
                    {p}
                  </button>
                );
              })}
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="p-1.5 rounded transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-30">
                <ChevronRight size={12} style={{ color: "var(--text-3)" }} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
