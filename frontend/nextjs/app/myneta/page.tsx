"use client";

import { useEffect, useMemo, useState } from "react";
import { GraphNode, GraphEdge, api, Candidate } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";
import GraphCanvas from "../graph/GraphCanvas";
import CandidateDialogue from "./CandidateDialogue";
import {
  ScrollText, Network, Award, AlertTriangle, GraduationCap,
  Wallet, Landmark, Users, ExternalLink, X, Search,
} from "lucide-react";
import { hexToRgba } from "@/lib/colors";

const NODE_COLORS: Record<string, string> = {
  Election:       "#f59e0b",
  Constituency:   "#f97316",
  Party:          "#8b5cf6",
  Candidate:      "#10b981",
  Education:      "#06b6d4",
  Profession:     "#14b8a6",
  CriminalRecord: "#dc2626",
  AssetTier:      "#eab308",
};

const PARTY_COLORS: Record<string, string> = {
  BJP: "#f97316", SP: "#ef4444", BSP: "#3b82f6", INC: "#22c55e",
  AAP: "#06b6d4", AD: "#8b5cf6", IND: "#64748b",
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  Election: Landmark, Constituency: Network, Party: Users, Candidate: Award,
  Education: GraduationCap, Profession: Users, CriminalRecord: AlertTriangle, AssetTier: Wallet,
};

