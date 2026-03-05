"""Tests for circuit breaker (GATES C5) and rate limit handler (GATES C6)."""

from unittest.mock import patch

import httpx
import pytest

from src.models.errors import MaxRetriesExceeded


class TestCircuitBreaker:
    """Test circuit breaker state machine (Gate C5)."""

    def test_initial_state_closed(self) -> None:
        """Circuit breaker starts in CLOSED state."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        assert cb.state == "CLOSED"

    def test_three_failures_trip_to_open(self) -> None:
        """3 consecutive 500s → OPEN."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"

    def test_two_failures_stays_closed(self) -> None:
        """< threshold failures → stays CLOSED."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"

    def test_success_resets_failure_count(self) -> None:
        """Success resets consecutive failure counter."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == "CLOSED"
        # Now 3 more failures needed to trip
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"

    def test_open_to_half_open_after_timeout(self) -> None:
        """After recovery_timeout → HALF_OPEN."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"

        # Simulate time passing beyond recovery_timeout
        with patch("time.monotonic", return_value=cb._opened_at + 301):
            assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes(self) -> None:
        """HALF_OPEN + 1 success → CLOSED."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()

        # Move to HALF_OPEN
        with patch("time.monotonic", return_value=cb._opened_at + 301):
            assert cb.state == "HALF_OPEN"
            cb.record_success()

        assert cb.state == "CLOSED"

    def test_half_open_failure_reopens(self) -> None:
        """HALF_OPEN + 1 failure → back to OPEN."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()

        with patch("time.monotonic", return_value=cb._opened_at + 301):
            assert cb.state == "HALF_OPEN"
            cb.record_failure()

        assert cb.state == "OPEN"

    def test_429_does_not_trip(self) -> None:
        """429 responses do NOT trip the circuit breaker."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        # 429 is handled separately — should not count as failure
        for _ in range(5):
            cb.record_rate_limit()
        assert cb.state == "CLOSED"

    def test_open_blocks_requests(self) -> None:
        """OPEN state rejects requests."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()
        assert not cb.allow_request()

    def test_closed_allows_requests(self) -> None:
        """CLOSED state allows requests."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        assert cb.allow_request()

    def test_half_open_allows_one_request(self) -> None:
        """HALF_OPEN allows one test request."""
        from src.collectors.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()

        with patch("time.monotonic", return_value=cb._opened_at + 301):
            assert cb.allow_request()


class TestRateLimitHandler:
    """Test rate limit handler (Gate C6)."""

    @pytest.mark.asyncio()
    async def test_429_reads_retry_after(self) -> None:
        """429 response → reads Retry-After header → sleeps → retries."""
        from src.collectors.base import fetch_with_retry

        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    429, headers={"Retry-After": "1"}, text="Rate limited"
                )
            return httpx.Response(200, json={"data": "ok"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await fetch_with_retry(
                client, "https://example.com/api", params={}
            )
            assert result == {"data": "ok"}
            assert call_count == 2

    @pytest.mark.asyncio()
    async def test_max_retries_exceeded(self) -> None:
        """Max 3 retries → raises MaxRetriesExceeded."""
        from src.collectors.base import fetch_with_retry

        async def always_429(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429, headers={"Retry-After": "0"}, text="Rate limited"
            )

        transport = httpx.MockTransport(always_429)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(MaxRetriesExceeded):
                await fetch_with_retry(client, "https://example.com/api", params={})

    @pytest.mark.asyncio()
    async def test_timeout_with_exponential_backoff(self) -> None:
        """Timeout → exponential backoff → retry."""
        from src.collectors.base import fetch_with_retry

        call_count = 0

        async def timeout_then_ok(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.TimeoutException("timeout")
            return httpx.Response(200, json={"data": "ok"})

        transport = httpx.MockTransport(timeout_then_ok)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await fetch_with_retry(
                client, "https://example.com/api", params={}
            )
            assert result == {"data": "ok"}
            assert call_count == 3

    @pytest.mark.asyncio()
    async def test_default_retry_after(self) -> None:
        """Missing Retry-After header → default to 60s (capped for test)."""
        from src.collectors.base import fetch_with_retry

        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(429, text="Rate limited")  # No header
            return httpx.Response(200, json={"data": "ok"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await fetch_with_retry(
                client,
                "https://example.com/api",
                params={},
                max_retry_after=1,  # Cap for tests
            )
            assert result == {"data": "ok"}
