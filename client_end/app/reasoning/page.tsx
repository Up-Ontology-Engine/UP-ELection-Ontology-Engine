"use client";

import { useState, useRef, useEffect } from "react";
import { api, type ReasoningResult, type WebResult } from "@/lib/api";
import {
  Send, Code, Loader, Terminal, ChevronRight, Globe,
  Database, Zap, ExternalLink, ChevronDown, ChevronUp,
  Brain, Clock, AlertCircle,
} from "lucide-react";

const EXAMPLES = [
  { cat: "Booths",      q: "Which booths have the highest BJP pulse score?" },
  { cat: "Booths",      q: "Show booths with STRONG_OPP lean" },
  { cat: "Issues",      q: "What are the top 5 issues by mention count?" },
  { cat: "Issues",      q: "Which booths have water supply as the top issue?" },
  { cat: "Candidates",  q: "Who won in the 2022 Gorakhpur Urban election?" },
  { cat: "Candidates",  q: "Show candidates with criminal records" },
  { cat: "Intel",       q: "What is the current political situation in Gorakhpur?" },
  { cat: "Intel",       q: "What development schemes are active in Gorakhpur Urban?" },
  { cat: "Intel",       q: "What issues are dominating Gorakhpur politics recently?" },
];

const MODE_CONFIG: Record<string, { label: string; color: string; bg: string; Icon: React.ElementType }> = {
  hybrid: { label: "HYBRID", color: "#a78bfa", bg: "rgba(167,139,250,0.1)", Icon: Zap      },
  graph:  { label: "GRAPH",  color: "#10b981", bg: "rgba(16,185,129,0.1)",  Icon: Database  },
  web:    { label: "WEB",    color: "#3b82f6", bg: "rgba(59,130,246,0.1)",  Icon: Globe     },
  llm:    { label: "LLM",    color: "#f59e0b", bg: "rgba(245,158,11,0.1)",  Icon: Brain     },
};

function SourceCard({ r }: { r: WebResult }) {
  const host = r.url
    ? (() => { try { return new URL(r.url).hostname.replace("www.", ""); } catch { return r.source; } })()
    : r.source;
  return (
    <a href={r.url || "#"} target="_blank" rel="noopener noreferrer"
      className="block rounded-lg p-2.5 transition-all hover:bg-white/5"
      style={{ border: "1px solid #1a2b44", background: "#060e1c" }}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-white line-clamp-2 flex-1">{r.title}</p>
        {r.url && <ExternalLink size={10} className="flex-shrink-0 mt-0.5" style={{ color: "#4d6480" }} />}
      </div>
      <p className="text-xs mt-1 line-clamp-2" style={{ color: "#4d6480" }}>{r.snippet}</p>
      <p className="mono mt-1.5 flex items-center gap-1" style={{ color: "#2e4260", fontSize: 9 }}>
        <Globe size={8} /> {host}
        <span className="ml-1 px-1 rounded" style={{ background: "#0f1929", color: "#2e4260" }}>
          {r.source}
        </span>
      </p>
    </a>
  );
}

