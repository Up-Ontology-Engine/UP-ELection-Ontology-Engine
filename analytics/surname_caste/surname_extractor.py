"""
surname_extractor.py
=====================
Multi-signal surname extraction from Indian voter roll names.

Extraction algorithm
--------------------
1.  Clean the full name: strip OCR artefacts, honorifics, numeric suffixes.
2.  Take the LAST word as the primary surname candidate.
3.  If last word is a GENERIC_SUFFIX (Devi, Kumar, Prasad …) try second-to-last.
4.  Cross-validate with the last word of relation_name.
5.  Assign a confidence level:
      HIGH   : primary == family signal (same last word)
      MEDIUM : primary ≠ family signal but both are non-generic
      LOW    : primary is the second-to-last word fallback
      VERY_LOW: everything else; only family signal was usable
6.  Apply RapidFuzz-based normalisation against the known caste dict keys.

Returns columns: surname, surname_confidence, surname_source
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# ── Generic suffixes that appear at the END of a name but are NOT surnames ────
GENERIC_SUFFIXES = frozenset(
    {
        # Female honorifics / given-name components
        "DEVI", "BAI", "WATI", "KUMARI", "NISHA", "BEGUM",
        # Male suffixes
        "KUMAR", "KUMARA", "LAL", "RAM", "RAMA", "PRASAD", "PRASADA",
        "NATH", "NATHA", "LAL", "DAS", "DASA",
        # Neutral
        "SHRI", "SRI", "DR", "PROF", "MR", "MRS", "SMT",
        # OCR noise / numeric artefacts
        "80", "80A",
    }
)

# Prefixes to strip from the START of any token
_PREFIX_STRIP = re.compile(
    r"^(shri|sva|sva\.|mo\.|mu\.|dr\.|dr|prof\.?|smt\.?|mr\.?|mrs\.?)\b",
    re.IGNORECASE,
)

# Match strings that are purely numeric / OCR garbage
_GARBAGE = re.compile(r"^[\d\W]+$")

# Remove trailing punctuation patterns from OCR
_OCR_CLEAN = re.compile(r"[.\-,;:\"\'`(){}\[\]<>|\\/@#%^&*=+~]+")

# Strings appended to Muslim female names after the main name (e.g. ".khatuna 80")
_KHATUN_SUFFIX = re.compile(r"\s*\.?khatun[a]?\s*\d*", re.IGNORECASE)
_NUMERIC_SUFFIX = re.compile(r"\s+\d+\s*[A-Za-z]?\s*$")


def _clean_token(tok: str) -> str:
    tok = _OCR_CLEAN.sub("", tok).strip()
    tok = _PREFIX_STRIP.sub("", tok).strip()
    return tok.upper()


def _tokenise(name: str) -> list[str]:
    """Clean and tokenise a raw name string."""
    name = _KHATUN_SUFFIX.sub(" Khatun", name)
    name = _NUMERIC_SUFFIX.sub("", name)
    tokens = [_clean_token(t) for t in name.split()]
    return [t for t in tokens if t and not _GARBAGE.match(t)]


def extract_surname_row(row: pd.Series) -> tuple[str, str, str]:
    """
    Extract (surname, confidence, source) from a single voter row.

    Parameters
    ----------
    row : must have 'full_name' and 'relation_name' columns

    Returns
    -------
    (surname, confidence, source)
    """
    name_tokens = _tokenise(str(row.get("full_name", "") or ""))
    rel_tokens = _tokenise(str(row.get("relation_name", "") or ""))

    # ── Primary extraction: last non-generic word of full name ──────────────
    primary: str | None = None
    for tok in reversed(name_tokens):
        if tok not in GENERIC_SUFFIXES:
            primary = tok
            break

    # If only generic tokens → try second-to-last
    if primary is None and len(name_tokens) >= 2:
        for tok in reversed(name_tokens[:-1]):
            if tok not in GENERIC_SUFFIXES:
                primary = tok
                break

    # ── Family signal: last non-generic word of relation_name ───────────────
    family_signal: str | None = None
    for tok in reversed(rel_tokens):
        if tok not in GENERIC_SUFFIXES:
            family_signal = tok
            break

    # ── Decision tree ────────────────────────────────────────────────────────
    if primary is None and family_signal is None:
        return ("UNKNOWN", "VERY_LOW", "none")

    if primary is not None and family_signal is not None:
        if primary == family_signal:
            return (primary, "HIGH", "name+relation")
        else:
            # Both present but different → prefer primary, note divergence
            return (primary, "MEDIUM", "name_primary")

    if primary is not None:
        confidence = "MEDIUM" if len(name_tokens) > 1 else "LOW"
        return (primary, confidence, "name_only")

    # Only family signal available
    return (family_signal, "VERY_LOW", "relation_only")


def extract_surnames(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'surname', 'surname_confidence', 'surname_source' columns to the voter roll.
    Returns a new DataFrame (does not modify in-place).
    """
    log.info("Extracting surnames from %d voter records…", len(df))

    results = df.apply(extract_surname_row, axis=1, result_type="expand")
    results.columns = ["surname", "surname_confidence", "surname_source"]

    df = df.copy()
    df["surname"] = results["surname"]
    df["surname_confidence"] = results["surname_confidence"]
    df["surname_source"] = results["surname_source"]

    # Log stats
    conf_dist = df["surname_confidence"].value_counts().to_dict()
    n_unknown = (df["surname"] == "UNKNOWN").sum()
    log.info(
        "Surname extraction done. Confidence dist: %s | UNKNOWN: %d (%.1f%%)",
        conf_dist,
        n_unknown,
        100 * n_unknown / len(df),
    )
    return df


