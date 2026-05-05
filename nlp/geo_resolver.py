"""Resolve free-text location mentions → booth_id via fuzzy matching."""
from __future__ import annotations
from thefuzz import process as fuzz
from .schemas import GeoResolution
from typing import Optional

DEFAULT_AC_ID = "GKP_URBAN"


class GeoResolver:
    """
    alias_data: {
      "Deoria Naka": {"id": "GKP_U_045", "type": "booth"},
      "Civil Lines": {"id": "GKP_U_012", "type": "booth"},
      "Gorakhpur Urban": {"id": "GKP_URBAN", "type": "ac"},
      ...
    }
    """
    def __init__(self, alias_data: dict):
        self.aliases = alias_data
        self.keys = list(alias_data.keys())

    def resolve(self, location_text: str, threshold: int = 75) -> Optional[GeoResolution]:
        if not location_text or len(location_text) < 3 or not self.keys:
            return None

        match, score = fuzz.extractOne(location_text, self.keys)
        geo_conf = round(score / 100.0, 3)

        entry = self.aliases[match]
        is_booth = entry["type"] == "booth" and score >= threshold

        return GeoResolution(
            matched_text=match if score >= threshold else None,
            mapped_id=entry["id"] if score >= threshold else DEFAULT_AC_ID,
            mapped_type=entry["type"] if score >= threshold else "ac",
            mapped_booth_id=entry["id"] if is_booth else None,
            mapped_ac_id=entry["id"] if entry["type"] == "ac" else DEFAULT_AC_ID,
            geo_confidence=geo_conf if score >= threshold else 0.3,
        )
