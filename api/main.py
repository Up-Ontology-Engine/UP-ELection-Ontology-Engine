"""FastAPI application — 6 endpoints for the Gorakhpur KG dashboard."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from .queries import (
    _rac,
    get_booths_for_ac, get_booth_summary, get_booth_history,
    get_booth_issues, get_booth_pulse, get_booth_comments,
    get_ac_candidates, get_scheme_gap,
    get_booth_quality, get_booth_narratives, get_booth_contradictions,
    get_ac_schemes, get_ac_narratives, get_ac_events,
    get_ac_quality, get_ac_recommendations, get_graph_subgraph,
    get_booth_geo, get_infrastructure_overview, get_graph_coverage,
    get_ac_intel_summary, get_ac_election_results, get_ac_demographics_summary,
    get_ac_booth_election_rows, get_ontology_status,
    get_ac_demographic_segments, get_heatmap_coverage, get_twin_snapshot,
    init_chat_tables, create_session, get_sessions, get_session,
    get_session_messages, add_message, update_session_title, delete_session,
    init_beneficiary_tables, seed_demo_beneficiaries,
    get_conversion_overview, get_conversion_targets,
    mark_beneficiary_contacted, bulk_import_beneficiaries, get_conversion_stats,
)
from .reasoning import reasoning_query

app = FastAPI(
    title="Gorakhpur KG API",
    description="Booth-level political intelligence for Gorakhpur Urban AC",
    version="0.1.0",
)


@app.on_event("startup")
def _startup():
    try:
        init_chat_tables()
    except Exception as exc:
        print(f"[startup] chat tables init failed: {exc}")
    try:
        init_beneficiary_tables()
    except Exception as exc:
        print(f"[startup] beneficiary tables init failed: {exc}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "ac": os.environ.get("PILOT_AC_ID", "GKP_URBAN")}


@app.get("/ac/{ac_id}/booths")
def list_booths(ac_id: str):
    """All booths for an AC with latest pulse scores. Powers the booth selector."""
    rows = get_booths_for_ac(_rac(ac_id))
    if not rows:
        raise HTTPException(404, f"AC '{ac_id}' not found or has no booths.")
    return {"ac_id": ac_id, "count": len(rows), "booths": rows}


@app.get("/booth/{booth_id}/summary")
def booth_summary(booth_id: str, days: int = Query(7, ge=1, le=90)):
    """
    Full Booth 223-style summary card:
    historical results + digital pulse + issues + scheme gap + insights.
    """
    meta = get_booth_summary(booth_id)
    if not meta:
        raise HTTPException(404, f"Booth '{booth_id}' not found.")

    history   = get_booth_history(booth_id)
    pulse     = get_booth_pulse(booth_id, days=days)
    issues    = get_booth_issues(booth_id, limit=5)
    comments  = get_booth_comments(booth_id, limit=5)
    scheme_gaps = get_scheme_gap(booth_id)

    # Derive BJP historical summary
    bjp_history = [h for h in history if h["party"] in ("BJP", "भाजपा")]
    bjp_wins = sum(1 for h in bjp_history if h["winner_flag"])
    bjp_shares = [h["vote_share"] for h in bjp_history if h["vote_share"] is not None]

    # Issue momentum text (top 3 with change %)
    import json
    momentum_raw = meta.get("issue_momentum") or "{}"
    momentum = json.loads(momentum_raw) if isinstance(momentum_raw, str) else {}
    top_momentum = sorted(momentum.items(), key=lambda x: abs(x[1]), reverse=True)[:3]

    # Intelligence layer
    quality       = get_booth_quality(booth_id)
    narratives    = get_booth_narratives(booth_id)
    contradictions = get_booth_contradictions(booth_id)

    # Confidence
    conf_label = meta.get("confidence_label", "UNKNOWN")

    # Generate key insight
    insight = _generate_insight(meta, bjp_wins, bjp_shares, issues, momentum)
    recommendation = _generate_recommendation(issues, momentum)

    return {
        "booth_id": booth_id,
        "booth_number": meta.get("booth_number"),
        "name": meta.get("polling_station_name"),
        "ac_name": os.environ.get("PILOT_AC_NAME", "Gorakhpur Urban"),
        "total_voters": meta.get("total_voters"),
        "male_voters": meta.get("male_voters"),
        "female_voters": meta.get("female_voters"),
        # Historical
        "historical": {
            "bjp_won_count": bjp_wins,
            "bjp_vote_shares": bjp_shares,
            "trend": "declining" if len(bjp_shares) >= 2 and bjp_shares[-1] < bjp_shares[-2] else "stable",
            "full_history": history,
        },
        # Digital pulse
        "digital_pulse": {
            "lean_label": meta.get("digital_lean_label", "Insufficient data"),
            "bjp_pulse": meta.get("bjp_pulse_score"),
            "opp_pulse": meta.get("opp_pulse_score"),
            "digital_lean": meta.get("digital_lean"),
            "pulse_detail": pulse,
        },
        # Confidence + quality
        "confidence": {
            "label": conf_label,
            "score": meta.get("data_confidence"),
            "event_count": meta.get("event_count", 0),
        },
        "data_quality": quality,
        # Issues
        "top_issues": issues,
        "issue_momentum": dict(top_momentum),
        # Comments (backing evidence)
        "backing_comments": comments,
        # Scheme gap
        "scheme_analysis": scheme_gaps,
        # Intelligence layer
        "narratives":      narratives,
        "contradictions":  contradictions,
        # Insight + recommendation
        "key_insight": insight,
        "recommendation": recommendation,
    }


@app.get("/booth/{booth_id}/quality")
def booth_quality(booth_id: str):
    """Data quality metrics for a booth — shows WHY confidence is what it is."""
    quality = get_booth_quality(booth_id)
    if not quality:
        raise HTTPException(404, f"No quality metrics found for booth '{booth_id}'.")
    return {"booth_id": booth_id, "quality": quality}


@app.get("/booth/{booth_id}/narratives")
def booth_narratives(
    booth_id: str,
    limit: int = Query(5, ge=1, le=10),
):
    """Detected narrative patterns for a booth (anti-incumbency, development, etc.)."""
    narratives = get_booth_narratives(booth_id, limit=limit)
    return {"booth_id": booth_id, "narratives": narratives}


@app.get("/booth/{booth_id}/contradictions")
def booth_contradictions(booth_id: str):
    """Cross-source signal conflicts for entities at a booth."""
    contradictions = get_booth_contradictions(booth_id)
    has_mixed = any(c["flag_label"] == "MIXED_SIGNALS" for c in contradictions)
    return {
        "booth_id":       booth_id,
        "has_mixed_signals": has_mixed,
        "contradictions": contradictions,
    }


@app.get("/booth/{booth_id}/pulse")
def booth_pulse(booth_id: str, days: int = Query(7, ge=1, le=90)):
    pulse = get_booth_pulse(booth_id, days=days)
    return {"booth_id": booth_id, "window_days": days, "pulse": pulse}


@app.get("/booth/{booth_id}/issues")
def booth_issues(booth_id: str, limit: int = Query(5, ge=1, le=10)):
    return {"booth_id": booth_id, "issues": get_booth_issues(booth_id, limit=limit)}


@app.get("/booth/{booth_id}/comments")
def booth_comments(
    booth_id: str,
    limit: int = Query(10, ge=1, le=50),
    source: str = Query("all"),
):
    return {"booth_id": booth_id, "comments": get_booth_comments(booth_id, limit, source)}


@app.get("/ac/{ac_id}/candidates")
def ac_candidates(ac_id: str):
    return {"ac_id": ac_id, "candidates": get_ac_candidates(_rac(ac_id))}


@app.get("/ac/{ac_id}/schemes")
def ac_schemes(ac_id: str):
    """Aggregated scheme gap analysis across all booths in an AC."""
    return {"ac_id": ac_id, "schemes": get_ac_schemes(_rac(ac_id))}


@app.get("/ac/{ac_id}/narratives")
def ac_narratives(ac_id: str):
    """Aggregate narrative trends for the AC."""
    return {"ac_id": ac_id, "narratives": get_ac_narratives(_rac(ac_id))}


@app.get("/ac/{ac_id}/events")
def ac_events(ac_id: str, limit: int = Query(50, ge=1, le=200)):
    """Political events timeline for the AC."""
    return {"ac_id": ac_id, "events": get_ac_events(_rac(ac_id), limit=limit)}


@app.get("/ac/{ac_id}/quality")
def ac_quality(ac_id: str):
    """AC-level data quality summary (aggregated across booths)."""
    return {"ac_id": ac_id, **get_ac_quality(_rac(ac_id))}


@app.get("/ac/{ac_id}/recommendations")
def ac_recommendations(ac_id: str):
    """Strategic risks, opportunities, and action items derived from live data."""
    recs = get_ac_recommendations(_rac(ac_id))
    if not recs:
        raise HTTPException(204, "Insufficient data for recommendations")
    return {"ac_id": ac_id, **recs}


@app.get("/graph/subgraph")
def graph_subgraph(
    entity_type:   str       = Query(..., description="AC | Booth | Issue | Candidate | Party | Scheme"),
    entity_id:     str       = Query(..., description="The entity's primary ID value"),
    exclude_types: list[str] = Query(default=[], description="Node types to exclude from results"),
    limit:         int       = Query(default=120, ge=1, le=300, description="Max neighbor nodes to return"),
):
    """1-hop subgraph from Neo4j around the specified entity."""
    result = get_graph_subgraph(entity_type, entity_id,
                                exclude_types=exclude_types, limit=limit)
    return result


@app.get("/ac/{ac_id}/geo")
def ac_geo(ac_id: str):
    """Geocoded booth positions with pulse scores — used by the Geospatial Intelligence page."""
    rows = get_booth_geo(_rac(ac_id))
    return {"ac_id": ac_id, "count": len(rows), "geo": rows}


@app.get("/ac/{ac_id}/intel-summary")
def ac_intel_summary(ac_id: str):
    """Combined intelligence summary: voter stats (PG) + issues/videos/candidates (Neo4j)."""
    return {"ac_id": ac_id, **get_ac_intel_summary(ac_id)}


@app.get("/ac/{ac_id}/booth-election-rows")
def ac_booth_election_rows(ac_id: str, year: int = Query(2022, ge=2000, le=2030)):
    """Per-booth per-party vote rows with turnout — bulk call for demographics page."""
    rows = get_ac_booth_election_rows(_rac(ac_id), year=year)
    return {"ac_id": ac_id, "year": year, "rows": rows}


@app.get("/ac/{ac_id}/election-results")
def ac_election_results(ac_id: str, year: int = Query(2022, ge=2000, le=2030)):
    """AC-level election results aggregated from booth_results."""
    data = get_ac_election_results(_rac(ac_id), year=year)
    if not data["results"]:
        raise HTTPException(404, f"No election results found for AC '{ac_id}', year {year}.")
    return {"ac_id": ac_id, **data}


@app.get("/ac/{ac_id}/demographics/summary")
def ac_demographics_summary(ac_id: str):
    """Voter demographics summary from ac_demographics table."""
    data = get_ac_demographics_summary(_rac(ac_id))
    if not data:
        raise HTTPException(404, f"No demographics data for AC '{ac_id}'.")
    return data


@app.get("/ac/{ac_id}/demographics/segments")
def ac_demographics_segments(ac_id: str):
    """Booth-level demographic segments for targeting and messaging."""
    segments = get_ac_demographic_segments(_rac(ac_id))
    return {"ac_id": ac_id, "segments": segments}


@app.get("/ac/{ac_id}/heatmap-coverage")
def ac_heatmap_coverage(ac_id: str, target_pct: float = Query(0.85, ge=0.1, le=1.0)):
    """Heatmap readiness KPI. Target default is 85% geocoded booth coverage."""
    return get_heatmap_coverage(_rac(ac_id), target_pct=target_pct)


@app.get("/ac/{ac_id}/twin-snapshot")
def ac_twin_snapshot(ac_id: str):
    """Ontology twin snapshot combining graph topology, heatmap readiness, and segments."""
    return get_twin_snapshot(_rac(ac_id))


@app.get("/infrastructure/overview")
def infrastructure_overview():
    """PostgreSQL table row counts + Neo4j node/edge topology for the Data Infrastructure page."""
    return get_infrastructure_overview()


@app.get("/ontology/status")
def ontology_status():
    """Live graph topology — node/rel counts, active constraints, PG table stats. Powers the Ontology Layer page."""
    return get_ontology_status()


@app.get("/ac/{ac_id}/graph-coverage")
def graph_coverage(ac_id: str):
    """Per-booth: lat/lon from PostgreSQL plus Neo4j graph presence and degree."""
    rows = get_graph_coverage(ac_id)
    neo4j_count = sum(1 for b in rows if b.get("in_neo4j"))
    return {"ac_id": ac_id, "total": len(rows), "in_neo4j": neo4j_count, "booths": rows}


class ReasoningRequest(BaseModel):
    question: str


@app.post("/reasoning/query")
def reasoning_endpoint(body: ReasoningRequest):
    """
    AI-assisted political reasoning: natural language → Cypher → Neo4j results.
    Powered by Sarvam LLM when `SARVAM_API_KEY` is set, otherwise Gemini.
    """
    if not body.question.strip():
        raise HTTPException(400, "question must not be empty")
    return reasoning_query(body.question.strip())


# ── Chat session endpoints ────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: Optional[str] = None

class AddMessageRequest(BaseModel):
    role: str
    content: str
    result: Optional[dict] = None
    ts: str

class UpdateTitleRequest(BaseModel):
    title: str


@app.get("/chat/sessions")
def list_sessions(limit: int = Query(50, ge=1, le=200)):
    """List all reasoning sessions, newest first."""
    return {"sessions": get_sessions(limit=limit)}


@app.post("/chat/sessions")
def new_session(body: CreateSessionRequest):
    """Create a new reasoning session."""
    return create_session(title=body.title)


@app.get("/chat/sessions/{session_id}")
def get_session_detail(session_id: str):
    """Get session metadata."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return sess


