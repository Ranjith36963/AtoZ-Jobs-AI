"""JobBase Pydantic model and source adapters.

Universal job schema (SPEC.md §2.1–§2.4) with adapters that map
each source's JSON response to the common format.
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from bs4 import BeautifulSoup
from pydantic import BaseModel, computed_field, field_validator, model_validator

# Type aliases for clarity
NonEmptyStr = Annotated[str, "non-empty string"]


def _strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(text: str) -> str:
    """Normalize text for content hash: lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


class JobBase(BaseModel):
    """Universal job schema for all sources.

    Maps to the `jobs` table. Every collector converts its source-specific
    format into this model before UPSERT.
    """

    source_name: str
    external_id: str
    source_url: str
    title: str
    description: str
    description_plain: str
    company_name: str
    location_raw: str
    latitude: float | None = None
    longitude: float | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_raw: str | None = None
    salary_period: str | None = None
    salary_currency: str | None = None
    salary_is_predicted: bool = False
    employment_type: list[str] = []
    contract_type: str | None = None
    date_posted: datetime | None = None
    date_expires: datetime | None = None
    category_raw: str | None = None
    raw_data: dict[str, object]

    @field_validator("title", "description", "company_name")
    @classmethod
    def not_empty(cls, v: str, info: object) -> str:
        """Reject empty or whitespace-only strings."""
        if not v or not v.strip():
            raise ValueError(f"{info} must not be empty")  # type: ignore[arg-type]
        return v.strip()

    @model_validator(mode="after")
    def salary_sanity(self) -> "JobBase":
        """Reject negative salaries or unreasonably high values (>£1M)."""
        for field_name in ("salary_min", "salary_max"):
            value = getattr(self, field_name)
            if value is not None and (value < 0 or value > 1_000_000):
                raise ValueError(f"{field_name}={value} out of range [0, 1000000]")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_hash(self) -> str:
        """SHA-256 of normalized title|company|location for dedup."""
        parts = "|".join(
            [
                _normalize_text(self.title),
                _normalize_text(self.company_name),
                _normalize_text(self.location_raw),
            ]
        )
        return hashlib.sha256(parts.encode("utf-8")).hexdigest()


class ReedJobAdapter:
    """Maps Reed API response to JobBase (SPEC.md §2.1)."""

    @staticmethod
    def to_job_base(data: dict[str, object]) -> JobBase:
        """Convert a single Reed job JSON object to JobBase."""
        description_html = str(data.get("jobDescription", ""))
        description_plain = _strip_html(description_html)

        # Build employment_type from boolean flags
        employment_type: list[str] = []
        if data.get("fullTime"):
            employment_type.append("full_time")
        if data.get("partTime"):
            employment_type.append("part_time")

        contract_type = str(data["contractType"]) if data.get("contractType") else None
        if contract_type:
            employment_type.append(contract_type)

        # Parse dates
        date_posted = None
        if data.get("date"):
            date_posted = datetime.fromisoformat(str(data["date"]))

        date_expires = None
        if data.get("expirationDate"):
            date_expires = datetime.fromisoformat(str(data["expirationDate"]))

        return JobBase(
            source_name="reed",
            external_id=str(data["jobId"]),
            source_url=str(data.get("jobUrl", "")),
            title=str(data["jobTitle"]),
            description=description_html,
            description_plain=description_plain,
            company_name=str(data.get("employerName", "")),
            location_raw=str(data.get("locationName", "")),
            salary_min=float(data["minimumSalary"])
            if data.get("minimumSalary") is not None
            else None,
            salary_max=float(data["maximumSalary"])
            if data.get("maximumSalary") is not None
            else None,
            salary_raw=None,
            salary_period="annual",
            salary_currency=str(data["currency"]) if data.get("currency") else None,
            salary_is_predicted=False,
            employment_type=employment_type,
            contract_type=contract_type,
            date_posted=date_posted,
            date_expires=date_expires,
            category_raw=str(data.get("jobCategoryName", "")),
            raw_data=dict(data),
        )


