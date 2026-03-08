"""Tests for search orchestrator (SPEC.md §6, Gates R14-R15)."""

from typing import Any

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_db(search_results: list[dict[str, Any]] | None = None) -> MagicMock:
    """Create a mock DB client with search_jobs_v2 RPC."""
    if search_results is None:
        search_results = [
            {
                "id": 1,
                "title": "Python Developer",
                "company_name": "TechCo",
                "description_plain": "Python Django role",
                "location_city": "London",
                "location_region": "London",
                "location_type": "hybrid",
                "salary_annual_min": 50000,
                "salary_annual_max": 70000,
                "rrf_score": 0.04,
            },
            {
                "id": 2,
                "title": "Senior Python Engineer",
                "company_name": "BigCorp",
                "description_plain": "Backend Python AWS",
                "location_city": "London",
                "location_region": "London",
                "location_type": "remote",
                "salary_annual_min": 70000,
                "salary_annual_max": 90000,
                "rrf_score": 0.03,
            },
        ]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = search_results
    return mock_db


class TestSearchOrchestrator:
    """Full search pipeline tests."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self) -> None:
        """Query → embed → search → rerank → results."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db()
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.return_value = [
                {"id": 2, "title": "Senior Python Engineer", "rerank_score": 0.95},
                {"id": 1, "title": "Python Developer", "rerank_score": 0.80},
            ]

            result = await search(
                query="Python developer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert "results" in result
        assert "total" in result
        assert "latency_ms" in result
        assert len(result["results"]) == 2
        mock_embed.assert_called_once_with("Python developer")
        mock_db.rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation(self) -> None:
        """Gate R14: Reranker fails → returns RRF results."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db()
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.side_effect = RuntimeError("Model not available")

            result = await search(
                query="Python developer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert len(result["results"]) == 2
        assert result["total"] == 2
        # No rerank_score since reranker failed
        assert "rerank_score" not in result["results"][0]

    @pytest.mark.asyncio
    async def test_with_filters(self) -> None:
        """Filters passed through to search_jobs_v2."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db()
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.return_value = (
                mock_db.rpc.return_value.execute.return_value.data[:20]
            )

            await search(
                query="developer",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={
                    "min_salary": 50000,
                    "category_filter": "IT Jobs",
                    "exclude_duplicates": True,
                },
            )

        rpc_call = mock_db.rpc.call_args
        params = rpc_call[0][1]
        assert params["min_salary"] == 50000
        assert params["category_filter"] == "IT Jobs"
        assert params["exclude_duplicates"] is True

    @pytest.mark.asyncio
    async def test_latency_tracked(self) -> None:
        """Response includes latency_ms."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        result = await search(
            query="test",
            db_client=mock_db,
            embed_fn=mock_embed,
        )

        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], float)
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_empty_query_with_filters(self) -> None:
        """Empty query + filters → returns results without embedding."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db()

        result = await search(
            query="",
            db_client=mock_db,
            embed_fn=None,
            filters={"category_filter": "Healthcare"},
        )

        assert result["total"] == 2
        # No re-ranking when query is empty
        rpc_params = mock_db.rpc.call_args[0][1]
        assert rpc_params["query_text"] is None
        assert rpc_params["query_embedding"] is None

    @pytest.mark.asyncio
    async def test_embed_failure_continues(self) -> None:
        """Embedding failure → search continues without embedding."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db()
        mock_embed = AsyncMock(side_effect=Exception("Gemini API down"))

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.return_value = (
                mock_db.rpc.return_value.execute.return_value.data[:20]
            )

            result = await search(
                query="developer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert result["total"] == 2
        rpc_params = mock_db.rpc.call_args[0][1]
        assert rpc_params["query_embedding"] is None

    @pytest.mark.asyncio
    async def test_no_results(self) -> None:
        """No search results → empty response."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        result = await search(
            query="nonexistent xyz",
            db_client=mock_db,
            embed_fn=mock_embed,
        )

        assert result["results"] == []
        assert result["total"] == 0
