"""Unit tests for geo resolution."""
import pytest
from pipeline.nlp.geo_resolver import GeoResolver

ALIAS_DATA = {
    "Deoria Naka": {"id": "GKP_U_045", "type": "booth"},
    "Civil Lines": {"id": "GKP_U_001", "type": "booth"},
    "Gorakhpur Urban": {"id": "GKP_URBAN", "type": "ac"},
}


def test_exact_match():
    r = GeoResolver(ALIAS_DATA)
    result = r.resolve("Deoria Naka")
    assert result is not None
    assert result.mapped_booth_id == "GKP_U_045"
    assert result.geo_confidence >= 0.9


def test_fuzzy_match():
    r = GeoResolver(ALIAS_DATA)
    result = r.resolve("Deoria Naaka")   # typo
    assert result is not None
    assert result.mapped_booth_id == "GKP_U_045"


def test_hindi_location():
    alias = dict(ALIAS_DATA)
    alias["देवरिया नाका"] = {"id": "GKP_U_045", "type": "booth"}
    r = GeoResolver(alias)
    result = r.resolve("देवरिया नाका")
    assert result is not None
    assert result.mapped_booth_id == "GKP_U_045"


def test_no_match_returns_ac_fallback():
    r = GeoResolver(ALIAS_DATA)
    result = r.resolve("Mars Colony")
    assert result is not None
    assert result.mapped_booth_id is None
    assert result.geo_confidence <= 0.5


def test_empty_input():
    r = GeoResolver(ALIAS_DATA)
    result = r.resolve("")
    assert result is None


def test_empty_alias_index():
    r = GeoResolver({})
    result = r.resolve("Civil Lines")
    assert result is None
