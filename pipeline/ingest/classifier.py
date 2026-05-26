"""
Political sentiment classifier for Gorakhpur content.

Classifies news articles, YouTube videos, and comments into:
  - pro-BJP
  - anti-BJP
  - neutral

Approach (Ensemble, ordered by availability):
  1. Zero-shot via facebook/bart-large-mnli  (if transformers installed)
  2. Keyword + sentiment scoring              (always available)

Each result includes: classification, confidence, pro_bjp_score, anti_bjp_score,
neutral_score, keywords_found, sentiment, entities (basic NER).
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── keyword lexicons ──────────────────────────────────────────────────────────
PRO_BJP_KEYWORDS: list[str] = [
    # Hindi
    "विकास", "योजना", "उन्नति", "प्रगति", "सुरक्षा", "स्थिरता",
    "योगी", "मोदी", "अमित शाह", "भाजपा", "बीजेपी",
    "सड़क", "बिजली", "पानी", "स्वच्छता", "आवास",
    # English
    "development", "growth", "stability", "security", "BJP", "Yogi",
    "Modi", "progress", "scheme", "infrastructure", "initiative",
    "governance", "achievement", "mission", "double engine",
]

ANTI_BJP_KEYWORDS: list[str] = [
    # Hindi
    "भ्रष्टाचार", "बेरोजगारी", "महंगाई", "किसान", "विरोध",
    "घोटाला", "बेकारी", "असफलता", "अराजकता", "अत्याचार",
    "सपा", "समाजवादी", "बसपा", "कांग्रेस",
    # English
    "corruption", "mismanagement", "failure", "protest", "scam",
    "unemployment", "inflation", "injustice", "opposition", "SP",
    "Samajwadi", "BSP", "Congress", "anti-government", "agitation",
]

NEUTRAL_OVERRIDES: list[str] = [
    "मौसम", "weather", "festival", "त्योहार", "cricket", "क्रिकेट",
    "accident", "हादसा", "flood", "बाढ़",
]

POLITICIAN_NAMES: list[str] = [
    "Yogi Adityanath", "योगी आदित्यनाथ",
    "Akhilesh Yadav", "अखिलेश यादव",
    "Narendra Modi", "नरेंद्र मोदी",
    "Amit Shah", "अमित शाह",
    "Mayawati", "मायावती",
    "Priyanka Gandhi", "प्रियंका गांधी",
]

ORGS: list[str] = [
    "BJP", "भाजपा", "बीजेपी",
    "SP", "सपा", "Samajwadi Party", "समाजवादी पार्टी",
    "BSP", "बसपा", "Bahujan Samaj Party",
    "Congress", "कांग्रेस",
]


# ── keyword scorer ────────────────────────────────────────────────────────────
def _keyword_score(text: str) -> tuple[float, float, list[str]]:
    """
    Returns (pro_bjp_raw, anti_bjp_raw, keywords_found).
    Raw scores are counts normalised loosely by text length.
    """
    text_lower = text.lower()
    pro_hits   = [kw for kw in PRO_BJP_KEYWORDS  if kw.lower() in text_lower]
    anti_hits  = [kw for kw in ANTI_BJP_KEYWORDS if kw.lower() in text_lower]
    return float(len(pro_hits)), float(len(anti_hits)), pro_hits + anti_hits


def _basic_sentiment(text: str) -> str:
    """Very lightweight positive/negative/neutral tagger."""
    positive_words = ["अच्छा", "बेहतर", "उत्कृष्ट", "शानदार", "great",
                      "good", "excellent", "positive", "success"]
    negative_words = ["बुरा", "खराब", "विफल", "गलत", "bad", "poor",
                      "failure", "wrong", "negative", "worst"]
    text_lower = text.lower()
    pos = sum(1 for w in positive_words if w in text_lower)
    neg = sum(1 for w in negative_words if w in text_lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _extract_entities(text: str) -> dict[str, list[str]]:
    persons = [n for n in POLITICIAN_NAMES if n.lower() in text.lower()]
    orgs    = [o for o in ORGS            if o.lower() in text.lower()]
    locs    = ["Gorakhpur", "गोरखपुर"] if any(
        w in text for w in ("Gorakhpur", "गोरखपुर")) else []
    return {"persons": list(set(persons)), "organizations": list(set(orgs)),
            "locations": list(set(locs))}


def _keyword_classify(text: str) -> dict[str, Any]:
    pro_raw, anti_raw, kws = _keyword_score(text)
    total = pro_raw + anti_raw + 1e-9
    pro_score  = round(pro_raw  / total, 3)
    anti_score = round(anti_raw / total, 3)
    neutral_sc = round(1.0 - pro_score - anti_score, 3)

    # neutral override check
    text_lower = text.lower()
    if any(w.lower() in text_lower for w in NEUTRAL_OVERRIDES):
        pro_score   = 0.1
        anti_score  = 0.1
        neutral_sc  = 0.8

    if pro_score > anti_score and pro_score > 0.5:
        label, conf = "pro-BJP", round(pro_score, 2)
    elif anti_score > pro_score and anti_score > 0.5:
        label, conf = "anti-BJP", round(anti_score, 2)
    else:
        label, conf = "neutral", round(neutral_sc, 2)

    return {
        "classification":           label,
        "confidence":               conf,
        "pro_bjp_score":            pro_score,
        "anti_bjp_score":           anti_score,
        "neutral_score":            max(neutral_sc, 0.0),
        "keywords_found":           kws,
        "sentiment":                _basic_sentiment(text),
        "entities":                 _extract_entities(text),
        "classification_method":    "keyword",
        "classification_reasoning": (
            f"pro_hits={int(pro_raw)}, anti_hits={int(anti_raw)}"
        ),
    }


# ── zero-shot via transformers (optional) ─────────────────────────────────────
_ZS_PIPELINE: Any = None
_ZS_LOADED    = False


def _load_zs_pipeline() -> Any:
    global _ZS_PIPELINE, _ZS_LOADED
    if _ZS_LOADED:
        return _ZS_PIPELINE
    _ZS_LOADED = True
    try:
        from transformers import pipeline
        logger.info("Loading zero-shot model (facebook/bart-large-mnli)…")
        _ZS_PIPELINE = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )
        logger.info("Zero-shot model loaded.")
    except Exception as exc:
        logger.warning(f"Transformers not available ({exc}); using keyword classifier.")
        _ZS_PIPELINE = None
    return _ZS_PIPELINE


def _zeroshot_classify(text: str) -> dict[str, Any] | None:
    pipe = _load_zs_pipeline()
    if pipe is None:
        return None
    try:
        # truncate to avoid model limits
        snippet = text[:512]
        result = pipe(snippet, candidate_labels=["pro-BJP", "anti-BJP", "neutral"])
        scores = dict(zip(result["labels"], result["scores"]))
        label  = result["labels"][0]
        conf   = round(result["scores"][0], 2)
        return {
            "classification":           label,
            "confidence":               conf,
            "pro_bjp_score":            round(scores.get("pro-BJP",  0.0), 3),
            "anti_bjp_score":           round(scores.get("anti-BJP", 0.0), 3),
            "neutral_score":            round(scores.get("neutral",  0.0), 3),
            "keywords_found":           [],
            "sentiment":                _basic_sentiment(text),
            "entities":                 _extract_entities(text),
            "classification_method":    "zero-shot",
            "classification_reasoning": f"bart-large-mnli: {label}={conf}",
        }
    except Exception as exc:
        logger.warning(f"Zero-shot failed: {exc}")
        return None


# ── public classify functions ─────────────────────────────────────────────────
def classify_text(text: str, use_zeroshot: bool = True) -> dict[str, Any]:
    """Classify a single piece of text. Returns classification dict."""
    if use_zeroshot:
        result = _zeroshot_classify(text)
        if result:
            return result
    return _keyword_classify(text)


def classify_articles(articles: list[dict], use_zeroshot: bool = True) -> list[dict]:
    """Classify a list of news article dicts. Returns enriched copies."""
    classified: list[dict] = []
    for art in articles:
        text = f"{art.get('headline', '')} {art.get('body_raw', '')}"
        classification = classify_text(text, use_zeroshot=use_zeroshot)
        enriched = {**art, **classification}
        classified.append(enriched)
    return classified


def classify_videos(videos: list[dict], use_zeroshot: bool = True) -> list[dict]:
    """Classify a list of YouTube video metadata dicts. Returns enriched copies."""
    classified: list[dict] = []
    for vid in videos:
        text = f"{vid.get('title', '')} {vid.get('description', '')}"
        classification = classify_text(text, use_zeroshot=use_zeroshot)
        enriched = {**vid, **classification}
        classified.append(enriched)
    return classified


def classify_comments(comments: list[dict], use_zeroshot: bool = True) -> list[dict]:
    """Classify a list of comment dicts. Returns enriched copies."""
    classified: list[dict] = []
    for c in comments:
        text = c.get("text_raw") or c.get("text", "")
        classification = classify_text(text, use_zeroshot=use_zeroshot)
        enriched = {**c, **classification}
        classified.append(enriched)
    return classified
