"""
Enhanced AI Political Reasoning Engine — UP Election Ontology Engine

Pipeline per question:
  1. Neo4j: NL -> Cypher -> graph results
  2. Web:   DuckDuckGo HTML + Wikipedia search
  3. LLM:   Sarvam-30b synthesis of graph + web into a comprehensive answer
  4. Return: rich response with answer, sources, mode, raw results

LLM chain: Sarvam (primary) -> Gemini (fallback) -> plain summarisation
Web search: DuckDuckGo HTML -> Wikipedia API (merged, deduplicated)
"""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Neo4j schema (for Cypher generation) ─────────────────────────────────────

_SCHEMA = """
NODE TYPES (with key properties):
- State              {state_id, name}
- District           {district_id, name}
- AssemblyConstituency {ac_id, name, ac_type}        -- ac_id e.g. "GKP_322"
- Booth              {booth_id, name, ac_id, total_voters, male_voters, female_voters}
- Party              {party_id, name, color}          -- BJP | SP | BSP | INC | AAP | AIMIM | NISHAD | AD
- Candidate          {candidate_id, name, party_id, election_year, is_incumbent,
                      criminal_cases, serious_cases, net_worth_cr, education, age}
- Issue              {code, label, category}          -- water | roads | electricity | jobs |
                                                         women_safety | price_rise | farmer |
                                                         health | education | corruption | law_order
- Scheme             {name, category}
- Panchayat          {panchayat_id, name, ac_id}
- PulseEvent         {event_id, source_type, entity, issue, polarity, confidence,
                      mapped_booth_id, mapped_ac_id}
- YouTubeVideo       {video_id, title, views, query_source}
- Channel            {channel_id, name}
- CriminalRecord     {record_id, candidate_id, candidate_name, total_cases,
                      serious_cases, election_year}
- AssetDeclaration   {decl_id, candidate_id, candidate_name, total_assets,
                      net_worth_cr, election_year}

RELATIONSHIP TYPES:
- (State)-[:HAS_DISTRICT]->(District)
- (District)-[:HAS_AC]->(AssemblyConstituency)
- (AssemblyConstituency)-[:HAS_BOOTH]->(Booth)
- (Candidate)-[:REPRESENTS]->(Party)
- (Candidate)-[:CONTESTED_IN]->(AssemblyConstituency)
- (Candidate)-[:HAS_CRIMINAL_RECORD]->(CriminalRecord)
- (Candidate)-[:HAS_ASSETS]->(AssetDeclaration)
- (YouTubeVideo)-[:ABOUT_AC]->(AssemblyConstituency)
- (YouTubeVideo)-[:FROM_CHANNEL]->(Channel)
- (Panchayat)-[:WITHIN_AC]->(AssemblyConstituency)

GORAKHPUR CONTEXT:
- Pilot AC: GKP_322 = Gorakhpur Urban (CM Yogi Adityanath's home constituency)
- Main parties: BJP (incumbent), SP (main opposition), BSP
- election_year = 2022 for latest data
"""

_CYPHER_SYSTEM = f"""You are a Cypher query generator for a political intelligence Neo4j graph about Gorakhpur, India.

SCHEMA:
{_SCHEMA}

STRICT RULES:
1. Output ONLY a valid Cypher query -- no explanation, no markdown, no comments.
2. Always include LIMIT (default 25 unless user asks for more, max 100).
3. Return flat key-value pairs in RETURN clause (not whole nodes or maps).
4. Use direct property access, not complex subqueries.
5. If the question cannot be answered from the schema, output exactly:
   RETURN "Cannot answer from available graph data" AS message
6. Never use undefined node types or properties.
"""

