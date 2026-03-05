"""Tests for Reed collector and adapter (GATES C1, C7, C9, C10)."""

import json
from pathlib import Path

import httpx
import pytest

from src.models.job import JobBase, ReedJobAdapter

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def reed_fixture() -> dict[str, object]:
    """Load Reed API response fixture."""
    with open(FIXTURES / "reed_response.json") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture()
def reed_job_data(reed_fixture: dict[str, object]) -> dict[str, object]:
    """Single Reed job from fixture."""
    results = reed_fixture["results"]
    assert isinstance(results, list)
    return results[0]  # type: ignore[no-any-return]


class TestReedAdapter:
    """Test ReedJobAdapter.to_job_base() mapping (Gate C1)."""

    def test_maps_fixture_to_job_base(self, reed_job_data: dict[str, object]) -> None:
        """Maps Reed JSON fixture to JobBase with zero validation errors."""
        job = ReedJobAdapter.to_job_base(reed_job_data)

        assert isinstance(job, JobBase)
        assert job.source_name == "reed"
        assert job.external_id == "12345678"
        assert job.title == "Senior Python Developer"
        assert job.company_name == "Acme Technologies Ltd"
        assert job.location_raw == "London, City of London"
        assert job.salary_min == 65000.0
        assert job.salary_max == 85000.0
        assert job.salary_currency == "GBP"
        assert job.salary_period == "annual"
        assert job.salary_is_predicted is False

    def test_html_stripping(self, reed_job_data: dict[str, object]) -> None:
        """HTML tags are stripped from description → description_plain."""
        job = ReedJobAdapter.to_job_base(reed_job_data)

        assert "<p>" not in job.description_plain
        assert "<strong>" not in job.description_plain
        assert "<ul>" not in job.description_plain
        assert "Senior Python Developer" in job.description_plain
        # Original HTML preserved in description
        assert "<p>" in job.description

    def test_employment_type_mapping(self, reed_job_data: dict[str, object]) -> None:
        """Boolean fullTime/partTime flags map to employment_type list."""
        job = ReedJobAdapter.to_job_base(reed_job_data)

        assert "full_time" in job.employment_type
        assert "part_time" not in job.employment_type
        assert "permanent" in job.employment_type

    def test_part_time_job(self, reed_fixture: dict[str, object]) -> None:
        """Part-time job maps correctly."""
        results = reed_fixture["results"]
        assert isinstance(results, list)
        job = ReedJobAdapter.to_job_base(results[1])

        assert "part_time" in job.employment_type
        assert "full_time" not in job.employment_type

    def test_null_salary(self, reed_fixture: dict[str, object]) -> None:
        """Null salary fields map to None."""
        results = reed_fixture["results"]
        assert isinstance(results, list)
        job = ReedJobAdapter.to_job_base(results[1])

        assert job.salary_min is None
        assert job.salary_max is None

    def test_date_parsing(self, reed_job_data: dict[str, object]) -> None:
        """ISO dates parse correctly."""
        job = ReedJobAdapter.to_job_base(reed_job_data)

        assert job.date_posted is not None
        assert job.date_posted.year == 2026
        assert job.date_expires is not None

    def test_source_url(self, reed_job_data: dict[str, object]) -> None:
        """Source URL preserved."""
        job = ReedJobAdapter.to_job_base(reed_job_data)
        assert "reed.co.uk" in job.source_url

    def test_raw_data_preserved(self, reed_job_data: dict[str, object]) -> None:
        """Original raw_data JSONB preserved for reprocessing."""
        job = ReedJobAdapter.to_job_base(reed_job_data)
        assert job.raw_data == reed_job_data

    def test_category_raw(self, reed_job_data: dict[str, object]) -> None:
        """Category raw field extracted."""
        job = ReedJobAdapter.to_job_base(reed_job_data)
        assert job.category_raw == "IT & Telecoms"


class TestContentHash:
    """Test content_hash computation (Gate C7)."""

    def test_content_hash_computed(self, reed_job_data: dict[str, object]) -> None:
        """content_hash is a SHA-256 hex string."""
        job = ReedJobAdapter.to_job_base(reed_job_data)
        assert len(job.content_hash) == 64  # SHA-256 hex = 64 chars

    def test_content_hash_stable(self, reed_job_data: dict[str, object]) -> None:
        """Same input → identical hash."""
        job1 = ReedJobAdapter.to_job_base(reed_job_data)
        job2 = ReedJobAdapter.to_job_base(reed_job_data)
        assert job1.content_hash == job2.content_hash

    def test_content_hash_different_for_different_input(
        self, reed_fixture: dict[str, object]
    ) -> None:
        """Different input → different hash."""
        results = reed_fixture["results"]
        assert isinstance(results, list)
        job1 = ReedJobAdapter.to_job_base(results[0])
        job2 = ReedJobAdapter.to_job_base(results[1])
        assert job1.content_hash != job2.content_hash

    def test_content_hash_case_insensitive(self) -> None:
        """Hash normalizes case — 'PYTHON' and 'python' produce same hash."""
        data_upper = {
            "jobId": 1,
            "jobTitle": "PYTHON DEV",
            "jobDescription": "desc",
            "employerName": "ACME",
            "locationName": "LONDON",
            "jobUrl": "https://example.com",
        }
        data_lower = {
            "jobId": 1,
            "jobTitle": "python dev",
            "jobDescription": "desc",
            "employerName": "acme",
            "locationName": "london",
            "jobUrl": "https://example.com",
        }
        job_upper = ReedJobAdapter.to_job_base(data_upper)
        job_lower = ReedJobAdapter.to_job_base(data_lower)
        assert job_upper.content_hash == job_lower.content_hash


