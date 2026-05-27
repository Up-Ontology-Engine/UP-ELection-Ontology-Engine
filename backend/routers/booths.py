from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..cache import clear_api_cache
from ..queries import (
    _rac,
    bulk_import_beneficiaries,
    get_booth_comments,
    get_booth_contradictions,
    get_booth_conversion,
    get_booth_history,
    get_booth_issues,
    get_booth_narratives,
    get_booth_pulse,
    get_booth_quality,
    get_booth_segments,
    get_booth_source_breakdown,
    get_booth_summary,
    get_booths_for_ac,
    get_conversion_targets,
    get_scheme_gap,
    mark_beneficiary_contacted,
    seed_demo_beneficiaries,
)
from ..validation import InputValidationRoute

router = APIRouter(route_class=InputValidationRoute)


class ContactRequest(BaseModel):
    notes: Optional[str] = None
    worker_id: Optional[str] = None


class ImportBeneficiariesRequest(BaseModel):
    rows: list[dict]


# ── Helper functions for insight/recommendation text ─────────────────────────


def _generate_insight(
    _meta: dict, bjp_wins: int, bjp_shares: list, issues: list, _momentum: dict
) -> str:
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


@router.get("/ac/{ac_id}/booths")
def list_booths(ac_id: str):
    """All booths for an AC with latest pulse scores. Powers the booth selector."""
    import json as _json

    from ..db import get_redis_client

    cache_key = f"cache:list_booths:{ac_id}"
    redis = get_redis_client()
    if redis:
        cached = redis.get(cache_key)
        if cached:
            return _json.loads(cached)

    rows = get_booths_for_ac(_rac(ac_id))
    if not rows:
        raise HTTPException(404, f"AC '{ac_id}' not found or has no booths.")
    result = {"ac_id": ac_id, "count": len(rows), "booths": rows}

    if redis:
        redis.setex(cache_key, 300, _json.dumps(result))
    return result


@router.get("/booth/{booth_id}/summary")
def booth_summary(booth_id: str, days: int = Query(7, ge=1, le=365)):
    """
    Full Booth 223-style summary card:
    historical results + digital pulse + issues + scheme gap + insights.
    """
    meta = get_booth_summary(booth_id)
    if not meta:
        raise HTTPException(404, f"Booth '{booth_id}' not found.")

    history = get_booth_history(booth_id)
    pulse = get_booth_pulse(booth_id, days=days)
    issues = get_booth_issues(booth_id, limit=12)
    comments = get_booth_comments(booth_id, limit=5)
    scheme_gaps = get_scheme_gap(booth_id)
    source_breakdown = get_booth_source_breakdown(booth_id)

    # Derive BJP historical summary
    bjp_history = [h for h in history if h["party"] in ("BJP", "भाजपा")]
    bjp_wins = sum(1 for h in bjp_history if h["winner_flag"])
    bjp_shares = [h["vote_share"] for h in bjp_history if h["vote_share"] is not None]

    # Issue momentum text (top 3 with change %)
    momentum_raw = meta.get("issue_momentum") or "{}"
    momentum = json.loads(momentum_raw) if isinstance(momentum_raw, str) else {}
    top_momentum = sorted(momentum.items(), key=lambda x: abs(x[1]), reverse=True)[:3]

    # Intelligence layer
    quality = get_booth_quality(booth_id)
    narratives = get_booth_narratives(booth_id)
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
        "address": meta.get("address"),
        "ac_name": os.environ.get("PILOT_AC_NAME", "Gorakhpur Urban"),
        "total_voters": meta.get("total_voters"),
        "male_voters": meta.get("male_voters"),
        "female_voters": meta.get("female_voters"),
        # Historical
        "historical": {
            "bjp_won_count": bjp_wins,
            "bjp_vote_shares": bjp_shares,
            "trend": (
                "declining"
                if len(bjp_shares) >= 2 and bjp_shares[-1] < bjp_shares[-2]
                else "stable"
            ),
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
        # Source breakdown
        "source_breakdown": source_breakdown,
        # Scheme gap
        "scheme_analysis": scheme_gaps,
        # Intelligence layer
        "narratives": narratives,
        "contradictions": contradictions,
        # Insight + recommendation
        "key_insight": insight,
        "recommendation": recommendation,
        # Honest attribution metadata — UI should gate on this
        "attribution_level": ("booth" if (meta.get("event_count") or 0) > 0 else "none"),
        "data_warning": (
            None
            if (meta.get("event_count") or 0) > 0
            else "Insufficient booth-linked digital evidence — no pulse events geo-attributed to this booth"
        ),
    }


