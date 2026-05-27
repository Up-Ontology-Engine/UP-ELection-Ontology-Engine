"""Language detection with Bhojpuri regex markers."""

import re

from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 42

BHOJPURI_MARKERS = [
    r"\bहऊ\b",
    r"\bहऊँ\b",
    r"\bबाड़े\b",
    r"\bबाड़ी\b",
    r"\bरहल\b",
    r"\bरहलीं\b",
    r"\bकहत\b",
    r"\bकहलस\b",
    r"\bखाईं\b",
    r"\bपइसा\b",
    r"\bनिकलल\b",
    r"\bमिलल\b",
    r"\bबनल\b",
    r"\bकइल\b",
    r"\bआईल\b",
    r"\bगइल\b",
    r"\bएहिजा\b",
    r"\bउहाँ\b",
    r"\bकवनो\b",
    r"\bहमनी\b",
    r"\bतोहनी\b",
    r"\bरउआ\b",
    r"\bईहाँ\b",
    r"\bकाहे\b",
    r"\bआवत\b",
    r"\bजात\b",
    r"\bखात\b",
]

HINGLISH_EXCLUSIVE = {
    "ne",
    "ki",
    "ka",
    "ke",
    "se",
    "bhi",
    "par",
    "aur",
    "ya",
    "toh",
    "kya",
    "kyu",
    "kyon",
    "kab",
    "kahan",
    "kaise",
    "nahi",
    "nhi",
    "na",
    "mat",
    "log",
    "logo",
    "sarkar",
    "bhai",
    "yaar",
    "paisa",
    "paise",
    "chahiye",
    "samasya",
    "pani",
    "paani",
    "bijli",
    "neta",
    "mantri",
    "chunav",
    "pratyashi",
    "jeete",
    "hare",
    "rasta",
    "sadak",
    "kaam",
    "vikas",
    "gunda",
    "gundagardi",
    "bhajpa",
    "sapai",
    "bahujan",
    "kamal",
    "hathi",
    "cycle",
    "hai",
    "hain",
    "ho",
    "kar",
    "raha",
    "re",
    "ko",
    "ye",
    "wo",
    "yogi",
    "modi",
    "akhilesh",
    "sarkar",
    "bura",
    "bhaiya",
    "badiya",
    "shukriya",
    "achha",
    "accha",
    "bilkul",
}

ENGLISH_STOPWORDS = {
    "the",
    "of",
    "and",
    "to",
    "in",
    "is",
    "you",
    "that",
    "it",
    "he",
    "was",
    "for",
    "on",
    "are",
    "as",
    "with",
    "his",
    "they",
    "i",
    "at",
    "be",
    "this",
    "have",
    "from",
    "or",
    "one",
    "had",
    "by",
    "but",
    "not",
    "what",
    "all",
    "were",
    "we",
    "when",
    "your",
    "can",
    "there",
    "use",
    "an",
    "each",
    "which",
    "she",
    "do",
    "how",
    "their",
    "if",
    "will",
    "up",
    "about",
    "out",
    "many",
    "then",
    "them",
    "these",
    "so",
    "some",
    "her",
    "would",
    "make",
    "like",
    "him",
    "into",
    "has",
}

