"""Shared collector logic: fetch_with_retry, rate limit handling (SPEC.md §2.7)."""

import asyncio

import httpx
import structlog

from src.models.errors import MaxRetriesExceeded

logger = structlog.get_logger()


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, str | int],
    max_retries: int = 3,
    max_retry_after: int = 60,
    method: str = "GET",
    json_body: dict[str, object] | None = None,
) -> dict[str, object]:
    """Fetch URL with retry on 429 and timeout (SPEC.md §2.7).

    Args:
        client: httpx async client.
        url: Request URL.
        params: Query parameters.
        max_retries: Maximum retry attempts.
        max_retry_after: Cap on Retry-After header value (for testing).
        method: HTTP method (GET or POST).
        json_body: JSON body for POST requests.

    Returns:
        Parsed JSON response.

    Raises:
        MaxRetriesExceeded: All retries exhausted.
    """
    for attempt in range(max_retries):
        try:
            if method == "POST":
                resp = await client.post(url, params=params, json=json_body)
            else:
                resp = await client.get(url, params=params)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", max_retry_after))
                retry_after = min(retry_after, max_retry_after)
                logger.warning(
                    "rate_limited",
                    url=url,
                    retry_after=retry_after,
                    attempt=attempt + 1,
                )
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            result: dict[str, object] = resp.json()
            return result

        except httpx.TimeoutException:
            backoff = 2**attempt
            logger.warning(
                "timeout",
                url=url,
                attempt=attempt + 1,
                backoff=backoff,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff)

    raise MaxRetriesExceeded(url, max_retries)
