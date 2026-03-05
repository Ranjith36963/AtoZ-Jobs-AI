"""Tests for Jooble collector and adapter (GATES C3, C7, C9, C10)."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from src.models.job import JobBase, JoobleJobAdapter

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def jooble_fixture() -> dict[str, object]:
    """Load Jooble API response fixture."""
    with open(FIXTURES / "jooble_response.json") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture()
def jooble_job_data(jooble_fixture: dict[str, object]) -> dict[str, object]:
    """Single Jooble job from fixture."""
    jobs = jooble_fixture["jobs"]
    assert isinstance(jobs, list)
    return jobs[0]  # type: ignore[no-any-return]


class TestJoobleAdapter:
    """Test JoobleJobAdapter.to_job_base() mapping (Gate C3)."""

    def test_maps_fixture_to_job_base(self, jooble_job_data: dict[str, object]) -> None:
        """Maps Jooble JSON to JobBase with zero validation errors."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)

        assert isinstance(job, JobBase)
        assert job.source_name == "jooble"
        assert job.external_id == "jb-7890123456"
        assert job.title == "DevOps Engineer"
        assert job.company_name == "CloudOps Scotland"
        assert job.location_raw == "Edinburgh, Scotland"

    def test_salary_raw_preserved(self, jooble_job_data: dict[str, object]) -> None:
        """Jooble salary string preserved as salary_raw."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert job.salary_raw == "£50,000 - £70,000"

    def test_empty_salary(self, jooble_fixture: dict[str, object]) -> None:
        """Empty salary string → salary_raw is None."""
        jobs = jooble_fixture["jobs"]
        assert isinstance(jobs, list)
        job = JoobleJobAdapter.to_job_base(jobs[1])
        assert job.salary_raw is None

    def test_employment_type(self, jooble_job_data: dict[str, object]) -> None:
        """Job type mapped to employment_type."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert "full_time" in job.employment_type

    def test_snippet_as_description(self, jooble_job_data: dict[str, object]) -> None:
        """Jooble snippet used as both description and description_plain."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert job.description == job.description_plain
        assert "DevOps" in job.description

    def test_content_hash_stable(self, jooble_job_data: dict[str, object]) -> None:
        """Content hash stable (Gate C7)."""
        job1 = JoobleJobAdapter.to_job_base(jooble_job_data)
        job2 = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert job1.content_hash == job2.content_hash

    def test_raw_data_preserved(self, jooble_job_data: dict[str, object]) -> None:
        """raw_data preserved."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert job.raw_data == jooble_job_data

    def test_30_day_default_expiry(self, jooble_job_data: dict[str, object]) -> None:
        """Jooble uses 30-day default expiry per SPEC §6."""
        job = JoobleJobAdapter.to_job_base(jooble_job_data)
        assert job.date_posted is not None
        assert job.date_expires is not None
        assert job.date_expires - job.date_posted == timedelta(days=30)


