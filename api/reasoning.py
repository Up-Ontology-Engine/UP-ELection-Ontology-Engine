"""
AI-assisted political reasoning engine.

Takes a natural language question, generates Cypher via Gemini (with the full
Neo4j schema as context), executes it, and returns structured results.

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
from typing import Any

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


def generate_cypher(question: str) -> str:
    """Ask Gemini to generate a Cypher query for the given question."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=500,
        ),
        contents=f"Generate Cypher for: {question}",
    )
    raw = (resp.text or "").strip()
    if not raw:
        raise ValueError("Gemini returned empty response")
    # Strip any accidental markdown fences
    raw = re.sub(r"^```(?:cypher)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "",           raw, flags=re.MULTILINE)
    return raw.strip()


def execute_cypher(cypher: str) -> list[dict[str, Any]]:
    """Run Cypher against Neo4j; return results as list of plain dicts."""
    from .db import get_neo4j_session
    with get_neo4j_session() as session:
        result = session.run(cypher)
        return [dict(record) for record in result]


def reasoning_query(question: str) -> dict:
    """
    Main entry point: natural language → Cypher → Neo4j results.
    Returns {question, cypher, results, error, row_count}.
    """
    try:
        cypher = generate_cypher(question)
        logger.info("Generated Cypher: %.200s", cypher)
    except Exception as exc:
        return {
            "question": question, "cypher": None,
            "results": [], "row_count": 0,
            "error": f"Cypher generation failed: {exc}",
        }

    try:
        results = execute_cypher(cypher)
        return {
            "question":  question,
            "cypher":    cypher,
            "results":   results[:100],
            "row_count": len(results),
            "error":     None,
        }
    except Exception as exc:
        return {
            "question":  question,
            "cypher":    cypher,
            "results":   [],
            "row_count": 0,
            "error":     f"Neo4j execution failed: {exc}",
        }
