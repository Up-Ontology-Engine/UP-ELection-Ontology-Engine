"""Bhashini translation with IndicTrans2 fallback."""
import os, requests, logging
logger = logging.getLogger(__name__)

PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


def _bhashini(text: str, src: str, tgt: str = "hi") -> tuple[str, str]:
    headers = {
        "userID": os.environ.get("BHASHINI_USER_ID", ""),
        "ulcaApiKey": os.environ.get("BHASHINI_API_KEY", ""),
        "Content-Type": "application/json",
    }
    payload = {
        "pipelineTasks": [{"taskType": "translation",
                           "config": {"language": {"sourceLanguage": src, "targetLanguage": tgt}}}],
        "inputData": {"input": [{"source": text}], "audio": []},
    }
    try:
        r = requests.post(PIPELINE_URL, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        translated = r.json()["pipelineResponse"][0]["output"][0]["target"]
        return translated, "bhashini"
    except Exception as e:
        logger.warning(f"Bhashini failed: {e}")
        return text, "failed"


def _indictrans2(text: str, src: str) -> tuple[str, str]:
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        model_id = "ai4bharat/indictrans2-indic-indic-dist-200M"
        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
        src_lang = "bho_Deva" if src == "bho" else "hin_Deva"
        inputs = tok(text, return_tensors="pt", src_lang=src_lang)
        out = mdl.generate(**inputs,
                           forced_bos_token_id=tok.lang_code_to_id["hin_Deva"],
                           max_length=512)
        return tok.decode(out[0], skip_special_tokens=True), "indictrans2"
    except Exception as e:
        logger.error(f"IndicTrans2 failed: {e}")
        return text, "none"


def normalize_text(text: str, detected_lang: str) -> tuple[str, str]:
    """Returns (normalized_hindi_text, method_used)."""
    if detected_lang in ("hi", "en", "unknown"):
        return text, "none"
    translated, method = _bhashini(text, src=detected_lang)
    if method == "bhashini":
        return translated, method
    return _indictrans2(text, src=detected_lang)
