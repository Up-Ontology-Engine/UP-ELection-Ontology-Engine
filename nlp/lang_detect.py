"""Language detection with Bhojpuri regex markers."""
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 42

BHOJPURI_MARKERS = [
    r"\bहऊ\b", r"\bहऊँ\b", r"\bबाड़े\b", r"\bबाड़ी\b",
    r"\bरहल\b", r"\bरहलीं\b", r"\bकहत\b", r"\bकहलस\b",
    r"\bखाईं\b", r"\bपइसा\b", r"\bनिकलल\b", r"\bमिलल\b",
    r"\bबनल\b", r"\bकइल\b", r"\bआईल\b", r"\bगइल\b",
    r"\bएहिजा\b", r"\bउहाँ\b", r"\bकवनो\b", r"\bहमनी\b",
    r"\bतोहनी\b", r"\bरउआ\b", r"\bईहाँ\b", r"\bकाहे\b",
    r"\bआवत\b", r"\bजात\b", r"\bखात\b",
]

def detect_language(text: str) -> str:
    """Returns: 'hi' | 'bho' | 'en' | 'mix' | 'unknown'"""
    if not text or len(text.strip()) < 5:
        return "unknown"

    hits = sum(1 for p in BHOJPURI_MARKERS if re.search(p, text))
    if hits >= 2:
        return "bho"
    if hits == 1:
        return "mix"

    try:
        lang = detect(text)
        if lang == "hi":
            return "hi"
        if lang in ("en",):
            return "en"
        if lang in ("mr", "ne", "sa", "gu", "pa"):
            return "hi"  # Devanagari misclassification
        return lang
    except LangDetectException:
        return "unknown"
