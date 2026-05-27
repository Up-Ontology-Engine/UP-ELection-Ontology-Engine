"""Unit tests for NLP pipeline components."""

from pipeline.nlp.lang_detect import detect_language
from pipeline.nlp.rule_classifier import rule_based_extract
from pipeline.nlp.schemas import ExtractionResult


def test_hindi_detected():
    assert detect_language("यह बहुत अच्छा काम है") == "hi"


def test_english_detected():
    assert detect_language("BJP is doing great work in Gorakhpur") == "en"


def test_bhojpuri_detected():
    text = "भाजपा के नेता बाड़े कहत हऊँ विकास होत बा"
    lang = detect_language(text)
    assert lang in ("bho", "mix")


def test_rule_classifier_bjp_negative():
    result = rule_based_extract("BJP ne pani ki samasya bilkul nahi suljhai, bahut bura hai")
    assert len(result.statements) > 0
    stmt = result.statements[0]
    assert stmt.entity == "BJP"
    assert stmt.polarity == -1


def test_rule_classifier_sp_positive():
    result = rule_based_extract("Akhilesh ne roads badiya kar diye, shukriya")
    assert len(result.statements) > 0
    assert result.statements[0].polarity == 1


def test_rule_classifier_no_political_content():
    result = rule_based_extract("aaj mausam bahut achha hai")
    assert result.is_political is False


def test_rule_classifier_water_issue():
    result = rule_based_extract("BJP sarkar mein bhi paani ki samasya khatam nahi hui")
    stmts = result.statements
    assert len(stmts) > 0
    water_stmts = [s for s in stmts if s.issue and s.issue.value == "water"]
    assert len(water_stmts) > 0


def test_extraction_result_schema():
    r = ExtractionResult(
        statements=[],
        primary_language="hi",
        is_political=False,
    )
    assert r.is_political is False
    assert r.statements == []


def test_bhashini_circuit_breaker():
    from unittest.mock import patch

    from pipeline.nlp.bhashini import _bhashini, _bhashini_breaker

    # Reset circuit breaker state
    _bhashini_breaker.state = "CLOSED"
    _bhashini_breaker.failure_count = 0

    # Mock the underlying call to fail
    with patch("nlp.bhashini._bhashini_call", side_effect=Exception("API Error")):
        # Call 1
        val, method = _bhashini("test text", "bho")
        assert val == "test text"
        assert method == "failed"
        assert _bhashini_breaker.state == "CLOSED"

        # Call 2
        _bhashini("test text", "bho")
        assert _bhashini_breaker.state == "CLOSED"

        # Call 3 (triggers trip)
        _bhashini("test text", "bho")
        assert _bhashini_breaker.state == "OPEN"

    # Subsequent call when OPEN should not even try to call _bhashini_call
    with patch("nlp.bhashini._bhashini_call") as mock_call:
        val, method = _bhashini("test text", "bho")
        assert val == "test text"
        assert method == "circuit_breaker_open"
        mock_call.assert_not_called()

    # Reset again to CLOSED for other tests
    _bhashini_breaker.state = "CLOSED"
    _bhashini_breaker.failure_count = 0
