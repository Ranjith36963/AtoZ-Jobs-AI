"""Free API collectors — 7 open endpoints requiring no API keys.

Sources:
1. Arbeitnow — arbeitnow.com/api/job-board-api
2. RemoteOK — remoteok.com/api
3. Jobicy — jobicy.com/api/v2/remote-jobs
4. Himalayas — himalayas.app/jobs/api
5. Remotive — remotive.com/api/remote-jobs
6. DevITjobs — devitjobs.uk/api/jobsLight
7. Landing.jobs — landing.jobs/api/v1/jobs.json

All collectors filter for UK/Remote jobs and follow the existing adapter pattern.
"""

import asyncio

import httpx
import structlog

from src.collectors.base import fetch_with_retry
from src.collectors.circuit_breaker import CircuitBreaker
from src.models.errors import SourceTimeoutError
from src.models.job import JobBase

logger = structlog.get_logger()

SLEEP_BETWEEN_REQUESTS = 1.0

# UK location keywords for filtering
UK_KEYWORDS = {
    "uk",
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "northern ireland",
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "glasgow",
    "edinburgh",
    "bristol",
    "liverpool",
    "cardiff",
    "belfast",
    "remote",
    "worldwide",
    "anywhere",
    "europe",
    "emea",
}


def _is_uk_or_remote(location: str) -> bool:
    """Check if location string indicates UK or remote."""
    if not location:
        return False
    loc_lower = location.lower()
    return any(kw in loc_lower for kw in UK_KEYWORDS)


class ArbeitnowCollector:
    """Collects jobs from Arbeitnow API with pagination."""

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="arbeitnow")

    async def fetch_page(self, page: int = 1) -> tuple[list[JobBase], bool]:
        """Fetch a single page. Returns (jobs, has_more)."""
        if not self.circuit_breaker.allow_request():
            return [], False

        try:
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={"page": page},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="arbeitnow") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        jobs_data = data.get("data", [])
        if not isinstance(jobs_data, list):
            return [], False

        jobs: list[JobBase] = []
        for item in jobs_data:
            if not isinstance(item, dict):
                continue
            try:
                location = str(item.get("location", ""))
                is_remote = bool(item.get("remote", False))
                if not is_remote and not _is_uk_or_remote(location):
                    continue
                jobs.append(_arbeitnow_to_job(item))
            except Exception as exc:
                logger.warning("arbeitnow.adapter_error", error=str(exc))

        has_more = len(jobs_data) > 0
        return jobs, has_more

    async def fetch_all(self, max_pages: int = 5) -> list[JobBase]:
        """Fetch all pages up to max_pages."""
        all_jobs: list[JobBase] = []
        for page in range(1, max_pages + 1):
            page_jobs, has_more = await self.fetch_page(page)
            all_jobs.extend(page_jobs)
            if not has_more:
                break
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("arbeitnow.complete", jobs=len(all_jobs))
        return all_jobs


class RemoteOKCollector:
    """Collects jobs from RemoteOK API (single endpoint, no pagination)."""

    BASE_URL = "https://remoteok.com/api"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="remoteok")

    async def fetch_all(self) -> list[JobBase]:
        """Fetch all jobs (single request, array response)."""
        if not self.circuit_breaker.allow_request():
            return []

        try:
            # RemoteOK requires a User-Agent header
            self.client.headers["User-Agent"] = "AtoZ-Jobs-Pipeline/1.0"
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="remoteok") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        # Response is an array; first element is metadata
        if not isinstance(data, list):
            # fetch_with_retry returns dict, but RemoteOK returns array
            # Handle both cases
            items = data if isinstance(data, list) else []
        else:
            items = data

        jobs: list[JobBase] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # Skip metadata element (has "legal" key, no "id")
            if "legal" in item or "id" not in item:
                continue
            try:
                location = str(item.get("location", ""))
                if not _is_uk_or_remote(location):
                    continue
                jobs.append(_remoteok_to_job(item))
            except Exception as exc:
                logger.warning("remoteok.adapter_error", error=str(exc))

        logger.info("remoteok.complete", jobs=len(jobs))
        return jobs