_SYNTHESIS_SYSTEM = """You are an expert political intelligence analyst for Gorakhpur Urban Assembly Constituency (AC-322), Uttar Pradesh, India.

You have access to a proprietary knowledge graph with booth-level voter data, issue tracking, digital pulse scores, and candidate information -- and live web search results about Indian politics and UP elections.

RESPONSE RULES:
- Answer the question directly in the FIRST sentence
- Quote specific numbers and percentages when available from the data
- When using graph data, say "Our constituency database shows..."
- When using web data, briefly attribute it: "According to [source name]..."
- Be analytical and objective -- no party bias
- Keep responses to 2-4 tight paragraphs; bullets only when listing 3+ items
- If graph and web data conflict, note the discrepancy explicitly
- If neither source can answer, say so clearly and suggest what would help

Always end with one actionable insight relevant to electoral strategy or governance."""

# ── Shared HTTP client ────────────────────────────────────────────────────────

_HTTP_CLIENT = httpx.Client(timeout=30, follow_redirects=True)

_SARVAM_BASE = "https://api.sarvam.ai/v1"
_SARVAM_MODEL = os.environ.get("SARVAM_REASONING_MODEL", "sarvam-m")

# ── LLM calls ────────────────────────────────────────────────────────────────


def _call_sarvam(messages: list[dict], max_tokens: int = 2500) -> str:
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY not set")
    resp = _HTTP_CLIENT.post(
        f"{_SARVAM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": _SARVAM_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        },
        timeout=90,
    )
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    # Sarvam-30b is a reasoning model; answer is in `content` after thinking completes
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()


def _call_gemini(system: str, user: str, max_tokens: int = 1024) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    resp = client.models.generate_content(
        model=os.environ.get("GOOGLE_REASONING_MODEL", "gemini-2.5-flash"),
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            max_output_tokens=max_tokens,
        ),
        contents=user,
    )
    return (resp.text or "").strip()


def _clean_cypher(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:cypher)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    return raw.strip()


def generate_cypher(question: str) -> str:
    msgs = [
        {"role": "system", "content": _CYPHER_SYSTEM},
        {"role": "user", "content": f"Generate Cypher for: {question}"},
    ]
    try:
        return _clean_cypher(_call_sarvam(msgs, max_tokens=2000))
    except Exception as e:
        logger.warning("Sarvam Cypher gen failed (%s), trying Gemini", e)
    return _clean_cypher(_call_gemini(_CYPHER_SYSTEM, f"Generate Cypher for: {question}", 500))


def execute_cypher(cypher: str) -> list[dict[str, Any]]:
    from .db import get_neo4j_session

    with get_neo4j_session() as session:
        result = session.run(cypher)
        return [dict(record) for record in result]


# ── Web Search ────────────────────────────────────────────────────────────────

_WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_WIKI_UA = "UP-EOM-Research/1.0 (political intelligence; open-source) httpx/0.28"


def _decode_ddg_url(raw: str) -> str:
    if raw.startswith("//"):
        raw = "https:" + raw
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
    return qs.get("uddg", [raw])[0]


def _search_duckduckgo(query: str, max_results: int = 6) -> list[dict]:
    results: list[dict] = []
    try:
        resp = _HTTP_CLIENT.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=_WEB_HEADERS,
            timeout=12,
        )
        if not resp.is_success:
            return results
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".result__body")[:max_results]:
            title_el = item.select_one(".result__title")
            snippet_el = item.select_one(".result__snippet")
            url_el = item.select_one("a.result__url, .result__title a")
            title = title_el.get_text(strip=True) if title_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            url = _decode_ddg_url(url_el.get("href", "")) if url_el else ""
            if title or snippet:
                results.append(
                    {"title": title, "snippet": snippet, "url": url, "source": "DuckDuckGo"}
                )
    except Exception as e:
        logger.debug("DuckDuckGo search failed: %s", e)
    return results


