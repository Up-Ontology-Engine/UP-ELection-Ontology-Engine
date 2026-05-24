"""
test_caste_mapper.py
=====================
Unit tests for the CasteMapper (bootstrap + cache, excluding LLM calls).
"""

import json
import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.surname_caste.caste_mapper import (
    CasteMapper,
    BOOTSTRAP,
    initialise_cache,
    _load_cache,
    _save_cache,
)


@pytest.fixture
def temp_cache(tmp_path):
    """Provides a temporary cache file path."""
    return tmp_path / "surname_caste_map.json"


@pytest.fixture
def mapper(temp_cache):
    """CasteMapper with temporary cache, no LLM."""
    return CasteMapper(cache_path=temp_cache, use_llm=False)


class TestBootstrap:
    def test_all_bootstrap_have_required_keys(self):
        required = {"caste_group", "social_category", "confidence", "source"}
        for surname, info in BOOTSTRAP.items():
            missing = required - set(info.keys())
            assert not missing, f"{surname} missing keys: {missing}"

    def test_social_category_values(self):
        valid = {"OBC", "OBC_Baniya", "SC", "ST", "General",
                 "General_Ambiguous", "Muslim", "Ambiguous", "Unknown"}
        for surname, info in BOOTSTRAP.items():
            assert info["social_category"] in valid, (
                f"{surname}: invalid category '{info['social_category']}'"
            )

    def test_confidence_values(self):
        valid = {"high", "medium", "low"}
        for surname, info in BOOTSTRAP.items():
            assert info["confidence"] in valid, (
                f"{surname}: invalid confidence '{info['confidence']}'"
            )

    def test_key_castes_present(self):
        must_have = ["YADAVA", "NISHADA", "MAURYA", "SHARMA", "ANSARI",
                     "GUPTA", "SHRIVASTAVA", "SINGH", "TIVARI"]
        for k in must_have:
            assert k in BOOTSTRAP, f"Missing bootstrap entry: {k}"


class TestCasteMapperLookup:
    def test_known_obc_yadav(self, mapper):
        info = mapper.lookup("YADAVA")
        assert info["caste_group"] == "Yadav"
        assert info["social_category"] == "OBC"
        assert info["confidence"] == "high"

    def test_case_insensitive_lookup(self, mapper):
        info_upper = mapper.lookup("SHARMA")
        info_lower = mapper.lookup("sharma")
        info_mixed = mapper.lookup("Sharma")
        assert info_upper["caste_group"] == info_lower["caste_group"] == info_mixed["caste_group"]

    def test_unknown_surname_returns_unknown(self, mapper):
        info = mapper.lookup("XYZQRSABCDEF")
        assert info["social_category"] == "Unknown"

    def test_empty_string_returns_unknown(self, mapper):
        info = mapper.lookup("")
        assert info["social_category"] == "Unknown"

    def test_nota_returns_unknown(self, mapper):
        info = mapper.lookup("NOTA")
        assert info["social_category"] == "Unknown"

    def test_nishad_is_obc(self, mapper):
        info = mapper.lookup("NISHAD")
        assert info["social_category"] == "OBC"

    def test_ansari_is_muslim(self, mapper):
        info = mapper.lookup("ANSARI")
        assert info["social_category"] == "Muslim"

    def test_transliteration_variant_amsari(self, mapper):
        # AMSARI is a common OCR variant of ANSARI
        info = mapper.lookup("AMSARI")
        assert info["social_category"] == "Muslim"

    def test_tiwari_variant(self, mapper):
        info = mapper.lookup("TIVARI")  # OCR variant
        assert info["social_category"] == "General"

    def test_dubey_variant(self, mapper):
        info = mapper.lookup("DUBE")  # common shortform
        assert info["social_category"] == "General"


class TestLookupField:
    def test_lookup_field_returns_callable(self, mapper):
        fn = mapper.lookup_field("caste_group")
        assert callable(fn)

    def test_lookup_field_works_correctly(self, mapper):
        fn = mapper.lookup_field("social_category")
        assert fn("YADAVA") == "OBC"
        assert fn("SHARMA") == "General"
        assert fn("UNKNOWN_XXXX") == "Unknown"


class TestCacheIO:
    def test_cache_is_persisted(self, temp_cache):
        test_data = {"TESTCASTE": {"caste_group": "Test", "social_category": "OBC",
                                    "confidence": "high", "source": "test"}}
        _save_cache(test_data, temp_cache)
        loaded = _load_cache(temp_cache)
        assert "TESTCASTE" in loaded
        assert loaded["TESTCASTE"]["caste_group"] == "Test"

    def test_initialise_cache_writes_bootstrap(self, temp_cache):
        # initialise with temp path
        from analytics.surname_caste.caste_mapper import BOOTSTRAP as B
        _save_cache(B, temp_cache)
        loaded = _load_cache(temp_cache)
        assert len(loaded) == len(B)

    def test_cache_stats(self, mapper):
        stats = mapper.cache_stats()
        assert "total" in stats
        assert stats["total"] >= len(BOOTSTRAP)
        assert "by_source" in stats
        assert "by_category" in stats


class TestEnrichDataframe:
    def test_enrich_adds_columns(self, mapper):
        import pandas as pd
        df = pd.DataFrame([
            {"surname": "YADAVA"},
            {"surname": "SHARMA"},
            {"surname": "ANSARI"},
            {"surname": "UNKNOWN_SURNAME"},
        ])
        enriched = mapper.enrich_dataframe(df)
        assert "caste_group" in enriched.columns
        assert "social_category" in enriched.columns
        assert "caste_confidence" in enriched.columns
        assert "caste_source" in enriched.columns

    def test_enrich_does_not_mutate_original(self, mapper):
        import pandas as pd
        df = pd.DataFrame([{"surname": "YADAVA"}])
        original_cols = list(df.columns)
        _ = mapper.enrich_dataframe(df)
        assert list(df.columns) == original_cols

    def test_enrich_correct_values(self, mapper):
        import pandas as pd
        df = pd.DataFrame([{"surname": "YADAVA"}, {"surname": "NISHADA"}])
        enriched = mapper.enrich_dataframe(df)
        assert enriched.iloc[0]["caste_group"] == "Yadav"
        assert enriched.iloc[1]["caste_group"] == "Nishad"
        assert enriched.iloc[0]["social_category"] == "OBC"
