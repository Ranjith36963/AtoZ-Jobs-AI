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
