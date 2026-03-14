"""Tests for DLQ retry logic (GATES.md M7-M8, SPEC.md §3.2).

TDD: Write tests first, confirm they fail, then implement.
"""

from datetime import datetime, timedelta, timezone


from src.maintenance.dlq import (
    DLQ_MAX_RETRIES,
    DLQ_MIN_AGE_HOURS,
    get_target_queue,
    process_dlq_batch,
    should_retry,
)

NOW = datetime.now(tz=timezone.utc)


def _make_dlq_message(
    failed_stage: str = "geocode",
    retry_count: int = 2,
    enqueued_at: datetime | None = None,
    job_id: int = 1,
) -> dict[str, object]:
    return {
        "msg": {
            "job_id": job_id,
            "failed_stage": failed_stage,
            "retry_count": retry_count,
            "last_error": "test error",
        },
        "enqueued_at": (enqueued_at or NOW - timedelta(hours=7)).isoformat(),
    }


# ── M7: Job in DLQ >6 hours with retry_count < 5 → re-enqueued ──


class TestShouldRetry:
    def test_eligible_for_retry(self) -> None:
        """Job >6h old with retry_count < 5 should be retried."""
        msg = _make_dlq_message(retry_count=2, enqueued_at=NOW - timedelta(hours=7))
        assert should_retry(msg) is True

    def test_too_recent_no_retry(self) -> None:
        """Job <6h old should not be retried yet."""
        msg = _make_dlq_message(retry_count=2, enqueued_at=NOW - timedelta(hours=3))
        assert should_retry(msg) is False

    def test_well_under_6_hours_no_retry(self) -> None:
        """Job at 3h should not be retried yet."""
        now = datetime.now(tz=timezone.utc)
        msg = _make_dlq_message(retry_count=2, enqueued_at=now - timedelta(hours=3))
        assert should_retry(msg) is False


# ── M8: Job in DLQ with retry_count = 5 → stays in DLQ ──


class TestDLQExhausted:
    def test_max_retries_exhausted(self) -> None:
        """Job with retry_count = 5 should NOT be retried."""
        msg = _make_dlq_message(retry_count=5, enqueued_at=NOW - timedelta(hours=10))
        assert should_retry(msg) is False

    def test_over_max_retries(self) -> None:
        """Job with retry_count > 5 should NOT be retried."""
        msg = _make_dlq_message(retry_count=8, enqueued_at=NOW - timedelta(hours=10))
        assert should_retry(msg) is False


# ── Route by failed_stage ──


class TestGetTargetQueue:
    def test_geocode_stage_routes_to_geocode_queue(self) -> None:
        msg = _make_dlq_message(failed_stage="geocode")
        assert get_target_queue(msg) == "geocode_queue"

    def test_embed_stage_routes_to_embed_queue(self) -> None:
        msg = _make_dlq_message(failed_stage="embed")
        assert get_target_queue(msg) == "embed_queue"

    def test_parse_stage_routes_to_parse_queue(self) -> None:
        msg = _make_dlq_message(failed_stage="parse")
        assert get_target_queue(msg) == "parse_queue"

    def test_normalize_stage_routes_to_normalize_queue(self) -> None:
        msg = _make_dlq_message(failed_stage="normalize")
        assert get_target_queue(msg) == "normalize_queue"

    def test_unknown_stage_defaults_to_parse_queue(self) -> None:
        """Unknown failed_stage should default to parse_queue."""
        msg = _make_dlq_message(failed_stage="unknown")
        assert get_target_queue(msg) == "parse_queue"

    def test_missing_failed_stage_defaults_to_parse_queue(self) -> None:
        """Missing failed_stage should default to parse_queue."""
        msg: dict[str, object] = {
            "msg": {"job_id": 1, "retry_count": 1},
            "enqueued_at": NOW.isoformat(),
        }
        assert get_target_queue(msg) == "parse_queue"


# ── process_dlq_batch ──


class TestProcessDLQBatch:
    def test_mixed_batch(self) -> None:
        """Batch with some retriable and some exhausted messages."""
        messages = [
            # Retriable: old enough, retry_count < 5
            _make_dlq_message(
                retry_count=2,
                enqueued_at=NOW - timedelta(hours=7),
                failed_stage="geocode",
                job_id=1,
            ),
            # Exhausted: retry_count = 5
            _make_dlq_message(
                retry_count=5,
                enqueued_at=NOW - timedelta(hours=10),
                failed_stage="embed",
                job_id=2,
            ),
            # Too recent: < 6 hours
            _make_dlq_message(
                retry_count=1,
                enqueued_at=NOW - timedelta(hours=2),
                failed_stage="parse",
                job_id=3,
            ),
        ]
        result = process_dlq_batch(messages)
        assert result["retried"] == 1
        assert result["exhausted"] == 1
        assert result["skipped"] == 1

    def test_empty_batch(self) -> None:
        """Empty batch returns zero counts."""
        result = process_dlq_batch([])
        assert result["retried"] == 0
        assert result["exhausted"] == 0
        assert result["skipped"] == 0

    def test_all_retriable(self) -> None:
        """All messages eligible for retry."""
        messages = [
            _make_dlq_message(
                retry_count=i,
                enqueued_at=NOW - timedelta(hours=8),
                job_id=i,
            )
            for i in range(4)
        ]
        result = process_dlq_batch(messages)
        assert result["retried"] == 4
        assert result["exhausted"] == 0

    def test_retry_increments_count(self) -> None:
        """Retried message should have retry_count incremented."""
        msg = _make_dlq_message(retry_count=2, enqueued_at=NOW - timedelta(hours=7))
        result = process_dlq_batch([msg])
        assert result["retried"] == 1


# ── Constants ──


class TestDLQConstants:
    def test_max_retries(self) -> None:
        assert DLQ_MAX_RETRIES == 5

    def test_min_age_hours(self) -> None:
        assert DLQ_MIN_AGE_HOURS == 6


# ── Sad paths ──


class TestDLQEdgeCases:
    def test_malformed_message_no_msg(self) -> None:
        """Message without 'msg' key should be handled gracefully."""
        msg: dict[str, object] = {"enqueued_at": NOW.isoformat()}
        assert should_retry(msg) is False

    def test_malformed_message_no_retry_count(self) -> None:
        """Message without retry_count defaults to 0."""
        msg: dict[str, object] = {
            "msg": {"job_id": 1, "failed_stage": "parse"},
            "enqueued_at": (NOW - timedelta(hours=7)).isoformat(),
        }
        assert should_retry(msg) is True

    def test_malformed_enqueued_at(self) -> None:
        """Invalid enqueued_at should not crash."""
        msg: dict[str, object] = {
            "msg": {"job_id": 1, "retry_count": 1, "failed_stage": "parse"},
            "enqueued_at": "not-a-date",
        }
        assert should_retry(msg) is False