# ── Optional: RapidFuzz normalisation against known caste-map keys ────────────

def normalise_surnames_against_map(
    df: pd.DataFrame,
    caste_map: dict,
    *,
    threshold: int = 85,
) -> pd.DataFrame:
    """
    For each extracted surname, fuzzy-match against known caste_map keys.
    If a match is found (score ≥ threshold), replace the surname with the
    canonical key from caste_map.

    Requires: rapidfuzz  (pip install rapidfuzz)
    """
    try:
        from rapidfuzz import process as rfprocess, fuzz
    except ImportError:
        log.warning("rapidfuzz not installed — skipping surname normalisation")
        return df

    known_keys = list(caste_map.keys())
    if not known_keys:
        return df

    unique_surnames = df["surname"].unique().tolist()
    normalised: dict[str, str] = {}

    for sname in unique_surnames:
        if sname in ("UNKNOWN", "NOTA"):
            normalised[sname] = sname
            continue
        if sname in caste_map:
            normalised[sname] = sname  # exact match
            continue
        result = rfprocess.extractOne(sname, known_keys, scorer=fuzz.ratio)
        if result and result[1] >= threshold:
            normalised[sname] = result[0]
        else:
            normalised[sname] = sname  # keep original

    df = df.copy()
    df["surname_normalised"] = df["surname"].map(normalised)
    changed = (df["surname"] != df["surname_normalised"]).sum()
    log.info("Surname normalisation: %d surnames fuzzy-corrected (threshold=%d%%)", changed, threshold)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    # Quick smoke-test
    test_data = pd.DataFrame(
        [
            {"full_name": "Shivama Shrivastava", "relation_name": "Prema Prakasha Shrivastava"},
            {"full_name": "Harirama", "relation_name": "Ramadata"},
            {"full_name": "Sunita Devi", "relation_name": "Ramachandra Yadava"},
            {"full_name": "Khushabu", "relation_name": "Sanoja"},
            {"full_name": "Samtosha Maurya", "relation_name": "Ramavrxa Maurya"},
            {"full_name": "Jubaida .khatuna 80", "relation_name": "Mu0 Phata Pa"},
            {"full_name": "Abdula Qadira", "relation_name": "Mohammada Umara"},
            {"full_name": "Aravinda Kumara Sharma", "relation_name": "Chandrika Prasada Sharma"},
            {"full_name": "Sachina Sharma", "relation_name": "Rajemdra Prasada"},
            {"full_name": "Na Da Akhtara", "relation_name": "Ajajurrahamana"},
        ]
    )
    result = extract_surnames(test_data)
    print(result[["full_name", "relation_name", "surname", "surname_confidence", "surname_source"]])
