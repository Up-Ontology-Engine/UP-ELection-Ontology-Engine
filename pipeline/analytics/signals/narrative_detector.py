"""Narrative detector moved into analytics.signals."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

NARRATIVE_ISSUE_MAP: dict[str, list[str]] = {
    "development_positive":  ["roads", "electricity", "water", "sanitation", "development"],
    "anti_incumbency":       [],
    "corruption_narrative":  ["corruption"],
    "price_rise_narrative":  ["prices", "inflation"],
    "women_safety_narrative":["women_safety", "crime"],
    "employment_crisis":     ["jobs", "unemployment", "employment"],
    "scheme_success":        ["pmay", "ujjwala", "swachh_bharat", "pm_kisan"],
    "swing_possible":        [],
}

RULING_PARTY = "BJP"
MIN_STRENGTH = 0.15


def _weighted_sentiment(rows, filter_fn=None) -> tuple[float, int]:
    source_weight = {"survey": 1.0, "field_note": 0.9, "youtube": 0.6, "news": 0.4}
    total_w = 0.0
    total_wv = 0.0
    count = 0
    for r in rows:
        if filter_fn and not filter_fn(r):
            continue
        w = (r["nlp_confidence"] or 0.5) * source_weight.get(r["source_type"] or "", 0.5)
        total_w += w
        total_wv += w * (r["final_polarity"] or 0)
        count += 1
    if total_w == 0:
        return 0.0, 0
    return total_wv / total_w, count


def detect_narratives_for_booth(
    engine: Engine,
    booth_id: str,
    window_days: int = 7,
    computed_at: Optional[datetime] = None,
) -> list[dict]:
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)
    cutoff = computed_at - timedelta(days=window_days)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    final_issue     AS issue,
                    entity,
                    entity_type,
                    final_polarity  AS final_polarity,
                    final_confidence AS nlp_confidence,
                    source_type
                FROM pulse_events
                WHERE mapped_booth_id = :booth_id
                  AND created_at >= :cutoff
                  AND created_at <= :now
                  AND final_polarity IS NOT NULL
            """), {"booth_id": booth_id, "cutoff": cutoff, "now": computed_at}).mappings().fetchall()

    if not rows:
        return []

    rows = [dict(r) for r in rows]
    narratives: list[dict] = []

    def top_items(field: str, limit: int = 5) -> list[str]:
        counts: dict[str, int] = {}
        for r in rows:
            val = r.get(field)
            if val:
                counts[val] = counts.get(val, 0) + 1
        return [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]]

    dev_issues = NARRATIVE_ISSUE_MAP["development_positive"]
    dev_rows   = [r for r in rows if r.get("issue") in dev_issues]
    dev_pol, dev_count = _weighted_sentiment(dev_rows)
    if dev_count >= 3 and dev_pol >= 0.2:
        narratives.append(_build_narrative(
            booth_id, "development_positive", computed_at, window_days,
            strength=round(dev_pol, 3),
            description=f"Positive development signal across {dev_count} events (roads/water/electricity).",
            top_issues=[r["issue"] for r in dev_rows if r.get("issue")],
            top_entities=[r["entity"] for r in dev_rows if r.get("entity")],
            evidence_count=dev_count,
            confidence=min(1.0, dev_count / 20),
        ))

    ruling_rows = [r for r in rows if (r.get("entity") or "").upper() == RULING_PARTY]
    anti_pol, anti_count = _weighted_sentiment(ruling_rows)
    if anti_count >= 3 and anti_pol <= -0.2:
        narratives.append(_build_narrative(
            booth_id, "anti_incumbency", computed_at, window_days,
            strength=round(abs(anti_pol), 3),
            description=f"Anti-incumbency signal detected — {RULING_PARTY} scoring negative across {anti_count} events.",
            top_issues=top_items("issue"),
            top_entities=[RULING_PARTY],
            evidence_count=anti_count,
            confidence=min(1.0, anti_count / 20),
        ))

    corr_rows = [r for r in rows if r.get("issue") in NARRATIVE_ISSUE_MAP["corruption_narrative"]]
    _, corr_count = _weighted_sentiment(corr_rows)
    if corr_count >= 2:
        narratives.append(_build_narrative(
            booth_id, "corruption_narrative", computed_at, window_days,
            strength=round(corr_count / max(len(rows), 1), 3),
            description=f"Corruption/leakage narrative in {corr_count} events.",
            top_issues=["corruption"],
            top_entities=[r["entity"] for r in corr_rows if r.get("entity")],
            evidence_count=corr_count,
            confidence=min(1.0, corr_count / 10),
        ))

    price_rows = [r for r in rows if r.get("issue") in NARRATIVE_ISSUE_MAP["price_rise_narrative"]]
    _, price_count = _weighted_sentiment(price_rows)
    if price_count >= 2:
        narratives.append(_build_narrative(
            booth_id, "price_rise_narrative", computed_at, window_days,
            strength=round(price_count / max(len(rows), 1), 3),
            description=f"Price rise / inflation narrative in {price_count} events.",
            top_issues=["prices", "inflation"],
            top_entities=[],
            evidence_count=price_count,
            confidence=min(1.0, price_count / 10),
        ))

    ws_rows = [r for r in rows if r.get("issue") in NARRATIVE_ISSUE_MAP["women_safety_narrative"]]
    _, ws_count = _weighted_sentiment(ws_rows)
    if ws_count >= 2:
        narratives.append(_build_narrative(
            booth_id, "women_safety_narrative", computed_at, window_days,
            strength=round(ws_count / max(len(rows), 1), 3),
            description=f"Women safety / crime narrative in {ws_count} events.",
            top_issues=["women_safety"],
            top_entities=[r["entity"] for r in ws_rows if r.get("entity")],
            evidence_count=ws_count,
            confidence=min(1.0, ws_count / 10),
        ))

    emp_rows = [r for r in rows if r.get("issue") in NARRATIVE_ISSUE_MAP["employment_crisis"]]
    _, emp_count = _weighted_sentiment(emp_rows)
    if emp_count >= 2:
        narratives.append(_build_narrative(
            booth_id, "employment_crisis", computed_at, window_days,
            strength=round(emp_count / max(len(rows), 1), 3),
            description=f"Employment crisis narrative in {emp_count} events.",
            top_issues=["jobs", "unemployment"],
            top_entities=[],
            evidence_count=emp_count,
            confidence=min(1.0, emp_count / 10),
        ))

    sc_rows = [r for r in rows if r.get("issue") in NARRATIVE_ISSUE_MAP["scheme_success"]]
    sc_pol, sc_count = _weighted_sentiment(sc_rows)
    if sc_count >= 2 and sc_pol >= 0.2:
        narratives.append(_build_narrative(
            booth_id, "scheme_success", computed_at, window_days,
            strength=round(sc_pol, 3),
            description=f"Positive scheme awareness / success signal in {sc_count} events.",
            top_issues=[r["issue"] for r in sc_rows if r.get("issue")],
            top_entities=[],
            evidence_count=sc_count,
            confidence=min(1.0, sc_count / 10),
        ))

    with engine.connect() as conn:
        mixed = conn.execute(text("SELECT COUNT(*) AS n FROM contradiction_flags WHERE booth_id = :booth_id AND computed_at <= :now AND flag_label IN ('MIXED_SIGNALS', 'SWING_INDICATOR')"), {"booth_id": booth_id, "now": computed_at}).scalar()

    if (mixed or 0) >= 2:
        narratives.append(_build_narrative(
            booth_id, "swing_possible", computed_at, window_days,
            strength=round(min(1.0, mixed / 5), 3),
            description=f"Contradictory signals across sources ({mixed} mixed-signal pairs) — voter intent uncertain.",
            top_issues=top_items("issue"),
            top_entities=top_items("entity"),
            evidence_count=mixed,
            confidence=0.5,
        ))

    return sorted([n for n in narratives if n["strength"] >= MIN_STRENGTH], key=lambda x: -x["strength"]) 


