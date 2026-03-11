"""Tests for fuzzy duplicate matching (SPEC.md §4.2-4.3, Gates D3-D10)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from src.dedup.fuzzy_matcher import (
    DUPLICATE_THRESHOLD,
    compute_local_duplicate_score,
    pick_canonical,
)


class TestCompositeDuplicateScore:
    """Composite scoring formula tests."""

    def test_weights_sum_to_one(self) -> None:
        """Gate D3: Weights sum to 1.0 at maximum."""
        score = compute_local_duplicate_score(
            title_sim=1.0,
            company_match=True,
            location_km=0.0,
            salary_overlap=1.0,
            date_diff_days=0,
        )
        assert abs(score - 1.0) < 0.001

    def test_gate_d3_example(self) -> None:
        """Gate D3: compute_duplicate_score(0.7, true, 3.0, 0.8, 5) = 0.865."""
        score = compute_local_duplicate_score(
            title_sim=0.7,
            company_match=True,
            location_km=3.0,
            salary_overlap=0.8,
            date_diff_days=5,
        )
        expected = 0.35 * 0.7 + 0.25 + 0.15 + 0.15 * 0.8 + 0.10
        assert abs(score - expected) < 0.001
        assert abs(score - 0.865) < 0.001

    def test_title_only(self) -> None:
        score = compute_local_duplicate_score(
            title_sim=0.8,
            company_match=False,
            location_km=100.0,
            salary_overlap=0.0,
            date_diff_days=30,
        )
        assert abs(score - 0.28) < 0.001  # 0.8 * 0.35

    def test_location_tiers(self) -> None:
        """Location: ≤5km = 0.15, ≤25km = 0.08, >25km = 0."""
        close = compute_local_duplicate_score(0.0, False, 3.0, 0.0, 30)
        medium = compute_local_duplicate_score(0.0, False, 15.0, 0.0, 30)
        far = compute_local_duplicate_score(0.0, False, 50.0, 0.0, 30)
        assert abs(close - 0.15) < 0.001
        assert abs(medium - 0.08) < 0.001
        assert abs(far - 0.0) < 0.001

    def test_date_tiers(self) -> None:
        """Date: ≤7d = 0.10, ≤14d = 0.05, >14d = 0."""
        recent = compute_local_duplicate_score(0.0, False, 100.0, 0.0, 5)
        medium = compute_local_duplicate_score(0.0, False, 100.0, 0.0, 10)
        old = compute_local_duplicate_score(0.0, False, 100.0, 0.0, 30)
        assert abs(recent - 0.10) < 0.001
        assert abs(medium - 0.05) < 0.001
        assert abs(old - 0.0) < 0.001

    def test_above_threshold_is_duplicate(self) -> None:
        """Score >= 0.65 → should be flagged as duplicate."""
        score = compute_local_duplicate_score(
            title_sim=0.7,
            company_match=True,
            location_km=3.0,
            salary_overlap=0.5,
            date_diff_days=5,
        )
        assert score >= DUPLICATE_THRESHOLD

    def test_below_threshold_not_duplicate(self) -> None:
        """Low-similarity pair should be below threshold."""
        score = compute_local_duplicate_score(
            title_sim=0.3,
            company_match=False,
            location_km=50.0,
            salary_overlap=0.0,
            date_diff_days=30,
        )
        assert score < DUPLICATE_THRESHOLD


class TestPickCanonical:
    """Canonical selection tests."""

    def test_keeps_richer_version(self) -> None:
        """Gate D10: Job with more non-null fields is kept."""
        job_a = {
            "id": 1,
            "salary_annual_max": 50000,
            "location_city": "London",
            "description_plain": "A" * 500,  # 500 chars
            "embedding": [0.1] * 768,
        }
        job_b = {
            "id": 2,
            "salary_annual_max": None,
            "location_city": None,
            "description_plain": "Short",
            "embedding": None,
        }
        canonical_id, duplicate_id = pick_canonical(job_a, job_b)
        assert canonical_id == 1
        assert duplicate_id == 2

    def test_keeps_longer_description(self) -> None:
        job_a = {
            "id": 1,
            "salary_annual_max": None,
            "location_city": None,
            "description_plain": "A" * 300,
            "embedding": None,
        }
        job_b = {
            "id": 2,
            "salary_annual_max": None,
            "location_city": None,
            "description_plain": "A" * 100,
            "embedding": None,
        }
        canonical_id, duplicate_id = pick_canonical(job_a, job_b)
        assert canonical_id == 1
        assert duplicate_id == 2

    def test_equal_richness_keeps_first(self) -> None:
        job_a = {
            "id": 1,
            "salary_annual_max": None,
            "location_city": None,
            "description_plain": "",
            "embedding": None,
        }
        job_b = {
            "id": 2,
            "salary_annual_max": None,
            "location_city": None,
            "description_plain": "",
            "embedding": None,
        }
        canonical_id, duplicate_id = pick_canonical(job_a, job_b)
        assert canonical_id == 1
        assert duplicate_id == 2

    def test_missing_fields_handled(self) -> None:
        """Missing keys don't crash."""
        job_a = {"id": 1}
        job_b = {"id": 2, "salary_annual_max": 40000}
        canonical_id, duplicate_id = pick_canonical(job_a, job_b)
        assert canonical_id == 2
        assert duplicate_id == 1

    def test_none_description(self) -> None:
        """None description handled safely."""
        job_a = {"id": 1, "description_plain": None}
        job_b = {"id": 2, "description_plain": "A" * 200, "salary_annual_max": 50000}
        canonical_id, _dup = pick_canonical(job_a, job_b)
        assert canonical_id == 2


class TestPropertyBased:
    """Hypothesis property-based tests for parsers (test-standards.md §4)."""

    @given(
        title_sim=st.floats(min_value=0.0, max_value=1.0),
        company_match=st.booleans(),
        location_km=st.floats(min_value=0.0, max_value=1000.0),
        salary_overlap=st.floats(min_value=0.0, max_value=1.0),
        date_diff_days=st.integers(min_value=0, max_value=365),
    )
    @settings(max_examples=200)
    def test_score_always_bounded(
        self,
        title_sim: float,
        company_match: bool,
        location_km: float,
        salary_overlap: float,
        date_diff_days: int,
    ) -> None:
        """Score must always be 0.0 ≤ score ≤ 1.0 for any valid input."""
        score = compute_local_duplicate_score(
            title_sim,
            company_match,
            location_km,
            salary_overlap,
            date_diff_days,
        )
        assert 0.0 <= score <= 1.0 + 1e-9  # float tolerance

    @given(
        title_sim=st.floats(min_value=0.0, max_value=1.0),
        salary_overlap=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_max_possible_score_is_one(
        self, title_sim: float, salary_overlap: float
    ) -> None:
        """Max signal (all True, close, recent) never exceeds 1.0."""
        score = compute_local_duplicate_score(
            title_sim=title_sim,
            company_match=True,
            location_km=0.0,
            salary_overlap=salary_overlap,
            date_diff_days=0,
        )
        assert score <= 1.0 + 1e-9

    @given(
        title_sim=st.floats(min_value=0.0, max_value=1.0),
        salary_overlap=st.floats(min_value=0.0, max_value=1.0),
        date_diff_days=st.integers(min_value=0, max_value=365),
    )
    @settings(max_examples=100)
    def test_score_never_raises(
        self, title_sim: float, salary_overlap: float, date_diff_days: int
    ) -> None:
        """Function never raises on arbitrary valid input."""
        compute_local_duplicate_score(
            title_sim,
            False,
            50.0,
            salary_overlap,
            date_diff_days,
        )
