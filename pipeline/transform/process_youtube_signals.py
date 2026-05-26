"""
Rule-based NLP pipeline: YouTube video titles → pulse_events → booth_metrics

Works without any API keys or LLM. Extracts entity / issue / polarity from
Hindi+English video titles using keyword dictionaries, then populates
pulse_events and recomputes booth_metrics.

Run: python -m etl.process_youtube_signals
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Entity keywords ────────────────────────────────────────────────────────────
_ENTITIES: dict[str, tuple[str, list[str]]] = {
    # (entity_type, [keyword variants])
    "BJP":              ("party",     ["bjp", "भाजपा", "भारतीय जनता", "yogi", "योगी", "मोदी", "modi", "भाजप"]),
    "SP":               ("party",     ["samajwadi", "सपा", "समाजवादी", "akhilesh", "अखिलेश", "sp "]),
    "BSP":              ("party",     ["bahujan", "बसपा", "mayawati", "मायावती", "bsp"]),
    "INC":              ("party",     ["congress", "कांग्रेस", "inc ", "rahul", "राहुल"]),
    "Yogi Adityanath":  ("candidate", ["yogi", "योगी", "adityanath", "आदित्यनाथ", "cm yogi", "मुख्यमंत्री"]),
    "Akhilesh Yadav":   ("candidate", ["akhilesh", "अखिलेश", "akhilesh yadav"]),
    "Mayawati":         ("candidate", ["mayawati", "मायावती", "behan ji", "बहनजी"]),
}

# ── Issue keywords ─────────────────────────────────────────────────────────────
_ISSUES: dict[str, list[str]] = {
    "water":        ["water", "पानी", "jal", "जल", "drinking water", "pipeline", "नल", "नल जल", "jjm"],
    "roads":        ["road", "सड़क", "highway", "अधोसंरचना", "pothole", "bridge", "पुल", "sadak"],
    "electricity":  ["bijli", "बिजली", "electricity", "power cut", "light", "generator"],
    "jobs":         ["job", "rojgar", "रोजगार", "unemployment", "berozgari", "बेरोजगारी", "employment"],
    "farmer":       ["kisan", "किसान", "farmer", "sugarcane", "crop", "fasal", "msp"],
    "health":       ["hospital", "health", "स्वास्थ्य", "aiims", "doctor", "medicine", "covid"],
    "education":    ["school", "education", "शिक्षा", "teacher", "result", "exam"],
    "corruption":   ["corruption", "भ्रष्टाचार", "scam", "घोटाला", "bribe", "fraud"],
    "price_rise":   ["mehangai", "महंगाई", "inflation", "price rise", "costly", "petrol", "gas"],
    "housing":      ["pmay", "awas", "आवास", "housing", "ghar", "घर"],
    "women_safety": ["women", "महिला", "safety", "suraksha", "crime against women"],
    "law_order":    ["law and order", "crime", "police", "अपराध", "gangster"],
}

# ── Positive / negative signal words ──────────────────────────────────────────
_POSITIVE = [
    "victory", "win", "जीत", "development", "विकास", "progress", "achievement",
    "success", "जीता", "rally", "support", "समर्थन", "popular", "लोकप्रिय",
    "good", "positive", "celebration", "उत्सव", "promise", "वादा", "deliver",
    "inauguration", "उद्घाटन", "launch", "शुभारंभ",
]
_NEGATIVE = [
    "protest", "विरोध", "anger", "गुस्सा", "problem", "समस्या", "crisis",
    "failure", "विफलता", "corruption", "भ्रष्टाचार", "loss", "नुकसान",
    "disappointed", "निराश", "issue", "मुद्दा", "fight", "demand", "मांग",
    "opposition", "oppose", "scam", "घोटाला", "strike", "हड़ताल",
]

# Default: map all Gorakhpur videos to GKP_322 (Urban) at AC level
_DEFAULT_AC   = "GKP_322"
_DEFAULT_GEO  = "ac"


def _normalise(text: str) -> str:
    return text.lower().strip()


def _detect_entity(title: str) -> tuple[Optional[str], Optional[str]]:
    t = _normalise(title)
    for entity, (etype, keywords) in _ENTITIES.items():
        for kw in keywords:
            if kw in t:
                return entity, etype
    return None, None


def _detect_issue(title: str) -> Optional[str]:
    t = _normalise(title)
    for issue, keywords in _ISSUES.items():
        for kw in keywords:
            if kw in t:
                return issue
    return None


def _detect_polarity(title: str) -> tuple[int, float]:
    """Returns (polarity, confidence) where polarity ∈ {-1, 0, 1}."""
    t = _normalise(title)
    pos = sum(1 for w in _POSITIVE if w in t)
    neg = sum(1 for w in _NEGATIVE if w in t)
    if pos > neg:
        conf = min(0.4 + pos * 0.1, 0.8)
        return 1, conf
    if neg > pos:
        conf = min(0.4 + neg * 0.1, 0.8)
        return -1, conf
    return 0, 0.35


def _source_id(video_id: str, title: str) -> str:
    return hashlib.sha256(f"yt:{video_id}:{title}".encode()).hexdigest()[:32]


def run() -> int:
    engine = sa.create_engine(
        os.environ.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/gorakhpur_db")
    )

    with engine.connect() as conn:
        # Read all YouTube videos
        rows = conn.execute(text("""
            SELECT v.video_id, v.title, v.description, v.view_count,
                   v.query_source, v.created_at
            FROM yt_videos v
            WHERE v.title IS NOT NULL AND v.title != ''
            ORDER BY v.view_count DESC NULLS LAST
        """)).mappings().fetchall()

    logger.info("Processing %d YouTube video titles for signals", len(rows))

    inserted = 0
    skipped  = 0

    with engine.connect() as conn:
        for r in rows:
            video_id    = r["video_id"]
            title       = r["title"] or ""
            description = (r["description"] or "")[:200]
            full_text   = f"{title} {description}"
            views       = int(r["view_count"] or 0)

            entity, entity_type = _detect_entity(full_text)
            issue               = _detect_issue(full_text)
            polarity, conf      = _detect_polarity(full_text)

            # Boost confidence for high-view videos
            if views > 50_000:
                conf = min(conf + 0.1, 0.9)
            elif views > 10_000:
                conf = min(conf + 0.05, 0.85)

            # Skip if we can't extract any signal
            if entity is None and issue is None and polarity == 0:
                skipped += 1
                continue

            # Source weight: YouTube = 0.6 (standard)
            source_weight = 0.6

            sid = _source_id(video_id, title)

            try:
                conn.execute(text("""
                    INSERT INTO pulse_events (
                        source_type, source_id, text_raw,
                        language_detected, extraction_method,
                        entity, entity_type, issue,
                        final_polarity, final_issue, final_confidence,
                        polarity, confidence,
                        mapped_ac_id, geo_level,
                        source_weight, created_at
                    ) VALUES (
                        'youtube', :sid, :text,
                        'hi', 'rule_based',
                        :entity, :etype, :issue,
                        :polarity, :issue, :conf,
                        :polarity, :conf,
                        :ac_id, 'ac',
                        :sw, NOW()
                    )
                    ON CONFLICT DO NOTHING
                """), {
                    "sid":     sid,
                    "text":    title[:500],
                    "entity":  entity,
                    "etype":   entity_type,
                    "issue":   issue,
                    "polarity":polarity,
                    "conf":    conf,
                    "ac_id":   _DEFAULT_AC,
                    "sw":      source_weight,
                })
                inserted += 1
            except Exception as e:
                logger.debug("Skip %s: %s", video_id, e)
                conn.rollback()
                continue

        conn.commit()

    logger.info("Inserted %d pulse_events, skipped %d (no signal)", inserted, skipped)

    # Now compute booth_metrics for the AC
    _compute_ac_metrics(engine, _DEFAULT_AC)

    return inserted


def _compute_ac_metrics(engine: sa.Engine, ac_id: str) -> None:
    """Compute booth_metrics for the AC from pulse_events."""
    logger.info("Computing AC-level metrics for %s …", ac_id)

    with engine.connect() as conn:
        # Entity-level pulse scores
        rows = conn.execute(text("""
            SELECT entity,
                   ROUND((SUM(final_polarity * final_confidence * source_weight) /
                          NULLIF(SUM(final_confidence * source_weight), 0))::numeric, 3) AS pulse_score,
                   COUNT(*) AS event_count
            FROM pulse_events
            WHERE mapped_ac_id = :ac_id
              AND entity IS NOT NULL
            GROUP BY entity
        """), {"ac_id": ac_id}).mappings().fetchall()

        entity_scores = {r["entity"]: (float(r["pulse_score"] or 0), int(r["event_count"]))
                         for r in rows}

        bjp_score = entity_scores.get("BJP", (0, 0))[0]
        sp_score  = entity_scores.get("SP", (0, 0))[0]
        bsp_score = entity_scores.get("BSP", (0, 0))[0]
        opp_score = max(sp_score, bsp_score)
        lean      = bjp_score - opp_score

        # Issue breakdown
        issue_rows = conn.execute(text("""
            SELECT final_issue AS issue, COUNT(*) AS cnt
            FROM pulse_events
            WHERE mapped_ac_id = :ac_id AND final_issue IS NOT NULL
            GROUP BY final_issue ORDER BY cnt DESC
        """), {"ac_id": ac_id}).mappings().fetchall()

        issue_breakdown = {r["issue"]: int(r["cnt"]) for r in issue_rows}
        top_issue = issue_rows[0]["issue"] if issue_rows else None
        total_events = sum(issue_breakdown.values())

        lean_label = (
            "Lean BJP"        if lean > 0.15 else
            "Slightly BJP"    if lean > 0.05 else
            "Lean Opposition" if lean < -0.15 else
            "Slightly Opp"    if lean < -0.05 else
            "Contested"
        )

        confidence = min(total_events / 200, 1.0)
        conf_label = "HIGH" if confidence > 0.7 else "MEDIUM" if confidence > 0.3 else "LOW"

        now = datetime.now(timezone.utc)

        # Update ALL booths in the AC with the AC-level aggregated signal
        # (individual booth mapping requires comments scraped per booth)
        conn.execute(text("""
            INSERT INTO booth_metrics
                (booth_id, window_start, window_end,
                 bjp_pulse_score, opp_pulse_score, digital_lean, digital_lean_label,
                 top_issue, issue_breakdown, event_count,
                 data_confidence, confidence_label, last_computed_at)
            SELECT
                booth_id,
                :now - INTERVAL '7 days',
                :now,
                :bjp, :opp, :lean, :lean_label,
                :top_issue, :breakdown,
                :events, :conf_val, :conf_label, :now
            FROM booth_master
            WHERE ac_id = :ac_id AND booth_id NOT LIKE '%_TOTAL'
            ON CONFLICT (booth_id, window_start) DO UPDATE SET
                bjp_pulse_score   = EXCLUDED.bjp_pulse_score,
                opp_pulse_score   = EXCLUDED.opp_pulse_score,
                digital_lean      = EXCLUDED.digital_lean,
                digital_lean_label= EXCLUDED.digital_lean_label,
                top_issue         = EXCLUDED.top_issue,
                issue_breakdown   = EXCLUDED.issue_breakdown,
                event_count       = EXCLUDED.event_count,
                data_confidence   = EXCLUDED.data_confidence,
                confidence_label  = EXCLUDED.confidence_label,
                last_computed_at  = EXCLUDED.last_computed_at
        """), {
            "ac_id":      ac_id,
            "bjp":        bjp_score,
            "opp":        opp_score,
            "lean":       lean,
            "lean_label": lean_label,
            "top_issue":  top_issue,
            "breakdown":  json.dumps(issue_breakdown),
            "events":     total_events,
            "conf_val":   confidence,
            "conf_label": conf_label,
            "now":        now,
        })
        conn.commit()

    logger.info(
        "AC %s — BJP: %+.3f | Opp: %+.3f | Lean: %s | Events: %d | Top issue: %s",
        ac_id, bjp_score, opp_score, lean_label, total_events, top_issue
    )

    # ── AC-level strategic summary ─────────────────────────────────────────────
    _print_strategic_summary(entity_scores, issue_breakdown, lean_label, lean, ac_id)


def _print_strategic_summary(
    entity_scores: dict,
    issue_breakdown: dict,
    lean_label: str,
    lean: float,
    ac_id: str,
) -> None:
    sep = "=" * 60
    bar_char = "#"

    lines = [
        "",
        sep,
        f"  STRATEGIC SIGNAL SUMMARY -- {ac_id}",
        sep,
        f"\n  Digital Lean    : {lean_label} ({lean:+.3f})",
        f"\n  Party Pulse Scores (from {sum(v[1] for v in entity_scores.values())} YouTube signals):",
    ]
    for entity, (score, count) in sorted(entity_scores.items(), key=lambda x: -x[1][1]):
        bar  = bar_char * max(1, int(abs(score) * 20))
        sign = "+" if score >= 0 else ""
        lines.append(f"    {entity:<25} {sign}{score:.3f}  {bar}  ({count} mentions)")

    lines.append("\n  Top Issues (by mention volume):")
    top5 = sorted(issue_breakdown.items(), key=lambda x: -x[1])[:5]
    for issue, cnt in top5:
        bar = bar_char * max(1, int(cnt / max(issue_breakdown.values()) * 20))
        lines.append(f"    {issue:<20} {bar}  {cnt}")

    lines.append("\n  Recommended Actions:")
    if lean_label in ("Lean BJP", "Slightly BJP"):
        lines.append("    [+] BJP ahead on digital. Consolidate base + address top negative issues.")
    elif lean_label in ("Lean Opposition", "Slightly Opp"):
        lines.append("    [!] Opposition gaining. Urgently address voter concerns + visibility.")
    else:
        lines.append("    [~] Contested. Swing vote is critical -- focus on undecided booth pockets.")

    if top5:
        top_issue = top5[0][0].replace("_", " ")
        lines.append(f"    [*] Top campaign priority: {top_issue.upper()} -- dominant in YouTube discourse.")

    if "corruption" in issue_breakdown:
        lines.append(f"    [!] Anti-corruption narrative present ({issue_breakdown['corruption']} mentions) -- address proactively.")
    if "price_rise" in issue_breakdown:
        lines.append(f"    [$] Price rise ({issue_breakdown['price_rise']} mentions) -- economic relief messaging needed.")

    lines.append("\n" + sep + "\n")

    output = "\n".join(lines)
    try:
        print(output)
    except UnicodeEncodeError:
        print(output.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    n = run()
    print(f"Total signals processed: {n}")
