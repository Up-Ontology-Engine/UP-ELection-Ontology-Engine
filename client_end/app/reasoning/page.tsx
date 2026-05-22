"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { api, type ReasoningResult, type WebResult, type ChatSession, type ChatMessage } from "@/lib/api";
import {
  Send, Code, Loader, ChevronRight, Globe,
  Database, Zap, ExternalLink, ChevronDown, ChevronUp,
  Brain, Clock, AlertCircle, Plus, Trash2, MessageSquare,
  PencilLine,
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

interface LocalMessage {
  role: "user" | "assistant";
  content: string;
  result?: ReasoningResult;
  ts: string;
}

function sessionLabel(s: ChatSession) {
  return s.title || "Untitled chat";
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return d.toLocaleDateString("en-IN", { weekday: "short" });
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export default function ReasoningPage() {
  const [sessions, setSessions]             = useState<ChatSession[]>([]);
  const [currentId, setCurrentId]           = useState<string | null>(null);
  const [messages, setMessages]             = useState<LocalMessage[]>([]);
  const [input, setInput]                   = useState("");
  const [loading, setLoading]               = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [renaming, setRenaming]             = useState<string | null>(null);
  const [renameVal, setRenameVal]           = useState("");
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);
  const renameRef  = useRef<HTMLInputElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Load sessions on mount; restore last session from localStorage
  useEffect(() => {
    loadSessions().then(() => {
      const saved = typeof window !== "undefined" ? localStorage.getItem("reasoning_session_id") : null;
      if (saved) switchSession(saved);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadSessions() {
    setSessionsLoading(true);
    try {
      const { sessions: list } = await api.chat.sessions();
      setSessions(list);
    } catch { /* backend may be offline */ }
    setSessionsLoading(false);
  }

  const switchSession = useCallback(async (id: string) => {
    setCurrentId(id);
    if (typeof window !== "undefined") localStorage.setItem("reasoning_session_id", id);
    setMessages([]);
    try {
      const { messages: dbMsgs } = await api.chat.messages(id);
      const hydrated: LocalMessage[] = dbMsgs.map((m: ChatMessage) => ({
        role: m.role,
        content: m.content,
        result: m.result ?? undefined,
        ts: m.ts,
      }));
      setMessages(hydrated);
    } catch { /* ignore load failure */ }
  }, []);

  async function newChat() {
    try {
      const sess = await api.chat.createSession();
      setSessions((prev) => [sess, ...prev]);
      setCurrentId(sess.session_id);
      if (typeof window !== "undefined") localStorage.setItem("reasoning_session_id", sess.session_id);
      setMessages([]);
      setTimeout(() => inputRef.current?.focus(), 50);
    } catch {
      // Offline: just clear messages locally without persisting
      setCurrentId(null);
      setMessages([]);
    }
  }

  async function removeSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.chat.deleteSession(id);
    } catch { /* ignore */ }
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    if (currentId === id) {
      setCurrentId(null);
      setMessages([]);
      if (typeof window !== "undefined") localStorage.removeItem("reasoning_session_id");
    }
  }

  function startRename(s: ChatSession, e: React.MouseEvent) {
    e.stopPropagation();
    setRenaming(s.session_id);
    setRenameVal(s.title ?? "");
    setTimeout(() => renameRef.current?.focus(), 30);
  }

  async function commitRename(id: string) {
    const title = renameVal.trim() || "Untitled chat";
    setRenaming(null);
    setSessions((prev) => prev.map((s) => s.session_id === id ? { ...s, title } : s));
    try { await api.chat.renameSession(id, title); } catch { /* ignore */ }
  }

  function ts() {
    return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  }

  async function ensureSession(): Promise<string | null> {
    if (currentId) return currentId;
    try {
      const sess = await api.chat.createSession();
      setSessions((prev) => [sess, ...prev]);
      setCurrentId(sess.session_id);
      if (typeof window !== "undefined") localStorage.setItem("reasoning_session_id", sess.session_id);
      return sess.session_id;
    } catch {
      return null;
    }
  }

  async function submit(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setInput("");

    const userTs = ts();
    const userMsg: LocalMessage = { role: "user", content: q, ts: userTs };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const sessionId = await ensureSession();

    // Persist user message (fire-and-forget)
    if (sessionId) {
      api.chat.addMessage(sessionId, { role: "user", content: q, ts: userTs }).catch(() => {});

      // Auto-title: first message becomes session title
      const isFirst = messages.length === 0;
      if (isFirst) {
        const title = q.length > 60 ? q.slice(0, 57) + "…" : q;
        api.chat.renameSession(sessionId, title).catch(() => {});
        setSessions((prev) => prev.map((s) => s.session_id === sessionId ? { ...s, title } : s));
      }
    }

    try {
      const result = await api.reason(q);
      const asstTs = ts();
      const asstMsg: LocalMessage = {
        role: "assistant",
        content: result.answer || result.summary || "Analysis complete.",
        result,
        ts: asstTs,
      };
      setMessages((prev) => [...prev, asstMsg]);

      // Persist assistant message (fire-and-forget)
      if (sessionId) {
        api.chat.addMessage(sessionId, {
          role: "assistant",
          content: asstMsg.content,
          result: result as unknown as Record<string, unknown>,
          ts: asstTs,
        }).then(() => {
          // Update local message_count
          setSessions((prev) => prev.map((s) =>
            s.session_id === sessionId
              ? { ...s, message_count: s.message_count + 2, updated_at: new Date().toISOString() }
              : s
          ));
        }).catch(() => {});
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}`, ts: ts() }]);
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
              Knowledge Graph + Web Search · Sarvam-30b · Persistent Sessions
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
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sessions sidebar */}
        <div className="w-56 flex-shrink-0 flex flex-col overflow-hidden"
          style={{ borderRight: "1px solid #0f1d30", background: "#030710" }}>

          {/* New chat button */}
          <div className="p-3 flex-shrink-0" style={{ borderBottom: "1px solid #0f1d30" }}>
            <button onClick={newChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all hover:opacity-90"
              style={{ background: "rgba(167,139,250,0.12)", border: "1px solid rgba(167,139,250,0.25)", color: "#a78bfa" }}>
              <Plus size={12} /> New Chat
            </button>
          </div>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto p-2">
            {sessionsLoading && (
              <p className="mono text-center py-4" style={{ color: "#1e3a5f", fontSize: 9 }}>Loading...</p>
            )}
            {!sessionsLoading && sessions.length === 0 && (
              <p className="mono text-center py-4" style={{ color: "#1e3a5f", fontSize: 9 }}>No saved chats</p>
            )}
            {sessions.map((s) => (
              <div key={s.session_id}
                onClick={() => switchSession(s.session_id)}
                className={`group relative flex flex-col gap-0.5 px-2 py-2 rounded-lg mb-1 cursor-pointer transition-all ${
                  currentId === s.session_id ? "bg-white/6" : "hover:bg-white/3"
                }`}
                style={currentId === s.session_id ? { border: "1px solid #1a2b44" } : { border: "1px solid transparent" }}>

                {renaming === s.session_id ? (
                  <input
                    ref={renameRef}
                    value={renameVal}
                    onChange={(e) => setRenameVal(e.target.value)}
                    onBlur={() => commitRename(s.session_id)}
                    onKeyDown={(e) => { if (e.key === "Enter") commitRename(s.session_id); if (e.key === "Escape") setRenaming(null); }}
                    className="w-full text-xs bg-transparent outline-none text-white"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <p className="text-xs font-medium truncate pr-10" style={{ color: currentId === s.session_id ? "#e2e8f0" : "#4d6480" }}>
                    {sessionLabel(s)}
                  </p>
                )}

                <p className="mono flex items-center gap-1" style={{ color: "#1e3a5f", fontSize: 9 }}>
                  <MessageSquare size={8} /> {s.message_count}
                  <span className="ml-auto">{fmtDate(s.updated_at)}</span>
                </p>

                {/* Action buttons — visible on hover / active */}
                <div className="absolute right-1.5 top-1.5 hidden group-hover:flex items-center gap-0.5">
                  <button onClick={(e) => startRename(s, e)}
                    className="p-1 rounded hover:bg-white/10 transition-colors"
                    style={{ color: "#2e4260" }}>
                    <PencilLine size={9} />
                  </button>
                  <button onClick={(e) => removeSession(s.session_id, e)}
                    className="p-1 rounded hover:bg-red-500/10 transition-colors"
                    style={{ color: "#2e4260" }}>
                    <Trash2 size={9} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Example queries */}
          <div className="flex-shrink-0 overflow-y-auto p-2 max-h-56" style={{ borderTop: "1px solid #0f1d30" }}>
            <p className="mono mb-2 px-1" style={{ color: "#1e3a5f", fontSize: 9, letterSpacing: "0.1em" }}>
              EXAMPLES
            </p>
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat} className="mb-3">
                <p className="mono mb-1 px-1" style={{ color: "#1e3a5f", fontSize: 9 }}>{cat.toUpperCase()}</p>
                {items.map(({ q }) => (
                  <button key={q} onClick={() => submit(q)} disabled={loading}
                    className="w-full text-left px-2 py-1 rounded text-xs mb-0.5 hover:bg-white/5 flex items-start gap-1.5 disabled:opacity-40"
                    style={{ color: "#3d5a7a" }}>
                    <ChevronRight size={8} className="mt-0.5 flex-shrink-0 opacity-50" />
                    <span className="line-clamp-2">{q}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Chat area */}
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
                  Combines real-time web search with our knowledge graph. Sessions are saved automatically —
                  pick up any conversation after login.
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
                    <div className="rounded-xl px-4 py-3"
                      style={{ background: "#0b1626", border: "1px solid #1a2b44" }}>
                      <p className="text-sm" style={{ color: "#cbd5e1" }}>{m.content}</p>
                    </div>
                  )}
                  <p className="mono mt-1 px-1" style={{ color: "#1e3a5f", fontSize: 9 }}>{m.ts}</p>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-md flex-shrink-0 flex items-center justify-center mt-0.5"
                  style={{ background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)" }}>
                  <Loader size={12} style={{ color: "#a78bfa" }} className="animate-spin" />
                </div>
                <div className="rounded-xl px-4 py-3"
                  style={{ background: "#0b1626", border: "1px solid #1a2b44" }}>
                  <div className="flex flex-col gap-1.5">
                    {[
                      { icon: Database, color: "#10b981", label: "Querying graph..." },
                      { icon: Globe,    color: "#3b82f6", label: "Searching web..."  },
                      { icon: Brain,    color: "#a78bfa", label: "Synthesising..."   },
                    ].map(({ icon: Ic, color, label }, idx) => (
                      <div key={idx} className="flex items-center gap-2 mono" style={{ color, fontSize: 10 }}>
                        <Ic size={10} className="animate-pulse" style={{ animationDelay: `${idx * 0.3}s` }} />
                        {label}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="flex-shrink-0 p-4" style={{ borderTop: "1px solid #0f1d30" }}>
            <div className="flex gap-2 rounded-xl p-1"
              style={{ background: "#070e1b", border: "1px solid #1a2b44" }}>
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
                placeholder="Ask about booths, candidates, issues, or UP politics…"
                disabled={loading}
                className="flex-1 bg-transparent outline-none text-sm text-white placeholder-opacity-30 px-3 py-2 disabled:opacity-50"
                style={{ color: "#e2e8f0" }}
              />
              <button
                onClick={() => submit()}
                disabled={loading || !input.trim()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-40"
                style={{ background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)", color: "#a78bfa" }}>
                {loading ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
                {loading ? "…" : "Ask"}
              </button>
            </div>
            <p className="mono text-center mt-2" style={{ color: "#1e3a5f", fontSize: 9 }}>
              Chats auto-saved · Sessions persist across logins
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