class TestJoobleCollector:
    """Test Jooble collector — paginate until empty (Gate C3, C10)."""

    @pytest.mark.asyncio()
    async def test_paginate_until_empty(self) -> None:
        """Jooble has no totalResults — paginate until empty results array."""
        from src.collectors.jooble import JoobleCollector

        page_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal page_count
            page_count += 1
            if page_count <= 2:
                return httpx.Response(
                    200,
                    json={
                        "jobs": [
                            {
                                "id": f"jb-{page_count}",
                                "title": "Test Job",
                                "snippet": "Description",
                                "company": "TestCo",
                                "location": "London",
                                "link": "https://example.com",
                                "updated": "2026-03-05",
                            }
                        ]
                    },
                )
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_all(keyword="python")
            assert len(jobs) == 2
            assert page_count == 3  # 2 pages with data + 1 empty

    @pytest.mark.asyncio()
    async def test_empty_results_first_page(self) -> None:
        """Empty results on first page handled."""
        from src.collectors.jooble import JoobleCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_all(keyword="nonexistent")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_no_total_results_field(self) -> None:
        """Response has no totalResults field — should not crash."""
        from src.collectors.jooble import JoobleCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_all(keyword="test")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_timeout_handling(self) -> None:
        """Timeout handled."""
        from src.collectors.jooble import JoobleCollector

        async def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

        transport = httpx.MockTransport(timeout_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            with pytest.raises(Exception):
                await collector.fetch_all(keyword="test")

    @pytest.mark.asyncio()
    async def test_malformed_json(self) -> None:
        """Malformed JSON response handled without crash (Gate C10)."""
        from src.collectors.jooble import JoobleCollector

        async def malformed_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not valid json {{{")

        transport = httpx.MockTransport(malformed_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            with pytest.raises(Exception):
                await collector.fetch_all(keyword="test")


def _make_jooble_job(n: int) -> JobBase:
    """Create a minimal valid JobBase for orchestration tests."""
    return JobBase(
        source_name="jooble",
        external_id=str(n),
        source_url=f"https://jooble.org/jdp/{n}",
        title=f"Test Job {n}",
        description=f"Description {n}",
        description_plain=f"Description {n}",
        company_name="TestCo",
        location_raw="London",
        raw_data={"id": n},
    )


class TestJoobleCollectorCoverage:
    """Coverage tests for Jooble collector internals."""

    @pytest.mark.asyncio()
    async def test_circuit_breaker_open_returns_empty(self) -> None:
        """Open circuit breaker → fetch_all returns [] immediately."""
        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.jooble import JoobleCollector

        breaker = CircuitBreaker(name="jooble", failure_threshold=1)
        breaker.record_failure()

        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(
                client=client, api_key="test-key", circuit_breaker=breaker
            )
            jobs = await collector.fetch_all(keyword="python")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_fetch_all_success_with_adapter(
        self, jooble_fixture: dict[str, object]
    ) -> None:
        """fetch_all parses response through adapter and returns JobBase list."""
        from src.collectors.jooble import JoobleCollector

        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json=jooble_fixture)
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_all(keyword="devops")
            assert len(jobs) == 2
            assert all(isinstance(j, JobBase) for j in jobs)
            assert jobs[0].title == "DevOps Engineer"

    @pytest.mark.asyncio()
    async def test_non_list_jobs_raises_parse_error(self) -> None:
        """Non-list 'jobs' field raises ParseError."""
        from src.collectors.jooble import JoobleCollector
        from src.models.errors import ParseError

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": "not a list"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            with pytest.raises(ParseError):
                await collector.fetch_all(keyword="test")

    @pytest.mark.asyncio()
    async def test_adapter_error_skips_bad_job(
        self, jooble_fixture: dict[str, object]
    ) -> None:
        """Invalid job in results is skipped; valid jobs pass through."""
        from src.collectors.jooble import JoobleCollector

        bad_job = {
            "id": "bad",
            "title": "",
            "snippet": "x",
            "company": "A",
            "location": "L",
            "link": "https://x.com",
            "updated": "2026-03-05",
        }
        jobs_data = list(jooble_fixture["jobs"])  # type: ignore[arg-type]
        fixture = {"jobs": [bad_job, *jobs_data]}
        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json=fixture)
            return httpx.Response(200, json={"jobs": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_all(keyword="test")
            assert len(jobs) == 2  # bad job skipped

    @pytest.mark.asyncio()
    async def test_timeout_records_circuit_breaker_failure(self) -> None:
        """TimeoutException records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.jooble import JoobleCollector
        from src.models.errors import SourceTimeoutError

        breaker = CircuitBreaker(name="jooble")
        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(
                client=client, api_key="test-key", circuit_breaker=breaker
            )
            with patch(
                "src.collectors.jooble.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(SourceTimeoutError):
                    await collector.fetch_all(keyword="test")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_429_records_rate_limit(self) -> None:
        """429 HTTPStatusError records rate limit on circuit breaker."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.jooble import JoobleCollector

        breaker = CircuitBreaker(name="jooble")
        mock_request = httpx.Request("POST", "https://jooble.org/api/key")
        mock_response = httpx.Response(429, text="Rate limited", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(
                client=client, api_key="test-key", circuit_breaker=breaker
            )
            with patch(
                "src.collectors.jooble.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "429", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_all(keyword="test")
            assert breaker._failure_count == 0

    @pytest.mark.asyncio()
    async def test_5xx_records_circuit_breaker_failure(self) -> None:
        """500 HTTPStatusError records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.jooble import JoobleCollector

        breaker = CircuitBreaker(name="jooble")
        mock_request = httpx.Request("POST", "https://jooble.org/api/key")
        mock_response = httpx.Response(500, text="Error", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(
                client=client, api_key="test-key", circuit_breaker=breaker
            )
            with patch(
                "src.collectors.jooble.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "500", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_all(keyword="test")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_generic_exception_records_failure(self) -> None:
        """Generic exception records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.jooble import JoobleCollector

        breaker = CircuitBreaker(name="jooble")
        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(
                client=client, api_key="test-key", circuit_breaker=breaker
            )
            with patch(
                "src.collectors.jooble.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = RuntimeError("unexpected")
                with pytest.raises(RuntimeError):
                    await collector.fetch_all(keyword="test")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_sweep_all_iterates_keywords(self) -> None:
        """sweep_all calls fetch_all for every Jooble keyword."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.jooble import JOOBLE_KEYWORDS, JoobleCollector

        async with httpx.AsyncClient() as client:
            collector = JoobleCollector(client=client, api_key="test-key")
            with patch.object(
                collector, "fetch_all", new_callable=AsyncMock
            ) as mock_fa:
                mock_fa.return_value = [_make_jooble_job(1)]
                jobs = await collector.sweep_all()
                assert len(jobs) == len(JOOBLE_KEYWORDS)
                assert mock_fa.call_count == len(JOOBLE_KEYWORDS)

    def test_date_only_format_parsing(self) -> None:
        """Jooble date '2024-01-15' (no time) parsed via fallback."""
        job = JoobleJobAdapter.to_job_base(
            {
                "id": "test-date",
                "title": "Date Test Job",
                "snippet": "Testing date parsing",
                "company": "TestCo",
                "location": "London",
                "link": "https://example.com",
                "updated": "2024-01-15",
            }
        )
        assert job.date_posted is not None
        assert job.date_posted.year == 2024
        assert job.date_posted.month == 1
        assert job.date_posted.day == 15
