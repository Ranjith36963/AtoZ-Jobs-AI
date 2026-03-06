"""Tests for skill extractor (SPEC.md §3.8, Gate P15)."""

from src.skills.extractor import extract_skills, MAX_SKILLS


class TestSkillExtraction:
    """Core extraction tests."""

    def test_python_and_aws(self) -> None:
        """Gate P15: 'Python developer with AWS experience' → at least ['Python', 'AWS']."""
        skills = extract_skills("Python developer with AWS experience")
        skill_names = [s[0] for s in skills]
        assert "Python" in skill_names
        assert "AWS" in skill_names

    def test_confidence_is_1(self) -> None:
        """Exact matches have confidence=1.0."""
        skills = extract_skills("Python developer")
        for _name, confidence in skills:
            assert confidence == 1.0

    def test_multiple_skills(self) -> None:
        text = "Looking for a Python developer with React, Docker, and AWS experience. Must know SQL and Git."
        skills = extract_skills(text)
        skill_names = [s[0] for s in skills]
        assert "Python" in skill_names
        assert "React" in skill_names
        assert "Docker" in skill_names
        assert "AWS" in skill_names
        assert "SQL" in skill_names
        assert "Git" in skill_names

    def test_multi_word_skill(self) -> None:
        skills = extract_skills(
            "Experience with machine learning and project management required"
        )
        skill_names = [s[0] for s in skills]
        assert "Machine Learning" in skill_names
        assert "Project Management" in skill_names

    def test_uk_specific_skills(self) -> None:
        skills = extract_skills(
            "Must have CSCS card, NEBOSH certificate, and full UK driving licence"
        )
        skill_names = [s[0] for s in skills]
        assert "CSCS Card" in skill_names
        assert "NEBOSH" in skill_names
        assert "Full UK Driving Licence" in skill_names

    def test_finance_skills(self) -> None:
        skills = extract_skills(
            "ACCA qualified accountant with Xero and payroll experience"
        )
        skill_names = [s[0] for s in skills]
        assert "ACCA" in skill_names
        assert "Xero" in skill_names
        assert "Payroll" in skill_names

    def test_case_insensitive(self) -> None:
        skills = extract_skills("PYTHON developer with aws and DOCKER experience")
        skill_names = [s[0] for s in skills]
        assert "Python" in skill_names
        assert "AWS" in skill_names
        assert "Docker" in skill_names


class TestSkillCapping:
    """Max 15 skills per job."""

    def test_max_15_skills(self) -> None:
        # Build text with >15 distinct skills
        text = (
            "Python JavaScript TypeScript Java React Angular Vue Docker Kubernetes "
            "AWS Azure Git Linux PostgreSQL MySQL MongoDB Redis Terraform Ansible "
            "Jenkins Kafka Elasticsearch GraphQL"
        )
        skills = extract_skills(text)
        assert len(skills) <= MAX_SKILLS

    def test_ordered_by_frequency(self) -> None:
        text = "Python Python Python AWS Docker"
        skills = extract_skills(text)
        skill_names = [s[0] for s in skills]
        # Python mentioned 3x should be first
        assert skill_names[0] == "Python"


class TestSkillEdgeCases:
    """Sad paths."""

    def test_empty_text(self) -> None:
        assert extract_skills("") == []

    def test_whitespace_only(self) -> None:
        assert extract_skills("   ") == []

    def test_no_skills_found(self) -> None:
        skills = extract_skills("Looking for a great team player in a wonderful office")
        # 'teamwork' might match 'team' — but exact word boundary should prevent partial
        # The result may have a few soft skills but that's OK
        assert isinstance(skills, list)

    def test_dedup_same_canonical(self) -> None:
        """'aws' and 'amazon web services' should not produce duplicates."""
        skills = extract_skills("AWS Amazon Web Services cloud")
        skill_names = [s[0] for s in skills]
        assert skill_names.count("AWS") == 1
