"""FastAPI application — 6 endpoints for the Gorakhpur KG dashboard."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .queries import (
    get_booths_for_ac, get_booth_summary, get_booth_history,
    get_booth_issues, get_booth_pulse, get_booth_comments,
    get_ac_candidates, get_candidate_issue_sentiment, get_scheme_gap,
    get_booth_quality, get_booth_narratives, get_booth_contradictions,
    get_ac_schemes, get_ac_narratives, get_ac_events,
    get_ac_quality, get_ac_recommendations, get_graph_subgraph,
)

app = FastAPI(
    title="Gorakhpur KG API",
    description="Booth-level political intelligence for Gorakhpur Urban AC",
    version="0.1.0",
)

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
    rows = get_booths_for_ac(ac_id)
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
    return {"ac_id": ac_id, "candidates": get_ac_candidates(ac_id)}


@app.get("/ac/{ac_id}/schemes")
def ac_schemes(ac_id: str):
    """Aggregated scheme gap analysis across all booths in an AC."""
    return {"ac_id": ac_id, "schemes": get_ac_schemes(ac_id)}


@app.get("/ac/{ac_id}/narratives")
def ac_narratives(ac_id: str):
    """Aggregate narrative trends for the AC."""
    return {"ac_id": ac_id, "narratives": get_ac_narratives(ac_id)}


@app.get("/ac/{ac_id}/events")
def ac_events(ac_id: str, limit: int = Query(50, ge=1, le=200)):
    """Political events timeline for the AC."""
    return {"ac_id": ac_id, "events": get_ac_events(ac_id, limit=limit)}


@app.get("/ac/{ac_id}/quality")
def ac_quality(ac_id: str):
    """AC-level data quality summary (aggregated across booths)."""
    return {"ac_id": ac_id, **get_ac_quality(ac_id)}


@app.get("/ac/{ac_id}/recommendations")
def ac_recommendations(ac_id: str):
    """Strategic risks, opportunities, and action items derived from live data."""
    recs = get_ac_recommendations(ac_id)
    if not recs:
        raise HTTPException(204, "Insufficient data for recommendations")
    return {"ac_id": ac_id, **recs}


@app.get("/graph/subgraph")
def graph_subgraph(
    entity_type: str = Query(..., description="AC | Booth | Issue | Candidate | Party | Scheme"),
    entity_id:   str = Query(..., description="The entity's primary ID value"),
):
    """1-hop subgraph from Neo4j around the specified entity."""
    result = get_graph_subgraph(entity_type, entity_id)
    return result if result else {"nodes": [], "edges": []}


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
