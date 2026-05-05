"""Unit tests for NLP pipeline components."""
import pytest
from nlp.lang_detect import detect_language
from nlp.rule_classifier import rule_based_extract
from nlp.schemas import ExtractionResult


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