def _search_duckduckgo_instant(query: str) -> list[dict]:
    results: list[dict] = []
    try:
        resp = _HTTP_CLIENT.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=_WEB_HEADERS,
            timeout=8,
        )
        if not resp.is_success:
            return results
        data = resp.json()
        if data.get("AbstractText"):
            results.append(
                {
                    "title": data.get("Heading") or query,
                    "snippet": data["AbstractText"][:500],
                    "url": data.get("AbstractURL") or "",
                    "source": "DuckDuckGo Instant",
                }
            )
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": topic["Text"][:80],
                        "snippet": topic["Text"][:400],
                        "url": topic.get("FirstURL") or "",
                        "source": "DuckDuckGo",
                    }
                )
    except Exception as e:
        logger.debug("DDG instant failed: %s", e)
    return results


def _search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    results: list[dict] = []
    try:
        resp = _HTTP_CLIENT.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
                "utf8": 1,
            },
            headers={"User-Agent": _WIKI_UA},
            timeout=10,
        )
        if not resp.is_success:
            return results
        for hit in resp.json().get("query", {}).get("search", []):
            snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", ""))
            title = hit.get("title", "")
            results.append(
                {
                    "title": title,
                    "snippet": snippet[:400],
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                    "source": "Wikipedia",
                }
            )
    except Exception as e:
        logger.debug("Wikipedia search failed: %s", e)
    return results


def web_search(question: str, max_results: int = 8) -> list[dict]:
    """Combine DDG HTML + Instant + Wikipedia, deduplicated."""
    enriched = f"{question} Gorakhpur UP India" if "gorakhpur" not in question.lower() else question

    instant = _search_duckduckgo_instant(question)
    ddg_html = _search_duckduckgo(enriched, max_results=6)
    wiki = _search_wikipedia(question, max_results=3)

    seen: set[str] = set()
    merged: list[dict] = []
    for r in instant + ddg_html + wiki:
        key = r.get("url") or r.get("title", "")
        if key and key not in seen:
            seen.add(key)
            merged.append(r)
        if len(merged) >= max_results:
            break
    return merged


# ── Question classifier ───────────────────────────────────────────────────────

_GRAPH_ONLY_TERMS = {
    "booth",
    "pulse score",
    "bjp score",
    "opp score",
    "digital lean",
    "event count",
    "confidence_label",
    "narrative",
    "contradiction",
    "scheme gap",
}

_WEB_SIGNALS = {
    "latest",
    "recent",
    "current",
    "news",
    "today",
    "2024",
    "2025",
    "2026",
    "who is",
    "who won",
    "who will",
    "result",
    "winner",
    "yogi adityanath",
    "modi",
    "rahul",
    "akhilesh",
    "mayawati",
    "government policy",
    "scheme launch",
    "budget",
    "census",
    "why",
    "explain",
    "what is",
    "background",
    "history",
}


def _needs_web_search(question: str, graph_results: list[dict]) -> bool:
    q = question.lower()
    # Graph returned nothing useful
    if not graph_results:
        return True
    if len(graph_results) == 1 and "cannot answer" in str(graph_results[0]).lower():
        return True
    # Question is about real-time or general knowledge
    if any(kw in q for kw in _WEB_SIGNALS):
        return True
    # Graph-native question with good results -> still supplement unless purely internal
    if any(kw in q for kw in _GRAPH_ONLY_TERMS) and len(graph_results) >= 3:
        return False
    return True  # default: always supplement with web


# ── Synthesis ─────────────────────────────────────────────────────────────────


def _build_context(graph_results: list[dict], web_results: list[dict]) -> str:
    import json

    parts: list[str] = []
    has_graph = graph_results and not (
        len(graph_results) == 1 and "cannot answer" in str(graph_results[0]).lower()
    )
    if has_graph:
        parts.append(f"=== KNOWLEDGE GRAPH DATA ({len(graph_results)} records) ===")
        for row in graph_results[:15]:
            parts.append(json.dumps(row, default=str))
    if web_results:
        parts.append(f"\n=== WEB SEARCH RESULTS ({len(web_results)} sources) ===")
        for r in web_results:
            parts.append(f"[{r.get('source','Web')}] {r.get('title','')}")
            parts.append(f"  {r.get('snippet','')}")
            if r.get("url"):
                parts.append(f"  Source: {r['url']}")
    return "\n".join(parts) if parts else "No data available."


