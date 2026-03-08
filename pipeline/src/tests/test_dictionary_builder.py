"""Tests for skill dictionary builder (SPEC.md §3.2)."""

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from src.skills.dictionary_builder import build_dictionary, build_uk_entries

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_CSV = os.path.join(FIXTURES_DIR, "esco_sample.csv")


class TestBuildUkEntries:
    """UK-specific entries tests."""

    def test_returns_dict(self) -> None:
        entries = build_uk_entries()
        assert isinstance(entries, dict)
        assert len(entries) > 80  # ~96 entries in current implementation

    def test_construction_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["cscs card"] == "CSCS Card"
        assert entries["smsts"] == "SMSTS"
        assert entries["sssts"] == "SSSTS"

    def test_finance_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["acca"] == "ACCA"
        assert entries["cima"] == "CIMA"

    def test_healthcare_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["nmc registered"] == "NMC Registered"
        assert entries["nmc"] == "NMC Registered"

    def test_hr_management_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["cipd"] == "CIPD"
        assert entries["prince2"] == "PRINCE2"

    def test_sia_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["sia licence"] == "SIA Licence"

    def test_driving_entries(self) -> None:
        entries = build_uk_entries()
        assert entries["full uk driving licence"] == "Full UK Driving Licence"
        assert entries["hgv class 1"] == "HGV Class 1"


class TestBuildDictionary:
    """Combined dictionary tests."""

    def test_without_esco(self) -> None:
        """Without ESCO CSV, returns Phase 1 + UK entries."""
        d = build_dictionary()
        assert len(d) > 200  # Phase 1 (~150) + UK (~300), minus overlap
        # Phase 1 entries present
        assert d["python"] == "Python"
        assert d["aws"] == "AWS"
        # UK entries present
        assert d["cscs card"] == "CSCS Card"
        assert d["cipd"] == "CIPD"

    def test_with_esco(self) -> None:
        """With ESCO CSV, merges ESCO patterns too."""
        d = build_dictionary(esco_csv_path=SAMPLE_CSV)
        assert len(d) > 200
        # ESCO alt labels present
        assert d["python programming"] == "Python"
        assert d["data analytics"] == "data analysis"

    def test_dedup_lowercase_keys(self) -> None:
        """Same lowercase key doesn't create duplicates."""
        d = build_dictionary()
        # All keys should be lowercase
        for key in d:
            assert key == key.lower()

    def test_phase1_entries_preserved(self) -> None:
        """Phase 1 dictionary entries are all present."""
        d = build_dictionary()
        assert d["docker"] == "Docker"
        assert d["kubernetes"] == "Kubernetes"
        assert d["react"] == "React"
        assert d["machine learning"] == "Machine Learning"

    def test_gate_s5_entries(self) -> None:
        """Gate S5: UK-specific canonical names present."""
        d = build_dictionary()
        canonical_values = set(d.values())
        assert "CSCS Card" in canonical_values
        assert "CIPD" in canonical_values
        assert "NMC Registered" in canonical_values
        assert "SIA Licence" in canonical_values
        assert "ACCA" in canonical_values

    def test_uk_entry_count_spec(self) -> None:
        """SPEC §3.2: ~300 UK-specific entries."""
        entries = build_uk_entries()
        assert len(entries) >= 250, f"Expected ~300 UK entries, got {len(entries)}"

    def test_combined_pattern_count(self) -> None:
        """SPEC §3.2: ~450+ patterns total without ESCO."""
        d = build_dictionary()
        assert len(d) >= 400, f"Expected ~450+ patterns, got {len(d)}"


class TestPropertyBased:
    """Hypothesis property-based tests (test-standards.md §4)."""

    @given(key=st.sampled_from(list(build_uk_entries().keys())))
    @settings(max_examples=100)
    def test_uk_keys_always_lowercase(self, key: str) -> None:
        """Every UK dictionary key must be lowercase."""
        assert key == key.lower()

    @given(key=st.sampled_from(list(build_dictionary().keys())))
    @settings(max_examples=200)
    def test_all_keys_lowercase(self, key: str) -> None:
        """Every combined dictionary key must be lowercase."""
        assert key == key.lower()

    @given(key=st.sampled_from(list(build_dictionary().keys())))
    @settings(max_examples=100)
    def test_values_never_empty(self, key: str) -> None:
        """Every key maps to a non-empty canonical name."""
        d = build_dictionary()
        assert len(d[key]) > 0
