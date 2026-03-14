"""Tests for fuzzy duplicate matching (SPEC.md §4.2-4.3, Gates D3-D10)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.dedup.fuzzy_matcher import (
    DUPLICATE_THRESHOLD,
    compute_local_duplicate_score,
    find_fuzzy_candidates,
    mark_duplicate,
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


# ===========================================================================
# find_fuzzy_candidates — DB RPC call (mocked)
# ===========================================================================


class TestFindFuzzyCandidates:
    """Tests for find_fuzzy_candidates with mocked Supabase client."""

    @pytest.mark.asyncio
    async def test_returns_candidates_above_threshold(self) -> None:
        """Only rows with dup_score >= DUPLICATE_THRESHOLD are returned."""
        db = MagicMock()
        rpc_chain = MagicMock()
        db.rpc.return_value = rpc_chain
        rpc_chain.execute.return_value = MagicMock(
            data=[
                {"id": 10, "dup_score": 0.80, "title_sim": 0.7},
                {"id": 20, "dup_score": 0.50, "title_sim": 0.4},
                {"id": 30, "dup_score": 0.70, "title_sim": 0.6},
            ]
        )

        result = await find_fuzzy_candidates(1, db)

        db.rpc.assert_called_once_with("find_fuzzy_duplicates", {"target_job_id": 1})
        assert len(result) == 2
        assert result[0]["id"] == 10
        assert result[1]["id"] == 30

    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(self) -> None:
        """Empty RPC result returns empty list."""
        db = MagicMock()
        rpc_chain = MagicMock()
        db.rpc.return_value = rpc_chain
        rpc_chain.execute.return_value = MagicMock(data=[])

        result = await find_fuzzy_candidates(1, db)
        assert result == []

    @pytest.mark.asyncio
    async def test_null_data_returns_empty(self) -> None:
        """None data from RPC returns empty list."""
        db = MagicMock()
        rpc_chain = MagicMock()
        db.rpc.return_value = rpc_chain
        rpc_chain.execute.return_value = MagicMock(data=None)

        result = await find_fuzzy_candidates(1, db)
        assert result == []

    @pytest.mark.asyncio
    async def test_all_below_threshold_returns_empty(self) -> None:
        """All candidates below threshold → empty result."""
        db = MagicMock()
        rpc_chain = MagicMock()
        db.rpc.return_value = rpc_chain
        rpc_chain.execute.return_value = MagicMock(
            data=[
                {"id": 10, "dup_score": 0.30},
                {"id": 20, "dup_score": 0.50},
            ]
        )

        result = await find_fuzzy_candidates(1, db)
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_dup_score_defaults_to_zero(self) -> None:
        """Row without dup_score defaults to 0 → filtered out."""
        db = MagicMock()
        rpc_chain = MagicMock()
        db.rpc.return_value = rpc_chain
        rpc_chain.execute.return_value = MagicMock(
            data=[{"id": 10, "title_sim": 0.9}]  # no dup_score key
        )

        result = await find_fuzzy_candidates(1, db)
        assert result == []


# ===========================================================================
# mark_duplicate — DB update call (mocked)
# ===========================================================================


class TestMarkDuplicate:
    """Tests for mark_duplicate with mocked Supabase client."""

    @pytest.mark.asyncio
    async def test_updates_correct_fields(self) -> None:
        """Calls update with is_duplicate, canonical_id, duplicate_score."""
        db = MagicMock()
        chain = MagicMock()
        db.table.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain

        await mark_duplicate(42, 10, 0.85, db)

        db.table.assert_called_once_with("jobs")
        chain.update.assert_called_once_with(
            {
                "is_duplicate": True,
                "canonical_id": 10,
                "duplicate_score": 0.85,
            }
        )
        chain.eq.assert_called_once_with("id", 42)
        chain.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_duplicate_with_zero_score(self) -> None:
        """Edge case: score of 0 is valid."""
        db = MagicMock()
        chain = MagicMock()
        db.table.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain

        await mark_duplicate(1, 2, 0.0, db)

        chain.update.assert_called_once_with(
            {
                "is_duplicate": True,
                "canonical_id": 2,
                "duplicate_score": 0.0,
            }
        )