function GraphTable({ results }: { results: Record<string, unknown>[] }) {
  if (!results.length) return null;
  const keys = Object.keys(results[0]);
  return (
    <div className="rounded overflow-hidden mt-2" style={{ border: "1px solid #1a2b44" }}>
      <div className="px-3 py-1.5 flex items-center gap-2"
        style={{ background: "#060b14", borderBottom: "1px solid #1a2b44" }}>
        <Database size={10} style={{ color: "#10b981" }} />
        <span className="mono text-xs" style={{ color: "#4d6480" }}>
          {results.length} row{results.length !== 1 ? "s" : ""} from graph
        </span>
      </div>
      <div className="overflow-x-auto max-h-48">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: "#060b14", borderBottom: "1px solid #1a2b44" }}>
              {keys.map((k) => (
                <th key={k} className="px-3 py-1.5 text-left"
                  style={{ color: "#2e4260", fontSize: 9, textTransform: "uppercase" }}>
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.slice(0, 25).map((row, ri) => (
              <tr key={ri} style={{ borderBottom: "1px solid #1a2b4420",
                background: ri % 2 === 0 ? "#0f1929" : "transparent" }}>
                {keys.map((k) => (
                  <td key={k} className="px-3 py-1.5 mono" style={{ color: "#8ba0bc" }}>
                    {String(row[k] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AssistantMessage({ result }: { result: ReasoningResult }) {
  const [showCypher,  setShowCypher]  = useState(false);
  const [showTable,   setShowTable]   = useState(false);
  const [showSources, setShowSources] = useState(false);

  const conf = MODE_CONFIG[result.mode] ?? MODE_CONFIG.llm;
  const { Icon } = conf;
  const hasGraph  = (result.graph_results?.length ?? 0) > 0 &&
    !(result.graph_results?.length === 1 && String(result.graph_results[0]).includes("Cannot answer"));
  const hasWeb    = (result.web_results?.length ?? 0) > 0;
  const hasCypher = Boolean(result.cypher);

  function renderAnswer(text: string) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#f1f5f9">$1</strong>')
      .split("\n")
      .map((line) => {
        if (!line.trim()) return '<div style="height:8px"></div>';
        if (line.match(/^\d+\./))
          return `<div style="margin:3px 0;padding-left:12px;color:#cbd5e1">${line}</div>`;
        if (line.startsWith("* ") || line.startsWith("• "))
          return `<div style="margin:2px 0;padding-left:12px;color:#94a3b8">• ${line.slice(2)}</div>`;
        return `<div style="margin:2px 0;color:#cbd5e1;line-height:1.65">${line}</div>`;
      })
      .join("");
  }

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: "#0b1626", border: "1px solid #1a2b44" }}>
      {/* Mode header */}
      <div className="flex items-center gap-2 px-4 py-2"
        style={{ background: "#070e1b", borderBottom: "1px solid #1a2b4440" }}>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full"
          style={{ background: conf.bg, border: `1px solid ${conf.color}30` }}>
          <Icon size={9} style={{ color: conf.color }} />
          <span className="mono font-bold" style={{ color: conf.color, fontSize: 9 }}>{conf.label}</span>
        </div>
        {hasGraph && (
          <span className="mono" style={{ color: "#2e4260", fontSize: 9 }}>
            {result.row_count} graph rows
          </span>
        )}
        {hasWeb && (
          <span className="mono flex items-center gap-1" style={{ color: "#2e4260", fontSize: 9 }}>
            <Globe size={8} /> {result.web_results.length} sources
          </span>
        )}
        <span className="ml-auto mono flex items-center gap-1" style={{ color: "#1e3a5f", fontSize: 9 }}>
          <Clock size={8} /> {result.elapsed_ms}ms
        </span>
      </div>

      {/* Answer text */}
      <div className="px-4 py-3">
        {result.error && !result.answer && (
          <div className="flex items-start gap-2 text-xs rounded-lg p-2 mb-3"
            style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#fca5a5" }}>
            <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
            <span>{result.error}</span>
          </div>
        )}
        {result.answer && (
          <div className="text-sm" dangerouslySetInnerHTML={{ __html: renderAnswer(result.answer) }} />
        )}
      </div>

      {/* Sources */}
      {hasWeb && (
        <div style={{ borderTop: "1px solid #1a2b4430" }}>
          <button onClick={() => setShowSources((s) => !s)}
            className="w-full flex items-center gap-2 px-4 py-2 text-xs hover:bg-white/3 transition-colors"
            style={{ color: "#3b82f6" }}>
            <Globe size={10} />
            {result.web_results.length} web source{result.web_results.length !== 1 ? "s" : ""}
            {showSources ? <ChevronUp size={10} className="ml-auto" /> : <ChevronDown size={10} className="ml-auto" />}
          </button>
          {showSources && (
            <div className="px-4 pb-3 grid grid-cols-1 gap-2">
              {result.web_results.map((r, i) => <SourceCard key={i} r={r} />)}
            </div>
          )}
        </div>
      )}

      {/* Cypher */}
      {hasCypher && (
        <div style={{ borderTop: "1px solid #1a2b4430" }}>
          <button onClick={() => setShowCypher((s) => !s)}
            className="w-full flex items-center gap-2 px-4 py-2 text-xs hover:bg-white/3 transition-colors"
            style={{ color: "#8b5cf6" }}>
            <Code size={10} /> Cypher query
            {showCypher ? <ChevronUp size={10} className="ml-auto" /> : <ChevronDown size={10} className="ml-auto" />}
          </button>
          {showCypher && (
            <div className="px-4 pb-3">
              <pre className="p-3 rounded text-xs overflow-x-auto"
                style={{ background: "#030508", color: "#8b5cf6", border: "1px solid #1a2b44", fontSize: 11 }}>
                {result.cypher}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Graph table */}
      {hasGraph && (
        <div style={{ borderTop: "1px solid #1a2b4430" }}>
          <button onClick={() => setShowTable((s) => !s)}
            className="w-full flex items-center gap-2 px-4 py-2 text-xs hover:bg-white/3 transition-colors"
            style={{ color: "#10b981" }}>
            <Database size={10} /> Raw graph data ({result.row_count} rows)
            {showTable ? <ChevronUp size={10} className="ml-auto" /> : <ChevronDown size={10} className="ml-auto" />}
          </button>
          {showTable && (
            <div className="px-4 pb-3">
              <GraphTable results={result.graph_results} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface Message {
  role: "user" | "assistant";
  content: string;
  result?: ReasoningResult;
  ts: string;
}

export default function ReasoningPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  function ts() {
    return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  }

  async function submit(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q, ts: ts() }]);
    setLoading(true);
    try {
      const result = await api.reason(q);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.answer || result.summary || "Analysis complete.",
        result,
        ts: ts(),
      }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: `Error: ${msg}`,
        ts: ts(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  const grouped = EXAMPLES.reduce<Record<string, typeof EXAMPLES>>((acc, e) => {
    (acc[e.cat] ??= []).push(e);
    return acc;
  }, {});

  return (
    <div className="flex h-screen flex-col" style={{ background: "#040810" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 flex-shrink-0"
        style={{ borderBottom: "1px solid #0f1d30", background: "#040810" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg,rgba(167,139,250,0.2),rgba(59,130,246,0.2))",
                     border: "1px solid rgba(167,139,250,0.3)" }}>
            <Brain size={15} style={{ color: "#a78bfa" }} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">AI Political Reasoning</h1>
            <p className="mono text-xs" style={{ color: "#2e4260" }}>
              Knowledge Graph + Web Search · Sarvam-30b Synthesis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {Object.entries(MODE_CONFIG).map(([k, v]) => {
            const { Icon: ModeIcon } = v;
            return (
              <div key={k} className="hidden md:flex items-center gap-1 px-2 py-0.5 rounded"
                style={{ background: v.bg, border: `1px solid ${v.color}20` }}>
                <ModeIcon size={9} style={{ color: v.color }} />
                <span className="mono" style={{ color: v.color, fontSize: 9 }}>{v.label}</span>
              </div>
            );
          })}
          <button onClick={() => setMessages([])}
            className="px-3 py-1.5 rounded text-xs hover:bg-white/5"
            style={{ border: "1px solid #0f1d30", color: "#2e4260" }}>
            Clear
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-52 flex-shrink-0 overflow-y-auto"
          style={{ borderRight: "1px solid #0f1d30", background: "#040810" }}>
          <div className="p-3">
            <p className="mono mb-3" style={{ color: "#1e3a5f", fontSize: 9, letterSpacing: "0.1em" }}>
              EXAMPLE QUERIES
            </p>
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} className="mb-4">
                <p className="mono mb-2" style={{ color: "#1e3a5f", fontSize: 9 }}>{cat.toUpperCase()}</p>
                {items.map(({ q }) => (
                  <button key={q} onClick={() => submit(q)} disabled={loading}
                    className="w-full text-left px-2 py-1.5 rounded text-xs mb-1 hover:bg-white/5 flex items-start gap-1.5 disabled:opacity-40"
                    style={{ color: "#3d5a7a" }}>
                    <ChevronRight size={8} className="mt-0.5 flex-shrink-0 opacity-50" />
                    {q}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full py-20">
                <div className="w-20 h-20 rounded-2xl flex items-center justify-center mb-5"
                  style={{ background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.2)" }}>
                  <Brain size={36} style={{ color: "#a78bfa" }} />
                </div>
                <p className="text-white font-bold text-lg mb-2">Political Intelligence Engine</p>
                <p className="text-sm text-center mb-5 max-w-md" style={{ color: "#2e4260" }}>
                  Combines real-time web search with our knowledge graph — ask about local booth data
                  or broad UP political context; the system intelligently routes and synthesises.
                </p>
                <div className="flex items-center gap-5 text-xs mono" style={{ color: "#1e3a5f" }}>
                  <span className="flex items-center gap-1.5">
                    <Database size={11} style={{ color: "#10b981" }} /> Neo4j Graph
                  </span>
                  <span>+</span>
                  <span className="flex items-center gap-1.5">
                    <Globe size={11} style={{ color: "#3b82f6" }} /> DuckDuckGo + Wikipedia
                  </span>
                  <span>+</span>
                  <span className="flex items-center gap-1.5">
                    <Brain size={11} style={{ color: "#a78bfa" }} /> Sarvam-30b
                  </span>
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && (
                  <div className="w-7 h-7 rounded-md flex-shrink-0 flex items-center justify-center mt-0.5"
                    style={{ background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)" }}>
                    <Brain size={12} style={{ color: "#a78bfa" }} />
                  </div>
                )}

                <div className={`flex-1 ${m.role === "user" ? "flex flex-col items-end" : ""}`}>
                  {m.role === "user" ? (
                    <div className="inline-block rounded-xl px-4 py-2.5"
                      style={{ background: "rgba(249,115,22,0.07)", border: "1px solid rgba(249,115,22,0.2)" }}>
                      <p className="text-sm text-white">{m.content}</p>
                    </div>
                  ) : m.result ? (
                    <div className="max-w-3xl w-full">
                      <AssistantMessage result={m.result} />
                    </div>
                  ) : (
                    <div className="rounded-xl px-4 py-3" style={{ background: "#0b1626", border: "1px solid #1a2b44" }}>
                      <p className="text-sm" style={{ color: "#ef4444" }}>{m.content}</p>
                    </div>
                  )}
                  <div className="flex items-center gap-1 mt-1 px-1">
                    <Clock size={8} style={{ color: "#0f1d30" }} />
                    <span className="mono" style={{ color: "#0f1d30", fontSize: 9 }}>{m.ts}</span>
                  </div>
                </div>

                {m.role === "user" && (
                  <div className="w-7 h-7 rounded-md flex-shrink-0 flex items-center justify-center mt-0.5"
                    style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.2)" }}>
                    <span className="mono text-xs font-bold" style={{ color: "#f97316" }}>U</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-md flex-shrink-0 flex items-center justify-center"
                  style={{ background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)" }}>
                  <Loader size={12} className="animate-spin" style={{ color: "#a78bfa" }} />
                </div>
                <div className="rounded-xl px-4 py-3"
                  style={{ background: "#0b1626", border: "1px solid #1a2b44" }}>
                  <div className="space-y-1.5">
                    {[
                      { Icon: Database, label: "Querying knowledge graph…", color: "#10b981" },
                      { Icon: Globe,    label: "Searching the web…",        color: "#3b82f6" },
                      { Icon: Brain,    label: "Synthesising answer…",      color: "#a78bfa" },
                    ].map(({ Icon: StepIcon, label, color }) => (
                      <div key={label} className="flex items-center gap-2">
                        <StepIcon size={10} style={{ color }} />
                        <span className="mono text-xs" style={{ color: "#2e4260" }}>{label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-5 py-4 flex-shrink-0"
            style={{ borderTop: "1px solid #0f1d30", background: "#040810" }}>
            <div className="flex gap-3">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && submit()}
                placeholder="Ask about booths, candidates, issues, UP politics, current events…"
                className="flex-1 px-4 py-3 rounded-xl text-sm text-white outline-none"
                style={{ background: "#0b1626", border: "1px solid #0f1d30" }}
              />
              <button onClick={() => submit()} disabled={loading || !input.trim()}
                className="px-5 rounded-xl flex items-center gap-2 text-sm font-semibold hover:opacity-80 disabled:opacity-30"
                style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", color: "#fff" }}>
                <Send size={15} />
              </button>
            </div>
            <p className="mono mt-2" style={{ color: "#0f1d30", fontSize: 9 }}>
              Enter to submit · Graph + DuckDuckGo + Wikipedia + Sarvam-30b ·{" "}
              {messages.filter((m) => m.role === "user").length} queries this session
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
