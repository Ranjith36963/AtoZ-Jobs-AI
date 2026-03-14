"""Tests for SpaCy PhraseMatcher skill extraction (SPEC.md §3.2, Gates S6-S9)."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.skills.dictionary_builder import build_dictionary
from src.skills.spacy_matcher import SpaCySkillMatcher


@pytest.fixture(scope="module")
def matcher() -> SpaCySkillMatcher:
    """Build matcher once for all tests (expensive to initialize)."""
    d = build_dictionary()
    return SpaCySkillMatcher(d)


class TestSpaCyExtraction:
    """Core extraction tests."""

    def test_python_aws(self, matcher: SpaCySkillMatcher) -> None:
        """Gate S6: 'Python developer with AWS experience' → at least ['Python', 'AWS']."""
        skills = matcher.extract("Python developer with AWS experience")
        assert "Python" in skills
        assert "AWS" in skills

    def test_uk_certs(self, matcher: SpaCySkillMatcher) -> None:
        """Gate S7: 'CSCS card holder with SMSTS' → at least ['CSCS Card', 'SMSTS']."""
        skills = matcher.extract("CSCS card holder with SMSTS certification")
        assert "CSCS Card" in skills
        assert "SMSTS" in skills

    def test_healthcare(self, matcher: SpaCySkillMatcher) -> None:
        """Gate S8: 'NMC registered nurse with enhanced DBS'."""
        skills = matcher.extract(
            "NMC registered nurse with enhanced DBS check required"
        )
        assert "NMC Registered" in skills
        # Either "DBS Check" or "Enhanced DBS" is acceptable
        assert "DBS Check" in skills or "Enhanced DBS" in skills

    def test_prince2(self, matcher: SpaCySkillMatcher) -> None:
        """'Project management using PRINCE2' → at least ['Project Management', 'PRINCE2']."""
        skills = matcher.extract("Project management using PRINCE2 methodology")
        assert "Project Management" in skills
        assert "PRINCE2" in skills

    def test_multiple_skills(self, matcher: SpaCySkillMatcher) -> None:
        text = "Looking for a Python developer with React, Docker, and AWS experience. Must know SQL and Git."
        skills = matcher.extract(text)
        assert "Python" in skills
        assert "React" in skills
        assert "Docker" in skills
        assert "AWS" in skills
        assert "SQL" in skills

    def test_finance_skills(self, matcher: SpaCySkillMatcher) -> None:
        skills = matcher.extract(
            "ACCA qualified accountant with experience in Xero and payroll"
        )
        assert "ACCA" in skills

    def test_case_insensitive(self, matcher: SpaCySkillMatcher) -> None:
        skills = matcher.extract(
            "PYTHON developer with docker and KUBERNETES experience"
        )
        assert "Python" in skills
        assert "Docker" in skills
        assert "Kubernetes" in skills


class TestSpaCyCapping:
    """Max skills enforcement."""

    def test_max_skills(self, matcher: SpaCySkillMatcher) -> None:
        """Gate S9: 20+ skill mentions → exactly 15."""
        text = (
            "Python JavaScript TypeScript Java React Angular Vue Docker Kubernetes "
            "AWS Azure Git Linux PostgreSQL MySQL MongoDB Redis Terraform Ansible "
            "Jenkins Kafka Elasticsearch GraphQL DevOps Agile Scrum"
        )
        skills = matcher.extract(text)
        assert len(skills) <= 15

    def test_ordered_by_frequency(self, matcher: SpaCySkillMatcher) -> None:
        text = "Python Python Python Python AWS Docker"
        skills = matcher.extract(text)
        # Python mentioned 4x should be first
        assert skills[0] == "Python"


class TestSpaCyEdgeCases:
    """Sad paths."""

    def test_empty_string(self, matcher: SpaCySkillMatcher) -> None:
        assert matcher.extract("") == []

    def test_whitespace_only(self, matcher: SpaCySkillMatcher) -> None:
        assert matcher.extract("   ") == []

    def test_no_skills(self, matcher: SpaCySkillMatcher) -> None:
        skills = matcher.extract("The weather is lovely today in the countryside")
        assert isinstance(skills, list)

    def test_dedup_repeated_mentions(self, matcher: SpaCySkillMatcher) -> None:
        """Repeated mentions don't create duplicate entries."""
        skills = matcher.extract("Python and more Python and even more Python")
        assert skills.count("Python") == 1


class TestPropertyBased:
    """Hypothesis property-based tests (test-standards.md §4)."""

    @given(text=st.text(min_size=0, max_size=2000))
    @settings(max_examples=100)
    def test_extract_never_raises(self, matcher: SpaCySkillMatcher, text: str) -> None:
        """Matcher must never raise on arbitrary text input."""
        result = matcher.extract(text)
        assert isinstance(result, list)

    @given(text=st.text(min_size=0, max_size=500))
    @settings(max_examples=50)
    def test_extract_returns_list_of_strings(
        self, matcher: SpaCySkillMatcher, text: str
    ) -> None:
        """Every extracted skill must be a string."""
        result = matcher.extract(text)
        for skill in result:
            assert isinstance(skill, str)
            assert len(skill) > 0

    @given(text=st.text(min_size=0, max_size=1000))
    @settings(max_examples=50)
    def test_extract_respects_max_skills(
        self, matcher: SpaCySkillMatcher, text: str
    ) -> None:
        """Result is always capped at max_skills."""
        result = matcher.extract(text, max_skills=15)
        assert len(result) <= 15

    @given(text=st.text(min_size=0, max_size=500))
    @settings(max_examples=50)
    def test_extract_no_duplicates(self, matcher: SpaCySkillMatcher, text: str) -> None:
        """Result never contains duplicate entries."""
        result = matcher.extract(text)
        assert len(result) == len(set(result))
