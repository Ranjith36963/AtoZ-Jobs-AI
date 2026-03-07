"""Adzuna API collector (SPEC.md §2.2).

- Base URL: https://api.adzuna.com/v1/api/jobs/gb/search/{page}
- Auth: Query params app_id + app_key
- Rate limit: 1.0s sleep between requests
- Pagination: results_per_page=50, page number in URL path (1-indexed)
- Extract latitude/longitude directly
"""

import asyncio

import httpx
import structlog

from src.collectors.base import fetch_with_retry
from src.collectors.circuit_breaker import CircuitBreaker
from src.models.errors import ParseError, SourceTimeoutError
from src.models.job import AdzunaJobAdapter, JobBase

logger = structlog.get_logger()

BASE_URL = "https://api.adzuna.com/v1/api/jobs/gb/search"
RESULTS_PER_PAGE = 50
SLEEP_BETWEEN_REQUESTS = 1.0

# Adzuna category tags
ADZUNA_CATEGORIES = [
    "it-jobs",
    "engineering-jobs",
    "healthcare-nursing-jobs",
    "accounting-finance-jobs",
    "teaching-jobs",
    "sales-jobs",
    "admin-jobs",
    "legal-jobs",
    "hr-jobs",
    "customer-services-jobs",
    "logistics-warehouse-jobs",
    "manufacturing-jobs",
    "scientific-qa-jobs",
    "social-work-jobs",
    "creative-design-jobs",
    "consultancy-jobs",
    "energy-oil-gas-jobs",
    "property-jobs",
    "retail-jobs",
    "hospitality-catering-jobs",
    "travel-jobs",
    "graduate-jobs",
    "part-time-jobs",
]


class AdzunaCollector:
    """Collects jobs from Adzuna API with category + date sweep."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        app_id: str,
        app_key: str,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.app_id = app_id
        self.app_key = app_key
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="adzuna")

    @staticmethod
    def has_more_pages(results_count: int, total_count: int) -> bool:
        """Check if there are more pages."""
        if results_count == 0:
            return False
        return results_count >= RESULTS_PER_PAGE

    async def fetch_page(
        self,
        page: int = 1,
        category: str = "",
    ) -> list[JobBase]:
        """Fetch a single page from Adzuna API."""
        if not self.circuit_breaker.allow_request():
            logger.warning("adzuna.circuit_breaker_open", category=category)
            return []

        url = f"{BASE_URL}/{page}"
        params: dict[str, str | int] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": RESULTS_PER_PAGE,
            "max_days_old": 1,
            "sort_by": "date",
        }
        if category:
            params["category"] = category

        try:
            data = await fetch_with_retry(self.client, url, params=params)
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="adzuna") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise
        except Exception:
            self.circuit_breaker.record_failure()
            raise

        results = data.get("results", [])
        if not isinstance(results, list):
            raise ParseError("Expected 'results' array", source="adzuna")

        jobs: list[JobBase] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            try:
                job = AdzunaJobAdapter.to_job_base(item)
                jobs.append(job)
            except Exception as exc:
                logger.warning(
                    "adzuna.adapter_error",
                    error=str(exc),
                    job_id=item.get("id"),
                )
        return jobs

    async def fetch_category(self, category: str) -> list[JobBase]:
        """Fetch all pages for a single category."""
        all_jobs: list[JobBase] = []
        page = 1

        while True:
            page_jobs = await self.fetch_page(page=page, category=category)
            all_jobs.extend(page_jobs)

            if not self.has_more_pages(len(page_jobs), 0):
                break

            page += 1
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info(
            "adzuna.category_complete",
            category=category,
            jobs=len(all_jobs),
        )
        return all_jobs

    async def fetch_all(self) -> list[JobBase]:
        """Sweep all Adzuna categories."""
        all_jobs: list[JobBase] = []
        for category in ADZUNA_CATEGORIES:
            category_jobs = await self.fetch_category(category)
            all_jobs.extend(category_jobs)
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("adzuna.sweep_complete", total_jobs=len(all_jobs))
        return all_jobs
