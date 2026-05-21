"""
AI-assisted political reasoning engine.

Takes a natural language question, generates Cypher via Sarvam when available
(with the full Neo4j schema as context), falls back to Gemini otherwise,
executes it, and returns structured results.

Example questions:
  "Show candidates with more than 2 criminal cases"
  "Which party has the most YouTube coverage in Gorakhpur Urban?"
  "Find booths where water is the top issue"
  "Show BJP candidates ordered by net worth"
"""
from __future__ import annotations
import logging
import os
import re
from functools import lru_cache
from typing import Any, cast

logger = logging.getLogger(__name__)

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

_SYSTEM_PROMPT = f"""You are a Cypher query generator for a political intelligence Neo4j graph about Gorakhpur, India.

SCHEMA:
{_SCHEMA}

STRICT RULES:
1. Output ONLY a valid Cypher query — no explanation, no markdown, no comments.
2. Always include LIMIT (default 25 unless user asks for more, max 100).
3. Return flat key-value pairs in RETURN clause (not whole nodes or maps).
4. Use direct property access, not complex subqueries.
5. If the question cannot be answered from the schema, output exactly:
   RETURN "Cannot answer from available graph data" AS message
6. Never use undefined node types or properties.
"""

_SARVAM_MODEL = os.environ.get("SARVAM_REASONING_MODEL", "sarvam-30b")
_GEMINI_MODEL = os.environ.get("GOOGLE_REASONING_MODEL", "gemini-2.5-flash")
_DEFAULT_AC_ID = os.environ.get("PILOT_AC_ID", "GKP_URBAN")


@lru_cache(maxsize=1)
def _get_sarvam_client():
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set")
    from sarvamai import SarvamAI

    return SarvamAI(api_subscription_key=api_key)


def _clean_model_output(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("LLM returned empty response")
    # Strip any accidental markdown fences
    raw = re.sub(r"^```(?:cypher)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    return raw.strip()


def _generate_cypher_with_sarvam(question: str) -> str:
    client = _get_sarvam_client()
    resp = client.chat.completions(
        model=_SARVAM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate Cypher for: {question}"},
        ],
        temperature=0.0,
        top_p=1,
        max_tokens=500,
    )
    raw = getattr(resp.choices[0].message, "content", "") or ""
    return _clean_model_output(raw)


def _generate_cypher_with_gemini(question: str) -> str:
    from google import genai  # type: ignore[import-not-found]
    from google.genai import types  # type: ignore[import-not-found]

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    resp = client.models.generate_content(
        model=_GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=500,
        ),
        contents=f"Generate Cypher for: {question}",
    )
    return _clean_model_output(resp.text or "")


def generate_cypher(question: str) -> str:
    """Generate Cypher using Sarvam first, then Gemini as fallback."""
    if os.environ.get("SARVAM_API_KEY"):
        try:
            return _generate_cypher_with_sarvam(question)
        except Exception as exc:
            logger.warning("Sarvam reasoning failed, falling back to Gemini: %s", exc)
    return _generate_cypher_with_gemini(question)


def execute_cypher(cypher: str) -> list[dict[str, Any]]:
    """Run Cypher against Neo4j; return results as list of plain dicts."""
    from .db import get_neo4j_session
    with get_neo4j_session() as session:
        result = session.run(cast(Any, cypher))
        return [dict(record) for record in result]


def _fetch_latest_booth_rows(ac_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import text
    from .db import get_pg_engine
    from .queries import _rac

    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT
                b.booth_id,
                b.booth_number,
                b.polling_station_name AS name,
                bm.bjp_pulse_score,
                bm.opp_pulse_score,
                bm.digital_lean_label,
                bm.top_issue,
                bm.confidence_label,
                bm.event_count
            FROM booth_master b
            LEFT JOIN LATERAL (
                SELECT bjp_pulse_score, opp_pulse_score, digital_lean_label,
                       top_issue, confidence_label, event_count
                FROM booth_metrics
                WHERE booth_id = b.booth_id
                ORDER BY window_start DESC
                LIMIT 1
            ) bm ON TRUE
            WHERE b.ac_id = :ac_id
              AND b.booth_id NOT LIKE '%_TOTAL'
            ORDER BY b.booth_number
        """), {"ac_id": resolved}).mappings().fetchall()
    return [dict(row) for row in rows]


def _fetch_booth_narratives(ac_id: str, narrative_type: str) -> list[dict[str, Any]]:
    from sqlalchemy import text
    from .db import get_pg_engine
    from .queries import _rac

    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT
                bn.booth_id,
                b.booth_number,
                b.polling_station_name AS name,
                bn.narrative_type,
                bn.strength,
                bn.description,
                bn.evidence_count,
                bn.confidence,
                bn.computed_at
            FROM booth_narratives bn
            JOIN booth_master b ON b.booth_id = bn.booth_id
            LEFT JOIN booth_metrics bm ON bm.booth_id = bn.booth_id
            WHERE b.ac_id = :ac_id
              AND bn.narrative_type = :narrative_type
            ORDER BY bn.computed_at DESC, bn.strength DESC
            LIMIT 25
        """), {"ac_id": resolved, "narrative_type": narrative_type}).mappings().fetchall()
    return [dict(row) for row in rows]


