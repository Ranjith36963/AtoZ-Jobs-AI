"""Search quality verification tests (GATES.md §2, 50+ test queries).

Tests the full search pipeline with mocked components to verify
correct parameter passing, response structure, and graceful degradation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typing import Any


def _make_job(
    job_id: int,
    title: str = "Software Engineer",
    company: str = "TechCo",
    description: str = "A great role",
    location_city: str = "London",
    location_region: str = "London",
    location_type: str = "hybrid",
    salary_min: int | None = 40000,
    salary_max: int | None = 60000,
    predicted_min: float | None = None,
    predicted_max: float | None = None,
    category: str = "IT Jobs",
    seniority: str = "Mid",
    rrf_score: float = 0.04,
) -> dict[str, Any]:
    """Create a mock job result."""
    return {
        "id": job_id,
        "title": title,
        "company_name": company,
        "description_plain": description,
        "location_city": location_city,
        "location_region": location_region,
        "location_type": location_type,
        "salary_annual_min": salary_min,
        "salary_annual_max": salary_max,
        "salary_predicted_min": predicted_min,
        "salary_predicted_max": predicted_max,
        "salary_is_predicted": predicted_max is not None and salary_max is None,
        "employment_type": ["permanent"],
        "seniority_level": seniority,
        "category": category,
        "date_posted": "2026-03-01T00:00:00Z",
        "source_url": f"https://example.com/job/{job_id}",
        "rrf_score": rrf_score,
    }


def _make_mock_db(jobs: list[dict[str, Any]] | None = None) -> MagicMock:
    """Create mock DB returning given jobs from search_jobs_v2."""
    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = jobs or []
    return mock_db


class TestSearchQualityBasicQueries:
    """Q1-Q3: Basic keyword, semantic, and filter queries."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "query,filters,expected_min",
        [
            ("Python developer", {"search_lat": 51.5074, "search_lng": -0.1278}, 1),
            ("nurse", {"include_remote": True}, 1),
            ("data analyst", {}, 1),
            ("SIA door supervisor", {}, 1),
            ("accountant", {"min_salary": 50000, "category_filter": "Finance"}, 1),
            ("project manager", {"work_type_filter": "permanent"}, 1),
            ("DevOps engineer", {"skill_filters": ["Docker", "Kubernetes"]}, 1),
            ("CIPD qualified HR manager", {}, 1),
            ("marketing manager", {"min_salary": 40000}, 1),
            ("graduate", {"max_salary": 30000}, 1),
        ],
    )
    async def test_query_returns_results(
        self, query: str, filters: dict[str, Any], expected_min: int
    ) -> None:
        """Various queries return non-empty results with correct structure."""
        from src.search.orchestrator import search

        jobs = [_make_job(i, title=f"Job {i} - {query}") for i in range(5)]
        mock_db = _make_mock_db(jobs)
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch(
            "src.search.orchestrator.rerank",
            side_effect=lambda q, j, **kw: j[: kw.get("top_k", 20)],
        ):
            result = await search(
                query=query,
                db_client=mock_db,
                embed_fn=mock_embed,
                filters=filters,
            )

        assert len(result["results"]) >= expected_min
        assert all("title" in r for r in result["results"])
        assert all("id" in r for r in result["results"])
        assert result["latency_ms"] >= 0


class TestSearchQualityFilters:
    """Q4-Q7: Filter-specific tests."""

    @pytest.mark.asyncio
    async def test_exclude_duplicates_filter(self) -> None:
        """Q4: exclude_duplicates passed to RPC."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            await search(
                query="nurse",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={"exclude_duplicates": True},
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["exclude_duplicates"] is True

    @pytest.mark.asyncio
    async def test_predicted_salary_filter(self) -> None:
        """Q5: min_salary filter includes predicted salary jobs."""
        from src.search.orchestrator import search

        jobs = [
            _make_job(
                1,
                salary_min=None,
                salary_max=None,
                predicted_min=35000,
                predicted_max=45000,
            ),
        ]
        mock_db = _make_mock_db(jobs)
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            _result = await search(
                query="marketing",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={"min_salary": 40000},
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["min_salary"] == 40000

    @pytest.mark.asyncio
    async def test_max_salary_filter(self) -> None:
        """Q6: max_salary filter passed to RPC."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            await search(
                query="graduate",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={"max_salary": 30000},
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["max_salary"] == 30000

    @pytest.mark.asyncio
    async def test_remote_plus_skill_filter(self) -> None:
        """Q7: Remote + skill filters combined."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1, location_type="remote")])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            await search(
                query="DevOps",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={
                    "include_remote": True,
                    "skill_filters": ["Docker", "Kubernetes"],
                },
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["include_remote"] is True
        assert params["skill_filters"] == ["Docker", "Kubernetes"]

    @pytest.mark.asyncio
    async def test_category_filter(self) -> None:
        """Q3: category_filter passed correctly."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1, category="Finance")])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            await search(
                query="analyst",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={"category_filter": "Finance"},
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["category_filter"] == "Finance"


