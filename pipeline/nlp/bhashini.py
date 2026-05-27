# ruff: noqa: E402, F401, F404, F405, F841, F811
"""Bhashini translation with IndicTrans2 and LLM fallback."""

import logging
import os

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, IOError)),
    reraise=True,
)
def _bhashini_call(text: str, src: str, tgt: str = "hi") -> str:
    headers = {
        "userID": os.environ.get("BHASHINI_USER_ID", ""),
        "ulcaApiKey": os.environ.get("BHASHINI_API_KEY", ""),
        "Content-Type": "application/json",
    }
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {"language": {"sourceLanguage": src, "targetLanguage": tgt}},
            }
        ],
        "inputData": {"input": [{"source": text}], "audio": []},
    }
    r = requests.post(PIPELINE_URL, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()["pipelineResponse"][0]["output"][0]["target"]


import time


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_state_change = 0.0

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.warning(
                f"Bhashini Circuit Breaker TRIPPED (OPEN) due to {self.failure_count} consecutive failures."
            )

    def can_execute(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_time:
                self.state = "HALF-OPEN"
                logger.info("Bhashini Circuit Breaker is now HALF-OPEN; testing endpoint.")
                return True
            return False
        return True


_bhashini_breaker = CircuitBreaker(failure_threshold=3, recovery_time=60)


def _bhashini(text: str, src: str, tgt: str = "hi") -> tuple[str, str]:
    if not _bhashini_breaker.can_execute():
        logger.warning("Bhashini circuit breaker is OPEN; falling back to alternative models.")
        return text, "circuit_breaker_open"
    try:
        translated = _bhashini_call(text, src, tgt)
        _bhashini_breaker.record_success()
        return translated, "bhashini"
    except Exception as e:
        _bhashini_breaker.record_failure()
        logger.warning(f"Bhashini failed after retries: {e}")
        return text, "failed"


def _indictrans2(text: str, src: str) -> tuple[str, str]:
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        model_id = "ai4bharat/indictrans2-indic-indic-dist-200M"
        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
        src_lang = "bho_Deva" if src == "bho" else "hin_Deva"
        inputs = tok(text, return_tensors="pt", src_lang=src_lang)
        out = mdl.generate(
            **inputs, forced_bos_token_id=tok.lang_code_to_id["hin_Deva"], max_length=512
        )
        return tok.decode(out[0], skip_special_tokens=True), "indictrans2"
    except Exception as e:
        logger.debug(f"IndicTrans2 fallback not available/failed: {e}")
        return text, "failed"


def _translate_via_llm(text: str, src: str, tgt: str = "hi") -> tuple[str, str]:
    # Try Sarvam first
    sarvam_key = os.environ.get("SARVAM_API_KEY")
    if sarvam_key:
        try:
            url = "https://api.sarvam.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {sarvam_key}", "Content-Type": "application/json"}
            prompt = f"Translate the following text from ISO 639-1 language code '{src}' to '{tgt}' (Hindi). Output ONLY the translated text, do not add any explanation or preamble.\n\nText: {text}"
            payload = {
                "model": os.environ.get("SARVAM_REASONING_MODEL", "sarvam-m"),
                "messages": [
                    {"role": "system", "content": "You are a precise translator."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            r.raise_for_status()
            translated = r.json()["choices"][0]["message"]["content"].strip()
            if translated:
                return translated, "sarvam_translation"
        except Exception as e:
            logger.warning(f"Sarvam translation fallback failed: {e}")

    # Try Gemini next
    gemini_key = os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_key)
            prompt = f"Translate the following text from language '{src}' to '{tgt}' (Hindi). Output ONLY the translated text, do not add any explanation or preamble.\n\nText: {text}"
            resp = client.models.generate_content(
                model=os.environ.get("GOOGLE_REASONING_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a precise translator.",
                    temperature=0.0,
                    max_output_tokens=1024,
                ),
            )
            translated = (resp.text or "").strip()
            if translated:
                return translated, "gemini_translation"
        except Exception as e:
            logger.warning(f"Gemini translation fallback failed: {e}")

    return text, "failed"


def normalize_text(text: str, detected_lang: str) -> tuple[str, str]:
    """Returns (normalized_hindi_text, method_used)."""
    if detected_lang in ("hi", "en", "unknown"):
        return text, "none"
    translated, method = _bhashini(text, src=detected_lang)
    if method == "bhashini":
        return translated, method

    # Fallback 1: Local IndicTrans2
    translated_it2, method_it2 = _indictrans2(text, src=detected_lang)
    if method_it2 == "indictrans2":
        return translated_it2, method_it2

    # Fallback 2: LLM fallback (Sarvam / Gemini)
    translated_llm, method_llm = _translate_via_llm(text, src=detected_lang)
    if method_llm != "failed":
        return translated_llm, method_llm

    return text, "failed"