class JobicyCollector:
    """Collects jobs from Jobicy API."""

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="jobicy")

    async def fetch_all(self, count: int = 50) -> list[JobBase]:
        """Fetch jobs from Jobicy."""
        if not self.circuit_breaker.allow_request():
            return []

        try:
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={"count": count, "geo": "uk"},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="jobicy") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        jobs_data = data.get("jobs", [])
        if not isinstance(jobs_data, list):
            return []

        jobs: list[JobBase] = []
        for item in jobs_data:
            if not isinstance(item, dict):
                continue
            try:
                jobs.append(_jobicy_to_job(item))
            except Exception as exc:
                logger.warning("jobicy.adapter_error", error=str(exc))

        logger.info("jobicy.complete", jobs=len(jobs))
        return jobs


class HimalayasCollector:
    """Collects jobs from Himalayas API with pagination."""

    BASE_URL = "https://himalayas.app/jobs/api"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="himalayas")

    async def fetch_all(self, max_pages: int = 5, limit: int = 50) -> list[JobBase]:
        """Fetch jobs with pagination."""
        if not self.circuit_breaker.allow_request():
            return []

        all_jobs: list[JobBase] = []
        offset = 0

        for _ in range(max_pages):
            try:
                data = await fetch_with_retry(
                    self.client,
                    self.BASE_URL,
                    params={"limit": limit, "offset": offset},
                )
                self.circuit_breaker.record_success()
            except httpx.TimeoutException as exc:
                self.circuit_breaker.record_failure()
                raise SourceTimeoutError(str(exc), source="himalayas") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    self.circuit_breaker.record_rate_limit()
                else:
                    self.circuit_breaker.record_failure()
                raise

            jobs_data = data.get("jobs", [])
            if not isinstance(jobs_data, list) or not jobs_data:
                break

            for item in jobs_data:
                if not isinstance(item, dict):
                    continue
                try:
                    locations = item.get("locationRestrictions", [])
                    loc_str = (
                        " ".join(str(loc) for loc in locations)
                        if isinstance(locations, list)
                        else str(locations)
                    )
                    if not _is_uk_or_remote(loc_str):
                        continue
                    all_jobs.append(_himalayas_to_job(item))
                except Exception as exc:
                    logger.warning("himalayas.adapter_error", error=str(exc))

            if len(jobs_data) < limit:
                break
            offset += limit
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

        logger.info("himalayas.complete", jobs=len(all_jobs))
        return all_jobs


class RemotiveCollector:
    """Collects jobs from Remotive API."""

    BASE_URL = "https://remotive.com/api/remote-jobs"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="remotive")

    async def fetch_all(self, limit: int = 100) -> list[JobBase]:
        """Fetch jobs from Remotive."""
        if not self.circuit_breaker.allow_request():
            return []

        try:
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={"limit": limit},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="remotive") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        jobs_data = data.get("jobs", [])
        if not isinstance(jobs_data, list):
            return []

        jobs: list[JobBase] = []
        for item in jobs_data:
            if not isinstance(item, dict):
                continue
            try:
                location = str(item.get("candidate_required_location", ""))
                if not _is_uk_or_remote(location):
                    continue
                jobs.append(_remotive_to_job(item))
            except Exception as exc:
                logger.warning("remotive.adapter_error", error=str(exc))

        logger.info("remotive.complete", jobs=len(jobs))
        return jobs


class DevITJobsCollector:
    """Collects jobs from DevITjobs.uk API."""

    BASE_URL = "https://devitjobs.uk/api/jobsLight"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="devitjobs")

    async def fetch_all(self) -> list[JobBase]:
        """Fetch all UK dev/IT jobs (single endpoint, array response)."""
        if not self.circuit_breaker.allow_request():
            return []

        try:
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="devitjobs") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        # Response is a JSON array directly
        items = data if isinstance(data, list) else []

        jobs: list[JobBase] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                jobs.append(_devitjobs_to_job(item))
            except Exception as exc:
                logger.warning("devitjobs.adapter_error", error=str(exc))

        logger.info("devitjobs.complete", jobs=len(jobs))
        return jobs


