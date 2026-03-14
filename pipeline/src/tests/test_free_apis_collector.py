"""Tests for free API collectors and adapters."""

import json
from pathlib import Path

import httpx
import pytest

from src.models.job import JobBase

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def free_apis_fixtures() -> dict[str, object]:
    """Load all free API response fixtures."""
    with open(FIXTURES / "free_apis_responses.json") as f:
        return json.load(f)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Arbeitnow adapter tests
# ---------------------------------------------------------------------------


class TestArbeitnowAdapter:
    """Test Arbeitnow adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job = _arbeitnow_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "arbeitnow"
        assert job.external_id == "senior-python-developer-london-12345"
        assert job.title == "Senior Python Developer"
        assert job.company_name == "TechCorp UK"
        assert job.location_raw == "London, UK"

    def test_html_stripped(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job = _arbeitnow_to_job(data)
        assert "<p>" not in job.description_plain

    def test_employment_type(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job = _arbeitnow_to_job(data)
        assert "full_time" in job.employment_type or "full-time" in job.employment_type

    def test_date_from_unix(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job = _arbeitnow_to_job(data)
        assert job.date_posted is not None
        assert job.date_expires is not None

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job = _arbeitnow_to_job(data)
        assert job.raw_data == data

    def test_content_hash_stable(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        data = free_apis_fixtures["arbeitnow"]["data"][0]
        job1 = _arbeitnow_to_job(data)
        job2 = _arbeitnow_to_job(data)
        assert job1.content_hash == job2.content_hash


# ---------------------------------------------------------------------------
# RemoteOK adapter tests
# ---------------------------------------------------------------------------


class TestRemoteOKAdapter:
    """Test RemoteOK adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _remoteok_to_job

        data = free_apis_fixtures["remoteok"][1]  # Skip metadata
        job = _remoteok_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "remoteok"
        assert job.external_id == "rok-111222"
        assert job.title == "Full Stack Engineer"
        assert job.company_name == "CloudNine Systems"

    def test_salary_extraction(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remoteok_to_job

        data = free_apis_fixtures["remoteok"][1]
        job = _remoteok_to_job(data)
        assert job.salary_min == 60000.0
        assert job.salary_max == 90000.0

    def test_zero_salary_is_none(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remoteok_to_job

        data = free_apis_fixtures["remoteok"][2]
        job = _remoteok_to_job(data)
        assert job.salary_min is None
        assert job.salary_max is None

    def test_date_from_iso(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remoteok_to_job

        data = free_apis_fixtures["remoteok"][1]
        job = _remoteok_to_job(data)
        assert job.date_posted is not None

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remoteok_to_job

        data = free_apis_fixtures["remoteok"][1]
        job = _remoteok_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# Jobicy adapter tests
# ---------------------------------------------------------------------------


class TestJobicyAdapter:
    """Test Jobicy adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _jobicy_to_job

        data = free_apis_fixtures["jobicy"]["jobs"][0]
        job = _jobicy_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "jobicy"
        assert job.external_id == "98765"
        assert job.title == "Backend Developer"
        assert job.company_name == "FintechPro"
        assert job.location_raw == "UK"

    def test_salary_fields(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _jobicy_to_job

        data = free_apis_fixtures["jobicy"]["jobs"][0]
        job = _jobicy_to_job(data)
        assert job.salary_min == 55000.0
        assert job.salary_max == 75000.0
        assert job.salary_currency == "GBP"
        assert job.salary_period == "annual"

    def test_employment_type_from_array(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _jobicy_to_job

        data = free_apis_fixtures["jobicy"]["jobs"][0]
        job = _jobicy_to_job(data)
        assert len(job.employment_type) > 0

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _jobicy_to_job

        data = free_apis_fixtures["jobicy"]["jobs"][0]
        job = _jobicy_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# Himalayas adapter tests
# ---------------------------------------------------------------------------


class TestHimalayasAdapter:
    """Test Himalayas adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _himalayas_to_job

        data = free_apis_fixtures["himalayas"]["jobs"][0]
        job = _himalayas_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "himalayas"
        assert job.external_id == "him-pm-001"
        assert job.title == "Product Manager"
        assert job.company_name == "SaaSify"

    def test_salary_fields(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _himalayas_to_job

        data = free_apis_fixtures["himalayas"]["jobs"][0]
        job = _himalayas_to_job(data)
        assert job.salary_min == 70000.0
        assert job.salary_max == 95000.0
        assert job.salary_currency == "GBP"

    def test_unix_timestamp_date(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _himalayas_to_job

        data = free_apis_fixtures["himalayas"]["jobs"][0]
        job = _himalayas_to_job(data)
        assert job.date_posted is not None
        assert job.date_expires is not None

    def test_location_from_restrictions(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _himalayas_to_job

        data = free_apis_fixtures["himalayas"]["jobs"][0]
        job = _himalayas_to_job(data)
        assert "UK" in job.location_raw or "Europe" in job.location_raw

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _himalayas_to_job

        data = free_apis_fixtures["himalayas"]["jobs"][0]
        job = _himalayas_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# Remotive adapter tests
# ---------------------------------------------------------------------------


class TestRemotiveAdapter:
    """Test Remotive adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][0]
        job = _remotive_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "remotive"
        assert job.external_id == "55555"
        assert job.title == "React Developer"
        assert job.company_name == "WebAgency"

    def test_salary_raw_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][0]
        job = _remotive_to_job(data)
        assert job.salary_raw == "£45,000 - £65,000"

    def test_empty_salary(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][1]
        job = _remotive_to_job(data)
        assert job.salary_raw is None

    def test_html_stripped(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][0]
        job = _remotive_to_job(data)
        assert "<p>" not in job.description_plain

    def test_location_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][0]
        job = _remotive_to_job(data)
        assert job.location_raw == "UK"

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _remotive_to_job

        data = free_apis_fixtures["remotive"]["jobs"][0]
        job = _remotive_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# DevITjobs adapter tests
# ---------------------------------------------------------------------------


class TestDevITJobsAdapter:
    """Test DevITjobs adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _devitjobs_to_job

        data = free_apis_fixtures["devitjobs"][0]
        job = _devitjobs_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "devitjobs"
        assert job.external_id == "dit-abc123"
        assert job.title == "Security Engineer"
        assert job.company_name == "CyberSafe Ltd"

    def test_salary_fields(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _devitjobs_to_job

        data = free_apis_fixtures["devitjobs"][0]
        job = _devitjobs_to_job(data)
        assert job.salary_min == 50000.0
        assert job.salary_max == 70000.0
        assert job.salary_currency == "GBP"
        assert job.salary_period == "annual"

    def test_coordinates_extracted(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _devitjobs_to_job

        data = free_apis_fixtures["devitjobs"][0]
        job = _devitjobs_to_job(data)
        assert job.latitude == 53.4808
        assert job.longitude == -2.2426

    def test_location_from_city(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _devitjobs_to_job

        data = free_apis_fixtures["devitjobs"][0]
        job = _devitjobs_to_job(data)
        assert job.location_raw == "Manchester"

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _devitjobs_to_job

        data = free_apis_fixtures["devitjobs"][0]
        job = _devitjobs_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# Landing.jobs adapter tests
# ---------------------------------------------------------------------------


class TestLandingJobsAdapter:
    """Test Landing.jobs adapter mapping."""

    def test_maps_fixture_to_job_base(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _landingjobs_to_job

        data = free_apis_fixtures["landingjobs"][0]
        job = _landingjobs_to_job(data)

        assert isinstance(job, JobBase)
        assert job.source_name == "landingjobs"
        assert job.external_id == "19019"
        assert job.title == "DevOps Engineer"

    def test_salary_fields(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _landingjobs_to_job

        data = free_apis_fixtures["landingjobs"][0]
        job = _landingjobs_to_job(data)
        assert job.salary_min == 50000.0
        assert job.salary_max == 73000.0
        assert job.salary_currency == "EUR"

    def test_location_from_locations_array(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import _landingjobs_to_job

        data = free_apis_fixtures["landingjobs"][0]
        job = _landingjobs_to_job(data)
        assert "London" in job.location_raw
        assert "United Kingdom" in job.location_raw

    def test_html_stripped(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _landingjobs_to_job

        data = free_apis_fixtures["landingjobs"][0]
        job = _landingjobs_to_job(data)
        assert "<div>" not in job.description_plain

    def test_raw_data_preserved(self, free_apis_fixtures: dict[str, object]) -> None:
        from src.collectors.free_apis import _landingjobs_to_job

        data = free_apis_fixtures["landingjobs"][0]
        job = _landingjobs_to_job(data)
        assert job.raw_data == data


# ---------------------------------------------------------------------------
# UK/Remote filter tests
# ---------------------------------------------------------------------------


class TestUKRemoteFilter:
    """Test _is_uk_or_remote filter function."""

    def test_uk_location(self) -> None:
        from src.collectors.free_apis import _is_uk_or_remote

        assert _is_uk_or_remote("London, UK") is True
        assert _is_uk_or_remote("Manchester") is True
        assert _is_uk_or_remote("Edinburgh, Scotland") is True

    def test_remote_location(self) -> None:
        from src.collectors.free_apis import _is_uk_or_remote

        assert _is_uk_or_remote("Remote") is True
        assert _is_uk_or_remote("Worldwide") is True
        assert _is_uk_or_remote("Anywhere") is True

    def test_non_uk_location(self) -> None:
        from src.collectors.free_apis import _is_uk_or_remote

        assert _is_uk_or_remote("Berlin, Germany") is False
        assert _is_uk_or_remote("New York, USA") is False

    def test_empty_location(self) -> None:
        from src.collectors.free_apis import _is_uk_or_remote

        assert _is_uk_or_remote("") is False

    def test_europe_matches(self) -> None:
        from src.collectors.free_apis import _is_uk_or_remote

        assert _is_uk_or_remote("Europe") is True
        assert _is_uk_or_remote("EMEA") is True


# ---------------------------------------------------------------------------
# Collector integration tests (with mock HTTP)
# ---------------------------------------------------------------------------


class TestArbeitnowCollector:
    """Test ArbeitnowCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_page_success(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import ArbeitnowCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["arbeitnow"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ArbeitnowCollector(client=client)
            jobs, has_more = await collector.fetch_page(page=1)
            assert len(jobs) == 2
            assert has_more is True
            assert all(isinstance(j, JobBase) for j in jobs)

    @pytest.mark.asyncio()
    async def test_empty_page_returns_no_more(self) -> None:
        from src.collectors.free_apis import ArbeitnowCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ArbeitnowCollector(client=client)
            jobs, has_more = await collector.fetch_page(page=1)
            assert jobs == []
            assert has_more is False

    @pytest.mark.asyncio()
    async def test_circuit_breaker_open(self) -> None:
        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.free_apis import ArbeitnowCollector

        breaker = CircuitBreaker(name="arbeitnow", failure_threshold=1)
        breaker.record_failure()

        async with httpx.AsyncClient() as client:
            collector = ArbeitnowCollector(client=client, circuit_breaker=breaker)
            jobs, has_more = await collector.fetch_page()
            assert jobs == []
            assert has_more is False

    @pytest.mark.asyncio()
    async def test_timeout_handling(self) -> None:
        from unittest.mock import AsyncMock, patch

        from src.collectors.free_apis import ArbeitnowCollector
        from src.models.errors import SourceTimeoutError

        async with httpx.AsyncClient() as client:
            collector = ArbeitnowCollector(client=client)
            with patch(
                "src.collectors.free_apis.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = httpx.TimeoutException("timeout")
                with pytest.raises(SourceTimeoutError):
                    await collector.fetch_page()


class TestRemoteOKCollector:
    """Test RemoteOKCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_all_filters_metadata(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import RemoteOKCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["remoteok"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = RemoteOKCollector(client=client)
            jobs = await collector.fetch_all()
            # Both have worldwide/europe locations
            assert len(jobs) == 2
            assert all(isinstance(j, JobBase) for j in jobs)
            # Metadata entry filtered out
            assert all(j.source_name == "remoteok" for j in jobs)

    @pytest.mark.asyncio()
    async def test_circuit_breaker_open(self) -> None:
        from src.collectors.circuit_breaker import CircuitBreaker
        from src.collectors.free_apis import RemoteOKCollector

        breaker = CircuitBreaker(name="remoteok", failure_threshold=1)
        breaker.record_failure()

        async with httpx.AsyncClient() as client:
            collector = RemoteOKCollector(client=client, circuit_breaker=breaker)
            jobs = await collector.fetch_all()
            assert jobs == []


class TestJobicyCollector:
    """Test JobicyCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_all_success(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import JobicyCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["jobicy"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = JobicyCollector(client=client)
            jobs = await collector.fetch_all()
            assert len(jobs) == 1
            assert jobs[0].title == "Backend Developer"


class TestRemotiveCollector:
    """Test RemotiveCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_all_filters_uk(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import RemotiveCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["remotive"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = RemotiveCollector(client=client)
            jobs = await collector.fetch_all()
            # Both jobs have UK/Anywhere locations
            assert len(jobs) == 2
            assert all(isinstance(j, JobBase) for j in jobs)


class TestDevITJobsCollector:
    """Test DevITJobsCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_all_success(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import DevITJobsCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["devitjobs"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = DevITJobsCollector(client=client)
            jobs = await collector.fetch_all()
            assert len(jobs) == 1
            assert jobs[0].title == "Security Engineer"


class TestLandingJobsCollector:
    """Test LandingJobsCollector with mocked HTTP."""

    @pytest.mark.asyncio()
    async def test_fetch_all_filters_uk(
        self, free_apis_fixtures: dict[str, object]
    ) -> None:
        from src.collectors.free_apis import LandingJobsCollector

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=free_apis_fixtures["landingjobs"])

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = LandingJobsCollector(client=client)
            jobs = await collector.fetch_all()
            assert len(jobs) == 1
            assert jobs[0].title == "DevOps Engineer"


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class TestFetchAllFreeSources:
    """Test the orchestrator that calls all 7 sources."""

    @pytest.mark.asyncio()
    async def test_continues_on_source_failure(self) -> None:
        """One source failing doesn't prevent others from returning jobs."""
        from src.collectors.free_apis import fetch_all_free_sources

        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            url = str(request.url)

            if "arbeitnow" in url:
                return httpx.Response(500, text="Server Error")
            if "remoteok" in url:
                return httpx.Response(
                    200,
                    json=[
                        {"last_updated": 1, "legal": "x"},
                        {
                            "id": "1",
                            "position": "Test",
                            "description": "Desc",
                            "company": "Co",
                            "location": "UK",
                            "date": "2025-03-01T00:00:00+00:00",
                            "url": "https://example.com",
                        },
                    ],
                )
            # Return empty for all others
            return httpx.Response(200, json={"jobs": [], "data": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            jobs = await fetch_all_free_sources(client)
            # Should have at least the 1 RemoteOK job despite arbeitnow failure
            assert len(jobs) >= 1

    @pytest.mark.asyncio()
    async def test_empty_sources_return_empty(self) -> None:
        """All sources returning empty data gives empty result."""
        from src.collectors.free_apis import fetch_all_free_sources

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": [], "data": []})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            jobs = await fetch_all_free_sources(client)
            assert jobs == []


# ---------------------------------------------------------------------------
# Sad path tests
# ---------------------------------------------------------------------------


class TestSadPaths:
    """Test null, empty, timeout, malformed data handling."""

    def test_adapter_empty_title_raises(self) -> None:
        from src.collectors.free_apis import _arbeitnow_to_job

        with pytest.raises(Exception):
            _arbeitnow_to_job(
                {
                    "slug": "test",
                    "title": "",
                    "description": "desc",
                    "company_name": "Co",
                    "location": "UK",
                    "url": "https://test.com",
                    "created_at": 1741824000,
                }
            )

    def test_adapter_missing_company_raises(self) -> None:
        from src.collectors.free_apis import _remotive_to_job

        with pytest.raises(Exception):
            _remotive_to_job(
                {
                    "id": "1",
                    "title": "Test",
                    "description": "desc",
                    "company_name": "",
                    "url": "https://test.com",
                }
            )

    def test_adapter_null_data_raises(self) -> None:
        from src.collectors.free_apis import _jobicy_to_job

        with pytest.raises(Exception):
            _jobicy_to_job({})

    @pytest.mark.asyncio()
    async def test_malformed_json_response(self) -> None:
        from src.collectors.free_apis import ArbeitnowCollector

        async def malformed_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not valid json {{{")

        transport = httpx.MockTransport(malformed_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ArbeitnowCollector(client=client)
            with pytest.raises(Exception):
                await collector.fetch_page()

    @pytest.mark.asyncio()
    async def test_rate_limit_429(self) -> None:
        from unittest.mock import AsyncMock, patch

        from src.collectors.free_apis import JobicyCollector

        async with httpx.AsyncClient() as client:
            collector = JobicyCollector(client=client)
            with patch(
                "src.collectors.free_apis.fetch_with_retry", new_callable=AsyncMock
            ) as mock_fetch:
                mock_request = httpx.Request(
                    "GET", "https://jobicy.com/api/v2/remote-jobs"
                )
                mock_response = httpx.Response(
                    429, text="Rate limited", request=mock_request
                )
                mock_fetch.side_effect = httpx.HTTPStatusError(
                    "429", request=mock_request, response=mock_response
                )
                with pytest.raises(httpx.HTTPStatusError):
                    await collector.fetch_all()