class TestSchemaValidation:
    """Test Pydantic validation errors (Gate C9)."""

    def test_null_title_raises(self) -> None:
        """Null title → ValidationError."""
        data = {
            "jobId": 1,
            "jobTitle": "",
            "jobDescription": "desc",
            "employerName": "Acme",
            "locationName": "London",
            "jobUrl": "https://example.com",
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            ReedJobAdapter.to_job_base(data)

    def test_null_company_raises(self) -> None:
        """Empty company → ValidationError."""
        data = {
            "jobId": 1,
            "jobTitle": "Dev",
            "jobDescription": "desc",
            "employerName": "",
            "locationName": "London",
            "jobUrl": "https://example.com",
        }
        with pytest.raises(Exception):
            ReedJobAdapter.to_job_base(data)

    def test_negative_salary_raises(self) -> None:
        """Negative salary → ValidationError."""
        data = {
            "jobId": 1,
            "jobTitle": "Dev",
            "jobDescription": "desc",
            "employerName": "Acme",
            "locationName": "London",
            "jobUrl": "https://example.com",
            "minimumSalary": -5000,
        }
        with pytest.raises(Exception):
            ReedJobAdapter.to_job_base(data)

    def test_salary_over_million_raises(self) -> None:
        """Salary > 1,000,000 → ValidationError."""
        data = {
            "jobId": 1,
            "jobTitle": "Dev",
            "jobDescription": "desc",
            "employerName": "Acme",
            "locationName": "London",
            "jobUrl": "https://example.com",
            "maximumSalary": 2_000_000,
        }
        with pytest.raises(Exception):
            ReedJobAdapter.to_job_base(data)


class TestReedCollector:
    """Test Reed collector (Gate C1, C10)."""

    @pytest.mark.asyncio()
    async def test_pagination_boundary(self) -> None:
        """Exactly 100 results → has next page. <100 → no more pages."""
        from src.collectors.reed import ReedCollector

        # 100 results means there could be more pages
        assert ReedCollector.has_more_pages(results_count=100, total_results=247)
        # < 100 means last page
        assert not ReedCollector.has_more_pages(results_count=47, total_results=247)
        # 0 results means no more
        assert not ReedCollector.has_more_pages(results_count=0, total_results=0)

    @pytest.mark.asyncio()
    async def test_empty_results(self) -> None:
        """Empty results handled without crash."""
        from src.collectors.reed import ReedCollector

        empty_response = {"results": [], "totalResults": 0}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=empty_response)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ReedCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_page(skip=0, category="IT")
            assert jobs == []

    @pytest.mark.asyncio()
    async def test_timeout_handling(self) -> None:
        """Timeout raises SourceTimeoutError."""
        from src.collectors.reed import ReedCollector

        async def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Connection timed out")

        transport = httpx.MockTransport(timeout_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ReedCollector(client=client, api_key="test-key")
            with pytest.raises(Exception):
                await collector.fetch_page(skip=0, category="IT")

    @pytest.mark.asyncio()
    async def test_500_error_handling(self) -> None:
        """500 server error handled."""
        from src.collectors.reed import ReedCollector

        async def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(error_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ReedCollector(client=client, api_key="test-key")
            with pytest.raises(Exception):
                await collector.fetch_page(skip=0, category="IT")

    @pytest.mark.asyncio()
    async def test_429_rate_limit(self) -> None:
        """429 triggers retry, not circuit breaker trip."""
        from src.collectors.reed import ReedCollector

        call_count = 0

        async def rate_limit_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    429, headers={"Retry-After": "1"}, text="Rate limited"
                )
            return httpx.Response(200, json={"results": [], "totalResults": 0})

        transport = httpx.MockTransport(rate_limit_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ReedCollector(client=client, api_key="test-key")
            jobs = await collector.fetch_page(skip=0, category="IT")
            assert jobs == []
            assert call_count == 2

    @pytest.mark.asyncio()
    async def test_malformed_json(self) -> None:
        """Malformed JSON handled without crash."""
        from src.collectors.reed import ReedCollector

        async def malformed_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json{{{")

        transport = httpx.MockTransport(malformed_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            collector = ReedCollector(client=client, api_key="test-key")
            with pytest.raises(Exception):
                await collector.fetch_page(skip=0, category="IT")
