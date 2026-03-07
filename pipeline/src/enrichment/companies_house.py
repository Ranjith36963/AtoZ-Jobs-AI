"""Companies House API client (SPEC.md §5.2).

Free API for UK company data: search, profiles, SIC codes.
Rate limit: 600 requests per 5 minutes = 2 req/sec sustained.
"""

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

COMPANIES_HOUSE_BASE = "https://api.company-information.service.gov.uk"

# SIC code 2-digit prefix → section letter (A-U) mapping
_SIC_RANGES: list[tuple[int, int, str]] = [
    (1, 3, "A"), (5, 9, "B"), (10, 33, "C"), (35, 35, "D"),
    (36, 39, "E"), (41, 43, "F"), (45, 47, "G"), (49, 53, "H"),
    (55, 56, "I"), (58, 63, "J"), (64, 66, "K"), (68, 68, "L"),
    (69, 75, "M"), (77, 82, "N"), (84, 84, "O"), (85, 85, "P"),
    (86, 88, "Q"), (90, 93, "R"), (94, 96, "S"), (97, 98, "T"),
    (99, 99, "U"),
]


def sic_to_section(sic_code: str) -> str:
    """Map 5-digit SIC code to section letter (A-U).

    Args:
        sic_code: 5-digit SIC code string (e.g., '62020').

    Returns:
        Section letter (e.g., 'J' for Information and Communication).
    """
    if not sic_code or len(sic_code) < 2:
        return "S"  # default: Other Service Activities

    try:
        code = int(sic_code[:2])
    except ValueError:
        return "S"

    for start, end, section in _SIC_RANGES:
        if start <= code <= end:
            return section
    return "S"


async def search_company(
    name: str,
    api_key: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Search Companies House by company name.

    Args:
        name: Company name to search for.
        api_key: Companies House API key (used as Basic Auth username).
        client: Optional httpx client (for testing/reuse).

    Returns:
        Best match dict or None if not found.
    """
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True

    try:
        for attempt in range(3):
            try:
                resp = await client.get(
                    f"{COMPANIES_HOUSE_BASE}/search/companies",
                    params={"q": name, "items_per_page": 5},
                    auth=(api_key, ""),
                )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    logger.warning("companies_house.rate_limit", retry_after=retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 404:
                    return None

                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    return None
                return dict(items[0])

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        return None
    finally:
        if should_close:
            await client.aclose()


async def get_company_profile(
    company_number: str,
    api_key: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Get full company profile by Companies House number.

    Args:
        company_number: Companies House registration number.
        api_key: API key.
        client: Optional httpx client.

    Returns:
        Full company profile dict.
    """
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True

    try:
        resp = await client.get(
            f"{COMPANIES_HOUSE_BASE}/company/{company_number}",
            auth=(api_key, ""),
        )
        resp.raise_for_status()
        return dict(resp.json())
    finally:
        if should_close:
            await client.aclose()