class AdzunaJobAdapter:
    """Maps Adzuna API response to JobBase (SPEC.md §2.2)."""

    @staticmethod
    def to_job_base(data: dict[str, object]) -> JobBase:
        """Convert a single Adzuna job JSON object to JobBase."""
        description = str(data.get("description", ""))

        # Employment type from contract fields
        employment_type: list[str] = []
        if data.get("contract_type"):
            employment_type.append(str(data["contract_type"]))
        if data.get("contract_time"):
            employment_type.append(str(data["contract_time"]))

        # Location
        location_data = data.get("location", {})
        location_raw = ""
        if isinstance(location_data, dict):
            location_raw = str(location_data.get("display_name", ""))

        # Latitude/longitude extracted directly (skip postcodes.io)
        latitude = float(data["latitude"]) if data.get("latitude") is not None else None
        longitude = (
            float(data["longitude"]) if data.get("longitude") is not None else None
        )

        # Salary prediction flag: 0/1 → bool
        salary_is_predicted = bool(data.get("salary_is_predicted", 0))

        # Category
        category_data = data.get("category", {})
        category_raw = None
        if isinstance(category_data, dict):
            category_raw = str(category_data.get("tag", ""))

        # Company
        company_data = data.get("company", {})
        company_name = ""
        if isinstance(company_data, dict):
            company_name = str(company_data.get("display_name", ""))

        # Dates — no date_expires from Adzuna, use 45-day default
        date_posted = None
        if data.get("created"):
            date_posted = datetime.fromisoformat(
                str(data["created"]).replace("Z", "+00:00")
            )

        date_expires = None
        if date_posted:
            date_expires = date_posted + timedelta(days=45)

        return JobBase(
            source_name="adzuna",
            external_id=str(data["id"]),
            source_url=str(data.get("redirect_url", "")),
            title=str(data.get("title", "")),
            description=description,
            description_plain=description,  # Adzuna returns plain text
            company_name=company_name,
            location_raw=location_raw,
            latitude=latitude,
            longitude=longitude,
            salary_min=float(data["salary_min"])
            if data.get("salary_min") is not None
            else None,
            salary_max=float(data["salary_max"])
            if data.get("salary_max") is not None
            else None,
            salary_raw=None,
            salary_period="annual",
            salary_currency="GBP",
            salary_is_predicted=salary_is_predicted,
            employment_type=employment_type,
            contract_type=str(data["contract_type"])
            if data.get("contract_type")
            else None,
            date_posted=date_posted,
            date_expires=date_expires,
            category_raw=category_raw,
            raw_data=dict(data),
        )


class JoobleJobAdapter:
    """Maps Jooble API response to JobBase (SPEC.md §2.3)."""

    @staticmethod
    def to_job_base(data: dict[str, object]) -> JobBase:
        """Convert a single Jooble job JSON object to JobBase."""
        snippet = str(data.get("snippet", ""))

        # Employment type
        employment_type: list[str] = []
        job_type = data.get("type")
        if job_type:
            type_str = str(job_type).lower().replace("-", "_").replace(" ", "_")
            employment_type.append(type_str)

        # Date
        date_posted = None
        if data.get("updated"):
            date_str = str(data["updated"])
            try:
                date_posted = datetime.fromisoformat(date_str)
            except ValueError:
                # Try date-only format
                date_posted = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )

        # 30-day default expiry (SPEC §6: Jooble = 30 days)
        date_expires = None
        if date_posted:
            date_expires = date_posted + timedelta(days=30)

        return JobBase(
            source_name="jooble",
            external_id=str(data.get("id", "")),
            source_url=str(data.get("link", "")),
            title=str(data.get("title", "")),
            description=snippet,
            description_plain=snippet,
            company_name=str(data.get("company", "")),
            location_raw=str(data.get("location", "")),
            salary_raw=str(data.get("salary", "")) or None,
            employment_type=employment_type,
            date_posted=date_posted,
            date_expires=date_expires,
            raw_data=dict(data),
        )


class CareerjetJobAdapter:
    """Maps Careerjet API v4 response to JobBase (SPEC.md §2.4)."""

    @staticmethod
    def to_job_base(data: dict[str, object]) -> JobBase:
        """Convert a single Careerjet job JSON object to JobBase."""
        description = str(data.get("description", ""))

        # v4 structured salary fields
        salary_min = (
            float(data["salary_min"]) if data.get("salary_min") is not None else None
        )
        salary_max = (
            float(data["salary_max"]) if data.get("salary_max") is not None else None
        )
        salary_type = str(data["salary_type"]) if data.get("salary_type") else None
        salary_currency = (
            str(data["salary_currency_code"])
            if data.get("salary_currency_code")
            else None
        )
        salary_raw = str(data.get("salary", "")) or None

        # Map salary_type to period
        salary_period = None
        if salary_type:
            period_map = {
                "yearly": "annual",
                "monthly": "monthly",
                "weekly": "weekly",
                "daily": "daily",
                "hourly": "hourly",
            }
            salary_period = period_map.get(salary_type, salary_type)

        # Date
        date_posted = None
        if data.get("date"):
            date_str = str(data["date"])
            try:
                date_posted = datetime.fromisoformat(date_str)
            except ValueError:
                date_posted = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )

        # 30-day default expiry (SPEC §6: Careerjet = 30 days)
        date_expires = None
        if date_posted:
            date_expires = date_posted + timedelta(days=30)

        return JobBase(
            source_name="careerjet",
            external_id=str(data.get("url", "")),  # Careerjet uses URL as ID
            source_url=str(data.get("url", "")),
            title=str(data.get("title", "")),
            description=description,
            description_plain=description,
            company_name=str(data.get("company", "")),
            location_raw=str(data.get("locations", "")),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_raw=salary_raw,
            salary_period=salary_period,
            salary_currency=salary_currency,
            employment_type=[],
            date_posted=date_posted,
            date_expires=date_expires,
            raw_data=dict(data),
        )