class LandingJobsCollector:
    """Collects jobs from Landing.jobs API."""

    BASE_URL = "https://landing.jobs/api/v1/jobs.json"

    def __init__(
        self,
        client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="landingjobs")

    async def fetch_all(self, limit: int = 100) -> list[JobBase]:
        """Fetch jobs from Landing.jobs."""
        if not self.circuit_breaker.allow_request():
            return []

        try:
            data = await fetch_with_retry(
                self.client,
                self.BASE_URL,
                params={"limit": limit},
            )
            self.circuit_breaker.record_success()
        except httpx.TimeoutException as exc:
            self.circuit_breaker.record_failure()
            raise SourceTimeoutError(str(exc), source="landingjobs") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.circuit_breaker.record_rate_limit()
            else:
                self.circuit_breaker.record_failure()
            raise

        # Response is a JSON array directly
        items = data if isinstance(data, list) else []

        jobs: list[JobBase] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                locations = item.get("locations", [])
                loc_str = (
                    " ".join(
                        f"{loc.get('city', '')} {loc.get('country', '')}"
                        for loc in locations
                        if isinstance(loc, dict)
                    )
                    if isinstance(locations, list)
                    else ""
                )
                is_remote = bool(item.get("remote", False))
                if not is_remote and not _is_uk_or_remote(loc_str):
                    continue
                jobs.append(_landingjobs_to_job(item))
            except Exception as exc:
                logger.warning("landingjobs.adapter_error", error=str(exc))

        logger.info("landingjobs.complete", jobs=len(jobs))
        return jobs


# ---------------------------------------------------------------------------
# Adapter functions (map source JSON → JobBase)
# ---------------------------------------------------------------------------


