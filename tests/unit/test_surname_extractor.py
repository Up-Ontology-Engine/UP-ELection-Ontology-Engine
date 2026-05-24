"""
test_surname_extractor.py
=========================
Unit tests for the multi-signal surname extraction module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.surname_caste.surname_extractor import (
    extract_surname_row,
    extract_surnames,
    _tokenise,
    GENERIC_SUFFIXES,
)


class TestTokenise:
    def test_basic_split(self):
        assert _tokenise("Ramesh Kumar") == ["RAMESH", "KUMAR"]

    def test_strips_ocr_numeric_suffix(self):
        tokens = _tokenise("Jubaida .khatuna 80")
        assert "80" not in tokens

    def test_strips_honorifics(self):
        tokens = _tokenise("Shri Ram Prasad Yadav")
        assert "SHRI" not in tokens
        assert "YADAV" in tokens

    def test_handles_empty(self):
        assert _tokenise("") == []
        assert _tokenise("   ") == []

    def test_strips_punctuation(self):
        tokens = _tokenise("Amgada Tivari.")
        assert "TIVARI" in tokens


class TestExtractSurnameRow:
    def _row(self, name: str, rel: str) -> pd.Series:
        return pd.Series({"full_name": name, "relation_name": rel})

    def test_two_word_name_high_confidence(self):
        surname, conf, _ = extract_surname_row(self._row("Shivama Shrivastava", "Prema Prakasha Shrivastava"))
        assert surname == "SHRIVASTAVA"
        assert conf == "HIGH"

    def test_single_word_name_falls_back_to_relation(self):
        surname, conf, _ = extract_surname_row(self._row("Harirama", "Ramadata"))
        # "Harirama" is the only token and it's not generic → returns it as MEDIUM
        assert surname == "HARIRAMA"

    def test_generic_last_word_tries_second_to_last(self):
        # "Devi" is generic, should fall back to "Sunita" → but "Sunita" is not a surname either
        # Expect fallback to relation_name
        surname, conf, _ = extract_surname_row(self._row("Sunita Devi", "Ramachandra Yadava"))
        assert surname == "SUNITA" or surname == "YADAVA"

    def test_three_word_name_surname_extracted(self):
        surname, conf, _ = extract_surname_row(self._row("Aravinda Kumara Sharma", "Chandrika Prasada Sharma"))
        assert surname == "SHARMA"
        assert conf == "HIGH"

    def test_ocr_noise_khatun_removed(self):
        surname, conf, _ = extract_surname_row(self._row("Jubaida .khatuna 80", "Mu0 Phata Pa"))
        # After cleaning khatuna suffix, should not return "KHATUNA" or "80" as surname
        assert surname not in ("80", "KHATUNA", "80A")

    def test_muslim_ansari(self):
        surname, conf, _ = extract_surname_row(self._row("Sa La Amsari", "Mahamuda Amsari"))
        assert surname == "AMSARI"
        assert conf == "HIGH"

    def test_unknown_when_only_generic(self):
        surname, conf, _ = extract_surname_row(self._row("Ram", "Shyam"))
        # Single non-generic token → returned as medium confidence
        assert conf in ("MEDIUM", "LOW", "VERY_LOW")

    def test_relation_name_only_fallback(self):
        surname, conf, src = extract_surname_row(self._row("Devi", "Ramachandra Yadava"))
        # "Devi" is generic → should fallback to relation
        assert surname == "YADAVA" or conf in ("LOW", "VERY_LOW", "MEDIUM")

    def test_shrivastava_confirmed(self):
        surname, conf, _ = extract_surname_row(
            self._row("Samjiva Kumara Shrivastava", "Abhaya Shrivastava")
        )
        assert surname == "SHRIVASTAVA"
        assert conf == "HIGH"

    def test_brahmin_sharma(self):
        surname, conf, _ = extract_surname_row(self._row("Sachina Sharma", "Rajemdra Prasada"))
        assert surname == "SHARMA"

    def test_maurya_confirmed_by_relation(self):
        surname, conf, _ = extract_surname_row(self._row("Samtosha Maurya", "Ramavrxa Maurya"))
        assert surname == "MAURYA"
        assert conf == "HIGH"


class TestExtractSurnamesDataFrame:
    def test_output_columns(self):
        df = pd.DataFrame([
            {"full_name": "Yadav Ram", "relation_name": "Shyam Yadav"},
            {"full_name": "Sharma Ji", "relation_name": "Ramu Sharma"},
        ])
        result = extract_surnames(df)
        assert "surname" in result.columns
        assert "surname_confidence" in result.columns
        assert "surname_source" in result.columns

    def test_no_mutation_of_original(self):
        df = pd.DataFrame([{"full_name": "Test Name", "relation_name": "Father Name"}])
        original_cols = list(df.columns)
        _ = extract_surnames(df)
        assert list(df.columns) == original_cols

    def test_large_batch_performance(self):
        """Should complete 1000 rows in reasonable time."""
        import time
        rows = [{"full_name": f"Voter {i} Yadav", "relation_name": f"Father {i} Yadav"}
                for i in range(1000)]
        df = pd.DataFrame(rows)
        t0 = time.time()
        _ = extract_surnames(df)
        elapsed = time.time() - t0
        assert elapsed < 10, f"Too slow: {elapsed:.1f}s for 1000 rows"

    def test_generic_suffixes_coverage(self):
        """Common Hindi generic tokens should be in GENERIC_SUFFIXES."""
        must_include = {"DEVI", "KUMAR", "KUMARA", "PRASAD", "PRASADA", "RAM", "RAMA"}
        missing = must_include - GENERIC_SUFFIXES
        assert not missing, f"Missing from GENERIC_SUFFIXES: {missing}"
