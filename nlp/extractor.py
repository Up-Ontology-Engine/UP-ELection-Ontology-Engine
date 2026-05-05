"""Instructor + Groq LLM extraction with constrained JSON output."""
import os, logging, instructor
from groq import Groq
from .schemas import ExtractionResult

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = instructor.from_groq(
            Groq(api_key=os.environ["GROQ_API_KEY"]),
            mode=instructor.Mode.JSON,
        )
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

GORAKHPUR CONTEXT:
- "sarkar" without qualifier = BJP/UP state government
- "netaji", "cycle wale" = SP / Akhilesh Yadav
- "behan ji", "haathi" = BSP / Mayawati
- "yogi", "maharaj ji" = CM Yogi Adityanath (BJP)
- "double engine" = BJP both at state + centre
- Local Gorakhpur issues: sugarcane mill payments (गन्ना भुगतान), flooding (बाढ़),
  CM's home district so expectations are very high.
"""


def extract_from_normalized_text(text: str) -> ExtractionResult:
    if not text or len(text.strip()) < 5:
        return ExtractionResult(statements=[], is_political=False)
    try:
        return _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=ExtractionResult,
            max_retries=2,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract sentiment:\n\n{text}"},
            ],
        )
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return ExtractionResult(statements=[], is_political=True)
