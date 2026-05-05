"""Historical vote-share trend analysis from booth_results."""
from __future__ import annotations
import os, logging
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger(__name__)


def get_vote_share_trend(booth_id: str, engine: sa.Engine) -> list[dict]:
    """Returns [{election_year, party, vote_share, winner_flag}] sorted by year."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT election_year, party, vote_share, winner_flag
            FROM booth_results
            WHERE booth_id = :bid
            ORDER BY election_year ASC, vote_share DESC
        """), {"bid": booth_id}).mappings().fetchall()
    return [dict(r) for r in rows]


def get_bjp_trend_summary(booth_id: str, engine: sa.Engine) -> dict:
    """
    Returns a human-readable summary:
      {years: [2017,2022], shares: [55.2,48.1], won: [True,True],
       trend: 'declining', summary: 'BJP won last 2 elections. Share: 55% → 48% (declining)'}
    """
    rows = get_vote_share_trend(booth_id, engine)
    bjp_rows = [r for r in rows if r["party"] in ("BJP", "भाजपा")]

    if not bjp_rows:
        return {"summary": "No historical BJP data available", "years": [], "shares": []}

    years  = [r["election_year"] for r in bjp_rows]
    shares = [round(r["vote_share"] or 0, 1) for r in bjp_rows]
    wins   = [r["winner_flag"] for r in bjp_rows]

    # trend
    if len(shares) >= 2:
        delta = shares[-1] - shares[-2]
        trend = "declining" if delta < -2 else "rising" if delta > 2 else "stable"
    else:
        trend = "unknown"

    wins_count = sum(1 for w in wins if w)
    won_text = f"BJP won last {wins_count} election{'s' if wins_count > 1 else ''}"
    share_text = " → ".join(f"{s}%" for s in shares)
    summary = f"{won_text}. Vote share: {share_text} ({trend})"

    return {
        "years": years, "shares": shares, "wins": wins,
        "trend": trend, "wins_count": wins_count, "summary": summary,
    }
