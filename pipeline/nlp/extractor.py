"""Gemini LLM extraction with structured JSON output via google.genai SDK."""

import json as _json
import logging
import os
import re

from google import genai
from google.genai import types

from .schemas import ExtractionResult

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


def _extract_via_sarvam(compressed_text: str) -> ExtractionResult:
    sarvam_key = os.environ.get("SARVAM_API_KEY")
    if not sarvam_key:
        raise ValueError("Neither GOOGLE_API_KEY nor SARVAM_API_KEY is configured.")

    import requests

    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {sarvam_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.environ.get("SARVAM_REASONING_MODEL", "sarvam-30b"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract sentiment:\n\n{compressed_text}"},
        ],
        "temperature": 0.0,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    resp_data = r.json()
    raw = resp_data["choices"][0]["message"]["content"].strip()

    # Strip markdown code blocks if present
    if raw.startswith("```"):
        match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

    if not raw:
        return ExtractionResult(statements=[], is_political=True)

    # Robustify JSON parsing (remove trailing commas)
    raw_cleaned = re.sub(r",\s*([\]}])", r"\1", raw)
    data = _json.loads(raw_cleaned)

    # Sanitize statements
    valid_types = {"party", "candidate", "scheme", "issue", "govt"}
    for stmt in data.get("statements", []):
        stmt.setdefault("language", "hi")
        if "entity_type" in stmt:
            et = str(stmt["entity_type"]).lower().strip()
            if et not in valid_types:
                if et in ("person", "leader", "politician", "candidate"):
                    stmt["entity_type"] = "candidate"
                elif et in ("party", "political party"):
                    stmt["entity_type"] = "party"
                elif et in ("scheme", "govt_scheme"):
                    stmt["entity_type"] = "scheme"
                elif et in ("issue", "topic", "problem"):
                    stmt["entity_type"] = "issue"
                elif et in ("govt", "government"):
                    stmt["entity_type"] = "govt"
                else:
                    stmt["entity_type"] = "candidate"  # default safe fallback
        else:
            stmt["entity_type"] = "party"

    return ExtractionResult.model_validate(data)


SYSTEM_PROMPT = """\
You are a political sentiment extractor for Uttar Pradesh elections, India.

STRICT RULES:
1. Output ONLY valid JSON — no prose, no markdown, no explanation.
2. Parties to recognise: BJP, SP, BSP, Congress, AAP, RLD. Use exact English spelling.
3. Issues — ONLY these codes: water, roads, electricity, jobs, women_safety, price_rise,
   farmer, sugarcane, health, education, corruption, law_order, other
4. polarity: 1=positive/praise, -1=negative/criticism, 0=neutral/factual
5. confidence: 0.0–1.0. Under 0.5 for ambiguous/sarcastic text.
6. evidence: copy 1–4 words from original text that justify polarity.
7. location_mention: any ward, mohalla, village, chowk, school, area name. Raw text.
8. One SentimentStatement per distinct entity+issue combination.
9. If text is irrelevant to politics, return is_political=false, empty statements.
10. Sarcasm: heavy praise in political Hindi often = sarcasm → polarity=-1, confidence=0.6.
11. language field: one of hi | bho | en | mix

GORAKHPUR CONTEXT:
- "sarkar" without qualifier = BJP/UP state government
- "netaji", "cycle wale" = SP / Akhilesh Yadav
- "behan ji", "haathi" = BSP / Mayawati
- "yogi", "maharaj ji" = CM Yogi Adityanath (BJP)
- "double engine" = BJP both at state + centre
- Local Gorakhpur issues: sugarcane mill payments (गन्ना भुगतान), flooding (बाढ़),
  CM's home district so expectations are very high.

FEW-SHOT EXAMPLES OF SARCASM:
- Input text: "BJP ne toh paani ki samasya kya khoob suljhai hai, 4 din se ek boond nahi aayi!"
  JSON Output:
  {
    "is_political": true,
    "statements": [
      {
        "entity": "BJP",
        "entity_type": "party",
        "issue": "water",
        "polarity": -1,
        "confidence": 0.8,
        "evidence": "kya khoob suljhai",
        "location_mention": null,
        "language": "hi"
      }
    ]
  }
- Input text: "गजबे सड़क बनल बा महाराज, साइकिल हिचकोला खाके टूट गइल!"
  JSON Output:
  {
    "is_political": true,
    "statements": [
      {
        "entity": "BJP",
        "entity_type": "party",
        "issue": "roads",
        "polarity": -1,
        "confidence": 0.9,
        "evidence": "हिचकोला खाके",
        "location_mention": null,
        "language": "bho"
      }
    ]
  }
"""

_GEMINI_MODEL = "gemini-2.5-flash"

POLITICAL_KEYWORDS = {
    "bjp",
    "sp",
    "bsp",
    "congress",
    "aap",
    "rld",
    "yogi",
    "modi",
    "akhilesh",
    "mayawati",
    "sarkar",
    "chunav",
    "neta",
    "voter",
    "booth",
    "ganna",
    "cycle",
    "kamal",
    "hathi",
    "development",
    "kaam",
    "water",
    "road",
    "bijli",
    "jobs",
    "safety",
    "politic",
    "election",
    "candidate",
    "गन्ना",
    "चुनाव",
    "योगी",
    "मोदी",
    "अखिलेश",
    "मायावती",
    "सरकार",
    "काम",
    "सड़क",
    "पानी",
    "नौकरी",
    "रोजगार",
    "बिजली",
    "सुरक्षा",
    "भ्रष्टाचार",
    "कानून",
    "पार्टी",
}


def compress_text(text: str) -> str:
    """Pre-extraction text compression: removes HTML tags and keeps only sentences with political entities/keywords if text is long."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()

    # If the text is short, keep as is
    if len(text) <= 1200:
        return text

    # Split into sentences using punctuation markers
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    if len(sentences) <= 3:
        return text

    keep_indices = set()
    for idx, sentence in enumerate(sentences):
        words = re.findall(r"\b\w+\b", sentence.lower())
        has_keyword = any(w in POLITICAL_KEYWORDS for w in words)
        if not has_keyword:
            has_keyword = any(kw in sentence.lower() for kw in POLITICAL_KEYWORDS)

        if has_keyword:
            keep_indices.add(idx)
            if idx > 0:
                keep_indices.add(idx - 1)
            if idx < len(sentences) - 1:
                keep_indices.add(idx + 1)

    if not keep_indices:
        return " ".join(sentences[:3]) + "..."

    compressed_sentences = []
    last_idx = -1
    for idx in sorted(keep_indices):
        if last_idx != -1 and idx > last_idx + 1:
            compressed_sentences.append("[...]")
        compressed_sentences.append(sentences[idx])
        last_idx = idx

    return " ".join(compressed_sentences)


def extract_from_normalized_text(text: str) -> ExtractionResult:
    if not text or len(text.strip()) < 5:
        return ExtractionResult(statements=[], is_political=False)

    # Compress text to optimize context window and tokens
    compressed = compress_text(text)

    # Check for keys
    google_key = os.environ.get("GOOGLE_API_KEY")

    if not google_key:
        # Fall back to Sarvam
        try:
            return _extract_via_sarvam(compressed)
        except Exception as e:
            logger.error("Sarvam extraction failed: %s", e)
            return ExtractionResult(statements=[], is_political=True)

    try:
        resp = _get_client().models.generate_content(
            model=_GEMINI_MODEL,
            contents=f"Extract sentiment:\n\n{compressed}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        raw = (resp.text or "").strip()
        if not raw:
            return ExtractionResult(statements=[], is_political=True)
        data = _json.loads(raw)
        for stmt in data.get("statements", []):
            stmt.setdefault("entity_type", "party")
            stmt.setdefault("language", "hi")
        return ExtractionResult.model_validate(data)
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        # Try falling back to Sarvam if LLM failed and Sarvam key exists
        if os.environ.get("SARVAM_API_KEY"):
            try:
                logger.info("Retrying extraction using Sarvam fallback...")
                return _extract_via_sarvam(compressed)
            except Exception as se:
                logger.error("Sarvam extraction fallback also failed: %s", se)
        return ExtractionResult(statements=[], is_political=True)
