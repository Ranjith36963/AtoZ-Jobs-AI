"""Tests for seniority extraction (SPEC.md §3.6, Gate P13)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from src.processing.seniority import extract_experience_years, extract_seniority


class TestSeniorityLevels:
    """All 5 seniority patterns from SPEC.md §3.6."""

    # Junior
    def test_junior(self) -> None:
        assert extract_seniority("Junior Python Developer") == "Junior"

    def test_entry_level(self) -> None:
        assert extract_seniority("Entry Level Data Analyst") == "Junior"

    def test_graduate(self) -> None:
        assert extract_seniority("Graduate Software Engineer") == "Junior"

    def test_intern(self) -> None:
        assert extract_seniority("Marketing Intern") == "Junior"

    def test_trainee(self) -> None:
        assert extract_seniority("Trainee Accountant") == "Junior"

    # Mid
    def test_mid(self) -> None:
        assert extract_seniority("Mid-Level Developer") == "Mid"

    def test_intermediate(self) -> None:
        assert extract_seniority("Intermediate Java Developer") == "Mid"

    # Senior
    def test_senior(self) -> None:
        assert extract_seniority("Senior Data Engineer") == "Senior"

    def test_sr(self) -> None:
        assert extract_seniority("Sr. Software Developer") == "Senior"

    # Lead
    def test_lead(self) -> None:
        assert extract_seniority("Lead Backend Engineer") == "Lead"

    def test_principal(self) -> None:
        assert extract_seniority("Principal Architect") == "Lead"

    def test_staff(self) -> None:
        assert extract_seniority("Staff Engineer") == "Lead"

    # Executive
    def test_head_of(self) -> None:
        assert extract_seniority("Head of Engineering") == "Executive"

    def test_director(self) -> None:
        assert extract_seniority("Director of Operations") == "Executive"

    def test_vp(self) -> None:
        assert extract_seniority("VP of Sales") == "Executive"

    def test_cto(self) -> None:
        assert extract_seniority("CTO") == "Executive"

    def test_cfo(self) -> None:
        assert extract_seniority("CFO") == "Executive"

    # Not specified
    def test_no_match(self) -> None:
        assert extract_seniority("Data Analyst") == "Not specified"

    def test_generic_title(self) -> None:
        assert extract_seniority("Software Engineer") == "Not specified"

    def test_empty(self) -> None:
        assert extract_seniority("") == "Not specified"

    def test_none_like(self) -> None:
        assert extract_seniority("   ") == "Not specified"


class TestExperienceYears:
    """Experience years extraction."""

    def test_5_years(self) -> None:
        assert extract_experience_years("5 years of experience required") == 5

    def test_3_plus_yrs(self) -> None:
        assert extract_experience_years("3+ yrs exp") == 3

    def test_10_years_experience(self) -> None:
        assert extract_experience_years("10 years experience") == 10

    def test_no_match(self) -> None:
        assert extract_experience_years("Python developer wanted") is None

    def test_empty(self) -> None:
        assert extract_experience_years("") is None


class TestSeniorityPropertyBased:
    """Property test: never raises on arbitrary input."""

    @given(st.text(max_size=200))
    @settings(max_examples=100)
    def test_never_raises(self, text: str) -> None:
        result = extract_seniority(text)
        assert result in {
            "Junior",
            "Mid",
            "Senior",
            "Lead",
            "Executive",
            "Not specified",
        }
