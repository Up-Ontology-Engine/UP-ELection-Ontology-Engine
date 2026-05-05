"""
Cypher query library — all graph queries used by API, analytics, and dashboard.

All functions accept a neo4j.Session and return plain Python dicts.
Query names match the API endpoint they serve where applicable.
"""

from __future__ import annotations

from typing import Any, Optional
from neo4j import Session


# ── Structure ─────────────────────────────────────────────────────────────────

def get_booths_for_ac(session: Session, ac_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (a:AssemblyConstituency {ac_id: $ac_id})-[:HAS_BOOTH]->(b:Booth)
        RETURN
            b.booth_id   AS booth_id,
            b.booth_name AS booth_name,
            b.ward       AS ward,
            b.total_voters AS total_voters
        ORDER BY b.booth_name
        """,
        {"ac_id": ac_id},
    )
    return [dict(r) for r in result]


def get_booth_base(session: Session, booth_id: str) -> Optional[dict]:
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})
        OPTIONAL MATCH (b)<-[:HAS_BOOTH]-(a:AssemblyConstituency)
        RETURN
            b.booth_id     AS booth_id,
            b.booth_name   AS booth_name,
            b.ward         AS ward,
            b.total_voters AS total_voters,
            a.ac_id        AS ac_id,
            a.name         AS ac_name
        """,
        {"booth_id": booth_id},
    )
    record = result.single()
    return dict(record) if record else None


# ── Pulse / Sentiment ─────────────────────────────────────────────────────────

def get_booth_pulse(
    session: Session,
    booth_id: str,
    days: int = 7,
) -> dict:
    """
    Returns BJP pulse, opposition pulse, digital lean, and top entities.
    """
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})<-[:AT_BOOTH]-(pe:PulseEvent)
        WHERE pe.created_at >= datetime() - duration({days: $days})
        WITH
            pe,
            CASE WHEN pe.entity IN ['BJP', 'भाजपा'] THEN 'bjp'
                 WHEN pe.entity IN ['SP', 'Samajwadi Party', 'BSP', 'Congress', 'INC']
                      THEN 'opp'
                 ELSE 'other' END AS camp
        WITH
            camp,
            AVG(pe.final_polarity * pe.nlp_confidence) AS weighted_avg,
            COUNT(pe) AS events
        RETURN camp, weighted_avg, events
        """,
        {"booth_id": booth_id, "days": days},
    )

    bjp_score = opp_score = 0.0
    bjp_events = opp_events = 0
    for r in result:
        if r["camp"] == "bjp":
            bjp_score  = r["weighted_avg"] or 0
            bjp_events = r["events"]
        elif r["camp"] == "opp":
            opp_score  = r["weighted_avg"] or 0
            opp_events = r["events"]

    return {
        "bjp_pulse":    round(bjp_score, 3),
        "opp_pulse":    round(opp_score, 3),
        "digital_lean": round(bjp_score - opp_score, 3),
        "bjp_events":   bjp_events,
        "opp_events":   opp_events,
        "total_events": bjp_events + opp_events,
    }


def get_booth_issues(session: Session, booth_id: str, days: int = 7, limit: int = 8) -> list[dict]:
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})<-[:AT_BOOTH]-(pe:PulseEvent)
        WHERE pe.created_at >= datetime() - duration({days: $days})
          AND pe.issue IS NOT NULL
        WITH pe.issue AS issue, COUNT(pe) AS cnt, AVG(pe.final_polarity) AS avg_pol
        ORDER BY cnt DESC
        LIMIT $limit
        RETURN issue, cnt AS event_count, avg_pol AS avg_polarity
        """,
        {"booth_id": booth_id, "days": days, "limit": limit},
    )
    return [dict(r) for r in result]


