#!/usr/bin/env python3
"""
Post-process PoolBoothData JSON files to clean OCR label artifacts from name fields.
Run after pdf_to_json.py completes (or at any point — safe to re-run).
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JSON_DIR = BASE_DIR / "data" / "PoolBoothData_JSON"

_NAME_LABEL_ARTIFACT_RE = re.compile(
    r"\s+(?:Na|Naa|Pi|Pii|Rpa|Rp|Ha|Pita|Pati|Neem|Makan)\s*$",
    re.IGNORECASE,
)

# OCR noise in house numbers
_HOUSE_TRAIL_RE = re.compile(r"[\s\+\-\–\—\|०।a-zA-Z]+$")


def clean_name(s: str) -> str:
    if not s:
        return s
    return _NAME_LABEL_ARTIFACT_RE.sub("", s).strip()


def clean_house(s: str) -> str:
    if not s:
        return s
    # Keep only leading digits/letters that form a house number
    m = re.match(r"^[0-9A-Za-zऀ-ॿ/\-]+", s.strip())
    return m.group(0) if m else s.strip()


def process_json(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    for record in data.get("voter_records", []):
        for field in ("name", "relation_name"):
            old = record.get(field, "")
            new = clean_name(old)
            if new != old:
                record[field] = new
                changed += 1
        old_h = record.get("house_number", "")
        new_h = clean_house(old_h)
        if new_h != old_h:
            record["house_number"] = new_h
            changed += 1

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return changed


def main():
    json_files = sorted(JSON_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to clean")
    total_changes = 0
    for p in json_files:
        n = process_json(p)
        total_changes += n
        if n:
            print(f"  {p.name}: {n} fields cleaned")
    print(f"Done. Total field corrections: {total_changes}")


if __name__ == "__main__":
    main()
