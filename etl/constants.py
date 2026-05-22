"""
Shared constants for ETL, ingestion, and NLP layers.

Single source of truth for party normalization, AC name mapping,
and block→AC mapping so all scripts agree on the same canonical IDs.
"""
from __future__ import annotations

# ── Party normalization ───────────────────────────────────────────────────────
# Maps any spelling of a party name (English or Hindi, formal or colloquial)
# → canonical 2-8 char abbreviation used as party_id in Postgres and Neo4j.

PARTY_NORM: dict[str, str] = {
    # BJP
    "BHARATIYA JANATA PARTY": "BJP",
    "BHARATIYA JANATA PARTY (BJP)": "BJP",
    "B.J.P": "BJP",
    "B.J.P.": "BJP",
    "BJP": "BJP",
    "भारतीय जनता पार्टी": "BJP",
    "भाजपा": "BJP",

    # Samajwadi Party
    "SAMAJWADI PARTY": "SP",
    "SAMAJWADI PARTY (SP)": "SP",
    "SP": "SP",
    "समाजवादी पार्टी": "SP",
    "समाजवादी": "SP",
    "सपा": "SP",

    # Bahujan Samaj Party
    "BAHUJAN SAMAJ PARTY": "BSP",
    "BAHUJAN SAMAJ PARTY (BSP)": "BSP",
    "B.S.P": "BSP",
    "B.S.P.": "BSP",
    "BSP": "BSP",
    "बहुजन समाज पार्टी": "BSP",
    "बसपा": "BSP",

    # Indian National Congress
    "INDIAN NATIONAL CONGRESS": "INC",
    "INDIAN NATIONAL CONGRESS (INC)": "INC",
    "CONGRESS": "INC",
    "INC": "INC",
    "भारतीय राष्ट्रीय कांग्रेस": "INC",
    "कांग्रेस": "INC",

    # Aam Aadmi Party
    "AAM AADMI PARTY": "AAP",
    "AAM AADMI PARTY (AAP)": "AAP",
    "AAP": "AAP",
    "आम आदमी पार्टी": "AAP",

    # AIMIM
    "ALL INDIA MAJLIS-E-ITTEHADUL MUSLIMEEN": "AIMIM",
    "AIMIM": "AIMIM",
    "OWAISI": "AIMIM",

    # Apna Dal
    "APNA DAL": "AD",
    "AD": "AD",
    "APNA DAL (S)": "AD",

    # Nishad Party
    "NISHAD PARTY": "NISHAD",
    "NISHAD": "NISHAD",

    # NOTA
    "NOTA": "NOTA",
    "NONE OF THE ABOVE": "NOTA",

    # Independent candidates
    "INDEPENDENT": "IND",
    "INDPENDENT":  "IND",   # common misspelling
    "INDEPENDENT CANDIDATE": "IND",
    "IND": "IND",

    # Common BJP spellings / OCR variants
    "BHARATIYA JANTA PARTY": "BJP",   # missing 'A' in JANATA — very common
    "BHARATIYA JANATA PARTY": "BJP",
    "B J P": "BJP",
    "B.J.P": "BJP",
    "B.J.P.": "BJP",

    # Common BSP OCR artifacts (space-separated)
    "B A S P": "BSP",
    "B.S.P": "BSP",
    "B.S.P.": "BSP",
    "BAHUJAN SAMAJ PARTY": "BSP",

    # Common SP / AAP OCR artifacts
    "A A P": "AAP",
    "A.A.P": "AAP",
    "A.A.P.": "AAP",

    # PSP Lohia variants
    "PRAGATISHIL SAMAJWADI PARTY (LOHIA)": "PSP(L)",
    "PSP (LOHIYA)": "PSP(L)",
    "P.S.P LOHIYA": "PSP(L)",
    "PSP LOHIYA": "PSP(L)",

    # CPI
    "COMMUNIST PARTY OF INDIA": "CPI",
    "C.P.I": "CPI",
    "CPI": "CPI",

    # Suheldev Bharatiya Samaj Party
    "SUHELDEV BHARATIYA SAMAJ PARTY": "SBSP",

    # RLD
    "RASHTRIYA LOK DAL": "RLD",
    "RLD": "RLD",

    # Vikassheel Insaan Party
    "VIKASSSHEEL INSAAN PARTY": "VIP",
    "VIKASSHEEL INSAAN PARTY": "VIP",
}