HINGLISH_TRIGRAMS = {
    "hai",
    "nhi",
    "nah",
    "ahi",
    "kar",
    "rah",
    "aha",
    "log",
    "ogo",
    "aur",
    "bhi",
    "par",
    "kab",
    "kya",
    "kyu",
    "kyo",
    "yon",
    "kis",
    "jis",
    "uss",
    "iss",
    "neh",
    "nee",
    "sam",
    "ama",
    "mas",
    "asy",
    "sya",
    "pan",
    "ani",
    "aan",
    "bij",
    "ijl",
    "jli",
    "net",
    "eta",
    "man",
    "ant",
    "ntr",
    "tri",
    "chu",
    "hun",
    "una",
    "nav",
    "pra",
    "rat",
    "tya",
    "yas",
    "ash",
    "shi",
    "jee",
    "eet",
    "ete",
    "har",
    "are",
    "ras",
    "ast",
    "sta",
    "sad",
    "ada",
    "dak",
    "kaa",
    "aam",
    "vik",
    "ika",
    "kas",
    "gun",
    "und",
    "nda",
    "bha",
    "haj",
    "ajp",
    "jpa",
    "sap",
    "apa",
    "pai",
    "bah",
    "ahu",
    "huj",
    "uja",
    "jan",
    "kam",
    "ama",
    "mal",
    "hat",
    "ath",
    "thi",
    "cyc",
    "ycl",
    "cle",
    "yog",
    "ogi",
    "mod",
    "odi",
    "akh",
    "khi",
    "hil",
    "ile",
    "les",
    "esh",
    "sar",
    "ark",
    "rka",
    "aar",
    "bur",
    "ura",
    "bha",
    "hai",
    "iyb",
    "iya",
    "bad",
    "adi",
    "diy",
    "iya",
    "shu",
    "huk",
    "ukr",
    "kri",
    "riy",
    "iya",
    "ach",
    "chh",
    "hha",
    "acc",
    "cca",
    "cha",
    "bil",
    "ilk",
    "lku",
    "kul",
    "tha",
    "tho",
    "mer",
    "era",
    "ter",
    "era",
    "hum",
    "amn",
    "mni",
    "tum",
    "toh",
    "gup",
    "upt",
}

ENGLISH_TRIGRAMS = {
    "the",
    "and",
    "ing",
    "ent",
    "ion",
    "tio",
    "tha",
    "her",
    "ate",
    "for",
    "thi",
    "tis",
    "oth",
    "wit",
    "ith",
    "ver",
    "all",
    "uld",
    "est",
    "con",
    "res",
    "ter",
    "pre",
    "ave",
    "ere",
    "not",
    "but",
    "his",
    "the",
    "are",
    "our",
    "you",
    "out",
    "tiv",
    "ive",
    "nce",
    "nce",
    "sho",
    "hou",
    "und",
    "thi",
    "tin",
    "ati",
    "tio",
}


def is_transliterated_indic(text: str) -> bool:
    """
    Subword-level character n-gram + word vocabulary classifier for Hinglish/Bhojlish.
    """
    cleaned = re.sub(r"[^a-zA-Z\s]", "", text.lower())
    words = cleaned.split()
    if not words:
        return False

    hinglish_words = sum(1 for w in words if w in HINGLISH_EXCLUSIVE)
    english_words = sum(1 for w in words if w in ENGLISH_STOPWORDS)

    hinglish_trigram_hits = 0
    english_trigram_hits = 0
    total_trigrams = 0

    for word in words:
        if len(word) >= 3:
            for i in range(len(word) - 2):
                trigram = word[i : i + 3]
                total_trigrams += 1
                if trigram in HINGLISH_TRIGRAMS:
                    hinglish_trigram_hits += 1
                if trigram in ENGLISH_TRIGRAMS:
                    english_trigram_hits += 1

    hinglish_ratio = (hinglish_trigram_hits / total_trigrams) if total_trigrams > 0 else 0
    english_ratio = (english_trigram_hits / total_trigrams) if total_trigrams > 0 else 0

    if hinglish_words > english_words:
        return True
    if hinglish_ratio > 0.25 and hinglish_ratio > english_ratio:
        return True
    if hinglish_words >= 1 and hinglish_ratio > 0.15:
        return True
    return False


def detect_language(text: str) -> str:
    """Returns: 'hi' | 'bho' | 'en' | 'mix' | 'unknown'"""
    if not text or len(text.strip()) < 5:
        return "unknown"

    hits = sum(1 for p in BHOJPURI_MARKERS if re.search(p, text))
    if hits >= 2:
        return "bho"
    if hits == 1:
        return "mix"

    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))

    if has_latin and not has_devanagari:
        if is_transliterated_indic(text):
            return "mix"

    try:
        lang = detect(text)
        if lang == "hi" or (has_devanagari and lang in ("mr", "ne", "sa", "gu", "pa", "ur")):
            return "hi"
        if lang == "en":
            if has_latin and not has_devanagari and is_transliterated_indic(text):
                return "mix"
            return "en"
        if has_latin and not has_devanagari:
            if is_transliterated_indic(text):
                return "mix"
            return "en"
        return lang
    except LangDetectException:
        if has_latin and not has_devanagari:
            if is_transliterated_indic(text):
                return "mix"
            return "en"
        if has_devanagari:
            return "hi"
        return "unknown"
