"""Tests for Jooble collector and adapter (GATES C3, C7, C9, C10)."""

import json
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
