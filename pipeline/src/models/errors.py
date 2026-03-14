"""Pipeline error types.

Error taxonomy from SPEC.md — each error type has defined retry behaviour,
max retries, and backoff strategy.
"""


class PipelineError(Exception):
    """Base error for all pipeline operations."""

    retry: bool = False
    max_retries: int = 0

    def __init__(self, message: str, source: str = "") -> None:
        self.source = source
        super().__init__(message)


class CollectionValidationError(PipelineError):
    """Invalid job data that cannot be fixed by retrying.

    Examples: null title, missing external_id, salary < 0.
    """

    retry = False
    max_retries = 0


class RateLimitError(PipelineError):
    """429 response from source API.

    Retry after Retry-After header value (or default 60s).
    """

    retry = True
    max_retries = 3

    def __init__(self, message: str, source: str = "", retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(message, source)


class SourceTimeoutError(PipelineError):
    """Request to source API timed out.

    Retry with exponential backoff: 2^n seconds.
    """

    retry = True
    max_retries = 3


class ParseError(PipelineError):
    """Failed to parse source API response.

    Not retryable — likely an API response format change.
    Alert if >5% of source jobs fail parsing.
    """

    retry = False
    max_retries = 0


class EmbeddingError(PipelineError):
    """Failed to generate embedding vector.

    Retry with exponential backoff, then cascade:
    Gemini → OpenAI fallback → skip embedding.
    """

    retry = True
    max_retries = 3


class GeocodingError(PipelineError):
    """Failed to geocode location string.

    Retry up to 2 times, then fallback to city lookup table.
    """

    retry = True
    max_retries = 2


class DuplicateError(PipelineError):
    """Job already exists (same content_hash).

    Expected for aggregator sources (Jooble, Careerjet).
    Skip silently — not an error condition.
    """

    retry = False
    max_retries = 0


class MaxRetriesExceeded(PipelineError):
    """All retry attempts exhausted.

    Terminal error — job moves to dead letter queue.
    """

    retry = False
    max_retries = 0

    def __init__(self, url: str, attempts: int = 3) -> None:
        self.url = url
        self.attempts = attempts
        super().__init__(f"Max retries ({attempts}) exceeded for {url}", source="")
