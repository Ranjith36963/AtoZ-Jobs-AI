"""Tests for Careerjet collector and adapter (GATES C4, C7, C9, C10)."""

import json
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