def _arbeitnow_to_job(data: dict[str, object]) -> JobBase:
    """Convert Arbeitnow job JSON to JobBase."""
    from datetime import datetime, timedelta, timezone

    from src.models.job import _strip_html

    description_html = str(data.get("description", ""))
    description_plain = _strip_html(description_html)

    tags = data.get("tags", [])
    job_types = data.get("job_types", [])
    employment_type: list[str] = []
    if isinstance(job_types, list):
        for jt in job_types:
            employment_type.append(str(jt).lower().replace(" ", "_").replace("/", "_"))

    created_at = data.get("created_at")
    date_posted = None
    if isinstance(created_at, (int, float)):
        date_posted = datetime.fromtimestamp(int(created_at), tz=timezone.utc)

    date_expires = None
    if date_posted:
        date_expires = date_posted + timedelta(days=30)

    return JobBase(
        source_name="arbeitnow",
        external_id=str(data.get("slug", "")),
        source_url=str(data.get("url", "")),
        title=str(data.get("title", "")),
        description=description_html,
        description_plain=description_plain,
        company_name=str(data.get("company_name", "")),
        location_raw=str(data.get("location", "")),
        employment_type=employment_type,
        category_raw=", ".join(str(t) for t in tags)
        if isinstance(tags, list)
        else None,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _remoteok_to_job(data: dict[str, object]) -> JobBase:
    """Convert RemoteOK job JSON to JobBase."""
    from datetime import datetime, timedelta, timezone

    from src.models.job import _strip_html

    description_html = str(data.get("description", ""))
    description_plain = _strip_html(description_html)

    tags = data.get("tags", [])
    category_raw = ", ".join(str(t) for t in tags) if isinstance(tags, list) else None

    date_str = data.get("date")
    date_posted = None
    if date_str:
        try:
            date_posted = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except ValueError:
            pass

    if date_posted is None and data.get("epoch"):
        try:
            date_posted = datetime.fromtimestamp(int(data["epoch"]), tz=timezone.utc)  # type: ignore[arg-type]
        except (ValueError, TypeError, OSError):
            pass

    date_expires = None
    if date_posted:
        date_expires = date_posted + timedelta(days=30)

    salary_min = None
    salary_max = None
    if data.get("salary_min") and int(data["salary_min"]) > 0:  # type: ignore[arg-type]
        salary_min = float(data["salary_min"])  # type: ignore[arg-type]
    if data.get("salary_max") and int(data["salary_max"]) > 0:  # type: ignore[arg-type]
        salary_max = float(data["salary_max"])  # type: ignore[arg-type]

    return JobBase(
        source_name="remoteok",
        external_id=str(data.get("id", "")),
        source_url=str(
            data.get("url", f"https://remoteok.com/remote-jobs/{data.get('id', '')}")
        ),
        title=str(data.get("position", "")),
        description=description_html,
        description_plain=description_plain,
        company_name=str(data.get("company", "")),
        location_raw=str(data.get("location", "Remote")),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_period="annual" if salary_min else None,
        salary_currency="USD" if salary_min else None,
        employment_type=[],
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _jobicy_to_job(data: dict[str, object]) -> JobBase:
    """Convert Jobicy job JSON to JobBase."""
    from datetime import datetime, timedelta

    from src.models.job import _strip_html

    description_html = str(data.get("jobDescription", ""))
    description_plain = _strip_html(description_html)
    if not description_plain:
        description_plain = str(data.get("jobExcerpt", ""))

    job_types = data.get("jobType", [])
    employment_type: list[str] = []
    if isinstance(job_types, list):
        for jt in job_types:
            employment_type.append(str(jt).lower().replace("-", "_").replace(" ", "_"))

    date_posted = None
    if data.get("pubDate"):
        try:
            date_posted = datetime.fromisoformat(
                str(data["pubDate"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    date_expires = None
    if date_posted:
        date_expires = date_posted + timedelta(days=30)

    salary_min = None
    salary_max = None
    if data.get("salaryMin") is not None:
        try:
            salary_min = float(data["salaryMin"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    if data.get("salaryMax") is not None:
        try:
            salary_max = float(data["salaryMax"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

    salary_currency = (
        str(data["salaryCurrency"]) if data.get("salaryCurrency") else None
    )
    salary_period_raw = str(data["salaryPeriod"]) if data.get("salaryPeriod") else None
    salary_period = None
    if salary_period_raw:
        period_map = {
            "yearly": "annual",
            "monthly": "monthly",
            "weekly": "weekly",
            "hourly": "hourly",
        }
        salary_period = period_map.get(salary_period_raw.lower(), salary_period_raw)

    industries = data.get("jobIndustry", [])
    category_raw = (
        ", ".join(str(i) for i in industries) if isinstance(industries, list) else None
    )

    return JobBase(
        source_name="jobicy",
        external_id=str(data.get("id", "")),
        source_url=str(data.get("url", "")),
        title=str(data.get("jobTitle", "")),
        description=description_html,
        description_plain=description_plain,
        company_name=str(data.get("companyName", "")),
        location_raw=str(data.get("jobGeo", "Remote")),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_period=salary_period,
        employment_type=employment_type,
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _himalayas_to_job(data: dict[str, object]) -> JobBase:
    """Convert Himalayas job JSON to JobBase."""
    from datetime import datetime, timedelta, timezone

    description = str(data.get("description", ""))
    excerpt = str(data.get("excerpt", ""))

    locations = data.get("locationRestrictions", [])
    location_raw = (
        ", ".join(str(loc) for loc in locations)
        if isinstance(locations, list) and locations
        else "Remote"
    )

    employment_type_str = str(data.get("employmentType", ""))
    employment_type: list[str] = []
    if employment_type_str:
        employment_type.append(
            employment_type_str.lower().replace("-", "_").replace(" ", "_")
        )

    date_posted = None
    pub_date = data.get("pubDate")
    if isinstance(pub_date, (int, float)):
        date_posted = datetime.fromtimestamp(int(pub_date), tz=timezone.utc)

    date_expires = None
    expiry_date = data.get("expiryDate")
    if isinstance(expiry_date, (int, float)):
        date_expires = datetime.fromtimestamp(int(expiry_date), tz=timezone.utc)
    elif date_posted:
        date_expires = date_posted + timedelta(days=30)

    salary_min = None
    salary_max = None
    if data.get("minSalary") is not None:
        try:
            salary_min = float(data["minSalary"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    if data.get("maxSalary") is not None:
        try:
            salary_max = float(data["maxSalary"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

    salary_currency = str(data["currency"]) if data.get("currency") else None

    categories = data.get("categories", [])
    category_raw = (
        ", ".join(str(c) for c in categories) if isinstance(categories, list) else None
    )

    return JobBase(
        source_name="himalayas",
        external_id=str(data.get("guid", "")),
        source_url=str(data.get("applicationLink", "")),
        title=str(data.get("title", "")),
        description=description,
        description_plain=excerpt or description,
        company_name=str(data.get("companyName", "")),
        location_raw=location_raw,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_period="annual" if salary_min else None,
        employment_type=employment_type,
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _remotive_to_job(data: dict[str, object]) -> JobBase:
    """Convert Remotive job JSON to JobBase."""
    from datetime import datetime, timedelta

    from src.models.job import _strip_html

    description_html = str(data.get("description", ""))
    description_plain = _strip_html(description_html)

    job_type = str(data.get("job_type", ""))
    employment_type: list[str] = []
    if job_type:
        employment_type.append(job_type.lower().replace("-", "_").replace(" ", "_"))

    date_posted = None
    if data.get("publication_date"):
        try:
            date_posted = datetime.fromisoformat(
                str(data["publication_date"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    date_expires = None
    if date_posted:
        date_expires = date_posted + timedelta(days=30)

    category_raw = str(data.get("category", ""))

    salary_raw = str(data.get("salary", "")) or None

    return JobBase(
        source_name="remotive",
        external_id=str(data.get("id", "")),
        source_url=str(data.get("url", "")),
        title=str(data.get("title", "")),
        description=description_html,
        description_plain=description_plain,
        company_name=str(data.get("company_name", "")),
        location_raw=str(data.get("candidate_required_location", "Remote")),
        salary_raw=salary_raw,
        employment_type=employment_type,
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _devitjobs_to_job(data: dict[str, object]) -> JobBase:
    """Convert DevITjobs.uk job JSON to JobBase."""
    from datetime import datetime, timedelta

    job_name = str(data.get("name", ""))
    company = str(data.get("company", ""))
    city = str(data.get("actualCity", ""))
    address = str(data.get("address", ""))
    location_raw = city or address or "UK"

    employment_type: list[str] = []
    job_type = str(data.get("jobType", ""))
    if job_type:
        employment_type.append(job_type.lower().replace("-", "_").replace(" ", "_"))

    date_posted = None
    active_from = data.get("activeFrom")
    if active_from:
        try:
            date_posted = datetime.fromisoformat(
                str(active_from).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    date_expires = None
    if date_posted:
        date_expires = date_posted + timedelta(days=30)

    salary_min = None
    salary_max = None
    if data.get("annualSalaryFrom") is not None:
        try:
            salary_min = float(data["annualSalaryFrom"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    if data.get("annualSalaryTo") is not None:
        try:
            salary_max = float(data["annualSalaryTo"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

    technologies = data.get("technologies", [])
    category_raw = (
        ", ".join(str(t) for t in technologies)
        if isinstance(technologies, list)
        else None
    )

    latitude = None
    longitude = None
    if data.get("latitude") is not None:
        try:
            latitude = float(data["latitude"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    if data.get("longitude") is not None:
        try:
            longitude = float(data["longitude"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

    return JobBase(
        source_name="devitjobs",
        external_id=str(data.get("_id", "")),
        source_url=str(data.get("jobUrl", "")),
        title=job_name,
        description=job_name,
        description_plain=job_name,
        company_name=company,
        location_raw=location_raw,
        latitude=latitude,
        longitude=longitude,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_period="annual" if salary_min else None,
        salary_currency="GBP" if salary_min else None,
        employment_type=employment_type,
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


def _landingjobs_to_job(data: dict[str, object]) -> JobBase:
    """Convert Landing.jobs job JSON to JobBase."""
    from datetime import datetime, timedelta

    from src.models.job import _strip_html

    role_desc = str(data.get("role_description", ""))
    description_plain = _strip_html(role_desc)

    locations = data.get("locations", [])
    location_raw = ""
    if isinstance(locations, list) and locations:
        parts = []
        for loc in locations:
            if isinstance(loc, dict):
                city = str(loc.get("city", ""))
                country = str(loc.get("country", ""))
                parts.append(
                    f"{city}, {country}" if city and country else city or country
                )
        location_raw = "; ".join(parts)
    is_remote = bool(data.get("remote", False))
    if is_remote and not location_raw:
        location_raw = "Remote"

    employment_type: list[str] = []
    job_type = str(data.get("type", ""))
    if job_type:
        employment_type.append(job_type.lower().replace("-", "_").replace(" ", "_"))

    date_posted = None
    if data.get("published_at"):
        try:
            date_posted = datetime.fromisoformat(
                str(data["published_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    date_expires = None
    if data.get("expires_at"):
        try:
            date_expires = datetime.fromisoformat(
                str(data["expires_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass
    elif date_posted:
        date_expires = date_posted + timedelta(days=30)

    salary_min = None
    salary_max = None
    if data.get("gross_salary_low") is not None:
        try:
            salary_min = float(data["gross_salary_low"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    if data.get("gross_salary_high") is not None:
        try:
            salary_max = float(data["gross_salary_high"])  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

    salary_currency = str(data["currency_code"]) if data.get("currency_code") else None

    tags = data.get("tags", [])
    category_raw = ", ".join(str(t) for t in tags) if isinstance(tags, list) else None

    return JobBase(
        source_name="landingjobs",
        external_id=str(data.get("id", "")),
        source_url=str(data.get("url", "")),
        title=str(data.get("title", "")),
        description=role_desc,
        description_plain=description_plain,
        company_name=str(data.get("company_name", "Unknown")),
        location_raw=location_raw,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_period="annual" if salary_min else None,
        employment_type=employment_type,
        category_raw=category_raw,
        date_posted=date_posted,
        date_expires=date_expires,
        raw_data=dict(data),
    )


# ---------------------------------------------------------------------------
# Orchestrator: fetch from all 7 free sources
# ---------------------------------------------------------------------------


async def fetch_all_free_sources(client: httpx.AsyncClient) -> list[JobBase]:
    """Fetch jobs from all 7 free API sources.

    Args:
        client: httpx async client.

    Returns:
        Combined list of JobBase from all sources.
    """
    all_jobs: list[JobBase] = []
    collectors: list[tuple[str, object]] = [
        ("arbeitnow", ArbeitnowCollector(client=client)),
        ("remoteok", RemoteOKCollector(client=client)),
        ("jobicy", JobicyCollector(client=client)),
        ("himalayas", HimalayasCollector(client=client)),
        ("remotive", RemotiveCollector(client=client)),
        ("devitjobs", DevITJobsCollector(client=client)),
        ("landingjobs", LandingJobsCollector(client=client)),
    ]

    for name, collector in collectors:
        try:
            jobs = await collector.fetch_all()  # type: ignore[union-attr]
            all_jobs.extend(jobs)
            logger.info(f"free_api.{name}.collected", jobs=len(jobs))
        except Exception as exc:
            logger.error(f"free_api.{name}.failed", error=str(exc))
            # Continue with other sources — don't let one failure stop the rest

    logger.info("free_api.all_complete", total_jobs=len(all_jobs))
    return all_jobs
