"""Tests for Adzuna collector and adapter (GATES C2, C7, C9, C10)."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from src.models.job import AdzunaJobAdapter, JobBase

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def adzuna_fixture() -> dict[str, object]:
    """Load Adzuna API response fixture."""
    with open(FIXTURES / "adzuna_response.json") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture()
def adzuna_job_data(adzuna_fixture: dict[str, object]) -> dict[str, object]:
    """Single Adzuna job from fixture."""
    results = adzuna_fixture["results"]
    assert isinstance(results, list)
    return results[0]  # type: ignore[no-any-return]


class TestAdzunaAdapter:
    """Test AdzunaJobAdapter.to_job_base() mapping (Gate C2)."""

    def test_maps_fixture_to_job_base(self, adzuna_job_data: dict[str, object]) -> None:
        """Maps Adzuna JSON to JobBase with zero validation errors."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)

        assert isinstance(job, JobBase)
        assert job.source_name == "adzuna"
        assert job.external_id == "4987654321"
        assert job.title == "Machine Learning Engineer"
        assert job.company_name == "TechVentures UK"

    def test_latitude_longitude_direct(
        self, adzuna_job_data: dict[str, object]
    ) -> None:
        """Extracts latitude/longitude directly — no postcodes.io needed."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)

        assert job.latitude == pytest.approx(52.2053)
        assert job.longitude == pytest.approx(0.1218)

    def test_salary_is_predicted_false(
        self, adzuna_job_data: dict[str, object]
    ) -> None:
        """salary_is_predicted=0 maps to False."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.salary_is_predicted is False

    def test_salary_is_predicted_true(self, adzuna_fixture: dict[str, object]) -> None:
        """salary_is_predicted=1 maps to True."""
        results = adzuna_fixture["results"]
        assert isinstance(results, list)
        job = AdzunaJobAdapter.to_job_base(results[1])
        assert job.salary_is_predicted is True

    def test_category_tag_mapping(self, adzuna_job_data: dict[str, object]) -> None:
        """Category tag extracted from nested object."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.category_raw == "it-jobs"

    def test_location_display_name(self, adzuna_job_data: dict[str, object]) -> None:
        """Location uses display_name from nested location object."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.location_raw == "Cambridge, Cambridgeshire"

    def test_employment_type(self, adzuna_job_data: dict[str, object]) -> None:
        """Contract type and time map to employment_type."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert "permanent" in job.employment_type
        assert "full_time" in job.employment_type

    def test_45_day_default_expiry(self, adzuna_job_data: dict[str, object]) -> None:
        """No date_expires → 45-day default from date_posted."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)

        assert job.date_posted is not None
        assert job.date_expires is not None
        delta = job.date_expires - job.date_posted
        assert delta == timedelta(days=45)

    def test_company_from_nested_object(
        self, adzuna_job_data: dict[str, object]
    ) -> None:
        """Company name from nested company.display_name."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.company_name == "TechVentures UK"

    def test_raw_data_preserved(self, adzuna_job_data: dict[str, object]) -> None:
        """raw_data preserved for reprocessing."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.raw_data == adzuna_job_data

    def test_content_hash_stable(self, adzuna_job_data: dict[str, object]) -> None:
        """Content hash is stable for identical inputs (Gate C7)."""
        job1 = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        job2 = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job1.content_hash == job2.content_hash
        assert len(job1.content_hash) == 64

    def test_description_is_plain_text(
        self, adzuna_job_data: dict[str, object]
    ) -> None:
        """Adzuna returns plain text — description == description_plain."""
        job = AdzunaJobAdapter.to_job_base(adzuna_job_data)
        assert job.description == job.description_plain


