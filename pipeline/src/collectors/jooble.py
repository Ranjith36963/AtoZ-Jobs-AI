"""Jooble API collector (SPEC.md §2.3).

- Endpoint: POST https://jooble.org/api/{API_KEY}
- Auth: API key in URL path
- Rate limit: 1.0s sleep between requests
- Pagination: page (1-indexed), ~20 results/page
- No totalResults — paginate until empty results array
- Aggregator — expect heavy dedup via content_hash
"""

import asyncio

import httpx
import structlog

from src.collectors.base import fetch_with_retry
from src.collectors.circuit_breaker import CircuitBreaker
from src.models.errors import ParseError, SourceTimeoutError
from src.models.job import JobBase, JoobleJobAdapter

logger = structlog.get_logger()

SLEEP_BETWEEN_REQUESTS = 1.0

# Keywords for sweep across major job categories
JOOBLE_KEYWORDS = [
    "software developer",
    "data analyst",
    "project manager",
    "nurse",
    "teacher",
    "accountant",
    "engineer",
    "marketing",
    "sales",
    "customer service",
    "administration",
    "logistics",
    "healthcare",
    "legal",
    "finance",
]


class JoobleCollector:
    """Collects jobs from Jooble API with keyword sweep."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="jooble")

    async def fetch_all(self, keyword: str, location: str = "UK") -> list[JobBase]:
        """Fetch all pages for a keyword until empty results."""
        if not self.circuit_breaker.allow_request():
            logger.warning("jooble.circuit_breaker_open", keyword=keyword)
            return []

        url = f"https://jooble.org/api/{self.api_key}"
        all_jobs: list[JobBase] = []
        page = 1

        while True:
            json_body: dict[str, object] = {
                "keywords": keyword,
                "location": location,
                "page": page,
            }

            try:
                data = await fetch_with_retry(
                    self.client,
                    url,
                    params={},
                    method="POST",
                    json_body=json_body,
                )
                self.circuit_breaker.record_success()
            except httpx.TimeoutException as exc:
                self.circuit_breaker.record_failure()
                raise SourceTimeoutError(str(exc), source="jooble") from exc
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
                raise ParseError("Expected 'jobs' array", source="jooble")

            # No totalResults — stop when empty
            if not jobs_data:
                break

            for item in jobs_data:
                if not isinstance(item, dict):
                    continue
                try:
                    job = JoobleJobAdapter.to_job_base(item)
                    all_jobs.append(job)
                except Exception as exc:
                    logger.warning(
                        "jooble.adapter_error",
                        error=str(exc),
                        job_id=item.get("id"),
                    )

            page += 1
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info(
            "jooble.keyword_complete",
            keyword=keyword,
            jobs=len(all_jobs),
        )
        return all_jobs

    async def sweep_all(self) -> list[JobBase]:
        """Sweep all Jooble keywords."""
        all_jobs: list[JobBase] = []
        for keyword in JOOBLE_KEYWORDS:
            keyword_jobs = await self.fetch_all(keyword=keyword)
            all_jobs.extend(keyword_jobs)
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("jooble.sweep_complete", total_jobs=len(all_jobs))
        return all_jobs