def get_booth_recent_comments(
    session: Session,
    booth_id: str,
    limit: int = 20,
    source_type: Optional[str] = None,
) -> list[dict]:
    filters = "pe.created_at IS NOT NULL"
    if source_type:
        filters += " AND pe.source_type = $source_type"

    result = session.run(
        f"""
        MATCH (b:Booth {{booth_id: $booth_id}})<-[:AT_BOOTH]-(pe:PulseEvent)
        WHERE {filters}
        RETURN
            pe.event_id        AS event_id,
            pe.original_text   AS text,
            pe.entity          AS entity,
            pe.issue           AS issue,
            pe.final_polarity  AS polarity,
            pe.source_type     AS source_type,
            pe.language        AS language,
            pe.created_at      AS created_at
        ORDER BY pe.created_at DESC
        LIMIT $limit
        """,
        {"booth_id": booth_id, "limit": limit, "source_type": source_type},
    )
    return [dict(r) for r in result]


# ── Historical ────────────────────────────────────────────────────────────────

def get_booth_history(session: Session, booth_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})-[:HAD_RESULT]->(r:BoothResult)
        RETURN
            r.election_year AS year,
            r.winning_party AS winning_party,
            r.bjp_votes     AS bjp_votes,
            r.total_votes   AS total_votes,
            r.turnout_pct   AS turnout_pct
        ORDER BY r.election_year DESC
        """,
        {"booth_id": booth_id},
    )
    rows = [dict(r) for r in result]
    for row in rows:
        if row.get("bjp_votes") and row.get("total_votes"):
            row["bjp_share"] = round(row["bjp_votes"] / row["total_votes"] * 100, 1)
    return rows


# ── Candidates ────────────────────────────────────────────────────────────────

def get_ac_candidates(session: Session, ac_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (a:AssemblyConstituency {ac_id: $ac_id})<-[:CONTESTED_IN]-(c:Candidate)
        OPTIONAL MATCH (c)-[:REPRESENTS]->(p:Party)
        RETURN
            c.candidate_id  AS candidate_id,
            c.name          AS name,
            c.party         AS party,
            c.age           AS age,
            c.criminal_cases AS criminal_cases,
            c.total_assets  AS total_assets,
            p.name          AS party_name
        ORDER BY c.party
        """,
        {"ac_id": ac_id},
    )
    return [dict(r) for r in result]


def get_candidate_issue_sentiment(
    session: Session,
    candidate_id: str,
    days: int = 7,
) -> list[dict]:
    result = session.run(
        """
        MATCH (c:Candidate {candidate_id: $candidate_id})
        MATCH (pe:PulseEvent {entity: c.name})
        WHERE pe.created_at >= datetime() - duration({days: $days})
          AND pe.issue IS NOT NULL
        WITH pe.issue AS issue, AVG(pe.final_polarity) AS avg_pol, COUNT(pe) AS cnt
        ORDER BY cnt DESC
        RETURN issue, avg_pol AS avg_polarity, cnt AS event_count
        """,
        {"candidate_id": candidate_id, "days": days},
    )
    return [dict(r) for r in result]


# ── Intelligence layer ────────────────────────────────────────────────────────

def get_booth_quality(session: Session, booth_id: str) -> Optional[dict]:
    """Most recent DataQuality node for this booth."""
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})-[:HAS_QUALITY]->(dq:DataQuality)
        RETURN
            dq.overall_quality_score AS overall_quality_score,
            dq.quality_label         AS quality_label,
            dq.quality_reasons       AS quality_reasons,
            dq.total_events          AS total_events,
            dq.unique_sources        AS unique_sources,
            dq.avg_geo_confidence    AS avg_geo_confidence,
            dq.avg_nlp_confidence    AS avg_nlp_confidence,
            dq.source_diversity      AS source_diversity,
            dq.computed_at           AS computed_at
        ORDER BY dq.computed_at DESC
        LIMIT 1
        """,
        {"booth_id": booth_id},
    )
    record = result.single()
    return dict(record) if record else None


def get_booth_narratives(session: Session, booth_id: str, limit: int = 5) -> list[dict]:
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})-[:HAS_NARRATIVE]->(n:Narrative)
        RETURN
            n.narrative_type AS narrative_type,
            n.strength       AS strength,
            n.description    AS description,
            n.top_issues     AS top_issues,
            n.top_entities   AS top_entities,
            n.evidence_count AS evidence_count,
            n.confidence     AS confidence,
            n.computed_at    AS computed_at
        ORDER BY n.computed_at DESC, n.strength DESC
        LIMIT $limit
        """,
        {"booth_id": booth_id, "limit": limit},
    )
    return [dict(r) for r in result]