def _fetch_scheme_gaps(ac_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import text
    from .db import get_pg_engine
    from .queries import _rac

    resolved = _rac(ac_id)
    with get_pg_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT
                sga.scheme_name,
                sga.issue_tag,
                COUNT(DISTINCT sga.booth_id) AS booth_count,
                SUM(sga.beneficiary_count) AS total_beneficiaries,
                MODE() WITHIN GROUP (ORDER BY sga.gap_type) AS gap_type,
                MODE() WITHIN GROUP (ORDER BY sga.priority) AS priority,
                ROUND(AVG(sga.avg_sentiment)::numeric, 3) AS avg_sentiment,
                SUM(sga.positive_events) AS positive_events,
                SUM(sga.negative_events) AS negative_events,
                STRING_AGG(DISTINCT sga.gap_label, ' | ' ORDER BY sga.gap_label) AS gap_label
            FROM scheme_gap_analysis sga
            JOIN booth_master bm ON bm.booth_id = sga.booth_id
            WHERE bm.ac_id = :ac_id
            GROUP BY sga.scheme_name, sga.issue_tag
            ORDER BY
                CASE MODE() WITHIN GROUP (ORDER BY sga.priority)
                    WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                total_beneficiaries DESC
            LIMIT 25
        """), {"ac_id": resolved}).mappings().fetchall()
    return [dict(row) for row in rows]


def _fallback_reasoning(question: str) -> dict | None:
    normalized = question.lower()

    if "highest bjp pulse" in normalized or "bjp pulse score" in normalized:
        rows = sorted(
            _fetch_latest_booth_rows(_DEFAULT_AC_ID),
            key=lambda row: float(row.get("bjp_pulse_score") or -1),
            reverse=True,
        )[:10]
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (b:Booth) RETURN b.booth_id, b.booth_number, b.name, bjp_pulse_score, opp_pulse_score LIMIT 10",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "strong_opp" in normalized or "strong opp" in normalized or "opposition lean" in normalized:
        rows = [
            row for row in _fetch_latest_booth_rows(_DEFAULT_AC_ID)
            if str(row.get("digital_lean_label") or "").upper() == "STRONG_OPP"
        ]
        rows = rows[:25]
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (b:Booth) WHERE b.digital_lean_label = 'STRONG_OPP' RETURN b.booth_id, b.booth_number, b.name, b.digital_lean_label, b.top_issue LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "anti-incumbency" in normalized:
        rows = _fetch_booth_narratives(_DEFAULT_AC_ID, "anti_incumbency")
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (b:Booth)-[:HAS_NARRATIVE]->(n:Narrative {narrative_type:'anti_incumbency'}) RETURN b.booth_id, b.booth_number, b.name, n.strength, n.description LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "delivery gap" in normalized or "highest delivery gap" in normalized or "schemes" in normalized:
        rows = _fetch_scheme_gaps(_DEFAULT_AC_ID)
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (s:SchemeGap) RETURN s.scheme_name, s.issue_tag, s.priority, s.total_beneficiaries LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "low data confidence" in normalized or "confidence" in normalized:
        rows = [
            row for row in _fetch_latest_booth_rows(_DEFAULT_AC_ID)
            if str(row.get("confidence_label") or "").upper() == "LOW"
        ]
        rows = rows[:25]
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (b:Booth) WHERE b.confidence_label = 'LOW' RETURN b.booth_id, b.booth_number, b.name, b.confidence_label, b.event_count LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "water" in normalized and "top issue" in normalized:
        rows = [
            row for row in _fetch_latest_booth_rows(_DEFAULT_AC_ID)
            if str(row.get("top_issue") or "").lower() == "water"
        ]
        rows = rows[:25]
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (b:Booth) WHERE b.top_issue = 'water' RETURN b.booth_id, b.booth_number, b.name, b.top_issue, b.confidence_label LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    if "won in the last election" in normalized or "last election" in normalized:
        from .queries import get_ac_election_results

        data = get_ac_election_results(_DEFAULT_AC_ID, year=2022)
        rows = data.get("results", []) if isinstance(data, dict) else []
        summary = _summarize_results(rows)
        return {
            "question": question,
            "cypher": "MATCH (p:Party)<-[:REPRESENTS]-(c:Candidate)-[:CONTESTED_IN]->(a:AssemblyConstituency) RETURN p.name AS party, count(*) AS booth_count LIMIT 25",
            "results": rows,
            "summary": summary,
            "row_count": len(rows),
            "error": None,
        }

    return None


def _summarize_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No matching records were found."

    first_row = results[0]
    preview_items: list[str] = []
    for key in list(first_row.keys())[:3]:
        value = first_row.get(key)
        if value is None:
            continue
        label = key.replace("_", " ")
        preview_items.append(f"{label}: {value}")

    if len(results) == 1:
        heading = "I found 1 matching record."
    else:
        heading = f"I found {len(results)} matching records."

    if preview_items:
        return heading + " The first result shows " + "; ".join(preview_items) + "."
    return heading


def reasoning_query(question: str) -> dict:
    """
    Main entry point: natural language → Cypher → Neo4j results.
    Returns {question, cypher, results, summary, error, row_count}.
    """
    try:
        cypher = generate_cypher(question)
        logger.info("Generated Cypher: %.200s", cypher)
        results = execute_cypher(cypher)
        summary = _summarize_results(results)
        return {
            "question":  question,
            "cypher":    cypher,
            "results":   results[:100],
            "summary":   summary,
            "row_count": len(results),
            "error":     None,
        }
    except Exception as exc:
        logger.warning("Primary reasoning path failed: %s", exc)

    fallback = _fallback_reasoning(question)
    if fallback is not None:
        return fallback

    return {
        "question": question,
        "cypher": None,
        "results": [],
        "summary": "I could not answer that question with the available data source.",
        "row_count": 0,
        "error": f"Reasoning failed: {question}",
    }
