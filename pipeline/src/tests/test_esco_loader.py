"""Tests for ESCO CSV loader (SPEC.md §3.1)."""

import os

from src.skills.esco_loader import load_esco_csv

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_CSV = os.path.join(FIXTURES_DIR, "esco_sample.csv")


class TestEscoLoader:
    """Core loading tests."""

    def test_loads_all_rows(self) -> None:
        """Sample CSV has 10 rows."""
        skills = load_esco_csv(SAMPLE_CSV)
        assert len(skills) == 10

    def test_keyed_by_concept_uri(self) -> None:
        skills = load_esco_csv(SAMPLE_CSV)
        assert "http://data.europa.eu/esco/skill/001" in skills
        assert "http://data.europa.eu/esco/skill/010" in skills

    def test_preferred_label_extracted(self) -> None:
        skills = load_esco_csv(SAMPLE_CSV)
        assert (
            skills["http://data.europa.eu/esco/skill/001"]["preferred_label"]
            == "Python"
        )
        assert (
            skills["http://data.europa.eu/esco/skill/004"]["preferred_label"]
            == "JavaScript"
        )

    def test_alt_labels_split_by_newline(self) -> None:
        skills = load_esco_csv(SAMPLE_CSV)
        python_skill = skills["http://data.europa.eu/esco/skill/001"]
        assert "Python programming" in python_skill["alt_labels"]
        assert "Python 3" in python_skill["alt_labels"]

    def test_alt_labels_filters_short(self) -> None:
        """Alt labels with length <= 2 are filtered out."""
        skills = load_esco_csv(SAMPLE_CSV)
        # "Py" is 2 chars, should be filtered; "XY" is 2 chars, should be filtered
        python_skill = skills["http://data.europa.eu/esco/skill/001"]
        assert "Py" not in python_skill["alt_labels"]
        leadership = skills["http://data.europa.eu/esco/skill/010"]
        assert "XY" not in leadership["alt_labels"]

    def test_skill_type_extracted(self) -> None:
        skills = load_esco_csv(SAMPLE_CSV)
        assert (
            skills["http://data.europa.eu/esco/skill/001"]["skill_type"]
            == "skill/competence"
        )
        assert (
            skills["http://data.europa.eu/esco/skill/003"]["skill_type"] == "knowledge"
        )

    def test_description_extracted(self) -> None:
        skills = load_esco_csv(SAMPLE_CSV)
        assert "Python" in skills["http://data.europa.eu/esco/skill/001"]["description"]

    def test_multiple_alt_labels(self) -> None:
        """Communication skills has 3 alt labels."""
        skills = load_esco_csv(SAMPLE_CSV)
        comm = skills["http://data.europa.eu/esco/skill/005"]
        assert len(comm["alt_labels"]) == 3


class TestEscoLoaderEdgeCases:
    """Sad paths."""

    def test_nonexistent_file_raises(self) -> None:
        """Missing file raises FileNotFoundError."""
        try:
            load_esco_csv("/nonexistent/path.csv")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass

    def test_empty_alt_labels(self) -> None:
        """SQL skill has only one alt label 'structured query language'."""
        skills = load_esco_csv(SAMPLE_CSV)
        sql_skill = skills["http://data.europa.eu/esco/skill/008"]
        assert "structured query language" in sql_skill["alt_labels"]
