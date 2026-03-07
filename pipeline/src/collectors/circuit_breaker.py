"""Circuit breaker pattern for API collectors (SPEC.md §2.6).

3 states: CLOSED → OPEN → HALF_OPEN
- CLOSED: Execute requests. Count consecutive failures.
- OPEN: Skip all requests. After recovery_timeout → HALF_OPEN.
- HALF_OPEN: Allow one request. Success → CLOSED. Fail → OPEN.

429 responses do NOT trip the breaker — they trigger Retry-After backoff.
"""

import time

import structlog

logger = structlog.get_logger()


class CircuitBreaker:
    """Circuit breaker with configurable threshold and recovery timeout."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
        name: str = "",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._failure_count = 0
        self._state = "CLOSED"
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        """Current circuit breaker state, accounting for timeout transitions."""
        if self._state == "OPEN":
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                return "HALF_OPEN"
        return self._state

    def allow_request(self) -> bool:
        """Check if a request is allowed in the current state."""
        current_state = self.state
        if current_state == "CLOSED":
            return True
        if current_state == "HALF_OPEN":
            return True
        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful request."""
        self._failure_count = 0
        self._state = "CLOSED"
        logger.debug("circuit_breaker.success", name=self.name, state="CLOSED")

    def record_failure(self) -> None:
        """Record a failed request (5xx, timeout, connection error)."""
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            self._opened_at = time.monotonic()
            logger.warning(
                "circuit_breaker.opened",
                name=self.name,
                failures=self._failure_count,
            )
        else:
            logger.debug(
                "circuit_breaker.failure",
                name=self.name,
                count=self._failure_count,
                threshold=self.failure_threshold,
            )

    def record_rate_limit(self) -> None:
        """Record a 429 response — does NOT trip the breaker."""
        logger.info("circuit_breaker.rate_limit", name=self.name)
        # Intentionally does NOT increment failure count