def _build_narrative(
    booth_id: str,
    narrative_type: str,
    computed_at: datetime,
    window_days: int,
    strength: float,
    description: str,
    top_issues: list,
    top_entities: list,
    evidence_count: int,
    confidence: float,
) -> dict:
    def dedup(lst: list, limit: int = 5) -> list:
        seen: dict = {}
        for x in lst:
            if x and x not in seen:
                seen[x] = True
        return list(seen.keys())[:limit]

    return {
        "booth_id":       booth_id,
        "computed_at":    computed_at,
        "window_days":    window_days,
        "narrative_type": narrative_type,
        "strength":       strength,
        "description":    description,
        "top_issues":     dedup(top_issues),
        "top_entities":   dedup(top_entities),
        "evidence_count": evidence_count,
        "confidence":     round(confidence, 3),
    }


def upsert_narrative_rows(engine: Engine, rows: list[dict]) -> None:
    if not rows:
        return
    with engine.begin() as conn:
        for row in rows:
            conn.execute(text("""
                INSERT INTO booth_narratives (
                    booth_id, computed_at, window_days,
                    narrative_type, strength, description,
                    top_issues, top_entities, evidence_count, confidence
                ) VALUES (
                    :booth_id, :computed_at, :window_days,
                    :narrative_type, :strength, :description,
                    :top_issues, :top_entities, :evidence_count, :confidence
                )
                ON CONFLICT (booth_id, narrative_type, computed_at) DO UPDATE SET
                    strength       = EXCLUDED.strength,
                    description    = EXCLUDED.description,
                    top_issues     = EXCLUDED.top_issues,
                    top_entities   = EXCLUDED.top_entities,
                    evidence_count = EXCLUDED.evidence_count,
                    confidence     = EXCLUDED.confidence
            """), {**row, "top_issues": json.dumps(row["top_issues"]), "top_entities": json.dumps(row["top_entities"])})


def update_booth_metrics_narrative(engine: Engine, booth_id: str, computed_at: datetime) -> None:
    with engine.begin() as conn:
        result = conn.execute(text("""
                SELECT narrative_type, strength
                FROM booth_narratives
                WHERE booth_id = :booth_id
                  AND computed_at = :computed_at
                ORDER BY strength DESC
                LIMIT 1
            """), {"booth_id": booth_id, "computed_at": computed_at}).fetchone()

        if result:
            conn.execute(text("""
                    UPDATE booth_metrics
                    SET dominant_narrative  = :narrative_type,
                        narrative_strength  = :strength
                    WHERE booth_id = :booth_id
                """), {"booth_id": booth_id, "narrative_type": result[0], "strength": result[1]})


def run_all_booths(engine: Engine, window_days: int = 7) -> int:
    with engine.connect() as conn:
        booth_ids = [r[0] for r in conn.execute(text("SELECT DISTINCT mapped_booth_id FROM pulse_events WHERE mapped_booth_id IS NOT NULL")).fetchall()]

    computed_at = datetime.now(timezone.utc)
    for booth_id in booth_ids:
        narratives = detect_narratives_for_booth(engine, booth_id, window_days, computed_at)
        upsert_narrative_rows(engine, narratives)
        update_booth_metrics_narrative(engine, booth_id, computed_at)

    return len(booth_ids)
