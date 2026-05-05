"""
Fix 3 — Dynamic alias expansion for geo-resolution.

Problem: geo_resolver.py can only match location mentions that already exist
in gorakhpur_aliases.json. When an unmatched mention appears repeatedly, it
means either (a) the alias file needs a new entry, or (b) it's noise.

This module:
  1. Reads unresolved location_mention values from pulse_events.
  2. For each, attempts fuzzy match against existing canonical keys.
  3. If the best match is above a learning threshold (default 80), it proposes
     a new alias mapping and writes it back to gorakhpur_aliases.json.
  4. If below threshold, it logs the mention as unresolvable so a human can
     review and add it manually.

Usage (standalone):
    python -m nlp.alias_expander

Usage (import):
    from nlp.alias_expander import AliasExpander
    expander = AliasExpander()
    new_aliases = expander.propose_new_aliases(unmatched_mentions)
    expander.apply_and_save(new_aliases)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from thefuzz import process as fuzz_process

logger = logging.getLogger(__name__)

ALIAS_FILE = Path(__file__).parent.parent / "data" / "seeds" / "gorakhpur_aliases.json"

# Accept a fuzzy match as "same location" only above this score
LEARN_THRESHOLD = 80
# Below this, record as unresolvable — needs human review
UNRESOLVABLE_THRESHOLD = 50


class AliasExpander:
    def __init__(self, alias_file: Path = ALIAS_FILE) -> None:
        self.alias_file = alias_file
        self.alias_map: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.alias_file.exists():
            logger.warning("Alias file not found: %s", self.alias_file)
            return {}
        with open(self.alias_file, encoding="utf-8") as f:
            return json.load(f)

    def _save(self) -> None:
        with open(self.alias_file, "w", encoding="utf-8") as f:
            json.dump(self.alias_map, f, ensure_ascii=False, indent=2)
        logger.info("Alias map saved (%d entries).", len(self.alias_map))

    # ── Public API ────────────────────────────────────────────────────────

    def propose_new_aliases(
        self, unmatched: list[str]
    ) -> list[dict]:
        """
        For each unmatched mention, attempt to map it to an existing canonical key.

        Returns a list of proposal dicts:
            {"mention": str, "canonical": str, "booth_id": str, "score": int, "action": str}

        action values:
            "auto_add"   — score >= LEARN_THRESHOLD, safe to add automatically
            "review"     — score in (UNRESOLVABLE_THRESHOLD, LEARN_THRESHOLD)
            "unresolvable" — score <= UNRESOLVABLE_THRESHOLD, skip
        """
        canonicals = list(self.alias_map.keys())
        proposals = []

        for mention in unmatched:
            if not mention or mention in self.alias_map:
                continue

            if not canonicals:
                proposals.append(
                    {"mention": mention, "canonical": None, "booth_id": None, "score": 0, "action": "unresolvable"}
                )
                continue

            best_match, score = fuzz_process.extractOne(mention, canonicals)

            if score >= LEARN_THRESHOLD:
                action = "auto_add"
            elif score >= UNRESOLVABLE_THRESHOLD:
                action = "review"
            else:
                action = "unresolvable"

            proposals.append(
                {
                    "mention":   mention,
                    "canonical": best_match,
                    "booth_id":  self.alias_map[best_match]["id"] if best_match else None,
                    "score":     score,
                    "action":    action,
                }
            )

        return proposals

    def apply_and_save(self, proposals: list[dict]) -> int:
        """
        Add auto_add proposals to the in-memory map and persist to disk.
        Returns the number of new aliases added.
        """
        added = 0
        for p in proposals:
            if p["action"] != "auto_add":
                continue
            if p["mention"] in self.alias_map:
                continue
            canonical_entry = self.alias_map.get(p["canonical"], {})
            self.alias_map[p["mention"]] = {
                "id":   canonical_entry.get("id"),
                "type": canonical_entry.get("type", "booth"),
                "auto_learned": True,
            }
            added += 1
            logger.info("Auto-learned alias: '%s' → %s", p["mention"], canonical_entry.get("id"))

        if added:
            self._save()

        return added

    def add_alias(self, mention: str, booth_id: str, location_type: str = "booth") -> None:
        """Manually add a single alias and save."""
        self.alias_map[mention] = {"id": booth_id, "type": location_type, "auto_learned": False}
        self._save()

    def expand_from_db(self, engine) -> tuple[int, int]:
        """
        Pull unresolved location_mentions from pulse_events, run expansion,
        and return (proposals_count, auto_added_count).
        """
        from sqlalchemy import text

        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT DISTINCT location_mention
                    FROM pulse_events
                    WHERE location_mention IS NOT NULL
                      AND location_mention != ''
                      AND mapped_booth_id IS NULL
                    LIMIT 500
                """)
            ).fetchall()

        unmatched = [r[0] for r in rows if r[0]]
        if not unmatched:
            return 0, 0

        proposals = self.propose_new_aliases(unmatched)
        added = self.apply_and_save(proposals)

        review_count = sum(1 for p in proposals if p["action"] == "review")
        if review_count:
            logger.warning(
                "%d mentions need human review — run nlp/alias_expander.py --report to see them.",
                review_count,
            )

        return len(proposals), added


# ── CLI entry point ───────────────────────────────────────────────────────────

def _print_report(proposals: list[dict]) -> None:
    print(f"\n{'Mention':<35} {'Canonical':<35} {'Score':>5}  Action")
    print("-" * 90)
    for p in sorted(proposals, key=lambda x: -x["score"]):
        mention   = (p["mention"] or "")[:34]
        canonical = (p["canonical"] or "")[:34]
        print(f"{mention:<35} {canonical:<35} {p['score']:>5}  {p['action']}")


if __name__ == "__main__":
    import argparse
    from api.db import get_pg_engine

    parser = argparse.ArgumentParser(description="Expand geo-alias map from unresolved DB mentions.")
    parser.add_argument("--report", action="store_true", help="Print proposals without saving")
    args = parser.parse_args()

    expander = AliasExpander()
    engine   = get_pg_engine()

    from sqlalchemy import text
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT location_mention FROM pulse_events
                WHERE location_mention IS NOT NULL AND location_mention != ''
                  AND mapped_booth_id IS NULL LIMIT 500
            """)
        ).fetchall()
    unmatched = [r[0] for r in rows if r[0]]

    proposals = expander.propose_new_aliases(unmatched)
    _print_report(proposals)

    if not args.report:
        added = expander.apply_and_save(proposals)
        print(f"\nAuto-added {added} new aliases to {ALIAS_FILE}")
    else:
        print("\n(--report mode: no changes saved)")
