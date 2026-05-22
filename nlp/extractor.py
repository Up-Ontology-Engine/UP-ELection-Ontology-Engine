"""Gemini LLM extraction with structured JSON output via google.genai SDK."""
import os, logging, json as _json
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
"""

_GEMINI_MODEL = "gemini-2.5-flash"


def extract_from_normalized_text(text: str) -> ExtractionResult:
    if not text or len(text.strip()) < 5:
        return ExtractionResult(statements=[], is_political=False)
    try:
        resp = _get_client().models.generate_content(
            model=_GEMINI_MODEL,
            contents=f"Extract sentiment:\n\n{text}",
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
        return ExtractionResult(statements=[], is_political=True)
