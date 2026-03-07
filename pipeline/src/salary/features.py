"""Feature engineering for salary prediction (SPEC.md §5.1).

Extracts features from job data for XGBoost salary model training.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder

# 12 UK regions for one-hot encoding
UK_REGIONS = [
    "East Midlands", "East of England", "London", "North East",
    "North West", "Northern Ireland", "Scotland", "South East",
    "South West", "Wales", "West Midlands", "Yorkshire and the Humber",
]

# Seniority ordinal mapping
SENIORITY_MAP = {
    "Junior": 1, "Mid": 2, "Senior": 3, "Lead": 4, "Executive": 5,
}

# Internal categories for one-hot
CATEGORIES = [
    "Technology", "Finance", "Healthcare", "Education", "Construction",
    "Retail", "Hospitality", "Manufacturing", "Logistics & Transport",
    "Energy & Utilities", "Creative & Media", "Professional Services",
    "Public Sector", "Agriculture", "Property", "Administration", "Other",
]


def _encode_seniority(seniority: str | None) -> int:
    """Encode seniority level as ordinal integer."""
    if not seniority:
        return 0
    return SENIORITY_MAP.get(seniority, 0)


def _encode_region(region: str | None) -> list[int]:
    """One-hot encode a UK region."""
    encoding = [0] * len(UK_REGIONS)
    if region and region in UK_REGIONS:
        idx = UK_REGIONS.index(region)
        encoding[idx] = 1
    return encoding


def _encode_category(category: str | None) -> list[int]:
    """One-hot encode a job category."""
    encoding = [0] * len(CATEGORIES)
    if category and category in CATEGORIES:
        idx = CATEGORIES.index(category)
        encoding[idx] = 1
    return encoding


def build_features(
    jobs: list[dict[str, object]],
    max_tfidf_features: int = 500,
    top_skills: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build feature matrix and label vector from job data.

    Args:
        jobs: List of job dicts. Required keys: title, salary_annual_max.
              Optional: location_region, category, seniority_level,
              employment_type, skill_count, skills.
        max_tfidf_features: Max TF-IDF features from title.
        top_skills: List of top 50 skill names for binary features.

    Returns:
        Tuple of (feature_matrix, salary_labels) as numpy arrays.
        Only includes jobs where salary_annual_max is not None
        and salary_is_predicted is not True.
    """
    # Filter to jobs with real salary data
    labeled_jobs = [
        j for j in jobs
        if j.get("salary_annual_max") is not None
        and not j.get("salary_is_predicted", False)
    ]

    if not labeled_jobs:
        return np.array([]).reshape(0, 0), np.array([])

    # Extract salary labels
    labels = np.array([float(j["salary_annual_max"]) for j in labeled_jobs])  # type: ignore[arg-type]

    # TF-IDF on titles
    titles = [str(j.get("title", "")) for j in labeled_jobs]
    tfidf = TfidfVectorizer(max_features=max_tfidf_features, stop_words="english")
    tfidf_matrix = tfidf.fit_transform(titles).toarray()

    # Region one-hot
    region_features = np.array([
        _encode_region(str(j.get("location_region", "")) or None)
        for j in labeled_jobs
    ])

    # Category one-hot
    category_features = np.array([
        _encode_category(str(j.get("category", "")) or None)
        for j in labeled_jobs
    ])

    # Seniority ordinal
    seniority_features = np.array([
        [_encode_seniority(str(j.get("seniority_level", "")) or None)]
        for j in labeled_jobs
    ])

    # Skill count
    skill_count_features = np.array([
        [int(j.get("skill_count", 0) or 0)]
        for j in labeled_jobs
    ])

    # Top 50 skills binary presence
    if top_skills:
        skill_features = np.array([
            [1 if s in (j.get("skills", []) or []) else 0 for s in top_skills]
            for j in labeled_jobs
        ])
    else:
        skill_features = np.zeros((len(labeled_jobs), 0))

    # Concatenate all features
    feature_matrix = np.hstack([
        tfidf_matrix,
        region_features,
        category_features,
        seniority_features,
        skill_count_features,
        skill_features,
    ])

    return feature_matrix, labels
