"""Careerjet API v4 collector (SPEC.md §2.4).

- Endpoint: GET https://search.api.careerjet.net/v4/query
- Auth: affid query parameter
- Required: user_ip and user_agent (v4 anti-fraud)
- Rate limit: 1.0s sleep between requests
- Use httpx directly (Python 2 library deprecated)
- v4 structured salary: salary_currency_code, salary_min, salary_max, salary_type
"""

import asyncio

import httpx
import structlog

from src.collectors.base import fetch_with_retry
from src.collectors.circuit_breaker import CircuitBreaker
from src.models.errors import ParseError, SourceTimeoutError
from src.models.job import CareerjetJobAdapter, JobBase

logger = structlog.get_logger()

BASE_URL = "https://search.api.careerjet.net/v4/query"
SLEEP_BETWEEN_REQUESTS = 1.0

# Keywords and locations for sweep
CAREERJET_KEYWORDS = [
    "software engineer",
    "data scientist",
    "nurse",
    "teacher",
    "accountant",
    "project manager",
    "marketing manager",
    "sales executive",
    "mechanical engineer",
    "HR manager",
]

CAREERJET_LOCATIONS = [
    "London",
    "Manchester",
    "Birmingham",
    "Leeds",
    "Edinburgh",
    "Glasgow",
    "Bristol",
    "Cardiff",
    "Remote",
]


class CareerjetCollector:
    """Collects jobs from Careerjet API v4."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        affid: str,
        user_ip: str,
        user_agent: str,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.affid = affid
        self.user_ip = user_ip
        self.user_agent = user_agent
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="careerjet")

    @staticmethod
    def has_more_pages(current_page: int, total_pages: int) -> bool:
        """Check if there are more pages."""
        if total_pages == 0:
            return False
        return current_page < total_pages

    async def fetch_page(
        self,
        keywords: str = "",
        location: str = "",
        page: int = 1,
    ) -> list[JobBase]:
        """Fetch a single page from Careerjet API v4."""
        if not self.circuit_breaker.allow_request():
            logger.warning("careerjet.circuit_breaker_open", keywords=keywords)
            return []

        params: dict[str, str | int] = {
            "affid": self.affid,
            "user_ip": self.user_ip,
            "user_agent": self.user_agent,
            "keywords": keywords,
            "location": location,
            "locale_code": "en_GB",
            "page": page,
            "pagesize": 50,
            "sort": "date",
        }

        try:
            data = await fetch_with_retry(self.client, BASE_URL, params=params)
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="careerjet") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise
        except Exception:
            self.circuit_breaker.record_failure()
            raise

        jobs_data = data.get("jobs", [])
        if not isinstance(jobs_data, list):
            raise ParseError("Expected 'jobs' array", source="careerjet")

        jobs: list[JobBase] = []
        for item in jobs_data:
            if not isinstance(item, dict):
                continue
            try:
                job = CareerjetJobAdapter.to_job_base(item)
                jobs.append(job)
            except Exception as exc:
                logger.warning(
                    "careerjet.adapter_error",
                    error=str(exc),
                    url=item.get("url"),
                )
        return jobs

    async def fetch_keyword_location(
        self, keywords: str, location: str
    ) -> list[JobBase]:
        """Fetch all pages for a keyword+location pair."""
        all_jobs: list[JobBase] = []
        page = 1

        # First page to get total_pages
        page_jobs = await self.fetch_page(
            keywords=keywords, location=location, page=page
        )
        all_jobs.extend(page_jobs)

        # Continue if more pages (use page metadata if available)
        while len(page_jobs) >= 50:
            page += 1
            page_jobs = await self.fetch_page(
                keywords=keywords, location=location, page=page
            )
            all_jobs.extend(page_jobs)
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        return all_jobs

    async def sweep_all(self) -> list[JobBase]:
        """Sweep all keyword + location combinations."""
        all_jobs: list[JobBase] = []
        for keyword in CAREERJET_KEYWORDS:
            for location in CAREERJET_LOCATIONS:
                pair_jobs = await self.fetch_keyword_location(keyword, location)
                all_jobs.extend(pair_jobs)
                await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("careerjet.sweep_complete", total_jobs=len(all_jobs))
        return all_jobs
