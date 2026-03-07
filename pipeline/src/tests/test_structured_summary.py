"""Tests for structured summary builder (SPEC.md §3.7, Gate P14)."""

from src.processing.summary import build_summary


class TestSummaryTemplate:
    """6-field template: Title, Seniority, Company, Skills, Work Type, Location."""

    def test_full_summary(self) -> None:
        result = build_summary(
            title="Senior Python Developer",
            seniority_level="Senior",
            company_name="Acme Corp",
            industry="Technology",
            skills=["Python", "AWS", "Docker"],
            employment_type=["full_time", "permanent"],
            location_type="hybrid",
            location_city="London",
            location_region="Greater London",
        )
        assert "Title: Senior Python Developer" in result
        assert "Seniority: Senior" in result
        assert "Company: Acme Corp (Technology)" in result
        assert "Skills: Python, AWS, Docker" in result
        assert "Work Type: full_time, permanent | Hybrid" in result
        assert "Location: London, Greater London" in result

    def test_no_summary_field(self) -> None:
        """Summary template must NOT contain a 'Summary:' field."""
        result = build_summary(title="Test", company_name="Test Co")
        assert "Summary:" not in result

    def test_no_requirements_field(self) -> None:
        """Summary template must NOT contain a 'Requirements:' field."""
        result = build_summary(title="Test", company_name="Test Co")
        assert "Requirements:" not in result

    def test_exactly_6_fields(self) -> None:
        result = build_summary(
            title="Data Analyst",
            seniority_level="Not specified",
            company_name="Big Corp",
            industry="Finance",
            skills=["SQL", "Excel"],
            employment_type=["full_time"],
            location_type="onsite",
            location_city="Manchester",
            location_region="North West",
        )
        lines = result.strip().split("\n")
        assert len(lines) == 6

    def test_remote_location(self) -> None:
        result = build_summary(
            title="Remote Worker",
            location_type="remote",
        )
        assert "Location: Remote, UK-wide" in result

    def test_nationwide_location(self) -> None:
        result = build_summary(
            title="Field Engineer",
            location_type="nationwide",
        )
        assert "Location: Multiple locations, UK" in result

    def test_no_skills(self) -> None:
        result = build_summary(title="Cleaner")
        assert "Skills: Not extracted" in result

    def test_skills_capped_at_15(self) -> None:
        many_skills = [f"Skill{i}" for i in range(20)]
        result = build_summary(title="Dev", skills=many_skills)
        # Should only include first 15
        assert "Skill14" in result
        assert "Skill15" not in result

    def test_unknown_company(self) -> None:
        result = build_summary(title="Test", company_name="")
        assert "Company: Unknown" in result

    def test_default_seniority(self) -> None:
        result = build_summary(title="Test")
        assert "Seniority: Not specified" in result

    def test_no_employment_type(self) -> None:
        result = build_summary(title="Test")
        assert "Work Type: Not specified" in result