class TestAdzunaCollector:
    """Test Adzuna collector edge cases (Gate C10)."""

    @pytest.mark.asyncio()
    async def test_empty_results(self) -> None:
        """Empty results handled without crash."""
        from src.collectors.adzuna import AdzunaCollector

        empty_response = {"results": [], "count": 0}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=empty_response)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            jobs = await collector.fetch_page(page=1, category="it-jobs")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_pagination_boundary(self) -> None:
        """Exactly 50 results → more pages. <50 → last page."""
        from src.collectors.adzuna import AdzunaCollector

        assert AdzunaCollector.has_more_pages(results_count=50, total_count=200)
        assert not AdzunaCollector.has_more_pages(results_count=30, total_count=200)
        assert not AdzunaCollector.has_more_pages(results_count=0, total_count=0)

    @pytest.mark.asyncio()
    async def test_timeout_handling(self) -> None:
        """Timeout handled properly."""
        from src.collectors.adzuna import AdzunaCollector

        async def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Connection timed out")

        transport = httpx.MockTransport(timeout_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            with pytest.raises(Exception):
                await collector.fetch_page(page=1, category="it-jobs")

    @pytest.mark.asyncio()
    async def test_malformed_json(self) -> None:
        """Malformed JSON handled."""
        from src.collectors.adzuna import AdzunaCollector

        async def malformed_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json")

        transport = httpx.MockTransport(malformed_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            with pytest.raises(Exception):
                await collector.fetch_page(page=1, category="it-jobs")


def _make_adzuna_job(n: int) -> JobBase:
    """Create a minimal valid JobBase for orchestration tests."""
    return JobBase(
        source_name="adzuna",
        external_id=str(n),
        source_url=f"https://adzuna.co.uk/jobs/{n}",
        title=f"Test Job {n}",
        description=f"Description {n}",
        description_plain=f"Description {n}",
        company_name="TestCo",
        location_raw="London",
        raw_data={"id": n},
    )


class TestAdzunaCollectorCoverage:
    """Coverage tests for Adzuna collector internals."""

    @pytest.mark.asyncio()
    async def test_circuit_breaker_open_returns_empty(self) -> None:
        """Open circuit breaker → fetch_page returns [] immediately."""
        from src.collectors.adzuna import AdzunaCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="adzuna", failure_threshold=1)
        breaker.record_failure()

        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client,
                app_id="test-id",
                app_key="test-key",
                circuit_breaker=breaker,
            )
            jobs = await collector.fetch_page(page=1, category="it-jobs")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_fetch_page_success_with_adapter(
        self, adzuna_fixture: dict[str, object]
    ) -> None:
        """fetch_page parses response through adapter and returns JobBase list."""
        from src.collectors.adzuna import AdzunaCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=adzuna_fixture)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            jobs = await collector.fetch_page(page=1, category="it-jobs")
            assert len(jobs) == 2
            assert all(isinstance(j, JobBase) for j in jobs)
            assert jobs[0].title == "Machine Learning Engineer"

    @pytest.mark.asyncio()
    async def test_non_list_results_raises_parse_error(self) -> None:
        """Non-list 'results' field raises ParseError."""
        from src.collectors.adzuna import AdzunaCollector
        from src.models.errors import ParseError

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": "not a list", "count": 0})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            with pytest.raises(ParseError):
                await collector.fetch_page(page=1, category="it-jobs")

    @pytest.mark.asyncio()
    async def test_adapter_error_skips_bad_job(
        self, adzuna_fixture: dict[str, object]
    ) -> None:
        """Invalid job in results is skipped; valid jobs pass through."""
        from src.collectors.adzuna import AdzunaCollector

        bad_job = {
            "id": "bad",
            "title": "",
            "description": "x",
            "company": {"display_name": "A"},
            "location": {"display_name": "L"},
            "redirect_url": "https://x.com",
        }
        results = list(adzuna_fixture["results"])  # type: ignore[arg-type]
        fixture = {"results": [bad_job, *results], "count": 3}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            jobs = await collector.fetch_page(page=1, category="it-jobs")
            assert len(jobs) == 2  # bad job skipped

    @pytest.mark.asyncio()
    async def test_timeout_records_circuit_breaker_failure(self) -> None:
        """TimeoutException records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import AdzunaCollector
        from src.collectors.circuit_breaker import CircuitBreaker
        from src.models.errors import SourceTimeoutError

        breaker = CircuitBreaker(name="adzuna")
        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client,
                app_id="test-id",
                app_key="test-key",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.adzuna.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(SourceTimeoutError):
                    await collector.fetch_page(page=1, category="it-jobs")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_429_records_rate_limit(self) -> None:
        """429 HTTPStatusError records rate limit on circuit breaker."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import AdzunaCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="adzuna")
        mock_request = httpx.Request("GET", "https://adzuna.co.uk")
        mock_response = httpx.Response(429, text="Rate limited", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client,
                app_id="test-id",
                app_key="test-key",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.adzuna.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "429", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_page(page=1, category="it-jobs")
            assert breaker._failure_count == 0

    @pytest.mark.asyncio()
    async def test_5xx_records_circuit_breaker_failure(self) -> None:
        """500 HTTPStatusError records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import AdzunaCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="adzuna")
        mock_request = httpx.Request("GET", "https://adzuna.co.uk")
        mock_response = httpx.Response(500, text="Error", request=mock_request)

        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client,
                app_id="test-id",
                app_key="test-key",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.adzuna.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "500", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_page(page=1, category="it-jobs")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_generic_exception_records_failure(self) -> None:
        """Generic exception records circuit breaker failure."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import AdzunaCollector
        from src.collectors.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="adzuna")
        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client,
                app_id="test-id",
                app_key="test-key",
                circuit_breaker=breaker,
            )
            with patch(
                "src.collectors.adzuna.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = RuntimeError("unexpected")
                with pytest.raises(RuntimeError):
                    await collector.fetch_page(page=1, category="it-jobs")
            assert breaker._failure_count == 1

    @pytest.mark.asyncio()
    async def test_fetch_category_multi_page(self) -> None:
        """fetch_category iterates pages until fewer than RESULTS_PER_PAGE."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import RESULTS_PER_PAGE, AdzunaCollector

        full_page = [_make_adzuna_job(i) for i in range(RESULTS_PER_PAGE)]
        partial_page = [_make_adzuna_job(i + RESULTS_PER_PAGE) for i in range(30)]

        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            with patch.object(
                collector, "fetch_page", new_callable=AsyncMock
            ) as mock_fp:
                mock_fp.side_effect = [full_page, partial_page]
                jobs = await collector.fetch_category("it-jobs")
                assert len(jobs) == RESULTS_PER_PAGE + 30
                assert mock_fp.call_count == 2

    @pytest.mark.asyncio()
    async def test_fetch_all_sweeps_categories(self) -> None:
        """fetch_all calls fetch_category for every Adzuna category."""
        from unittest.mock import AsyncMock, patch

        from src.collectors.adzuna import ADZUNA_CATEGORIES, AdzunaCollector

        async with httpx.AsyncClient() as client:
            collector = AdzunaCollector(
                client=client, app_id="test-id", app_key="test-key"
            )
            with patch.object(
                collector, "fetch_category", new_callable=AsyncMock
            ) as mock_fc:
                mock_fc.return_value = [_make_adzuna_job(1)]
                jobs = await collector.fetch_all()
                assert len(jobs) == len(ADZUNA_CATEGORIES)
                assert mock_fc.call_count == len(ADZUNA_CATEGORIES)
