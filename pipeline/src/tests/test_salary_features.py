"""Tests for salary feature engineering (SPEC.md §5.1, Gates P5)."""

import numpy as np

from src.salary.features import (
    CATEGORIES,
    SENIORITY_MAP,
    UK_REGIONS,
    _encode_category,
    _encode_region,
    _encode_seniority,
    build_features,
)


class TestEncodeSeniority:
    """Seniority ordinal encoding."""

    def test_known_levels(self) -> None:
        assert _encode_seniority("Junior") == 1
        assert _encode_seniority("Mid") == 2
        assert _encode_seniority("Senior") == 3
        assert _encode_seniority("Lead") == 4
        assert _encode_seniority("Executive") == 5

    def test_missing_returns_zero(self) -> None:
        assert _encode_seniority(None) == 0
        assert _encode_seniority("") == 0
        assert _encode_seniority("Unknown") == 0


class TestEncodeRegion:
    """Region one-hot encoding."""

    def test_london(self) -> None:
        encoding = _encode_region("London")
        assert sum(encoding) == 1
        assert encoding[UK_REGIONS.index("London")] == 1

    def test_all_regions(self) -> None:
        for region in UK_REGIONS:
            encoding = _encode_region(region)
            assert sum(encoding) == 1

    def test_missing_region(self) -> None:
        encoding = _encode_region(None)
        assert sum(encoding) == 0

    def test_unknown_region(self) -> None:
        encoding = _encode_region("Mars")
        assert sum(encoding) == 0


class TestEncodeCategory:
    """Category one-hot encoding."""

    def test_technology(self) -> None:
        encoding = _encode_category("Technology")
        assert sum(encoding) == 1

    def test_missing_category(self) -> None:
        encoding = _encode_category(None)
        assert sum(encoding) == 0


class TestBuildFeatures:
    """Feature matrix building tests."""

    def test_basic_feature_extraction(self) -> None:
        """Gate P5: Features extracted, matrix shape correct."""
        jobs = [
            {"title": "Python Developer", "salary_annual_max": 50000,
             "location_region": "London", "category": "Technology",
             "seniority_level": "Senior", "skill_count": 5},
            {"title": "Data Analyst", "salary_annual_max": 35000,
             "location_region": "North West", "category": "Finance",
             "seniority_level": "Mid", "skill_count": 3},
        ]
        features, labels = build_features(jobs)
        assert features.shape[0] == 2
        assert labels.shape[0] == 2
        assert labels[0] == 50000
        assert labels[1] == 35000

    def test_tfidf_max_features(self) -> None:
        """TF-IDF produces at most max_features columns."""
        jobs = [
            {"title": f"Job title {i}", "salary_annual_max": 30000 + i * 1000}
            for i in range(20)
        ]
        features, labels = build_features(jobs, max_tfidf_features=10)
        # TF-IDF (10) + regions (12) + categories (17) + seniority (1) + skill_count (1) = 41
        assert features.shape[1] == 10 + len(UK_REGIONS) + len(CATEGORIES) + 1 + 1

    def test_jobs_without_salary_excluded(self) -> None:
        """Jobs without salary not included in training data."""
        jobs = [
            {"title": "Dev", "salary_annual_max": 50000},
            {"title": "Chef", "salary_annual_max": None},
            {"title": "Nurse", "salary_annual_max": 30000},
        ]
        features, labels = build_features(jobs)
        assert features.shape[0] == 2
        assert labels.shape[0] == 2

    def test_predicted_salary_excluded(self) -> None:
        """Jobs with salary_is_predicted=True excluded."""
        jobs = [
            {"title": "Dev", "salary_annual_max": 50000, "salary_is_predicted": False},
            {"title": "Chef", "salary_annual_max": 40000, "salary_is_predicted": True},
        ]
        features, labels = build_features(jobs)
        assert features.shape[0] == 1

    def test_no_nan_in_features(self) -> None:
        """No NaN values in feature matrix."""
        jobs = [
            {"title": "Developer", "salary_annual_max": 50000,
             "location_region": None, "category": None,
             "seniority_level": None, "skill_count": None},
        ]
        features, labels = build_features(jobs)
        assert not np.isnan(features).any()

    def test_empty_jobs_list(self) -> None:
        features, labels = build_features([])
        assert features.shape[0] == 0
        assert labels.shape[0] == 0

    def test_with_top_skills(self) -> None:
        """Top skills binary presence features."""
        top_skills = ["Python", "AWS", "Docker"]
        jobs = [
            {"title": "Dev", "salary_annual_max": 50000, "skills": ["Python", "AWS"]},
            {"title": "Chef", "salary_annual_max": 30000, "skills": []},
        ]
        features, labels = build_features(jobs, top_skills=top_skills)
        # Last 3 columns should be skill binary features
        assert features.shape[0] == 2
