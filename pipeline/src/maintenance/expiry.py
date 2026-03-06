"""Job expiry detection (SPEC.md §6, PLAYBOOK §4.1).

Source-specific logic:
  Reed: use expirationDate field (provided in API response), default 30 days
  Adzuna: 45 days from date_posted (no expiry field)
  Jooble/Careerjet: 30 days from date_posted (no expiry field)

State transitions: ready → expired → archived → hard delete (CASCADE).
"""

from datetime import datetime, timedelta, timezone

import structlog

logger = structlog.get_logger()

# Source-specific expiry defaults (days from date_posted when no date_expires)
REED_DEFAULT_EXPIRY_DAYS = 30
ADZUNA_EXPIRY_DAYS = 45
JOOBLE_CAREERJET_EXPIRY_DAYS = 30
DEFAULT_EXPIRY_DAYS = 30

ARCHIVE_AFTER_DAYS = 90
HARD_DELETE_AFTER_DAYS = 180

_SOURCE_EXPIRY_DAYS: dict[str, int] = {
    "reed": REED_DEFAULT_EXPIRY_DAYS,
    "adzuna": ADZUNA_EXPIRY_DAYS,
    "jooble": JOOBLE_CAREERJET_EXPIRY_DAYS,
    "careerjet": JOOBLE_CAREERJET_EXPIRY_DAYS,
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


def check_expiry(job: dict[str, object]) -> dict[str, object]:
    """Check if a job should be marked as expired.

    Args:
        job: Job dict with source_name, status, date_posted, date_expires fields.

    Returns:
        Job dict with status updated to 'expired' if applicable.
    """
    status = str(job.get("status", ""))
    if status in ("expired", "archived"):
        return job

    now = datetime.now(tz=timezone.utc)
    source_name = str(job.get("source_name", ""))

    # Check explicit date_expires first
    date_expires = _parse_datetime(
        str(job["date_expires"]) if job.get("date_expires") else None,
    )
    if date_expires is not None and date_expires < now:
        job["status"] = "expired"
        job["last_error"] = f"expired: date_expires={date_expires.isoformat()}"
        logger.info(
            "job_expired",
            job_id=job.get("id"),
            reason="date_expires",
            source=source_name,
        )
        return job

    # Fall back to source-specific default expiry from date_posted
    date_posted = _parse_datetime(
        str(job["date_posted"]) if job.get("date_posted") else None,
    )
    if date_posted is None:
        # Cannot determine expiry without date_posted — keep current status
        return job

    expiry_days = _SOURCE_EXPIRY_DAYS.get(source_name, DEFAULT_EXPIRY_DAYS)
    default_expires = date_posted + timedelta(days=expiry_days)

    if default_expires < now:
        job["status"] = "expired"
        job["last_error"] = (
            f"default-{expiry_days}d-expired: date_posted={date_posted.isoformat()}"
        )
        logger.info(
            "job_expired",
            job_id=job.get("id"),
            reason=f"default_{expiry_days}d",
            source=source_name,
        )

    return job


def archive_expired(jobs: list[dict[str, object]]) -> list[dict[str, object]]:
    """Archive expired jobs older than 90 days.

    Args:
        jobs: List of job dicts to evaluate.

    Returns:
        List of jobs that were archived (status changed to 'archived').
    """
    now = datetime.now(tz=timezone.utc)
    archived: list[dict[str, object]] = []

    for job in jobs:
        if str(job.get("status", "")) != "expired":
            continue

        date_crawled = _parse_datetime(
            str(job["date_crawled"]) if job.get("date_crawled") else None,
        )
        if date_crawled is None:
            continue

        if date_crawled < now - timedelta(days=ARCHIVE_AFTER_DAYS):
            job["status"] = "archived"
            archived.append(job)
            logger.info(
                "job_archived",
                job_id=job.get("id"),
                days_old=(now - date_crawled).days,
            )

    return archived


def hard_delete_candidates(jobs: list[dict[str, object]]) -> list[int]:
    """Identify archived jobs older than 180 days for hard deletion.

    Args:
        jobs: List of job dicts to evaluate.

    Returns:
        List of job IDs that should be deleted (CASCADE removes job_skills).
    """
    now = datetime.now(tz=timezone.utc)
    to_delete: list[int] = []

    for job in jobs:
        if str(job.get("status", "")) != "archived":
            continue

        date_crawled = _parse_datetime(
            str(job["date_crawled"]) if job.get("date_crawled") else None,
        )
        if date_crawled is None:
            continue

        if date_crawled < now - timedelta(days=HARD_DELETE_AFTER_DAYS):
            job_id = job.get("id")
            if isinstance(job_id, int):
                to_delete.append(job_id)
                logger.info(
                    "job_hard_delete_candidate",
                    job_id=job_id,
                    days_old=(now - date_crawled).days,
                )

    return to_delete


def mark_disappeared(
    current_ids: set[str],
    previous_ids: set[str],
    twice_missing: set[str],
) -> set[str]:
    """Track jobs that disappeared from API for re-verification.

    Jobs must be missing for 2 consecutive fetch cycles before being expired.

    Args:
        current_ids: External IDs found in the current fetch cycle.
        previous_ids: External IDs found in the previous fetch cycle.
        twice_missing: IDs already flagged as missing once (from prior call).

    Returns:
        Set of external IDs that are missing in this cycle (first or second miss).
        IDs in both this result AND twice_missing should be expired.
    """
    newly_missing = previous_ids - current_ids

    logger.info(
        "reverification_check",
        total_current=len(current_ids),
        total_previous=len(previous_ids),
        newly_missing=len(newly_missing),
        twice_missing_count=len(newly_missing & twice_missing),
    )

    return newly_missing