@router.get("/booth/{booth_id}/quality")
def booth_quality(booth_id: str):
    """Data quality metrics for a booth — shows WHY confidence is what it is."""
    quality = get_booth_quality(booth_id)
    if not quality:
        raise HTTPException(404, f"No quality metrics found for booth '{booth_id}'.")
    return {"booth_id": booth_id, "quality": quality}


@router.get("/booth/{booth_id}/narratives")
def booth_narratives(booth_id: str, limit: int = Query(5, ge=1, le=10)):
    """Detected narrative patterns for a booth (anti-incumbency, development, etc.)."""
    narratives = get_booth_narratives(booth_id, limit=limit)
    return {"booth_id": booth_id, "narratives": narratives}


@router.get("/booth/{booth_id}/contradictions")
def booth_contradictions(booth_id: str):
    """Cross-source signal conflicts for entities at a booth."""
    contradictions = get_booth_contradictions(booth_id)
    has_mixed = any(c["flag_label"] == "MIXED_SIGNALS" for c in contradictions)
    return {
        "booth_id": booth_id,
        "has_mixed_signals": has_mixed,
        "contradictions": contradictions,
    }


@router.get("/booth/{booth_id}/segments")
def booth_segments(booth_id: str):
    """Privacy-safe voter demographic segments aggregated from electoral roll."""
    segments = get_booth_segments(booth_id)
    return {"booth_id": booth_id, "segments": segments}


@router.get("/booth/{booth_id}/conversion")
def booth_conversion(booth_id: str):
    """Conversion opportunity scores and recommended field action for a booth."""
    data = get_booth_conversion(booth_id)
    if not data:
        raise HTTPException(status_code=404, detail="No conversion data for this booth")
    return data


@router.get("/booth/{booth_id}/pulse")
def booth_pulse(booth_id: str, days: int = Query(7, ge=1, le=365)):
    pulse = get_booth_pulse(booth_id, days=days)
    return {"booth_id": booth_id, "window_days": days, "pulse": pulse}


@router.get("/booth/{booth_id}/issues")
def booth_issues(booth_id: str, limit: int = Query(5, ge=1, le=10)):
    return {"booth_id": booth_id, "issues": get_booth_issues(booth_id, limit=limit)}


@router.get("/booth/{booth_id}/comments")
def booth_comments(booth_id: str, limit: int = Query(10, ge=1, le=50), source: str = Query("all")):
    return {"booth_id": booth_id, "comments": get_booth_comments(booth_id, limit, source)}


@router.get("/booth/{booth_id}/conversion-targets")
def booth_conversion_targets(
    booth_id: str,
    contacted: Optional[bool] = Query(None, description="Filter by contacted status"),
    limit: int = Query(200, ge=1, le=500),
):
    """Route map: ordered beneficiary list for a booth's field worker."""
    rows = get_conversion_targets(booth_id, contacted=contacted, limit=limit)
    return {"booth_id": booth_id, "count": len(rows), "targets": rows}


@router.patch("/beneficiaries/{beneficiary_id}/contact")
def contact_beneficiary(beneficiary_id: str, body: ContactRequest):
    """Mark a beneficiary as contacted (with optional notes and worker ID)."""
    ok = mark_beneficiary_contacted(beneficiary_id, body.notes, body.worker_id)
    if not ok:
        raise HTTPException(404, f"Beneficiary '{beneficiary_id}' not found.")
    clear_api_cache()
    return {"beneficiary_id": beneficiary_id, "contacted": True}


@router.post("/beneficiaries/import")
def import_beneficiaries(body: ImportBeneficiariesRequest):
    """Bulk-import beneficiary records from Electoral Roll / scheme data."""
    if not body.rows:
        raise HTTPException(400, "rows must not be empty")
    count = bulk_import_beneficiaries(body.rows)
    return {"imported": count}


@router.post("/ac/{ac_id}/conversion/seed-demo")
def seed_demo(ac_id: str, per_booth: int = Query(18, ge=5, le=50)):
    """Seed synthetic beneficiary data for demo purposes."""
    count = seed_demo_beneficiaries(_rac(ac_id), per_booth=per_booth)
    return {"ac_id": ac_id, "seeded": count}
