"""
Analysis and indexing module — Stage 8 of the implementation plan.

Reads classified JSON files from Youtube/videos/processed/ and
newspapers/processed/, generates sentiment distribution stats,
and writes summary JSONs to the analysis/ directories.

Usage:
    python -m ingestion.analyzer
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
YT_PROC_DIR      = _REPO / "data" / "Digital_Dataset" / "Youtube" / "videos" / "processed"
YT_ANALYSIS_DIR  = _REPO / "data" / "Digital_Dataset" / "Youtube" / "analysis"
NEWS_PROC_DIR    = _REPO / "data" / "Digital_Dataset" / "newspapers" / "processed"
GLOBAL_ANAL_DIR  = _REPO / "data" / "Digital_Dataset" / "analysis"

for _d in (YT_ANALYSIS_DIR, GLOBAL_ANAL_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _load_classified(directory: Path) -> list[dict]:
    records: list[dict] = []
    for f in sorted(directory.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            records.extend(data.get("classified_articles")
                           or data.get("videos")
                           or [])
        except Exception as exc:
            logger.warning(f"Could not read {f}: {exc}")
    return records


def _distribution_stats(records: list[dict]) -> dict:
    labels   = [r.get("classification", "unknown") for r in records]
    counts   = Counter(labels)
    total    = len(records)
    divisor  = max(total, 1)
    by_month: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        date_str = (r.get("upload_date") or r.get("published_at") or "")[:7]  # YYYY-MM
        if date_str:
            by_month[date_str][r.get("classification", "unknown")] += 1

    return {
        "total":             total,
        "pro_bjp_count":     counts.get("pro-BJP",  0),
        "anti_bjp_count":    counts.get("anti-BJP", 0),
        "neutral_count":     counts.get("neutral",  0),
        "pro_bjp_pct":       round(100 * counts.get("pro-BJP",  0) / divisor, 1),
        "anti_bjp_pct":      round(100 * counts.get("anti-BJP", 0) / divisor, 1),
        "neutral_pct":       round(100 * counts.get("neutral",  0) / divisor, 1),
        "by_month":          {k: dict(v) for k, v in sorted(by_month.items())},
    }


def run_analysis() -> None:
    now = datetime.now(timezone.utc).isoformat()

    # YouTube video analysis
    yt_records = _load_classified(YT_PROC_DIR)
    yt_stats   = _distribution_stats(yt_records)
    yt_out     = YT_ANALYSIS_DIR / "sentiment_distribution.json"
    yt_out.write_text(json.dumps({"generated_at": now, **yt_stats},
                                  ensure_ascii=False, indent=2),
                      encoding="utf-8")
    logger.info(f"YouTube analysis → {yt_out}")

    # News analysis
    news_records = _load_classified(NEWS_PROC_DIR)
    news_stats   = _distribution_stats(news_records)
    news_out     = GLOBAL_ANAL_DIR / "news_sentiment_summary.json"
    news_out.write_text(json.dumps({"generated_at": now, **news_stats},
                                    ensure_ascii=False, indent=2),
                        encoding="utf-8")
    logger.info(f"News analysis → {news_out}")

    # Combined
    combined = {
        "generated_at":    now,
        "youtube_videos":  yt_stats,
        "news_articles":   news_stats,
    }
    comb_out = GLOBAL_ANAL_DIR / "combined_analysis.json"
    comb_out.write_text(json.dumps(combined, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    logger.info(f"Combined analysis → {comb_out}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_analysis()