@app.get("/chat/sessions/{session_id}/messages")
def list_messages(session_id: str):
    """Load all messages for a session."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"session_id": session_id, "messages": get_session_messages(session_id)}


@app.post("/chat/sessions/{session_id}/messages")
def post_message(session_id: str, body: AddMessageRequest):
    """Append a message to a session."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return add_message(session_id, body.role, body.content, body.result, body.ts)


@app.patch("/chat/sessions/{session_id}/title")
def patch_session_title(session_id: str, body: UpdateTitleRequest):
    """Rename a session."""
    ok = update_session_title(session_id, body.title)
    if not ok:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"session_id": session_id, "title": body.title}


@app.delete("/chat/sessions/{session_id}")
def remove_session(session_id: str):
    """Delete a session and all its messages."""
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {"deleted": session_id}


# ── Voter Conversion Engine endpoints ────────────────────────────────────────

class ContactRequest(BaseModel):
    notes: Optional[str] = None
    worker_id: Optional[str] = None

class ImportBeneficiariesRequest(BaseModel):
    rows: list[dict]


@app.get("/ac/{ac_id}/conversion-overview")
def conversion_overview(ac_id: str):
    """Per-booth beneficiary + conversion funnel stats — powers the main dashboard."""
    rows = get_conversion_overview(_rac(ac_id))
    return {"ac_id": ac_id, "booths": rows}


