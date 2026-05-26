from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Query
from ..queries import (
    _rac, get_conversion_overview, get_conversion_stats,
    get_ac_candidates, get_ac_schemes, get_ac_narratives,
    get_ac_events, get_ac_quality, get_ac_recommendations,
    get_booth_geo, get_ac_intel_summary, get_ac_booth_election_rows,
    get_ac_election_results, get_ac_demographics_summary,
    get_ac_demographic_segments, get_heatmap_coverage,
    get_twin_snapshot, get_graph_coverage, get_ac_level_pulse,
    get_ac_level_issues
)
from ..validation import InputValidationRoute
from ..schemas import (
    CandidateResponse, SchemeResponse, ConversionOverviewResponse,
    BoothGeoResponse, IntelSummaryResponse
)

router = APIRouter(route_class=InputValidationRoute)


@router.get("/ac/{ac_id}/conversion-overview", response_model=ConversionOverviewResponse)
def conversion_overview(ac_id: str):
    """Per-booth beneficiary + conversion funnel stats — powers the main dashboard."""
    rows = get_conversion_overview(_rac(ac_id))
    return {"ac_id": ac_id, "booths": rows}


@router.get("/ac/{ac_id}/conversion-stats")
def conversion_stats(ac_id: str):
    """AC-level KPIs: total beneficiaries, targets, contacted, top schemes."""
    return {"ac_id": ac_id, **get_conversion_stats(_rac(ac_id))}


@router.get("/ac/{ac_id}/candidates", response_model=CandidateResponse)
def ac_candidates(ac_id: str):
    return {"ac_id": ac_id, "candidates": get_ac_candidates(_rac(ac_id))}


@router.get("/ac/{ac_id}/schemes", response_model=SchemeResponse)
def ac_schemes(ac_id: str):
    """Aggregated scheme gap analysis across all booths in an AC."""
    return {"ac_id": ac_id, "schemes": get_ac_schemes(_rac(ac_id))}


@router.get("/ac/{ac_id}/narratives")
def ac_narratives(ac_id: str):
    """Aggregate narrative trends for the AC."""
    return {"ac_id": ac_id, "narratives": get_ac_narratives(_rac(ac_id))}


@router.get("/ac/{ac_id}/events")
def ac_events(ac_id: str, limit: int = Query(50, ge=1, le=200)):
    """Political events timeline for the AC."""
    return {"ac_id": ac_id, "events": get_ac_events(_rac(ac_id), limit=limit)}


@router.get("/ac/{ac_id}/quality")
def ac_quality(ac_id: str):
    """AC-level data quality summary (aggregated across booths)."""
    return {"ac_id": ac_id, **get_ac_quality(_rac(ac_id))}


@router.get("/ac/{ac_id}/recommendations")
def ac_recommendations(ac_id: str):
    """Strategic risks, opportunities, and action items derived from live data."""
    recs = get_ac_recommendations(_rac(ac_id))
    if not recs:
        raise HTTPException(204, "Insufficient data for recommendations")
    return {"ac_id": ac_id, **recs}


@router.get("/ac/{ac_id}/geo", response_model=BoothGeoResponse)
def ac_geo(ac_id: str):
    """Geocoded booth positions with pulse scores — used by the Geospatial Intelligence page."""
    rows = get_booth_geo(_rac(ac_id))
    return {"ac_id": ac_id, "count": len(rows), "geo": rows}


@router.get("/ac/{ac_id}/intel-summary", response_model=IntelSummaryResponse)
def ac_intel_summary(ac_id: str):
    """Combined intelligence summary: voter stats (PG) + issues/videos/candidates (Neo4j)."""
    return {"ac_id": ac_id, **get_ac_intel_summary(ac_id)}


@router.get("/ac/{ac_id}/booth-election-rows")
def ac_booth_election_rows(ac_id: str, year: int = Query(2022, ge=2000, le=2030)):
    """Per-booth per-party vote rows with turnout — bulk call for demographics page."""
    rows = get_ac_booth_election_rows(_rac(ac_id), year=year)
    return {"ac_id": ac_id, "year": year, "rows": rows}


@router.get("/ac/{ac_id}/election-results")
def ac_election_results(ac_id: str, year: int = Query(2022, ge=2000, le=2030)):
    """AC-level election results aggregated from booth_results."""
    data = get_ac_election_results(_rac(ac_id), year=year)
    if not data["results"]:
        raise HTTPException(404, f"No election results found for AC '{ac_id}', year {year}.")
    return {"ac_id": ac_id, **data}


@router.get("/ac/{ac_id}/demographics/summary")
def ac_demographics_summary(ac_id: str):
    """Voter demographics summary from ac_demographics table."""
    data = get_ac_demographics_summary(_rac(ac_id))
    if not data:
        raise HTTPException(404, f"No demographics data for AC '{ac_id}'.")
    return data


@router.get("/ac/{ac_id}/demographics/segments")
def ac_demographics_segments(ac_id: str):
    """Booth-level demographic segments for targeting and messaging."""
    segments = get_ac_demographic_segments(_rac(ac_id))
    return {"ac_id": ac_id, "segments": segments}


@router.get("/ac/{ac_id}/heatmap-coverage")
def ac_heatmap_coverage(ac_id: str, target_pct: float = Query(0.85, ge=0.1, le=1.0)):
    """Heatmap readiness KPI. Target default is 85% geocoded booth coverage."""
    return get_heatmap_coverage(_rac(ac_id), target_pct=target_pct)


@router.get("/ac/{ac_id}/twin-snapshot")
def ac_twin_snapshot(ac_id: str):
    """Ontology twin snapshot combining graph topology, heatmap readiness, and segments."""
    return get_twin_snapshot(_rac(ac_id))


@router.get("/ac/{ac_id}/graph-coverage")
def graph_coverage(ac_id: str):
    """Per-booth: lat/lon from PostgreSQL plus Neo4j graph presence and degree."""
    rows = get_graph_coverage(ac_id)
    neo4j_count = sum(1 for b in rows if b.get("in_neo4j"))
    return {"ac_id": ac_id, "total": len(rows), "in_neo4j": neo4j_count, "booths": rows}


@router.get("/ac/{ac_id}/intel")
def ac_intel(ac_id: str, days: int = Query(365, ge=1, le=3650)):
    """
    Honest AC-level pulse intelligence derived from pulse_events.
    """
    pulse  = get_ac_level_pulse(_rac(ac_id), days=days)
    issues = get_ac_level_issues(_rac(ac_id), days=days)
    return {
        "ac_id":             ac_id,
        "attribution_level": pulse["attribution_level"],
        "window_days":       days,
        "total_events":      pulse["total_events"],
        "polarity_events":   pulse["polarity_events"],
        "booth_attributed":  pulse["booth_attributed"],
        "avg_geo_confidence": pulse["avg_geo_confidence"],
        "bjp_pulse":         pulse["bjp_pulse"],
        "opp_pulse":         pulse["opp_pulse"],
        "lean":              pulse["lean"],
        "top_issues":        issues,
        "warning":           pulse["warning"],
    }
