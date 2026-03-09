"""Tests for dedup orchestrator (PLAYBOOK §2.4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.dedup.orchestrator import _simple_similarity, run_advanced_dedup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock(jobs: list[dict[str, object]]) -> MagicMock:
    """Create a mock Supabase client returning the given jobs."""
    db = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=jobs)
    db.table.return_value = chain
    return db


def _make_job(
    job_id: str = "job-1",
    title: str = "Python Developer",
    company: str = "Acme Ltd",
    description: str = "Build Python services for our platform.",
    salary: int = 60000,
    city: str = "London",
    embedding: list[float] | None = None,
    date_posted: str = "2025-01-01",
) -> dict[str, object]:
    return {
        "id": job_id,
        "title": title,
        "company_name": company,
        "description_plain": description,
        "salary_annual_max": salary,
        "location_city": city,
        "embedding": embedding or [0.1] * 10,
        "date_posted": date_posted,
    }


# ===========================================================================
# _simple_similarity
# ===========================================================================


class TestSimpleSimilarity:
    """Trigram similarity approximation tests."""

    def test_identical_strings(self) -> None:
        assert _simple_similarity("Python Developer", "Python Developer") == 1.0

    def test_similar_strings(self) -> None:
        sim = _simple_similarity("Senior Python Developer", "Senior Python Dev")
        assert sim > 0.5

    def test_different_strings(self) -> None:
        sim = _simple_similarity("Python Developer", "Head Chef")
        assert sim < 0.3

    def test_empty_string(self) -> None:
        assert _simple_similarity("", "test") == 0.0
        assert _simple_similarity("test", "") == 0.0
        assert _simple_similarity("", "") == 0.0

    def test_case_insensitive(self) -> None:
        assert _simple_similarity("PYTHON", "python") == 1.0

    def test_short_strings_below_trigram_length(self) -> None:
        """Strings shorter than 3 chars produce no trigrams → 0.0."""
        assert _simple_similarity("ab", "ab") == 1.0  # equal → early return
        assert _simple_similarity("ab", "cd") == 0.0  # no trigrams

    def test_none_like_empty(self) -> None:
        """Empty-ish strings return 0."""
        assert _simple_similarity("", "") == 0.0

    @given(st.text(min_size=0, max_size=200), st.text(min_size=0, max_size=200))
    @settings(max_examples=50)
    def test_returns_between_zero_and_one(self, a: str, b: str) -> None:
        result = _simple_similarity(a, b)
        assert 0.0 <= result <= 1.0

    @given(st.text(min_size=3, max_size=100))
    @settings(max_examples=30)
    def test_self_similarity_is_one(self, s: str) -> None:
        assert _simple_similarity(s, s) == 1.0


# ===========================================================================
# run_advanced_dedup — empty / basic paths
# ===========================================================================


class TestRunAdvancedDedup:
    """Orchestrator integration tests."""

    @pytest.mark.asyncio
    async def test_no_jobs_returns_zero_stats(self) -> None:
        db = _make_db_mock([])
        stats = await run_advanced_dedup(db, use_minhash=False)
        assert stats["total_scanned"] == 0
        assert stats["duplicates_marked"] == 0

    @pytest.mark.asyncio
    async def test_stats_structure(self) -> None:
        db = _make_db_mock([])
        stats = await run_advanced_dedup(db, use_minhash=False)
        assert "total_scanned" in stats
        assert "fuzzy_candidates" in stats
        assert "minhash_candidates" in stats
        assert "duplicates_marked" in stats
        assert "errors" in stats

    @pytest.mark.asyncio
    async def test_scanned_count_matches_job_count(self) -> None:
        jobs = [_make_job(f"job-{i}") for i in range(5)]
        db = _make_db_mock(jobs)

        with patch(
            "src.dedup.orchestrator.find_fuzzy_candidates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["total_scanned"] == 5


# ===========================================================================
# Stage 2: Fuzzy matching paths
# ===========================================================================


class TestFuzzyStage:
    """Stage 2 fuzzy matching within the orchestrator."""

    @pytest.mark.asyncio
    async def test_fuzzy_candidates_counted(self) -> None:
        """Candidates returned by find_fuzzy_candidates are counted."""
        job = _make_job()
        db = _make_db_mock([job])

        candidates = [
            {"id": "dup-1", "dup_score": 0.4},  # below threshold
            {"id": "dup-2", "dup_score": 0.3},
        ]

        with patch(
            "src.dedup.orchestrator.find_fuzzy_candidates",
            new_callable=AsyncMock,
            return_value=candidates,
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["fuzzy_candidates"] == 2
        assert stats["duplicates_marked"] == 0  # none above threshold

    @pytest.mark.asyncio
    async def test_fuzzy_duplicates_marked(self) -> None:
        """Candidates above DUPLICATE_THRESHOLD are marked as duplicates."""
        job = _make_job()
        db = _make_db_mock([job])

        candidates = [
            {"id": "dup-1", "dup_score": 0.80},  # above 0.65
        ]

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=candidates,
            ),
            patch(
                "src.dedup.orchestrator.pick_canonical",
                return_value=("job-1", "dup-1"),
            ),
            patch(
                "src.dedup.orchestrator.mark_duplicate",
                new_callable=AsyncMock,
            ) as mock_mark,
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["duplicates_marked"] == 1
        mock_mark.assert_awaited_once_with("dup-1", "job-1", 0.80, db)

    @pytest.mark.asyncio
    async def test_fuzzy_multiple_candidates_mixed_scores(self) -> None:
        """Only candidates >= threshold are marked."""
        job = _make_job()
        db = _make_db_mock([job])

        candidates = [
            {"id": "dup-1", "dup_score": 0.90},
            {"id": "dup-2", "dup_score": 0.50},  # below
            {"id": "dup-3", "dup_score": 0.70},
        ]

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=candidates,
            ),
            patch(
                "src.dedup.orchestrator.pick_canonical",
                return_value=("job-1", "dup-x"),
            ),
            patch(
                "src.dedup.orchestrator.mark_duplicate",
                new_callable=AsyncMock,
            ),
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["fuzzy_candidates"] == 3
        assert stats["duplicates_marked"] == 2  # dup-1 and dup-3

    @pytest.mark.asyncio
    async def test_fuzzy_error_increments_error_count(self) -> None:
        """Errors during fuzzy matching increment the errors counter."""
        job = _make_job()
        db = _make_db_mock([job])

        with patch(
            "src.dedup.orchestrator.find_fuzzy_candidates",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB connection lost"),
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["errors"] == 1
        assert stats["duplicates_marked"] == 0

    @pytest.mark.asyncio
    async def test_fuzzy_error_does_not_stop_other_jobs(self) -> None:
        """An error on one job doesn't prevent processing others."""
        jobs = [_make_job("job-1"), _make_job("job-2")]
        db = _make_db_mock(jobs)

        call_count = 0

        async def side_effect(job_id: str, client: object) -> list[object]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("fail first")
            return []

        with patch(
            "src.dedup.orchestrator.find_fuzzy_candidates",
            new_callable=AsyncMock,
            side_effect=side_effect,
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        assert stats["errors"] == 1
        assert stats["total_scanned"] == 2


# ===========================================================================
# Stage 3: MinHash/LSH paths
# ===========================================================================


class TestMinHashStage:
    """Stage 3 MinHash/LSH within the orchestrator."""

    @pytest.mark.asyncio
    async def test_minhash_disabled(self) -> None:
        """use_minhash=False skips MinHash stage entirely."""
        job = _make_job()
        db = _make_db_mock([job])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index") as mock_build,
        ):
            stats = await run_advanced_dedup(db, use_minhash=False)

        mock_build.assert_not_called()
        assert stats["minhash_candidates"] == 0

    @pytest.mark.asyncio
    async def test_minhash_candidates_counted(self) -> None:
        """LSH candidates are counted in stats."""
        job_a = _make_job("job-a", title="Python Developer", description="Build Python apps for cloud platform.")
        job_b = _make_job("job-b", title="Python Developer", description="Build Python apps for cloud services.")
        db = _make_db_mock([job_a, job_b])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index") as mock_build,
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=["job-b"],
            ),
            patch("src.dedup.orchestrator.compute_minhash") as mock_mh,
            patch(
                "src.dedup.orchestrator.compute_local_duplicate_score",
                return_value=0.40,  # below threshold
            ),
        ):
            mock_build.return_value = MagicMock()
            mock_mh.return_value = MagicMock()

            stats = await run_advanced_dedup(db, use_minhash=True)

        assert stats["minhash_candidates"] >= 1

    @pytest.mark.asyncio
    async def test_minhash_marks_duplicate_above_threshold(self) -> None:
        """MinHash candidates above threshold get marked as duplicates."""
        job_a = _make_job("job-a", title="Python Dev", company="Acme")
        job_b = _make_job("job-b", title="Python Dev", company="Acme")
        db = _make_db_mock([job_a, job_b])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=["job-b"],
            ),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ),
            patch(
                "src.dedup.orchestrator.compute_local_duplicate_score",
                return_value=0.85,  # above threshold
            ),
            patch(
                "src.dedup.orchestrator.pick_canonical",
                return_value=("job-a", "job-b"),
            ),
            patch(
                "src.dedup.orchestrator.mark_duplicate",
                new_callable=AsyncMock,
            ) as mock_mark,
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        assert stats["duplicates_marked"] >= 1
        mock_mark.assert_awaited()

    @pytest.mark.asyncio
    async def test_minhash_skips_empty_description(self) -> None:
        """Jobs with empty description_plain are skipped in MinHash stage."""
        job_a = _make_job("job-a", description="")
        job_b = _make_job("job-b", description="Real description here for matching.")
        db = _make_db_mock([job_a, job_b])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=[],
            ),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ) as mock_mh,
        ):
            await run_advanced_dedup(db, use_minhash=True)

        # compute_minhash should only be called for job_b (non-empty description)
        assert mock_mh.call_count == 1

    @pytest.mark.asyncio
    async def test_minhash_candidate_not_in_jobs_skipped(self) -> None:
        """LSH candidate ID not found in jobs list is safely skipped."""
        job_a = _make_job("job-a")
        db = _make_db_mock([job_a])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=["nonexistent-id"],  # not in jobs
            ),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ),
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        # Should not crash and no duplicates marked
        assert stats["duplicates_marked"] == 0
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_minhash_error_increments_error_count(self) -> None:
        """Error in MinHash stage increments errors counter."""
        job = _make_job()
        db = _make_db_mock([job])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.dedup.orchestrator.build_lsh_index",
                side_effect=RuntimeError("LSH build failed"),
            ),
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        assert stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_minhash_below_threshold_not_marked(self) -> None:
        """MinHash candidates below threshold are NOT marked."""
        job_a = _make_job("job-a", title="Python Dev")
        job_b = _make_job("job-b", title="Java Dev")
        db = _make_db_mock([job_a, job_b])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=["job-b"],
            ),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ),
            patch(
                "src.dedup.orchestrator.compute_local_duplicate_score",
                return_value=0.30,  # well below 0.65
            ),
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        assert stats["duplicates_marked"] == 0


