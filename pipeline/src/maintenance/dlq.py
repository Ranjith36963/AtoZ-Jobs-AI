"""Dead Letter Queue retry logic (SPEC.md §3.2, PLAYBOOK §4.2).

Read from dead_letter_queue where enqueued > 6 hours ago.
Route back to original queue based on msg->>'failed_stage'.
Max 5 total retries. Alert if >5% of source enters DLQ.
"""

from datetime import datetime, timedelta, timezone

import structlog

logger = structlog.get_logger()

DLQ_MAX_RETRIES = 5
DLQ_MIN_AGE_HOURS = 6

# Queue routing based on failed_stage
_STAGE_QUEUE_MAP: dict[str, str] = {
    "parse": "parse_queue",
    "normalize": "normalize_queue",
    "dedup": "dedup_queue",
    "geocode": "geocode_queue",
    "embed": "embed_queue",
    "summary": "parse_queue",
}


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string, returning None on failure."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _get_msg(message: dict[str, object]) -> dict[str, object]:
    """Extract the msg payload from a DLQ message."""
    msg = message.get("msg")
    if isinstance(msg, dict):
        return msg
    return {}


def should_retry(message: dict[str, object]) -> bool:
    """Check if a DLQ message should be retried.

    Args:
        message: DLQ message with 'msg' (payload) and 'enqueued_at' fields.

    Returns:
        True if message is old enough AND retry_count < DLQ_MAX_RETRIES.
    """
    msg = _get_msg(message)
    if not msg:
        return False

    # Check retry count
    retry_count = int(msg.get("retry_count", 0))  # type: ignore[call-overload]
    if retry_count >= DLQ_MAX_RETRIES:
        return False

    # Check age (must be > DLQ_MIN_AGE_HOURS)
    enqueued_at = _parse_datetime(
        str(message["enqueued_at"]) if message.get("enqueued_at") else None,
    )
    if enqueued_at is None:
        return False

    now = datetime.now(tz=timezone.utc)
    min_age = timedelta(hours=DLQ_MIN_AGE_HOURS)

    return (now - enqueued_at) > min_age


def get_target_queue(message: dict[str, object]) -> str:
    """Determine the target queue for a DLQ message based on failed_stage.

    Args:
        message: DLQ message with 'msg' payload containing 'failed_stage'.

    Returns:
        Queue name to route the message to. Defaults to 'parse_queue'.
    """
    msg = _get_msg(message)
    failed_stage = str(msg.get("failed_stage", ""))
    return _STAGE_QUEUE_MAP.get(failed_stage, "parse_queue")


def process_dlq_batch(
    messages: list[dict[str, object]],
) -> dict[str, int]:
    """Process a batch of DLQ messages.

    For each message:
    - If eligible for retry (old enough, retry_count < 5): mark for re-enqueue
    - If exhausted (retry_count >= 5): skip permanently
    - If too recent: skip for now

    Args:
        messages: List of DLQ messages.

    Returns:
        Dict with counts: {"retried": N, "exhausted": N, "skipped": N}
    """
    retried = 0
    exhausted = 0
    skipped = 0

    for message in messages:
        msg = _get_msg(message)

        retry_count = int(msg.get("retry_count", 0))  # type: ignore[call-overload]

        if retry_count >= DLQ_MAX_RETRIES:
            exhausted += 1
            logger.warning(
                "dlq_exhausted",
                job_id=msg.get("job_id"),
                retry_count=retry_count,
                failed_stage=msg.get("failed_stage"),
            )
            continue

        if not should_retry(message):
            skipped += 1
            continue

        # Eligible for retry
        target_queue = get_target_queue(message)
        retried += 1

        logger.info(
            "dlq_retry",
            job_id=msg.get("job_id"),
            retry_count=retry_count + 1,
            target_queue=target_queue,
            failed_stage=msg.get("failed_stage"),
        )

    logger.info(
        "dlq_batch_complete",
        retried=retried,
        exhausted=exhausted,
        skipped=skipped,
        total=len(messages),
    )

    return {"retried": retried, "exhausted": exhausted, "skipped": skipped}
