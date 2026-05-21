"use client";

import { useState, useRef, useEffect } from "react";
import { api, type ReasoningResult } from "@/lib/api";
import { Send, Code, Loader, Terminal, ChevronRight, Clock, Database } from "lucide-react";

const EXAMPLES = [
  { cat: "Booths",     q: "Which booths have the highest BJP pulse score?" },
  { cat: "Booths",     q: "Show me all booths with STRONG_OPP lean" },
  { cat: "Issues",     q: "What are the top 5 issues by booth count?" },
  { cat: "Issues",     q: "Which booths have water supply as the top issue?" },
  { cat: "Schemes",    q: "Which schemes have the highest delivery gap?" },
  { cat: "Narratives", q: "List booths with anti-incumbency narrative" },
  { cat: "Quality",    q: "Show booths with LOW data confidence" },
  { cat: "Candidates", q: "Who won in the last election?" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  result?: ReasoningResult;
  ts: string;
  loading?: boolean;
}

export default function ReasoningPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCypher, setShowCypher] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  function ts() {
    return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  }

  async function submit(question?: string) {
    const q = question ?? input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q, ts: ts() }]);
    setLoading(true);
    try {
      const result = await api.reason(q);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.summary ?? "I could not generate a textual answer for that query.",
        result, ts: ts(),
      }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: `Error: ${message || "Could not reach the reasoning API. Ensure the backend is running with Neo4j connected."}`,
        ts: ts(),
      }]);
    } finally { setLoading(false); }
  }

  function toggleCypher(idx: number) {
    setShowCypher((s) => { const n = new Set(s); n.has(idx) ? n.delete(idx) : n.add(idx); return n; });
  }

  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--bg-base)" }}>

      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-surface)" }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)" }}>
            <Terminal size={13} style={{ color: "#ec4899" }} />
          </div>
          <div>
            <h1 className="text-sm font-bold" style={{ color: "var(--text-1)" }}>AI Political Reasoning</h1>
            <p className="text-xs mono" style={{ color: "var(--text-3)" }}>
              Natural language → Cypher → Knowledge Graph · Powered by Sarvam LLM
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs mono px-2 py-1 rounded"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-3)" }}>
            <Database size={10} style={{ color: "#10b981" }} />
            Neo4j
          </div>
          <button onClick={() => setMessages([])}
            className="px-3 py-1.5 rounded-md text-xs transition-colors"
            style={{ border: "1px solid var(--border)", color: "var(--text-3)" }}>
            Clear session
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Example sidebar */}
        <div className="w-56 flex-shrink-0 flex flex-col overflow-y-auto"
          style={{ borderRight: "1px solid var(--border)", background: "var(--bg-surface)" }}>
          <div className="px-3 py-3">
            <p className="label mb-3" style={{ color: "var(--text-3)" }}>Example Queries</p>
            {["Booths", "Issues", "Schemes", "Narratives", "Quality", "Candidates"].map((cat) => {
              const items = EXAMPLES.filter((e) => e.cat === cat);
              if (!items.length) return null;
              return (
                <div key={cat} className="mb-3">
                  <p className="label mb-1.5" style={{ color: "var(--text-4)" }}>{cat}</p>
                  {items.map(({ q }) => (
                    <button key={q} onClick={() => submit(q)}
                      className="w-full text-left px-2.5 py-2 rounded-md text-xs mb-1 transition-all flex items-start gap-1.5"
                      style={{ border: "1px solid transparent", color: "var(--text-3)" }}>
                      <ChevronRight size={9} className="mt-0.5 flex-shrink-0" style={{ color: "var(--text-4)" }} />
                      {q}
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full py-20">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                  style={{ background: "rgba(236,72,153,0.1)", border: "1px solid rgba(236,72,153,0.2)" }}>
                  <Terminal size={28} style={{ color: "#ec4899" }} />
                </div>
                <p className="font-semibold text-base mb-1" style={{ color: "var(--text-1)" }}>Political Intelligence Query Engine</p>
                <p className="text-sm mb-2" style={{ color: "var(--text-3)" }}>
                  Ask in plain English — queries are translated to Cypher and run against the knowledge graph
                </p>
                <div className="flex items-center gap-3 text-xs mono" style={{ color: "var(--text-4)" }}>
                  <span className="flex items-center gap-1"><Terminal size={10} /> Natural language</span>
                  <span>→</span>
                  <span className="flex items-center gap-1"><Code size={10} /> Cypher</span>
                  <span>→</span>
                  <span className="flex items-center gap-1"><Database size={10} /> Neo4j</span>
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 animate-fade-up ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && (
                  <div className="w-7 h-7 rounded-md flex-shrink-0 flex items-center justify-center mt-0.5"
                    style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)" }}>
                    <Terminal size={12} style={{ color: "#ec4899" }} />
                  </div>
                )}
                <div className="max-w-2xl flex-1" style={{ maxWidth: m.role === "user" ? "70%" : undefined }}>
                  <div className="rounded-lg px-4 py-3"
                    style={{
                      background: m.role === "user" ? "rgba(249,115,22,0.08)" : "var(--bg-card)",
                      border: `1px solid ${m.role === "user" ? "rgba(249,115,22,0.25)" : "var(--border)"}`,
                    }}>
                    <p className="text-sm mb-1" style={{ color: "var(--text-1)" }}>{m.content}</p>
                    {m.result?.cypher && (
                      <div>
                        <button onClick={() => toggleCypher(i)}
                          className="flex items-center gap-1.5 text-xs mono mt-2 transition-colors hover:text-purple-500"
                          style={{ color: "var(--text-3)" }}>
                          <Code size={10} />
                          {showCypher.has(i) ? "Hide" : "Show"} Cypher
                        </button>
                        {showCypher.has(i) && (
                          <pre className="mt-2 p-3 rounded text-xs mono overflow-x-auto"
                            style={{ background: "var(--bg-base)", color: "#8b5cf6", border: "1px solid var(--border)", fontSize: 11 }}>
                            {m.result.cypher}
                          </pre>
                        )}
                      </div>
                    )}
                    {m.result?.results && m.result.results.length > 0 && (
                      <div className="mt-3 rounded overflow-hidden" style={{ border: "1px solid var(--border)" }}>
                        <div className="px-3 py-1.5 flex items-center justify-between"
                          style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)" }}>
                          <span className="mono text-xs" style={{ color: "var(--text-3)" }}>
                            {m.result.results.length} row{m.result.results.length !== 1 ? "s" : ""} returned
                          </span>
                        </div>
                        <div className="overflow-x-auto max-h-48">
                          <table className="w-full data-table text-xs">
                            <thead>
                              <tr>
                                {Object.keys(m.result.results[0]).map((k) => <th key={k}>{k}</th>)}
                              </tr>
                            </thead>
                            <tbody>
                              {m.result.results.slice(0, 25).map((row, ri) => (
                                <tr key={ri}>
                                  {Object.values(row).map((v, vi) => (
                                    <td key={vi} className="mono" style={{ color: "var(--text-2)" }}>{String(v ?? "—")}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1 px-1">
                    <Clock size={9} style={{ color: "var(--text-4)" }} />
                    <span className="mono text-xs" style={{ color: "var(--text-4)", fontSize: 9 }}>{m.ts}</span>
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
                  style={{ background: "rgba(236,72,153,0.15)", border: "1px solid rgba(236,72,153,0.3)" }}>
                  <Loader size={12} className="animate-spin" style={{ color: "#ec4899" }} />
                </div>
                <div className="rounded-lg px-4 py-3"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "#ec4899" }} />
                      <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "#ec4899", animationDelay: "0.2s" }} />
                      <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "#ec4899", animationDelay: "0.4s" }} />
                    </div>
                    <span className="text-xs mono" style={{ color: "var(--text-3)" }}>Translating to Cypher and querying Neo4j…</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="px-6 py-4" style={{ borderTop: "1px solid var(--border)", background: "var(--bg-surface)" }}>
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <input value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && submit()}
                  placeholder="Ask about booths, candidates, issues, schemes, narratives…"
                  className="w-full px-4 py-3 rounded-lg text-sm outline-none"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-1)" }} />
              </div>
              <button onClick={() => submit()} disabled={loading || !input.trim()}
                className="px-5 rounded-lg flex items-center gap-2 text-sm font-semibold transition-all hover:opacity-80 disabled:opacity-30"
                style={{ background: "#ec4899", color: "#fff" }}>
                <Send size={15} />
              </button>
            </div>
            <p className="text-xs mono mt-2" style={{ color: "var(--text-4)" }}>
              Enter to submit · Results from Neo4j knowledge graph · Session not persisted
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
