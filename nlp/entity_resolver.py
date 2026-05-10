"""
Entity resolver: maps free-text political entity mentions → canonical IDs.

Used as Stage 5b of the NLP pipeline (after LLM extraction).
Resolves candidate names and party mentions to canonical IDs in
candidate_master / party, so every PulseEvent references a real graph node.
"""
from __future__ import annotations
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Gorakhpur-context candidate aliases → canonical display name
_CANDIDATE_ALIASES: dict[str, str] = {
    "yogi adityanath": "Yogi Adityanath",
    "yogi": "Yogi Adityanath",
    "योगी": "Yogi Adityanath",
    "cm yogi": "Yogi Adityanath",
    "maharaj ji": "Yogi Adityanath",
    "akhilesh yadav": "Akhilesh Yadav",
    "akhilesh": "Akhilesh Yadav",
    "अखिलेश": "Akhilesh Yadav",
    "netaji": "Akhilesh Yadav",
    "mayawati": "Mayawati",
    "behan ji": "Mayawati",
    "बहनजी": "Mayawati",
    "modi": "Narendra Modi",
    "pm modi": "Narendra Modi",
    "नमो": "Narendra Modi",
}

_PARTY_CANONICAL: dict[str, str] = {
    "bjp": "BJP", "भाजपा": "BJP", "lotus": "BJP", "double engine": "BJP",
    "sp": "SP", "samajwadi": "SP", "cycle": "SP", "सपा": "SP",
    "bsp": "BSP", "elephant": "BSP", "बसपा": "BSP",
    "inc": "INC", "congress": "INC", "कांग्रेस": "INC",
    "aap": "AAP", "आप": "AAP",
    "nishad": "NISHAD",
    "apna dal": "AD",
    "aimim": "AIMIM",
}

_SALUTATION_PREFIXES = (
    "shri ", "smt ", "dr ", "sh ", "श्री ", "श्रीमती ", "डॉ ", "mr ", "mrs ",
)


class EntityResolver:
    """
    Resolves raw entity text → (canonical_id, canonical_name, confidence).

    Loaded lazily from DB on first use. Safe to construct with no DB connection
    (degrades gracefully — alias lookups still work).
    """

    def __init__(self, postgres_url: Optional[str] = None):
        self._pg_url = postgres_url or os.environ.get("POSTGRES_URL", "")
        self._candidates: dict[str, tuple[str, str]] = {}  # lower → (id, name)
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._pg_url:
            return
        try:
            import sqlalchemy as sa
            from sqlalchemy import text
            engine = sa.create_engine(self._pg_url)
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT candidate_id::text, name FROM candidate_master WHERE name IS NOT NULL"
                )).fetchall()
            for cid, name in rows:
                key = name.lower().strip()
                self._candidates[key] = (cid, name)
                # Strip salutations and re-index
                stripped = key
                for pfx in _SALUTATION_PREFIXES:
                    if stripped.startswith(pfx):
                        stripped = stripped[len(pfx):].strip()
                        self._candidates.setdefault(stripped, (cid, name))
            logger.debug("EntityResolver: %d candidate entries loaded", len(self._candidates))
        except Exception as e:
            logger.warning("EntityResolver: DB load failed — %s", e)

    def resolve_party(self, raw: str) -> Optional[str]:
        """Return canonical party_id or None."""
        lower = raw.lower().strip()
        if lower in _PARTY_CANONICAL:
            return _PARTY_CANONICAL[lower]
        for key in sorted(_PARTY_CANONICAL, key=len, reverse=True):
            if key in lower:
                return _PARTY_CANONICAL[key]
        return None

    def resolve_candidate(self, raw: str) -> tuple[Optional[str], Optional[str], float]:
        """Return (candidate_id, canonical_name, confidence)."""
        self._ensure_loaded()
        if not raw:
            return None, None, 0.0

        lower = raw.lower().strip()

        # 1. Static alias lookup
        alias = _CANDIDATE_ALIASES.get(lower)
        if alias:
            for key, (cid, name) in self._candidates.items():
                if alias.lower() in name.lower():
                    return cid, name, 0.95
            return None, alias, 0.80

        # 2. Exact DB match
        if lower in self._candidates:
            cid, name = self._candidates[lower]
            return cid, name, 1.0

        # 3. Fuzzy match (thefuzz)
        if self._candidates:
            try:
                from thefuzz import process as fuzz
                keys = list(self._candidates.keys())
                match, score = fuzz.extractOne(lower, keys)
                if score >= 75:
                    cid, name = self._candidates[match]
                    return cid, name, round(score / 100.0, 2)
            except Exception:
                pass

        return None, None, 0.0

    def resolve(
        self, raw_entity: str, entity_type: str
    ) -> tuple[Optional[str], Optional[str], float]:
        """
        Unified resolve. Returns (resolved_id, resolved_name, confidence).
        For parties: resolved_id = party_id.
        For candidates: resolved_id = candidate_id (UUID string).
        """
        if entity_type in ("party", "govt"):
            pid = self.resolve_party(raw_entity)
            return pid, pid, (1.0 if pid else 0.0)
        elif entity_type == "candidate":
            return self.resolve_candidate(raw_entity)
        # scheme / issue / unknown — return as-is
        return None, raw_entity, 0.5


# Module-level singleton (lazy-initialised)
_resolver: Optional[EntityResolver] = None


def get_resolver() -> EntityResolver:
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