def get_booth_contradictions(session: Session, booth_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (b:Booth {booth_id: $booth_id})-[:HAS_CONTRADICTION]->(cf:ContradictionFlag)
        OPTIONAL MATCH (cf)-[:ABOUT_ENTITY]->(e)
        RETURN
            cf.entity            AS entity,
            cf.issue             AS issue,
            cf.source_a          AS source_a,
            cf.source_b          AS source_b,
            cf.polarity_a        AS polarity_a,
            cf.polarity_b        AS polarity_b,
            cf.delta             AS delta,
            cf.consistency_score AS consistency_score,
            cf.flag_label        AS flag_label,
            cf.computed_at       AS computed_at,
            labels(e)            AS entity_labels
        ORDER BY cf.computed_at DESC, cf.delta DESC
        """,
        {"booth_id": booth_id},
    )
    return [dict(r) for r in result]


def get_booth_scheme_gaps(
    session: Session,
    booth_id: str,
    priority: Optional[str] = None,
) -> list[dict]:
    filter_clause = "WHERE sg.booth_id = $booth_id"
    if priority:
        filter_clause += " AND sg.priority = $priority"

    result = session.run(
        f"""
        MATCH (b:Booth {{booth_id: $booth_id}})-[:HAS_SCHEME_GAP]->(sg:SchemeGap)
        {filter_clause}
        OPTIONAL MATCH (sg)-[:FOR_SCHEME]->(sc:Scheme)
        OPTIONAL MATCH (sg)-[:TAGGED_ISSUE]->(i:Issue)
        RETURN
            sg.scheme_name        AS scheme_name,
            sg.gap_type           AS gap_type,
            sg.gap_label          AS gap_label,
            sg.priority           AS priority,
            sg.beneficiary_count  AS beneficiary_count,
            sg.completion_status  AS completion_status,
            sg.avg_sentiment      AS avg_sentiment,
            sg.negative_events    AS negative_events,
            sg.total_events       AS total_events,
            sc.name               AS scheme_node_name,
            i.code                AS issue_code,
            sg.computed_at        AS computed_at
        ORDER BY sg.computed_at DESC,
                 CASE sg.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END
        """,
        {"booth_id": booth_id, "priority": priority},
    )
    return [dict(r) for r in result]


# ── AC overview ───────────────────────────────────────────────────────────────

def get_ac_booth_summary_table(session: Session, ac_id: str) -> list[dict]:
    """
    Returns one row per booth in the AC with aggregated pulse + quality info.
    Powers the AC overview map / table.
    """
    result = session.run(
        """
        MATCH (a:AssemblyConstituency {ac_id: $ac_id})-[:HAS_BOOTH]->(b:Booth)
        OPTIONAL MATCH (b)-[:HAS_QUALITY]->(dq:DataQuality)
        WITH b, dq ORDER BY dq.computed_at DESC
        WITH b, HEAD(COLLECT(dq)) AS latest_dq
        OPTIONAL MATCH (b)<-[:AT_BOOTH]-(pe:PulseEvent)
        WHERE pe.created_at >= datetime() - duration({days: 7})
        WITH b, latest_dq,
             AVG(CASE WHEN pe.entity IN ['BJP','भाजपा'] THEN pe.final_polarity END) AS bjp_avg,
             AVG(CASE WHEN pe.entity IN ['SP','BSP','Congress'] THEN pe.final_polarity END) AS opp_avg,
             COUNT(pe) AS total_events
        RETURN
            b.booth_id            AS booth_id,
            b.booth_name          AS booth_name,
            b.total_voters        AS total_voters,
            bjp_avg               AS bjp_pulse,
            opp_avg               AS opp_pulse,
            bjp_avg - opp_avg     AS digital_lean,
            total_events          AS event_count,
            latest_dq.quality_label AS quality_label,
            latest_dq.overall_quality_score AS quality_score
        ORDER BY b.booth_name
        """,
        {"ac_id": ac_id},
    )
    return [dict(r) for r in result]
