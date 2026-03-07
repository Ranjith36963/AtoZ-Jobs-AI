"""Tests for dedup orchestrator (PLAYBOOK §2.4)."""

from unittest.mock import MagicMock

import pytest

from src.dedup.orchestrator import _simple_similarity, run_advanced_dedup


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


class TestRunAdvancedDedup:
    """Orchestrator integration tests."""

    @pytest.mark.asyncio
    async def test_no_jobs_returns_zero_stats(self) -> None:
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        stats = await run_advanced_dedup(db, use_minhash=False)
        assert stats["total_scanned"] == 0
        assert stats["duplicates_marked"] == 0

    @pytest.mark.asyncio
    async def test_stats_structure(self) -> None:
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        stats = await run_advanced_dedup(db, use_minhash=False)
        assert "total_scanned" in stats
        assert "fuzzy_candidates" in stats
        assert "minhash_candidates" in stats
        assert "duplicates_marked" in stats
        assert "errors" in stats
