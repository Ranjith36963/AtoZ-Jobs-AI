"""Tests for Careerjet collector and adapter (GATES C4, C7, C9, C10)."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from src.models.job import CareerjetJobAdapter, JobBase

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def careerjet_fixture() -> dict[str, object]:
    """Load Careerjet API response fixture."""
    with open(FIXTURES / "careerjet_response.json") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture()
def careerjet_job_data(careerjet_fixture: dict[str, object]) -> dict[str, object]:
    """Single Careerjet job from fixture."""
    jobs = careerjet_fixture["jobs"]
    assert isinstance(jobs, list)
    return jobs[0]  # type: ignore[no-any-return]


class TestCareerjetAdapter:
    """Test CareerjetJobAdapter.to_job_base() mapping (Gate C4)."""

    def test_maps_fixture_to_job_base(
        self, careerjet_job_data: dict[str, object]
    ) -> None:
        """Maps Careerjet JSON to JobBase with zero validation errors."""
        job = CareerjetJobAdapter.to_job_base(careerjet_job_data)

        assert isinstance(job, JobBase)
        assert job.source_name == "careerjet"
        assert job.title == "Backend Engineer - Go/Python"
        assert job.company_name == "FinTech Solutions"
        assert job.location_raw == "Birmingham, West Midlands"

    def test_structured_salary_fields(
        self, careerjet_job_data: dict[str, object]
    ) -> None:
        """v4 structured salary fields extracted correctly."""
        job = CareerjetJobAdapter.to_job_base(careerjet_job_data)

        assert job.salary_min == 60000.0
        assert job.salary_max == 80000.0
        assert job.salary_currency == "GBP"
        assert job.salary_period == "annual"

    def test_null_salary_fields(self, careerjet_fixture: dict[str, object]) -> None:
        """Null salary fields → None."""
        jobs = careerjet_fixture["jobs"]
        assert isinstance(jobs, list)
        job = CareerjetJobAdapter.to_job_base(jobs[1])

        assert job.salary_min is None
        assert job.salary_max is None
        assert job.salary_currency is None
        assert job.salary_period is None

    def test_salary_raw_preserved(self, careerjet_job_data: dict[str, object]) -> None:
        """salary string preserved as salary_raw."""
        job = CareerjetJobAdapter.to_job_base(careerjet_job_data)
        assert job.salary_raw == "£60,000 - £80,000 per annum"

    def test_content_hash_stable(self, careerjet_job_data: dict[str, object]) -> None:
        """Content hash stable (Gate C7)."""
        job1 = CareerjetJobAdapter.to_job_base(careerjet_job_data)
        job2 = CareerjetJobAdapter.to_job_base(careerjet_job_data)
        assert job1.content_hash == job2.content_hash
        assert len(job1.content_hash) == 64

    def test_raw_data_preserved(self, careerjet_job_data: dict[str, object]) -> None:
        """raw_data preserved."""
        job = CareerjetJobAdapter.to_job_base(careerjet_job_data)
        assert job.raw_data == careerjet_job_data

    def test_30_day_default_expiry(self, careerjet_job_data: dict[str, object]) -> None:
        """Careerjet uses 30-day default expiry per SPEC §6."""
        job = CareerjetJobAdapter.to_job_base(careerjet_job_data)
        assert job.date_posted is not None
        assert job.date_expires is not None
        assert job.date_expires - job.date_posted == timedelta(days=30)


class TestCareerjetCollector:
    """Test Careerjet collector (Gate C4, C10)."""

    @pytest.mark.asyncio()
    async def test_user_ip_and_user_agent_required(self) -> None:
        """v4 requires user_ip and user_agent in request params."""
        from src.collectors.careerjet import CareerjetCollector

        captured_params: dict[str, str] = {}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            # Capture query params
            for key in ("user_ip", "user_agent"):
                val = request.url.params.get(key)
                if val:
                    captured_params[key] = val
            return httpx.Response(200, json={"jobs": [], "hits": 0, "pages": 0})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs-Pipeline/0.1",
            )
            await collector.fetch_page(keywords="python", page=1)
            assert "user_ip" in captured_params
            assert "user_agent" in captured_params
            assert captured_params["user_ip"] == "10.0.0.1"

    @pytest.mark.asyncio()
    async def test_empty_results(self) -> None:
        """Empty results handled."""
        from src.collectors.careerjet import CareerjetCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": [], "hits": 0, "pages": 0})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            jobs = await collector.fetch_page(keywords="nonexistent", page=1)
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_timeout_handling(self) -> None:
        """Timeout handled."""
        from src.collectors.careerjet import CareerjetCollector

        async def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

        transport = httpx.MockTransport(timeout_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            with pytest.raises(Exception):
                await collector.fetch_page(keywords="test", page=1)

    @pytest.mark.asyncio()
    async def test_pagination(self) -> None:
        """Pagination works via offset/page params."""
        from src.collectors.careerjet import CareerjetCollector

        assert CareerjetCollector.has_more_pages(current_page=1, total_pages=5)
        assert not CareerjetCollector.has_more_pages(current_page=5, total_pages=5)
        assert not CareerjetCollector.has_more_pages(current_page=1, total_pages=0)

    @pytest.mark.asyncio()
    async def test_malformed_json(self) -> None:
        """Malformed JSON response handled without crash (Gate C10)."""
        from src.collectors.careerjet import CareerjetCollector

        async def malformed_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not valid json {{{")

        transport = httpx.MockTransport(malformed_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            with pytest.raises(Exception):
                await collector.fetch_page(keywords="test", page=1)


def _make_careerjet_job(n: int) -> JobBase:
    """Create a minimal valid JobBase for orchestration tests."""
    return JobBase(
        source_name="careerjet",
        external_id=f"https://careerjet.co.uk/{n}",
        source_url=f"https://careerjet.co.uk/{n}",
        title=f"Test Job {n}",
        description=f"Description {n}",
        description_plain=f"Description {n}",
        company_name="TestCo",
        location_raw="London",
        raw_data={"url": f"https://careerjet.co.uk/{n}"},
    )


class TestCareerjetCollectorCoverage:
    """Coverage tests for Careerjet collector internals."""

    @pytest.mark.asyncio()
    async def test_circuit_breaker_open_returns_empty(self) -> None:
        """Open circuit breaker → fetch_page returns [] immediately."""
        from src.collectors.careerjet import CareerjetCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="careerjet", failure_threshold=1)
        breaker.record_failure()

        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
                circuit_breaker=breaker,
            )
            jobs = await collector.fetch_page(keywords="python", page=1)
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_fetch_page_success_with_adapter(
        self, careerjet_fixture: dict[str, object]
    ) -> None:
        """fetch_page parses response through adapter and returns JobBase list."""
        from src.collectors.careerjet import CareerjetCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=careerjet_fixture)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            jobs = await collector.fetch_page(keywords="backend", page=1)
            assert len(jobs) == 2
            assert all(isinstance(j, JobBase) for j in jobs)
            assert jobs[0].title == "Backend Engineer - Go/Python"

    @pytest.mark.asyncio()
    async def test_non_list_jobs_raises_parse_error(self) -> None:
        """Non-list 'jobs' field raises ParseError."""
        from src.collectors.careerjet import CareerjetCollector
        from src.models.errors import ParseError

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": "not a list", "hits": 0})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            with pytest.raises(ParseError):
                await collector.fetch_page(keywords="test", page=1)

    @pytest.mark.asyncio()
    async def test_adapter_error_skips_bad_job(
        self, careerjet_fixture: dict[str, object]
    ) -> None:
        """Invalid job in results is skipped; valid jobs pass through."""
        from src.collectors.careerjet import CareerjetCollector

        bad_job = {
            "url": "https://bad.com",
            "title": "",
            "description": "x",
            "company": "A",
            "locations": "L",
            "date": "2026-03-05",
        }
        jobs_data = list(careerjet_fixture["jobs"])  # type: ignore[call-overload]
        fixture = {"jobs": [bad_job, *jobs_data], "hits": 3, "pages": 1}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            jobs = await collector.fetch_page(keywords="test", page=1)
            assert len(jobs) == 2  # bad job skipped

    @pytest.mark.asyncio()
    async def test_timeout_records_circuit_breaker_failure(self) -> None:
        """TimeoutException records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import CareerjetCollector
        from src.collectors.circuit_breaker import CircuitBreaker
        from src.models.errors import SourceTimeoutError

        breaker = CircuitBreaker(name="careerjet")
        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.careerjet.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(SourceTimeoutError):
                    await collector.fetch_page(keywords="test", page=1)
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_429_records_rate_limit(self) -> None:
        """429 HTTPStatusError records rate limit on circuit breaker."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import CareerjetCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="careerjet")
        mock_request = httpx.Request("GET", "https://careerjet.net")
        mock_response = httpx.Response(429, text="Rate limited", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.careerjet.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "429", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_page(keywords="test", page=1)
            assert breaker._failure_count == 0

    @pytest.mark.asyncio()
    async def test_5xx_records_circuit_breaker_failure(self) -> None:
        """500 HTTPStatusError records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import CareerjetCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="careerjet")
        mock_request = httpx.Request("GET", "https://careerjet.net")
        mock_response = httpx.Response(500, text="Error", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.careerjet.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "500", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_page(keywords="test", page=1)
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_generic_exception_records_failure(self) -> None:
        """Generic exception records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import CareerjetCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="careerjet")
        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.careerjet.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = RuntimeError("unexpected")
                with pytest.raises(RuntimeError):
                    await collector.fetch_page(keywords="test", page=1)
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_fetch_keyword_location_multi_page(self) -> None:
        """fetch_keyword_location paginates until fewer than 50 results."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import CareerjetCollector

        full_page = [_make_careerjet_job(i) for i in range(50)]
        partial_page = [_make_careerjet_job(i + 50) for i in range(20)]

        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            with patch.object(
                collector, "fetch_page", new_callable=AsyncMock
            ) as mock_fp:
                mock_fp.side_effect = [full_page, partial_page]
                jobs = await collector.fetch_keyword_location("python", "London")
                assert len(jobs) == 70
                assert mock_fp.call_count == 2

    @pytest.mark.asyncio()
    async def test_sweep_all_iterates_keyword_locations(self) -> None:
        """sweep_all iterates all keyword × location combinations."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.careerjet import (
            CAREERJET_KEYWORDS,
            CAREERJET_LOCATIONS,
            CareerjetCollector,
        )

        async with httpx.AsyncClient() as client:
            collector = CareerjetCollector(
                client=client,
                affid="test-affid",
                user_ip="10.0.0.1",
                user_agent="AtoZ-Jobs/0.1",
            )
            with patch.object(
                collector, "fetch_keyword_location", new_callable=AsyncMock
            ) as mock_fkl:
                mock_fkl.return_value = [_make_careerjet_job(1)]
                jobs = await collector.sweep_all()
                expected = len(CAREERJET_KEYWORDS) * len(CAREERJET_LOCATIONS)
                assert len(jobs) == expected
                assert mock_fkl.call_count == expected

    def test_date_only_format_parsing(self) -> None:
        """Careerjet date '2024-01-15' (no time) parsed via fallback."""
        job = CareerjetJobAdapter.to_job_base(
            {
                "url": "https://careerjet.co.uk/test",
                "title": "Date Test Job",
                "description": "Testing date parsing",
                "company": "TestCo",
                "locations": "London",
                "date": "2024-01-15",
            }
        )
        assert job.date_posted is not None
        assert job.date_posted.year == 2024
        assert job.date_posted.month == 1
        assert job.date_posted.day == 15
