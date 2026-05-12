"""Resolve free-text location mentions → booth_id via fuzzy matching."""
from __future__ import annotations
from thefuzz import process as fuzz
from .schemas import GeoResolution
from typing import Optional

DEFAULT_AC_ID = "GKP_322"


def _ac_from_booth_id(booth_id: str) -> str:
    """Extract ac_id from a booth_id like 'GKP_322_045' → 'GKP_322'."""
    parts = booth_id.split("_")
    return "_".join(parts[:2]) if len(parts) >= 3 else DEFAULT_AC_ID


class GeoResolver:
    """
    alias_data: {
      "Deoria Naka": {"id": "GKP_322_045", "type": "booth"},
      "Civil Lines": {"id": "GKP_322_001", "type": "booth"},
      "Gorakhpur Urban": {"id": "GKP_322", "type": "ac"},
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

        if is_booth:
            mapped_ac = _ac_from_booth_id(entry["id"])
        elif entry["type"] == "ac" and score >= threshold:
            mapped_ac = entry["id"]
        else:
            mapped_ac = DEFAULT_AC_ID

        return GeoResolution(
            matched_text=match if score >= threshold else None,
            mapped_id=entry["id"] if score >= threshold else DEFAULT_AC_ID,
            mapped_type=entry["type"] if score >= threshold else "ac",
            mapped_booth_id=entry["id"] if is_booth else None,
            mapped_ac_id=mapped_ac,
            geo_confidence=geo_conf if score >= threshold else 0.3,
        )