def normalise_party(raw: str, fallback: str | None = None) -> str:
    """
    Normalize a raw party name string to its canonical abbreviation.

    Tries exact lookup first, then substring scan, then regex extraction
    from parentheses (e.g. "Bharatiya Janata Party (BJP)" → "BJP").
    """
    import re
    raw = raw.strip()
    upper = raw.upper()

    # Exact lookup
    if upper in PARTY_NORM:
        return PARTY_NORM[upper]

    # Substring scan (longest-key-first to avoid "SP" matching "BSP")
    for key in sorted(PARTY_NORM, key=len, reverse=True):
        if key in upper:
            return PARTY_NORM[key]

    # Parentheses extraction: "Bharatiya Janata Party (BJP)"
    m = re.search(r"\(([A-Z][A-Za-z.]{1,10})\)\s*$", raw)
    if m:
        abbrev = m.group(1).replace(".", "").strip()
        if 2 <= len(abbrev) <= 8 and abbrev.isupper():
            return abbrev

    if fallback is not None:
        return fallback
    return raw.split()[0].upper()[:10]


# ── Block → AC ID mapping ─────────────────────────────────────────────────────
# All 20 Gorakhpur blocks cross-referenced to their assembly constituency.
# Block names must match exactly as they appear in eGramSwaraj JSON.

BLOCK_TO_AC: dict[str, str] = {
    "Khorabar":      "GKP_322",  # Gorakhpur Urban
    "Sardarnagar":   "GKP_322",  # Gorakhpur Urban
    "Chargawan":     "GKP_322",  # Gorakhpur Urban
    "Campierganj":   "GKP_320",  # Caimpiyarganj
    "Pipraich":      "GKP_321",  # Pipraich
    "Piprauli":      "GKP_321",  # Pipraich (split)
    "Bhathat":       "GKP_321",  # Pipraich (split)
    "Sahjanawa":     "GKP_324",  # Sahajanwa
    "Bharohiya":     "GKP_324",  # Sahajanwa (split)
    "Khajni":        "GKP_325",  # Khajani
    "Barhalganj":    "GKP_326",  # Chauri-Chaura
    "Brahmpur":      "GKP_326",  # Chauri-Chaura (split)
    "Bansgaon":      "GKP_327",  # Bansgaon
    "Uruwa":         "GKP_327",  # Bansgaon (split)
    "Belghat":       "GKP_328",  # Chillupar
    "Jangal Kaudia": "GKP_328",  # Chillupar (split)
    "Gagaha":        "GKP_323",  # Gorakhpur Rural
    "Gola":          "GKP_323",  # Gorakhpur Rural
    "Kauri Ram":     "GKP_323",  # Gorakhpur Rural
    "Pali":          "GKP_323",  # Gorakhpur Rural
}


# ── AC display name → ac_id ───────────────────────────────────────────────────
# Used when parsing affidavit / election source data where AC names appear
# in various formats. Resolves all known spellings to the canonical ac_id.

AC_NAME_MAP: dict[str, str] = {
    "Gorakhpur Urban (322)":  "GKP_322",
    "Gorakhpur Urban":        "GKP_322",
    "Gorakhpur (322)":        "GKP_322",
    "Gorakhpur":              "GKP_322",   # ambiguous → default Urban
    "Gorakhpur Rural (323)":  "GKP_323",
    "Gorakhpur Rural":        "GKP_323",
    "Caimpiyarganj (320)":    "GKP_320",
    "Campierganj (320)":      "GKP_320",
    "Campierganj":            "GKP_320",
    "Pipraich (321)":         "GKP_321",
    "Pipraich":               "GKP_321",
    "Sahajanwa (324)":        "GKP_324",
    "Sahjanawa (324)":        "GKP_324",
    "Sahajanwa":              "GKP_324",
    "Khajani (325)":          "GKP_325",
    "Khajni (325)":           "GKP_325",
    "Khajani":                "GKP_325",
    "Chauri-Chaura (326)":    "GKP_326",
    "Chaurichaura (326)":     "GKP_326",
    "Chauri-Chaura":          "GKP_326",
    "Bansgaon (327)":         "GKP_327",
    "Bansgaon":               "GKP_327",
    "Chillupar (328)":        "GKP_328",
    "Chilllupar (328)":       "GKP_328",  # common misspelling
    "Chillupar":              "GKP_328",
    "Gorakhpur (64)":         "GKP_LS64", # Lok Sabha
    "Gorakhpur LS":           "GKP_LS64",
}