@app.get("/ac/{ac_id}/conversion-stats")
def conversion_stats(ac_id: str):
    """AC-level KPIs: total beneficiaries, targets, contacted, top schemes."""
    return {"ac_id": ac_id, **get_conversion_stats(_rac(ac_id))}


@app.get("/booth/{booth_id}/conversion-targets")
def booth_conversion_targets(
    booth_id: str,
    contacted: Optional[bool] = Query(None, description="Filter by contacted status"),
    limit: int = Query(200, ge=1, le=500),
):
    """Route map: ordered beneficiary list for a booth's field worker."""
    rows = get_conversion_targets(booth_id, contacted=contacted, limit=limit)
    return {"booth_id": booth_id, "count": len(rows), "targets": rows}


@app.patch("/beneficiaries/{beneficiary_id}/contact")
def contact_beneficiary(beneficiary_id: str, body: ContactRequest):
    """Mark a beneficiary as contacted (with optional notes and worker ID)."""
    ok = mark_beneficiary_contacted(beneficiary_id, body.notes, body.worker_id)
    if not ok:
        raise HTTPException(404, f"Beneficiary '{beneficiary_id}' not found.")
    return {"beneficiary_id": beneficiary_id, "contacted": True}


@app.post("/beneficiaries/import")
def import_beneficiaries(body: ImportBeneficiariesRequest):
    """Bulk-import beneficiary records from Electoral Roll / scheme data."""
    if not body.rows:
        raise HTTPException(400, "rows must not be empty")
    count = bulk_import_beneficiaries(body.rows)
    return {"imported": count}