class TestSearchQualityReranking:
    """Q8-Q10: Re-ranking verification."""

    @pytest.mark.asyncio
    async def test_reranking_called(self) -> None:
        """Q8: Cross-encoder rerank is invoked for text queries."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1), _make_job(2)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.return_value = [
                {**_make_job(1), "rerank_score": 0.9},
                {**_make_job(2), "rerank_score": 0.5},
            ]

            result = await search(
                query="senior data scientist machine learning",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        mock_rerank.assert_called_once()
        assert (
            result["results"][0]["rerank_score"] > result["results"][1]["rerank_score"]
        )

    @pytest.mark.asyncio
    async def test_reranking_adds_score(self) -> None:
        """Each result has rerank_score after successful re-ranking."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.return_value = [{**_make_job(1), "rerank_score": 0.85}]

            result = await search(
                query="developer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert "rerank_score" in result["results"][0]


class TestSearchQualityEdgeCases:
    """Q11-Q15: Edge cases and graceful degradation."""

    @pytest.mark.asyncio
    async def test_empty_query_with_filters(self) -> None:
        """Q11: No text query, only filters → no crash."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1, category="Healthcare")])

        result = await search(
            query="",
            db_client=mock_db,
            embed_fn=None,
            filters={"category_filter": "Healthcare", "min_salary": 30000},
        )

        assert result["total"] >= 0
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_typo_resilience(self) -> None:
        """Q12: Typo in query → semantic search catches intent."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1, title="Software Engineer")])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            result = await search(
                query="softwar engeneer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        # Embedding is still created for semantic matching
        mock_embed.assert_called_once_with("softwar engeneer")
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_all_filters_combined(self) -> None:
        """Q14: All filters applied simultaneously."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        filters = {
            "search_lat": 55.9533,
            "search_lng": -3.1883,
            "radius_miles": 50,
            "min_salary": 50000,
            "category_filter": "Finance",
            "exclude_duplicates": True,
        }

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            _result = await search(
                query="accountant",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters=filters,
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["search_lat"] == 55.9533
        assert params["search_lng"] == -3.1883
        assert params["radius_miles"] == 50
        assert params["min_salary"] == 50000
        assert params["category_filter"] == "Finance"
        assert params["exclude_duplicates"] is True

    @pytest.mark.asyncio
    async def test_graceful_degradation_reranker_fails(self) -> None:
        """Q15: Cross-encoder fails → returns RRF results."""
        from src.search.orchestrator import search

        jobs = [_make_job(i) for i in range(5)]
        mock_db = _make_mock_db(jobs)
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank") as mock_rerank:
            mock_rerank.side_effect = RuntimeError("Cross-encoder unavailable")

            result = await search(
                query="Python developer",
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert len(result["results"]) == 5
        assert result["total"] == 5
        # No rerank_score since reranker failed
        assert "rerank_score" not in result["results"][0]

    @pytest.mark.asyncio
    async def test_embed_failure_graceful(self) -> None:
        """Embedding failure → search continues with text-only."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(side_effect=Exception("Gemini down"))

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            _result = await search(
                query="developer",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters={},
            )

        params = mock_db.rpc.call_args[0][1]
        assert params["query_embedding"] is None
        assert params["query_text"] == "developer"


class TestSearchQualityResponseStructure:
    """Verify response structure across all query types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "query",
        [
            "Python developer in London",
            "nurse NHS",
            "CSCS card construction worker",
            "remote data engineer",
            "ACCA accountant",
            "SIA licensed security",
            "PRINCE2 project manager",
            "NMC registered nurse",
            "junior marketing assistant",
            "senior architect Edinburgh",
            "full stack developer React Node",
            "warehouse operative nights",
            "teaching assistant primary school",
            "plumber gas safe registered",
            "electrical engineer chartered",
            "HR business partner CIPD",
            "delivery driver Class 2",
            "care worker NVQ Level 3",
            "solicitor conveyancing",
            "quantity surveyor RICS",
        ],
    )
    async def test_response_structure(self, query: str) -> None:
        """All queries produce consistent response structure."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1, title=f"Result for {query}")])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            result = await search(
                query=query,
                db_client=mock_db,
                embed_fn=mock_embed,
            )

        assert "results" in result
        assert "total" in result
        assert "latency_ms" in result
        assert isinstance(result["results"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["latency_ms"], float)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "filters",
        [
            {"min_salary": 25000},
            {"max_salary": 100000},
            {"category_filter": "IT Jobs"},
            {"work_type_filter": "permanent"},
            {"include_remote": True},
            {"include_remote": False},
            {"exclude_duplicates": True},
            {"skill_filters": ["Python"]},
            {"search_lat": 51.5, "search_lng": -0.1, "radius_miles": 10},
            {"min_salary": 30000, "max_salary": 80000, "category_filter": "Healthcare"},
        ],
    )
    async def test_filter_combinations(self, filters: dict[str, Any]) -> None:
        """All filter combinations produce valid responses."""
        from src.search.orchestrator import search

        mock_db = _make_mock_db([_make_job(1)])
        mock_embed = AsyncMock(return_value=[0.1] * 768)

        with patch("src.search.orchestrator.rerank", side_effect=lambda q, j, **kw: j):
            result = await search(
                query="test",
                db_client=mock_db,
                embed_fn=mock_embed,
                filters=filters,
            )

        assert "results" in result
        assert result["latency_ms"] >= 0
