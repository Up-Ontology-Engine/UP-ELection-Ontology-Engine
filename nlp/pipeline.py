"""
Full NLP pipeline orchestrator.
Stages: detect → clean → translate → extract (LLM) → fallback (rules) → geo-resolve.
"""
from __future__ import annotations
import re
import json
import logging
from typing import Optional
from .schemas import PipelineResult, ExtractionResult, GeoResolution
from .lang_detect import detect_language
from .bhashini import normalize_text
from .extractor import extract_from_normalized_text
from .rule_classifier import rule_based_extract
from .geo_resolver import GeoResolver

logger = logging.getLogger(__name__)

_geo_resolver: Optional[GeoResolver] = None


def _get_resolver() -> GeoResolver:
    global _geo_resolver
    if _geo_resolver is None:
        import os
        path = os.environ.get("ALIAS_INDEX_PATH", "data/seeds/gorakhpur_aliases.json")
        try:
            with open(path, encoding="utf-8") as f:
                _geo_resolver = GeoResolver(json.load(f))
        except FileNotFoundError:
            logger.warning(f"Alias index not found at {path}. Geo resolution disabled.")
            _geo_resolver = GeoResolver({})
    return _geo_resolver


def _clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"(.)\1{3,}", r"\1\1", text)   # "aaaa" → "aa"
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def process_one(
    text_raw: str,
    source_id: str,
    source_type: str,
    confidence_threshold: float = 0.6,
) -> PipelineResult:
    errors: list[str] = []

    # Stage 1 — language detection
    lang = detect_language(text_raw)

    # Stage 2 — clean
    text_clean = _clean_text(text_raw)
    if not text_clean:
        return PipelineResult(
            source_id=source_id, source_type=source_type, text_raw=text_raw,
            language_detected=lang,
            extraction=ExtractionResult(statements=[], is_political=False),
            extraction_method="skipped",
            processing_errors=["empty after cleaning"],
        )

    # Stage 3 — translate if Bhojpuri / mixed
    if lang in ("bho", "mix"):
        normalized, method = normalize_text(text_clean, detected_lang=lang)
    else:
        normalized, method = text_clean, "none"

    # Stage 4a — LLM extraction
    extraction = extract_from_normalized_text(normalized)
    extraction_method = "llm"

    # Stage 4b — rule fallback
    needs_fallback = (
        not extraction.statements
        or all(s.confidence < confidence_threshold for s in extraction.statements)
    )
    if needs_fallback:
        rule_result = rule_based_extract(normalized)
        if rule_result.statements:
            extraction = rule_result
            extraction_method = "rule_based"
        elif extraction.statements:
            extraction_method = "llm+low_conf"

    # Stage 5 — geo resolution
    geo: Optional[GeoResolution] = None
    resolver = _get_resolver()
    for stmt in extraction.statements:
        if stmt.location_mention:
            resolved = resolver.resolve(stmt.location_mention)
            if resolved:
                geo = resolved
                break

    # Stage 6 — final values (best statement by confidence)
    final_polarity = None
    final_issue = None
    final_entity = None
    final_confidence = 0.0

    if extraction.statements:
        best = max(extraction.statements, key=lambda s: s.confidence)
        final_polarity = best.polarity
        final_issue = best.issue.value if best.issue else None
        final_entity = best.entity
        final_confidence = best.confidence

    return PipelineResult(
        source_id=source_id,
        source_type=source_type,
        text_raw=text_raw,
        text_normalized_hi=normalized if normalized != text_clean else None,
        language_detected=lang,
        translation_method=method,
        extraction=extraction,
        extraction_method=extraction_method,
        geo_resolution=geo,
        final_polarity=final_polarity,
        final_issue=final_issue,
        final_entity=final_entity,
        final_confidence=final_confidence,
        processing_errors=errors,
    )


def process_batch(rows: list[dict], batch_size: int = 50) -> list[PipelineResult]:
    """rows: list of {text_raw, source_id, source_type}"""
    results = []
    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i: i + batch_size]
        for row in batch:
            try:
                r = process_one(
                    text_raw=row["text_raw"],
                    source_id=row["source_id"],
                    source_type=row["source_type"],
                )
                results.append(r)
            except Exception as e:
                logger.error(f"pipeline error source_id={row.get('source_id')}: {e}")
        logger.info(f"NLP: {min(i + batch_size, total)}/{total} processed")
    return results
