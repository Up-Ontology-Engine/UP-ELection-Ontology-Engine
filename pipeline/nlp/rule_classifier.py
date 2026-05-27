"""Rule-based fallback classifier using the political lexicon."""

from __future__ import annotations

import json
import os

from .schemas import EntityType, ExtractionResult, IssueType, SentimentStatement

# ── Lexicon (loaded from JSON, with hardcoded defaults) ──────────────────────


def _load_lexicon() -> dict:
    path = os.environ.get("LEXICON_PATH", "data/seeds/political_lexicon.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return _DEFAULT_LEXICON


_DEFAULT_LEXICON = {
    "party_aliases": {
        "BJP": [
            "bjp",
            "भाजपा",
            "भारतीय जनता",
            "कमल",
            "lotus",
            "sarkar",
            "सरकार",
            "yogi",
            "योगी",
            "modi",
            "मोदी",
            "double engine",
            "डबल इंजन",
        ],
        "SP": [
            "sp",
            "समाजवादी",
            "सपा",
            "cycle",
            "साइकिल",
            "akhilesh",
            "अखिलेश",
            "netaji",
            "नेताजी",
            "mulayam",
            "मुलायम",
        ],
        "BSP": ["bsp", "बसपा", "बहुजन", "elephant", "हाथी", "mayawati", "मायावती", "behan ji"],
        "Congress": ["congress", "कांग्रेस", "inc", "rahul", "राहुल", "priyanka"],
    },
    "issue_terms": {
        "water": ["पानी", "water", "नल", "handpump", "हैंडपंप", "पेयजल", "drinking water"],
        "roads": ["सड़क", "road", "गड्ढे", "pothole", "खराब सड़क"],
        "electricity": ["बिजली", "bijli", "light", "load shedding", "लोड शेडिंग", "कटौती"],
        "jobs": ["बेरोजगारी", "नौकरी", "रोजगार", "job", "unemployment", "rojgar"],
        "price_rise": ["महंगाई", "inflation", "महंगा", "gas", "petrol", "दाम", "price"],
        "farmer": ["किसान", "kisan", "farmer", "खेती", "फसल", "crop"],
        "sugarcane": ["गन्ना", "sugarcane", "ganna", "चीनी मिल", "sugar mill", "भुगतान"],
        "women_safety": ["महिला", "woman", "rape", "safety", "बेटी", "सुरक्षा"],
        "health": ["hospital", "अस्पताल", "doctor", "डॉक्टर", "स्वास्थ्य"],
        "education": ["school", "स्कूल", "college", "शिक्षा", "teacher", "शिक्षक"],
        "corruption": ["भ्रष्टाचार", "corruption", "घोटाला", "scam", "रिश्वत"],
        "law_order": ["कानून व्यवस्था", "crime", "अपराध", "police"],
    },
    "positive_terms": [
        "अच्छा",
        "बढ़िया",
        "शानदार",
        "विकास",
        "तरक्की",
        "खुश",
        "धन्यवाद",
        "great",
        "best",
        "achha",
        "badiya",
        "development",
        "improve",
    ],
    "negative_terms": [
        "बुरा",
        "खराब",
        "बेकार",
        "झूठ",
        "धोखा",
        "नाराज",
        "परेशान",
        "fail",
        "fraud",
        "liar",
        "jhuth",
        "dhoka",
        "निराश",
        "बर्बाद",
        "भ्रष्ट",
        "गुंडा",
    ],
}

_LEXICON = _load_lexicon()


def _find_entity(text_lower: str) -> tuple[str | None, str]:
    for party, patterns in _LEXICON["party_aliases"].items():
        if any(p.lower() in text_lower for p in patterns):
            return party, "party"
    return None, "unknown"


def _find_issue(text_lower: str) -> str | None:
    for issue, patterns in _LEXICON["issue_terms"].items():
        if any(p.lower() in text_lower for p in patterns):
            return issue
    return None


def _find_polarity(text_lower: str) -> tuple[int, float]:
    pos = sum(1 for t in _LEXICON["positive_terms"] if t.lower() in text_lower)
    neg = sum(1 for t in _LEXICON["negative_terms"] if t.lower() in text_lower)
    if neg > pos:
        return -1, min(0.45 + neg * 0.1, 0.8)
    if pos > neg:
        return 1, min(0.45 + pos * 0.1, 0.8)
    return 0, 0.35


def rule_based_extract(text: str) -> ExtractionResult:
    tl = text.lower()
    entity, etype = _find_entity(tl)
    if entity is None:
        return ExtractionResult(statements=[], is_political=False)

    issue_str = _find_issue(tl)
    polarity, confidence = _find_polarity(tl)
    stmt = SentimentStatement(
        entity=entity,
        entity_type=EntityType(etype),
        issue=IssueType(issue_str) if issue_str else None,
        polarity=polarity,
        confidence=confidence,
        location_mention=None,
        language="hi",
        evidence="(rule-based)",
    )
    return ExtractionResult(statements=[stmt], is_political=True)