@app.post("/ac/{ac_id}/conversion/seed-demo")
def seed_demo(ac_id: str, per_booth: int = Query(18, ge=5, le=50)):
    """Seed synthetic beneficiary data for demo purposes."""
    count = seed_demo_beneficiaries(_rac(ac_id), per_booth=per_booth)
    return {"ac_id": ac_id, "seeded": count}


# ── Helper functions for insight/recommendation text ─────────────────────────

def _generate_insight(_meta: dict, bjp_wins: int, bjp_shares: list, issues: list, _momentum: dict) -> str:
    parts = []
    if bjp_wins >= 2:
        parts.append(f"Strong BJP base ({bjp_wins} consecutive wins)")
    if len(bjp_shares) >= 2 and bjp_shares[-1] < bjp_shares[-2]:
        parts.append(f"but vote share declining ({bjp_shares[-2]:.0f}% → {bjp_shares[-1]:.0f}%)")
    top_issue = issues[0]["issue"].replace("_", " ") if issues else ""
    if top_issue:
        parts.append(f"Growing dissatisfaction on {top_issue}")
    return ". ".join(parts) or "Insufficient data for insight."


def _generate_recommendation(issues: list, _momentum: dict) -> str:
    if not issues:
        return "Collect more data before making recommendations."
    top = [i["issue"].replace("_", " ") for i in issues[:2]]
    return f"Focus campaign on: {' + '.join(top)}. Address delivery gaps proactively."
