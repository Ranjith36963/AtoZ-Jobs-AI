"""Reed API collector (SPEC.md §2.1).

- Base URL: https://www.reed.co.uk/api/1.0/search
- Auth: Basic Auth (API key as username, empty password)
- Rate limit: 0.5s sleep between requests
- Category sweep: iterate Reed sectors with postedWithin=1
- Pagination: resultsToTake=100, resultsToSkip offset
"""

import asyncio

import httpx
import structlog

from src.collectors.base import fetch_with_retry
from src.collectors.circuit_breaker import CircuitBreaker
from src.models.errors import ParseError, SourceTimeoutError
from src.models.job import JobBase, ReedJobAdapter

logger = structlog.get_logger()

BASE_URL = "https://www.reed.co.uk/api/1.0/search"
RESULTS_PER_PAGE = 100
SLEEP_BETWEEN_REQUESTS = 0.5

# Reed sectors for category sweep
REED_SECTORS = [
    "Accountancy",
    "Banking",
    "Construction",
    "Education",
    "Engineering",
    "Health & Medicine",
    "IT & Telecoms",
    "Legal",
    "Manufacturing",
    "Marketing & PR",
    "Retail",
    "Sales",
    "Scientific",
    "Social Care",
    "Transport & Logistics",
]


class ReedCollector:
    """Collects jobs from Reed API with category sweep."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="reed")

    @staticmethod
    def has_more_pages(results_count: int, total_results: int) -> bool:
        """Check if there are more pages to fetch."""
        if results_count == 0:
            return False
        return results_count >= RESULTS_PER_PAGE

    async def fetch_page(
        self,
        skip: int = 0,
        category: str = "",
    ) -> list[JobBase]:
        """Fetch a single page of results from Reed API."""
        if not self.circuit_breaker.allow_request():
            logger.warning("reed.circuit_breaker_open", category=category)
            return []

        params: dict[str, str | int] = {
            "resultsToTake": RESULTS_PER_PAGE,
            "resultsToSkip": skip,
            "postedWithin": 1,
        }
        if category:
            params["keywords"] = category

        try:
            # Reed uses Basic Auth: API key as username, empty password
            self.client.auth = httpx.BasicAuth(self.api_key, "")
            data = await fetch_with_retry(self.client, BASE_URL, params=params)
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="reed") from exc
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
            raise ParseError("Expected 'results' array in Reed response", source="reed")

        jobs: list[JobBase] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            try:
                job = ReedJobAdapter.to_job_base(item)
                jobs.append(job)
            except Exception as exc:
                logger.warning(
                    "reed.adapter_error",
                    error=str(exc),
                    job_id=item.get("jobId"),
                )
        return jobs

    async def fetch_category(self, category: str) -> list[JobBase]:
        """Fetch all pages for a single category."""
        all_jobs: list[JobBase] = []
        skip = 0

        while True:
            page_jobs = await self.fetch_page(skip=skip, category=category)
            all_jobs.extend(page_jobs)

            if not self.has_more_pages(len(page_jobs), 0):
                break

            skip += RESULTS_PER_PAGE
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info(
            "reed.category_complete",
            category=category,
            jobs=len(all_jobs),
        )
        return all_jobs

    async def fetch_all(self) -> list[JobBase]:
        """Sweep all Reed sectors."""
        all_jobs: list[JobBase] = []
        for sector in REED_SECTORS:
            sector_jobs = await self.fetch_category(sector)
            all_jobs.extend(sector_jobs)
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("reed.sweep_complete", total_jobs=len(all_jobs))
        return all_jobs
