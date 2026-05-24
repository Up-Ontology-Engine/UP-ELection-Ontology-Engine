"""
caste_mapper.py
================
Maps extracted surnames to caste groups using:
1. Bootstrap dictionary for ~80 high-frequency UP/Gorakhpur surnames
2. Groq LLM (llama-3.3-70b) for all unknown surnames — batched, cached
3. RapidFuzz fallback for OCR transliteration variants

Cache: data/seeds/surname_caste_map.json
  {
    "YADAVA": {
      "caste_group": "Yadav",
      "social_category": "OBC",
      "confidence": "high",
      "source": "bootstrap"
    },
    ...
  }

social_category values: OBC | SC | ST | General | Muslim | Unknown | Ambiguous
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import TypedDict
from dotenv import load_dotenv

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "data" / "seeds" / "surname_caste_map.json"

load_dotenv(ROOT / ".env")

GROQ_MODEL = "llama-3.1-8b-instant"
BATCH_SIZE = 100


# ── Type ──────────────────────────────────────────────────────────────────────

class CasteInfo(TypedDict):
    caste_group: str
    social_category: str
    confidence: str
    source: str


# ── Bootstrap dictionary ───────────────────────────────────────────────────────
# This covers the most frequent surnames found in Gorakhpur voter rolls.
# Source: ECI demographic studies, academic UP caste surveys, field knowledge.

BOOTSTRAP: dict[str, dict] = {
    # ── OBC ──────────────────────────────────────────────────────────────────
    "YADAVA": {"caste_group": "Yadav", "social_category": "OBC", "confidence": "high"},
    "YADAV": {"caste_group": "Yadav", "social_category": "OBC", "confidence": "high"},
    "NISHADA": {"caste_group": "Nishad", "social_category": "OBC", "confidence": "high"},
    "NISHAD": {"caste_group": "Nishad", "social_category": "OBC", "confidence": "high"},
    "MAURYA": {"caste_group": "Maurya", "social_category": "OBC", "confidence": "high"},
    "KUSHWAHA": {"caste_group": "Kushwaha", "social_category": "OBC", "confidence": "high"},
    "KURMI": {"caste_group": "Kurmi", "social_category": "OBC", "confidence": "high"},
    "PRAJAPATI": {"caste_group": "Prajapati", "social_category": "OBC", "confidence": "high"},
    "PRAJA": {"caste_group": "Prajapati", "social_category": "OBC", "confidence": "medium"},
    "SAHANI": {"caste_group": "Sahani", "social_category": "OBC", "confidence": "high"},
    "SAHU": {"caste_group": "Sahu", "social_category": "OBC", "confidence": "high"},
    "KEWAT": {"caste_group": "Kewat", "social_category": "OBC", "confidence": "high"},
    "KEVAT": {"caste_group": "Kewat", "social_category": "OBC", "confidence": "high"},
    "BIND": {"caste_group": "Bind", "social_category": "OBC", "confidence": "high"},
    "CHAUHANA": {"caste_group": "Chauhan", "social_category": "OBC", "confidence": "high"},
    "CHAUHAN": {"caste_group": "Chauhan", "social_category": "OBC", "confidence": "high"},
    "RAJBHAR": {"caste_group": "Rajbhar", "social_category": "OBC", "confidence": "high"},
    "VISHVAKARMA": {"caste_group": "Vishwakarma", "social_category": "OBC", "confidence": "high"},
    "VISHWAKARMA": {"caste_group": "Vishwakarma", "social_category": "OBC", "confidence": "high"},
    "KASHYAPA": {"caste_group": "Kashyap", "social_category": "OBC", "confidence": "high"},
    "KASHYAP": {"caste_group": "Kashyap", "social_category": "OBC", "confidence": "high"},
    "MALLAH": {"caste_group": "Mallah", "social_category": "OBC", "confidence": "high"},
    "TELI": {"caste_group": "Teli", "social_category": "OBC", "confidence": "high"},
    "LUNIA": {"caste_group": "Lunia", "social_category": "OBC", "confidence": "high"},
    "MADDHESHIYA": {"caste_group": "Madheshiya", "social_category": "OBC", "confidence": "high"},
    # OBC / Baniya (trader)
    "GUPTA": {"caste_group": "Gupta", "social_category": "OBC_Baniya", "confidence": "high"},
    "AGARWAL": {"caste_group": "Agarwal", "social_category": "OBC_Baniya", "confidence": "high"},
    "JAYASAVALA": {"caste_group": "Jaiswal", "social_category": "OBC_Baniya", "confidence": "high"},
    "JAISAVALA": {"caste_group": "Jaiswal", "social_category": "OBC_Baniya", "confidence": "high"},
    "JAISWAL": {"caste_group": "Jaiswal", "social_category": "OBC_Baniya", "confidence": "high"},
    "VAISHYA": {"caste_group": "Vaishya", "social_category": "OBC_Baniya", "confidence": "high"},
    # ── SC ───────────────────────────────────────────────────────────────────
    "PASSI": {"caste_group": "Passi", "social_category": "SC", "confidence": "high"},
    "CHAMAR": {"caste_group": "Chamar", "social_category": "SC", "confidence": "high"},
    "VALMIKI": {"caste_group": "Valmiki", "social_category": "SC", "confidence": "high"},
    "KORI": {"caste_group": "Kori", "social_category": "SC", "confidence": "high"},
    "DHOBI": {"caste_group": "Dhobi", "social_category": "SC", "confidence": "high"},
    "MUSAHAR": {"caste_group": "Musahar", "social_category": "SC", "confidence": "high"},
    "DOM": {"caste_group": "Dom", "social_category": "SC", "confidence": "high"},
    "HARIJAN": {"caste_group": "Harijan", "social_category": "SC", "confidence": "high"},
    # ── General / Brahmin ─────────────────────────────────────────────────────
    "SHARMA": {"caste_group": "Sharma", "social_category": "General", "confidence": "high"},
    "TIVARI": {"caste_group": "Tiwari", "social_category": "General", "confidence": "high"},
    "TIWARI": {"caste_group": "Tiwari", "social_category": "General", "confidence": "high"},
    "PANDEY": {"caste_group": "Pandey", "social_category": "General", "confidence": "high"},
    "PANDEYA": {"caste_group": "Pandey", "social_category": "General", "confidence": "high"},
    "DUBEY": {"caste_group": "Dubey", "social_category": "General", "confidence": "high"},
    "DUBE": {"caste_group": "Dubey", "social_category": "General", "confidence": "high"},
    "MISHRA": {"caste_group": "Mishra", "social_category": "General", "confidence": "high"},
    "TRIPATHI": {"caste_group": "Tripathi", "social_category": "General", "confidence": "high"},
    "BAJPAI": {"caste_group": "Bajpai", "social_category": "General", "confidence": "high"},
    "UPADHYAY": {"caste_group": "Upadhyay", "social_category": "General", "confidence": "high"},
    # ── General / Kayastha ────────────────────────────────────────────────────
    "SHRIVASTAVA": {"caste_group": "Shrivastava", "social_category": "General", "confidence": "high"},
    "SRIVASTAVA": {"caste_group": "Shrivastava", "social_category": "General", "confidence": "high"},
    "SAXENA": {"caste_group": "Saxena", "social_category": "General", "confidence": "high"},
    # ── General / Rajput ─────────────────────────────────────────────────────
    "SINGH": {"caste_group": "Singh", "social_category": "General_Ambiguous",
              "confidence": "medium"},  # Rajput + Koeri OBC → ambiguous
    "RAJPUT": {"caste_group": "Rajput", "social_category": "General", "confidence": "high"},
    "THAKUR": {"caste_group": "Thakur", "social_category": "General", "confidence": "high"},
    "CHAUHANA": {"caste_group": "Chauhan", "social_category": "General_Ambiguous",
                 "confidence": "medium"},  # Rajput or OBC
    # ── Muslim ───────────────────────────────────────────────────────────────
    "ANSARI": {"caste_group": "Ansari", "social_category": "Muslim", "confidence": "high"},
    "AMSARI": {"caste_group": "Ansari", "social_category": "Muslim", "confidence": "high"},
    "KHAN": {"caste_group": "Khan", "social_category": "Muslim", "confidence": "high"},
    "ALI": {"caste_group": "Ali", "social_category": "Muslim", "confidence": "high"},
    "QURESHI": {"caste_group": "Qureshi", "social_category": "Muslim", "confidence": "high"},
    "SIDDIQUI": {"caste_group": "Siddiqui", "social_category": "Muslim", "confidence": "high"},
    "KHATUN": {"caste_group": "Muslim_Female", "social_category": "Muslim", "confidence": "high"},
    "KHATUNA": {"caste_group": "Muslim_Female", "social_category": "Muslim", "confidence": "high"},
    "RAHAMANA": {"caste_group": "Rahman", "social_category": "Muslim", "confidence": "high"},
    "RAHMANA": {"caste_group": "Rahman", "social_category": "Muslim", "confidence": "high"},
    "MOHAMMADA": {"caste_group": "Mohammad", "social_category": "Muslim", "confidence": "high"},
    "SHEIKH": {"caste_group": "Sheikh", "social_category": "Muslim", "confidence": "high"},
}

# Add source to all bootstrap entries
for _key in BOOTSTRAP:
    BOOTSTRAP[_key]["source"] = "bootstrap"


# ── Cache I/O ─────────────────────────────────────────────────────────────────

def _load_cache(path: Path = CACHE_PATH) -> dict[str, CasteInfo]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data
    except (json.JSONDecodeError, IOError) as exc:
        log.warning("Cache load failed (%s) — starting fresh", exc)
        return {}


def _save_cache(cache: dict, path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2, sort_keys=True)


# ── Groq LLM batch classifier ──────────────────────────────────────────────────

_LLM_SYSTEM = """\
You are an expert on Indian caste demographics in Uttar Pradesh, particularly the \
Gorakhpur region. You classify surnames into caste categories.