# ===========================================================================
# Combined / edge cases
# ===========================================================================


class TestCombinedPipeline:
    """End-to-end orchestrator behaviour with both stages."""

    @pytest.mark.asyncio
    async def test_both_stages_contribute_to_stats(self) -> None:
        """Both fuzzy and minhash stages add to stats."""
        job_a = _make_job("job-a", title="Data Engineer")
        job_b = _make_job("job-b", title="Data Engineer")
        db = _make_db_mock([job_a, job_b])

        fuzzy_candidates = [{"id": "fuzzy-dup", "dup_score": 0.70}]

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=fuzzy_candidates,
            ),
            patch(
                "src.dedup.orchestrator.pick_canonical",
                return_value=("job-a", "job-b"),
            ),
            patch(
                "src.dedup.orchestrator.mark_duplicate",
                new_callable=AsyncMock,
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.find_lsh_candidates",
                return_value=["job-b"],
            ),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ),
            patch(
                "src.dedup.orchestrator.compute_local_duplicate_score",
                return_value=0.80,
            ),
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        assert stats["fuzzy_candidates"] >= 1
        assert stats["minhash_candidates"] >= 1
        assert stats["duplicates_marked"] >= 1

    @pytest.mark.asyncio
    async def test_batch_size_passed_to_query(self) -> None:
        """Custom batch_size is used in the DB query."""
        db = _make_db_mock([])
        chain = db.table.return_value
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain

        await run_advanced_dedup(db, batch_size=250, use_minhash=False)

        chain.limit.assert_called_with(250)

    @pytest.mark.asyncio
    async def test_whitespace_only_description_skipped_in_minhash(self) -> None:
        """Whitespace-only descriptions are treated as empty in MinHash."""
        job = _make_job("job-1", description="   \n\t  ")
        db = _make_db_mock([job])

        with (
            patch(
                "src.dedup.orchestrator.find_fuzzy_candidates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.dedup.orchestrator.build_lsh_index", return_value=MagicMock()),
            patch(
                "src.dedup.orchestrator.compute_minhash",
                return_value=MagicMock(),
            ) as mock_mh,
        ):
            stats = await run_advanced_dedup(db, use_minhash=True)

        mock_mh.assert_not_called()
        assert stats["minhash_candidates"] == 0