function fmtRs(n: number | null | undefined): string {
  if (!n || n <= 0) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

export default function MyNetaPage() {
  const { theme } = useTheme();
  const [acId, setAcId] = useState("258"); // Default AC for demonstration
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [dossier, setDossier] = useState<GraphNode | null>(null);
  const [canvasKey, setCanvasKey] = useState(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    api.candidates(acId)
      .then((res) => {
        setCandidates(res.candidates);
        setCanvasKey((k) => k + 1);
        setError("");
      })
      .catch((err) => setError(err.message || "Failed to load candidates"))
      .finally(() => setLoading(false));
  }, [acId]);

  // Dynamically build graph elements from live API Candidate data
  const { graph, partyDist, topAssets, criminalFlagged } = useMemo(() => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const pCount: Record<string, number> = {};
    const cFlagged: Candidate[] = [];
    const parties = new Set<string>();

    candidates.forEach((c) => {
      const party = c.party || "IND";
      pCount[party] = (pCount[party] || 0) + 1;
      parties.add(party);

      if (c.criminal_cases && c.criminal_cases > 0) {
        cFlagged.push(c);
      }

      nodes.push({
        id: c.candidate_id,
        label: c.name,
        type: "Candidate",
        properties: { ...c as any, ac_name: acId, election_year: c.election_year || 2022 }
      });

      edges.push({
        source: `party_${party}`,
        target: c.candidate_id,
        type: "REPRESENTS"
      });
    });

    parties.forEach((p) => {
      nodes.push({
        id: `party_${p}`,
        label: p,
        type: "Party",
        properties: { name: p, weight: pCount[p] }
      });
    });

    return {
      graph: { nodes, edges },
      partyDist: Object.entries(pCount).sort((a, b) => b[1] - a[1]),
      topAssets: [...candidates].sort((a, b) => (b.net_worth_rs || 0) - (a.net_worth_rs || 0)).slice(0, 6),
      criminalFlagged: cFlagged,
    };
  }, [candidates, acId]);

  const onSelect = (n: GraphNode) => (n.type === "Candidate" ? setDossier(n) : setSelected(n));

  const filteredCandidates = useMemo(() => {
    const candNodes = graph.nodes.filter(n => n.type === "Candidate");
    if (!search.trim()) return candNodes;
    const q = search.toLowerCase();
    return candNodes.filter((c) =>
      (c.properties.name as string ?? "").toLowerCase().includes(q) ||
      (c.properties.party as string ?? "").toLowerCase().includes(q) ||
      (c.properties.ac_name as string ?? "").toLowerCase().includes(q)
    );
  }, [graph.nodes, search]);

  const S = {
    base: "var(--bg-base)", surface: "var(--bg-surface)", card: "var(--bg-card)",
    hover: "var(--bg-hover)", border: "var(--border)",
    t1: "var(--text-1)", t2: "var(--text-2)", t3: "var(--text-3)", t4: "var(--text-4)",
    saffron: "var(--saffron)",
  };

  const maxParty = partyDist[0]?.[1] ?? 1;

  return (
    <div className="flex" style={{ height: "calc(100vh - 56px)", background: S.base }}>
      {/* ── Left panel ── */}
      <div className="w-80 shrink-0 flex flex-col overflow-y-auto"
        style={{ borderRight: `1px solid ${S.border}` }}>

        <div className="px-4 py-3.5" style={{ borderBottom: `1px solid ${S.border}` }}>
          <div className="flex items-center gap-2 mb-0.5">
            <div className="w-6 h-6 rounded flex items-center justify-center"
              style={{ background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)" }}>
              <ScrollText size={12} style={{ color: S.saffron }} />
            </div>
            <h1 className="text-sm font-bold" style={{ color: S.t1 }}>My Neta Report Card</h1>
          </div>
          <p className="text-xs" style={{ color: S.t3 }}>
            Live candidate profiles mapped from Postgres
          </p>
        </div>

        {/* Search bar */}
        <div className="px-3 py-2.5" style={{ borderBottom: `1px solid ${S.border}` }}>
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
            style={{ background: S.surface, border: `1px solid ${S.border}` }}>
            <Search size={12} style={{ color: S.t4, flexShrink: 0 }} />
            <input
              type="text"
              placeholder="Search candidate, party…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setSelected(null); }}
              className="flex-1 bg-transparent outline-none text-xs"
              style={{ color: S.t1, caretColor: S.saffron }}
            />
            {search && (
              <button onClick={() => setSearch("")} style={{ color: S.t4, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                <X size={11} />
              </button>
            )}
          </div>
        </div>

        {/* Search results list */}
        {search.trim() && (
          <div className="flex-1 overflow-y-auto">
            {filteredCandidates.length === 0 ? (
              <div className="px-4 py-6 text-center text-xs" style={{ color: S.t4 }}>
                No candidates match &quot;{search}&quot;
              </div>
            ) : (
              <div className="p-2 space-y-1">
                <p className="text-xs px-2 py-1" style={{ color: S.t4 }}>
                  {filteredCandidates.length} candidate{filteredCandidates.length !== 1 ? "s" : ""} found
                </p>
                {filteredCandidates.map((c) => {
                  const party = (c.properties.party as string) ?? "IND";
                  const color = PARTY_COLORS[party] ?? "#64748b";
                  return (
                    <button key={c.id} onClick={() => setDossier(c)}
                      className="w-full text-left px-3 py-2.5 rounded-lg transition-all"
                      style={{ background: S.surface, border: `1px solid ${S.border}` }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = S.hover)}
                      onMouseLeave={(e) => (e.currentTarget.style.background = S.surface)}>
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-white font-bold shrink-0"
                          style={{ background: color, fontSize: 10 }}>
                          {party.slice(0, 2)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold truncate" style={{ color: S.t1 }}>
                            {c.properties.name as string}
                          </p>
                          <p className="text-xs truncate" style={{ color: S.t4, fontSize: 10 }}>
                            {party} · {c.properties.ac_name as string} · {c.properties.election_year as number}
                          </p>
                        </div>
                        <ExternalLink size={10} style={{ color: S.t4, flexShrink: 0 }} />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {!search.trim() && selected ? (
          <NodeDetail node={selected} onClose={() => setSelected(null)} S={S} />
        ) : !search.trim() ? (
          <div className="p-4 space-y-5">
            {/* Overview stats */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Candidates", val: candidates.length, color: NODE_COLORS.Candidate, icon: Award },
                { label: "Constituencies", val: 1, color: NODE_COLORS.Constituency, icon: Network },
                { label: "Parties", val: partyDist.length, color: NODE_COLORS.Party, icon: Users },
                { label: "Criminal-flagged", val: criminalFlagged.length, color: NODE_COLORS.CriminalRecord, icon: AlertTriangle },
              ].map(({ label, val, color, icon: Icon }) => (
                <div key={label} className="rounded-lg p-3" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon size={11} style={{ color }} />
                    <span className="text-xs" style={{ color: S.t4 }}>{label}</span>
                  </div>
                  <p className="mono text-xl font-bold tabular-nums" style={{ color }}>{val}</p>
                </div>
              ))}
            </div>

            {/* Party distribution */}
            <div>
              <p className="label mb-2" style={{ color: S.t4 }}>Candidates by Party</p>
              <div className="space-y-1.5">
                {partyDist.slice(0, 8).map(([party, n]) => {
                  const color = PARTY_COLORS[party] ?? "#64748b";
                  return (
                    <div key={party} className="flex items-center gap-2">
                      <span className="text-xs w-12 truncate" style={{ color: S.t2 }}>{party}</span>
                      <div className="flex-1 h-1.5 rounded-full" style={{ background: S.border }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${(n / maxParty) * 100}%`, background: color }} />
                      </div>
                      <span className="mono text-xs w-5 text-right tabular-nums" style={{ color }}>{n}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top by assets */}
            <div>
              <p className="label mb-2" style={{ color: S.t4 }}>Wealthiest Candidates</p>
              <div className="space-y-1">
                {topAssets.map((c) => (
                  <button key={c.candidate_id} onClick={() => setDossier(graph.nodes.find(n => n.id === c.candidate_id) || null)}
                    className="w-full text-left px-2.5 py-2 rounded-md flex items-center gap-2 transition-all"
                    style={{ background: S.surface, border: `1px solid ${S.border}` }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = S.hover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = S.surface)}>
                    <div className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: PARTY_COLORS[c.party] ?? "#64748b" }} />
                    <span className="flex-1 text-xs truncate" style={{ color: S.t2 }}>{c.name}</span>
                    <span className="mono text-xs shrink-0 tabular-nums" style={{ color: NODE_COLORS.AssetTier }}>
                      {fmtRs(c.net_worth_rs)}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="rounded-md px-3 py-2.5 text-xs"
                style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", color: "#dc2626" }}>
                {error}
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* ── Graph canvas ── */}
      <div className="flex-1 relative">
        {/* Title chip */}
        <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-3 py-1.5 rounded-md"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <Network size={12} style={{ color: "var(--saffron)" }} />
          <span className="text-xs" style={{ color: "var(--text-2)" }}>Parties → Candidates · click a candidate</span>
        </div>

        {/* Legend */}
        <div className="absolute top-3 right-3 z-10 rounded-lg p-2.5"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex flex-col gap-1">
            {[["Party", NODE_COLORS.Party], ["Candidate", NODE_COLORS.Candidate]].map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                <span className="text-xs" style={{ color: "var(--text-3)", fontSize: 10 }}>{type}</span>
              </div>
            ))}
          </div>
        </div>

        {!loading && graph.nodes.length > 0 ? (
          <GraphCanvas
            key={canvasKey}
            nodes={graph.nodes}
            edges={graph.edges}
            nodeColors={NODE_COLORS}
            selectedId={selected?.id}
            theme={theme}
            onSelect={onSelect}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center" style={{ color: "var(--text-4)" }}>
            <ScrollText size={28} className="mb-2" />
            <p className="text-xs">{error || (loading ? "Loading live candidate data…" : "No candidates found.")}</p>
          </div>
        )}
      </div>

      {/* ── Candidate dialogue ── */}
      {dossier && (
        <CandidateDialogue
          electionYear={Number(dossier.properties.election_year || new Date().getFullYear())}
          candidateData={dossier.properties as unknown as Candidate}
          onClose={() => setDossier(null)}
        />
      )}
    </div>
  );
}

// ── Selected-node detail (candidate report card) ────────────────────────────

function NodeDetail({ node, onClose, S }: {
  node: GraphNode;
  onClose: () => void;
  S: Record<string, string>;
}) {
  const p = node.properties;
  const Icon = TYPE_ICONS[node.type] ?? Network;
  const color = NODE_COLORS[node.type] ?? "#64748b";

  if (node.type === "Candidate") {
    const party = (p.party as string) ?? "IND";
    const partyColor = PARTY_COLORS[party] ?? "#64748b";
    const criminal = (p.criminal_cases as number) ?? 0;
    return (
      <div className="p-4 space-y-4">
        <button onClick={onClose} className="flex items-center gap-1 text-xs" style={{ color: S.t4 }}>
          <X size={11} /> Back to overview
        </button>

        <div className="rounded-lg p-3" style={{ background: hexToRgba(partyColor, "10"), border: `1px solid ${hexToRgba(partyColor, "35")}` }}>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0"
              style={{ background: partyColor, color: "#fff" }}>{party.slice(0, 3)}</div>
            <div className="min-w-0">
              <p className="font-bold text-sm truncate" style={{ color: S.t1 }}>{p.name as string}</p>
              <p className="text-xs" style={{ color: S.t3 }}>{p.ac_name as string} · {p.election_year as number}</p>
            </div>
            {p.is_winner ? <Award size={14} style={{ color: S.saffron, marginLeft: "auto" }} /> : null}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {[
            { label: "Total Assets", val: fmtRs(p.net_worth_rs as number), color: NODE_COLORS.AssetTier },
            { label: "Liabilities", val: p.total_liabilities || "—", color: "#ef4444" },
            { label: "Criminal Cases", val: String(criminal), color: criminal > 0 ? "#dc2626" : S.t2 },
            { label: "Age", val: p.age != null ? String(p.age) : "—", color: S.t2 },
          ].map(({ label, val, color: c }) => (
            <div key={label} className="rounded-md p-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
              <p className="text-xs mb-0.5" style={{ color: S.t4, fontSize: 10 }}>{label}</p>
              <p className="mono text-sm font-bold tabular-nums" style={{ color: c }}>{val}</p>
            </div>
          ))}
        </div>

        <div className="rounded-md px-3 py-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
          <p className="text-xs mb-1" style={{ color: S.t4, fontSize: 10 }}>EDUCATION</p>
          <p className="text-xs" style={{ color: S.t2 }}>{(p.education as string) || "Not stated"}</p>
          {p.self_profession ? (
            <>
              <p className="text-xs mt-2 mb-1" style={{ color: S.t4, fontSize: 10 }}>PROFESSION</p>
              <p className="text-xs" style={{ color: S.t2 }}>{p.self_profession as string}</p>
            </>
          ) : null}
        </div>

        {p.history_json && (
          <div className="mt-4 pt-3 border-t text-xs text-slate-500 overflow-x-hidden">
             See detailed dossier for rich history and financials.
          </div>
        )}
      </div>
    );
  }

  // Generic detail for non-candidate nodes
  return (
    <div className="p-4 space-y-4">
      <button onClick={onClose} className="flex items-center gap-1 text-xs" style={{ color: S.t4 }}>
        <X size={11} /> Back to overview
      </button>
        <div className="rounded-lg p-3" style={{ background: hexToRgba(color, "10"), border: `1px solid ${hexToRgba(color, "35")}` }}>
        <div className="flex items-center gap-2 mb-1">
          <Icon size={13} style={{ color }} />
          <p className="text-xs font-semibold" style={{ color }}>{node.type}</p>
        </div>
        <p className="text-sm font-bold" style={{ color: S.t1 }}>{(p.name as string) ?? node.label}</p>
      </div>
      <div className="rounded-md px-3 py-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
        <p className="text-xs" style={{ color: S.t3 }}>
          {node.type === "Party" && "Click candidates in the graph to inspect each neta's report card."}
          {node.type === "Constituency" && `Candidates who contested ${(p.ac_name as string) ?? ""} in ${(p.year as number) ?? ""}.`}
          {node.type === "Election" && `All constituencies and candidates in the ${(p.year as number) ?? ""} election.`}
          {node.type === "Education" && "Candidates with this declared education level."}
          {node.type === "AssetTier" && "Candidates whose declared assets fall in this band."}
          {node.type === "CriminalRecord" && "Candidates who declared one or more criminal cases."}
          {node.type === "Profession" && "Candidates with this declared profession."}
        </p>
      </div>
      <div className="text-xs" style={{ color: S.t4 }}>
        Graph connections: {(p.weight as number) ?? 0}
      </div>
    </div>
  );
}