def synthesize_answer(question: str, graph_results: list[dict], web_results: list[dict]) -> str:
    context = _build_context(graph_results, web_results)
    user_msg = (
        f"Question: {question}\n\n"
        f"Available Data:\n{context}\n\n"
        "Provide a comprehensive political intelligence analysis answering this question."
    )
    msgs = [
        {"role": "system", "content": _SYNTHESIS_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    try:
        answer = _call_sarvam(msgs, max_tokens=2500)
        if answer:
            return answer
    except Exception as e:
        logger.warning("Sarvam synthesis failed: %s", e)
    try:
        answer = _call_gemini(_SYNTHESIS_SYSTEM, user_msg, 1024)
        if answer:
            return answer
    except Exception as e:
        logger.warning("Gemini synthesis failed: %s", e)
    return _plain_summarise(graph_results, web_results)


def _plain_summarise(graph_results: list[dict], web_results: list[dict]) -> str:
    parts: list[str] = []
    if graph_results:
        parts.append(f"Knowledge graph returned {len(graph_results)} record(s).")
        first = graph_results[0]
        sample = "; ".join(f"{k}: {v}" for k, v in list(first.items())[:4])
        parts.append(f"Sample: {sample}")
    if web_results:
        parts.append(f"\nWeb search found {len(web_results)} result(s):")
        for r in web_results[:3]:
            parts.append(f"* {r.get('title','')}: {r.get('snippet','')[:150]}")
    return "\n".join(parts) or "No data found for this question."


def _mode_label(graph_results: list[dict], web_results: list[dict]) -> str:
    has_graph = bool(graph_results) and not (
        len(graph_results) == 1 and "cannot answer" in str(graph_results[0]).lower()
    )
    if has_graph and web_results:
        return "hybrid"
    if has_graph:
        return "graph"
    if web_results:
        return "web"
    return "llm"


# ── Public entry point ────────────────────────────────────────────────────────


def reasoning_query(question: str) -> dict:
    """
    Full pipeline: NL -> Cypher -> Neo4j -> web search -> LLM synthesis.

    Returns rich dict:
      question, cypher, graph_results, results (alias), web_results,
      answer, summary (compat), sources, mode, row_count, elapsed_ms, error
    """
    t0 = time.monotonic()
    cypher: str | None = None
    graph_results: list = []
    graph_error: str | None = None

    # Step 1: Neo4j
    try:
        cypher = generate_cypher(question)
        logger.info("Cypher generated: %.150s", cypher)
    except Exception as exc:
        graph_error = f"Cypher generation failed: {exc}"
        logger.warning(graph_error)

    if cypher and not graph_error:
        try:
            graph_results = execute_cypher(cypher)
        except Exception as exc:
            graph_error = f"Neo4j execution failed: {exc}"
            logger.warning(graph_error)

    # Step 2: Web search
    web_results: list[dict] = []
    if _needs_web_search(question, graph_results):
        try:
            web_results = web_search(question)
            logger.info("Web search: %d results", len(web_results))
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)

    # Step 3: Synthesis
    answer = ""
    try:
        answer = synthesize_answer(question, graph_results, web_results)
    except Exception as exc:
        logger.error("Synthesis failed: %s", exc)
        answer = _plain_summarise(graph_results, web_results)

    sources = [r["url"] for r in web_results if r.get("url")]
    mode = _mode_label(graph_results, web_results)

    return {
        "question": question,
        "cypher": cypher,
        "graph_results": graph_results,
        "results": graph_results,  # legacy field — keep for compat
        "web_results": web_results,
        "answer": answer,
        "summary": answer[:300] if answer else None,
        "sources": sources,
        "mode": mode,
        "row_count": len(graph_results),
        "elapsed_ms": round((time.monotonic() - t0) * 1000),
        "error": graph_error,
    }