Rules:
1. Respond ONLY with valid JSON — no prose, no markdown, no explanation.
2. For each surname, output exactly:
   {"caste_group": "<specific caste name>", "social_category": "<category>", "confidence": "<level>"}
3. social_category must be one of: OBC | SC | ST | General | Muslim | Ambiguous | Unknown
4. confidence must be one of: high | medium | low
5. If a token is NOT a surname (e.g. "Kumar", "Devi", "Ram") → caste_group="Ambiguous", social_category="Ambiguous", confidence="low"
6. For Muslim names/surnames → social_category="Muslim"
7. "Singh" → caste_group="Singh", social_category="Ambiguous" (could be Rajput or Koeri OBC)
8. Names that are clearly just first names without caste → Unknown
"""


def _call_groq_batch(
    surnames: list[str],
    api_key: str,
    *,
    model: str = GROQ_MODEL,
    max_retries: int = 3,
) -> dict[str, dict]:
    """Call Groq API for a batch of surnames. Returns {surname: caste_info}."""
    try:
        from groq import Groq
    except ImportError:
        log.error("groq package not installed. Run: pip install groq")
        return {}

    client = Groq(api_key=api_key)

    prompt_surnames = json.dumps(surnames, ensure_ascii=False)
    user_msg = (
        f"Classify the following {len(surnames)} surnames from Uttar Pradesh electoral rolls "
        f"into caste categories.\n\n"
        f"Surnames: {prompt_surnames}\n\n"
        f"Respond with a single JSON object mapping each surname to its classification:\n"
        f'{{"SURNAME1": {{"caste_group": "...", "social_category": "...", "confidence": "..."}}, ...}}'
    )

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _LLM_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)
            # Validate keys are in our input list
            cleaned = {}
            for sname in surnames:
                info = result.get(sname) or result.get(sname.upper()) or result.get(sname.lower())
                if info and isinstance(info, dict):
                    cleaned[sname] = {
                        "caste_group": str(info.get("caste_group", "Unknown")),
                        "social_category": str(info.get("social_category", "Unknown")),
                        "confidence": str(info.get("confidence", "low")),
                        "source": "llm",
                    }
                else:
                    cleaned[sname] = {
                        "caste_group": "Unknown",
                        "social_category": "Unknown",
                        "confidence": "low",
                        "source": "llm_missing",
                    }
            return cleaned

        except Exception as exc:
            log.warning("Groq attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    # All attempts failed → return Unknown for all
    return {
        s: {"caste_group": "Unknown", "social_category": "Unknown",
            "confidence": "low", "source": "llm_error"}
        for s in surnames
    }


# ── Main classifier ────────────────────────────────────────────────────────────

class CasteMapper:
    """
    Maps surnames to caste groups.

    Usage
    -----
    mapper = CasteMapper()
    info = mapper.lookup("YADAVA")
    # {"caste_group": "Yadav", "social_category": "OBC", "confidence": "high", "source": "bootstrap"}

    df["caste_group"] = df["surname"].apply(mapper.lookup_field("caste_group"))
    """

    def __init__(
        self,
        cache_path: Path = CACHE_PATH,
        *,
        api_key: str | None = None,
        use_llm: bool = True,
    ) -> None:
        self._cache_path = cache_path
        self._cache: dict[str, CasteInfo] = {**BOOTSTRAP, **_load_cache(cache_path)}
        self._api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_FALLBACK")
        self._use_llm = use_llm and bool(self._api_key)
        if use_llm and not self._api_key:
            log.warning("GROQ_API_KEY not set — LLM classification disabled, using bootstrap only")

    # ── Public API ─────────────────────────────────────────────────────────

    def lookup(self, surname: str) -> CasteInfo:
        """Return caste info for a single surname (upper-cased internally)."""
        key = str(surname).strip().upper()
        if not key or key in ("UNKNOWN", "NOTA"):
            return {"caste_group": "Unknown", "social_category": "Unknown",
                    "confidence": "low", "source": "none"}
        return self._cache.get(key, {"caste_group": "Unknown", "social_category": "Unknown",
                                     "confidence": "low", "source": "none"})

    def lookup_field(self, field: str):
        """Return a callable suitable for DataFrame.apply that extracts one field."""
        def _fn(surname: str) -> str:
            return self.lookup(surname).get(field, "Unknown")
        return _fn

    def enrich_dataframe(self, df, surname_col: str = "surname") -> "pd.DataFrame":
        """
        Add caste_group, social_category, caste_confidence, caste_source columns.
        Calls classify_batch for any uncached surnames first.
        """
        import pandas as pd  # local import to avoid top-level dep issue

        unique_surnames = df[surname_col].dropna().unique().tolist()
        self.classify_batch(unique_surnames)  # fill cache for all unknowns

        df = df.copy()
        df["caste_group"] = df[surname_col].apply(self.lookup_field("caste_group"))
        df["social_category"] = df[surname_col].apply(self.lookup_field("social_category"))
        df["caste_confidence"] = df[surname_col].apply(self.lookup_field("confidence"))
        df["caste_source"] = df[surname_col].apply(self.lookup_field("source"))
        return df

    def classify_batch(self, surnames: list[str]) -> dict[str, CasteInfo]:
        """
        Classify a list of surnames. Returns full mapping (cached + newly fetched).
        Only calls LLM for surnames not already in cache.
        """
        surnames_upper = [s.strip().upper() for s in surnames if s and s.strip()]
        unknown = [s for s in surnames_upper if s not in self._cache and s not in ("UNKNOWN", "NOTA", "")]

        if unknown:
            log.info("%d uncached surnames — classifying…", len(unknown))
            if self._use_llm:
                self._llm_classify(unknown)
            else:
                # Mark all as Unknown so they're in cache and won't re-query
                for s in unknown:
                    self._cache[s] = {
                        "caste_group": "Unknown",
                        "social_category": "Unknown",
                        "confidence": "low",
                        "source": "no_llm",
                    }
            self._save()
        else:
            log.info("All %d surnames found in cache", len(surnames_upper))

        return {s: self._cache.get(s, {}) for s in surnames_upper}

    # ── Internal ───────────────────────────────────────────────────────────

    def _llm_classify(self, surnames: list[str]) -> None:
        """Batch-call Groq for unknown surnames and merge into cache."""
        batches = [surnames[i: i + BATCH_SIZE] for i in range(0, len(surnames), BATCH_SIZE)]
        log.info("Calling Groq LLM in %d batch(es) of ≤%d…", len(batches), BATCH_SIZE)

        for i, batch in enumerate(batches, 1):
            log.info("Batch %d/%d: %d surnames", i, len(batches), len(batch))
            results = _call_groq_batch(batch, self._api_key)
            self._cache.update(results)
            if i < len(batches):
                time.sleep(3.5)  # Rate-limit buffer

    def _save(self) -> None:
        _save_cache(self._cache, self._cache_path)
        log.info("Caste cache saved → %s  (%d entries)", self._cache_path, len(self._cache))

    def cache_stats(self) -> dict:
        total = len(self._cache)
        by_source = {}
        by_category = {}
        for info in self._cache.values():
            src = info.get("source", "unknown")
            cat = info.get("social_category", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
        return {"total": total, "by_source": by_source, "by_category": by_category}


# ── Initialise cache file with bootstrap on first run ────────────────────────

def initialise_cache(force: bool = False) -> None:
    """Write bootstrap entries to cache file if it doesn't exist."""
    if CACHE_PATH.exists() and not force:
        return
    log.info("Initialising caste cache with %d bootstrap entries…", len(BOOTSTRAP))
    existing = _load_cache() if CACHE_PATH.exists() else {}
    merged = {**BOOTSTRAP, **existing}  # existing takes precedence
    _save_cache(merged)
    log.info("Cache initialised → %s", CACHE_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    initialise_cache()
    mapper = CasteMapper()
    test_surnames = ["YADAVA", "NISHADA", "SHARMA", "ANSARI", "UNKNOWN",
                     "MAURYA", "GUPTA", "SHRIVASTAVA", "SINGH", "KHATUNA"]
    for s in test_surnames:
        info = mapper.lookup(s)
        print(f"{s:20s} → {info['caste_group']:20s} [{info['social_category']:15s}] ({info['confidence']})")
    print("\nCache stats:", mapper.cache_stats())
