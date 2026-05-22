"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Brain,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Code,
  Database,
  ExternalLink,
  Globe,
  Loader,
  MessageSquare,
  Send,
  Terminal,
  Zap,
} from "lucide-react";
import { api, type ReasoningResult, type WebResult } from "@/lib/api";

const EXAMPLES = [
  { cat: "Booths", q: "Which booths have the highest BJP pulse score?" },
  { cat: "Booths", q: "Show me all booths with STRONG_OPP lean" },
  { cat: "Issues", q: "What are the top 5 issues by booth count?" },
  { cat: "Issues", q: "Which booths have water supply as the top issue?" },
  { cat: "Schemes", q: "Which schemes have the highest delivery gap?" },
  { cat: "Narratives", q: "List booths with anti-incumbency narrative" },
  { cat: "Quality", q: "Show booths with LOW data confidence" },
  { cat: "Candidates", q: "Who won in the last election?" },
];

type Mode = "hybrid" | "graph" | "web" | "llm";

const MODE_CONFIG: Record<Mode, { label: string; chip: string; icon: React.ElementType }> = {
  hybrid: { label: "HYBRID", chip: "border-violet-500/30 bg-violet-500/10 text-violet-300", icon: Zap },
  graph: { label: "GRAPH", chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300", icon: Database },
  web: { label: "WEB", chip: "border-sky-500/30 bg-sky-500/10 text-sky-300", icon: Globe },
  llm: { label: "LLM", chip: "border-amber-500/30 bg-amber-500/10 text-amber-300", icon: Brain },
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  result?: ReasoningResult;
  ts: string;
};

function SourceCard({ r }: { r: WebResult }) {
  const host = r.url
    ? (() => {
        try {
          return new URL(r.url).hostname.replace(/^www\./, "");
        } catch {
          return r.source;
        }
      })()
    : r.source;

  return (
    <a
      href={r.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-slate-800 bg-slate-950 p-3 transition-colors hover:bg-slate-900"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="line-clamp-2 flex-1 text-xs font-medium text-slate-100">{r.title}</p>
        {r.url && <ExternalLink size={10} className="mt-0.5 shrink-0 text-slate-500" />}
      </div>
      <p className="mt-1 line-clamp-2 text-xs text-slate-400">{r.snippet}</p>
      <div className="mt-2 flex items-center gap-1 text-[9px] text-slate-500">
        <Globe size={8} />
        <span>{host}</span>
        <span className="ml-1 rounded bg-slate-900 px-1 py-0.5 text-slate-500">{r.source}</span>
      </div>
    </a>
  );
}

function GraphTable({ results }: { results: Record<string, unknown>[] }) {
  if (!results.length) return null;
  const keys = Object.keys(results[0]);

  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-slate-800">
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-950 px-3 py-2">
        <Database size={10} className="text-emerald-400" />
        <span className="mono text-xs text-slate-400">
          {results.length} row{results.length !== 1 ? "s" : ""} from graph
        </span>
      </div>
      <div className="max-h-48 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950">
              {keys.map((k) => (
                <th key={k} className="px-3 py-1.5 text-left text-[9px] uppercase tracking-wide text-slate-500">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.slice(0, 25).map((row, ri) => (
              <tr
                key={ri}
                className={ri % 2 === 0 ? "border-b border-slate-800 bg-slate-950/60" : "border-b border-slate-800/50"}
              >
                {keys.map((k) => (
                  <td key={k} className="px-3 py-1.5 mono text-slate-300">{String(row[k] ?? "—")}</td>
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
  const [showSources, setShowSources] = useState(false);
  const [showCypher, setShowCypher] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const mode = (result.mode as Mode) ?? "llm";
  const conf = MODE_CONFIG[mode] ?? MODE_CONFIG.llm;
  const hasWeb = (result.web_results?.length ?? 0) > 0;
  const hasCypher = Boolean(result.cypher);
  const hasGraph = (result.graph_results?.length ?? 0) > 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/60 px-4 py-2">
        <div className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-bold ${conf.chip}`}>
          <conf.icon size={9} />
          <span>{conf.label}</span>
        </div>
        {hasGraph && <span className="mono text-[9px] text-slate-500">{result.row_count} graph rows</span>}
        {hasWeb && <span className="mono flex items-center gap-1 text-[9px] text-slate-500"><Globe size={8} />{result.web_results.length} sources</span>}
        <span className="ml-auto mono flex items-center gap-1 text-[9px] text-slate-500"><Clock size={8} />{result.elapsed_ms}ms</span>
      </div>

      <div className="px-4 py-3 text-sm text-slate-200">
        {result.error && !result.answer && (
          <div className="mb-3 flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-2 text-xs text-red-200">
            <AlertCircle size={12} className="mt-0.5 shrink-0" />
            <span>{result.error}</span>
          </div>
        )}
        {result.answer ? <p className="whitespace-pre-wrap leading-6 text-slate-200">{result.answer}</p> : null}
        {!result.answer && result.summary ? <p className="whitespace-pre-wrap leading-6 text-slate-200">{result.summary}</p> : null}
      </div>

      {hasWeb && (
        <div className="border-t border-slate-800">
          <button onClick={() => setShowSources((s) => !s)} className="flex w-full items-center gap-2 px-4 py-2 text-xs text-sky-400 transition-colors hover:bg-slate-900">
            <Globe size={10} />
            {result.web_results.length} web source{result.web_results.length !== 1 ? "s" : ""}
            {showSources ? <ChevronUp size={10} className="ml-auto" /> : <ChevronDown size={10} className="ml-auto" />}
          </button>
          {showSources && (
            <div className="grid gap-2 px-4 pb-3">
              {result.web_results.map((r, i) => <SourceCard key={i} r={r} />)}
            </div>
          )}
        </div>
      )}

      {hasCypher && (
        <div className="border-t border-slate-800">
          <button onClick={() => setShowCypher((s) => !s)} className="flex w-full items-center gap-2 px-4 py-2 text-xs text-violet-400 transition-colors hover:bg-slate-900">
            <Code size={10} /> Cypher query
            {showCypher ? <ChevronUp size={10} className="ml-auto" /> : <ChevronDown size={10} className="ml-auto" />}
          </button>
          {showCypher && (
            <div className="px-4 pb-3">
              <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-violet-300">{result.cypher}</pre>
            </div>
          )}
        </div>
      )}

      {hasGraph && (
        <div className="border-t border-slate-800">
          <button onClick={() => setShowTable((s) => !s)} className="flex w-full items-center gap-2 px-4 py-2 text-xs text-emerald-400 transition-colors hover:bg-slate-900">
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

export default function ReasoningPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const grouped = EXAMPLES.reduce<Record<string, typeof EXAMPLES>>((acc, item) => {
    (acc[item.cat] ??= []).push(item);
    return acc;
  }, {});

  function ts() {
    return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  }

  async function submit(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;

    setInput("");
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: q, ts: ts() }]);

    try {
      const result = await api.reason(q);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer || result.summary || "Analysis complete.", result, ts: ts() },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err instanceof Error ? `Error: ${err.message}` : "Error: Could not reach the reasoning API.", ts: ts() },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-[#060b14]">
      <div className="flex items-center justify-between border-b border-slate-800 bg-[#060b14] px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-fuchsia-500/30 bg-fuchsia-500/10">
            <Terminal size={13} className="text-fuchsia-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100">AI Political Reasoning</h1>
            <p className="mono text-xs text-slate-500">Natural language → Cypher → Knowledge Graph · Powered by Groq LLM</p>
          </div>
        </div>
        <div className="hidden items-center gap-1.5 mono text-xs text-slate-500 md:flex">
          <MessageSquare size={11} /> {messages.filter((m) => m.role === "user").length} queries this session
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-60 shrink-0 overflow-y-auto border-r border-slate-800 bg-[#060b14]">
          <div className="p-3">
            <p className="mono mb-3 text-[9px] tracking-widest text-slate-500">EXAMPLES</p>
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} className="mb-3">
                <p className="mono mb-2 text-[9px] text-slate-500">{cat.toUpperCase()}</p>
                {items.map(({ q }) => (
                  <button
                    key={q}
                    onClick={() => submit(q)}
                    disabled={loading}
                    className="mb-0.5 flex w-full items-start gap-1.5 rounded px-2 py-1 text-left text-xs text-slate-400 transition-colors hover:bg-slate-900 disabled:opacity-40"
                  >
                    <ChevronRight size={8} className="mt-0.5 shrink-0 opacity-50" />
                    <span className="line-clamp-2">{q}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </aside>

        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center py-20">
                <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10">
                  <Brain size={36} className="text-violet-400" />
                </div>
                <p className="mb-2 text-lg font-bold text-slate-100">Political Intelligence Engine</p>
                <p className="mb-5 max-w-md text-center text-sm text-slate-500">
                  Ask about booths, candidates, issues, or constituency trends.
                </p>
                <div className="flex max-w-3xl flex-wrap items-center justify-center gap-2">
                  {EXAMPLES.slice(0, 6).map((item) => (
                    <button
                      key={item.q}
                      onClick={() => submit(item.q)}
                      disabled={loading}
                      className="rounded-full border border-violet-500/25 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-300 transition-opacity hover:opacity-90 disabled:opacity-40"
                    >
                      {item.q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && (
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-violet-500/30 bg-violet-500/15">
                    <Brain size={12} className="text-violet-400" />
                  </div>
                )}

                <div className={`flex-1 ${m.role === "user" ? "flex flex-col items-end" : ""}`}>
                  {m.role === "user" ? (
                    <div className="inline-block rounded-xl border border-orange-500/20 bg-orange-500/10 px-4 py-2.5">
                      <p className="text-sm text-slate-100">{m.content}</p>
                    </div>
                  ) : m.result ? (
                    <div className="w-full max-w-3xl">
                      <AssistantMessage result={m.result} />
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
                      <p className="text-sm text-red-200">{m.content}</p>
                    </div>
                  )}
                  <p className="mono mt-1 px-1 text-[9px] text-slate-500">{m.ts}</p>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-violet-500/30 bg-violet-500/15">
                  <Loader size={12} className="animate-spin text-violet-400" />
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
                  <div className="flex flex-col gap-1.5">
                    {[
                      { icon: Database, color: "text-emerald-400", label: "Querying graph..." },
                      { icon: Globe, color: "text-sky-400", label: "Searching web..." },
                      { icon: Brain, color: "text-violet-400", label: "Synthesising..." },
                    ].map(({ icon: Ic, color, label }, idx) => (
                      <div key={idx} className={`mono flex items-center gap-2 text-[10px] ${color}`}>
                        <Ic size={10} className="animate-pulse" />
                        {label}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="shrink-0 border-t border-slate-800 p-4">
            <div className="flex gap-2 rounded-xl border border-slate-800 bg-slate-900 p-1">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                placeholder="Ask about booths, candidates, issues, or UP politics…"
                disabled={loading}
                className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 outline-none disabled:opacity-50"
              />
              <button
                onClick={() => submit()}
                disabled={loading || !input.trim()}
                className="flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-500/15 px-4 py-2 text-xs font-medium text-violet-300 transition-opacity disabled:opacity-40"
              >
                {loading ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
                {loading ? "…" : "Ask"}
              </button>
            </div>
            <p className="mono mt-2 text-center text-[9px] text-slate-500">Chats auto-saved · Sessions persist across logins</p>
          </div>
        </main>
      </div>
    </div>
  );
}
