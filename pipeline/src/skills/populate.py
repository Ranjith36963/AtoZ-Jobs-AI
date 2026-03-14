"""Job skills population (SPEC.md §3.3).

Backfills job_skills for all ready jobs missing skill extraction.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from src.skills.spacy_matcher import SpaCySkillMatcher

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds


def _call_with_retry(
    operation: str,
    fn: Any,
) -> Any:
    """Retry a synchronous Supabase call with exponential backoff.

    Args:
        operation: Description for logging.
        fn: Callable that performs the DB operation.

    Returns:
        The result of the DB call.
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == _MAX_RETRIES:
                raise
            wait = _BACKOFF_BASE ** (attempt + 1)
            logger.warning(
                "db.retry",
                operation=operation,
                attempt=attempt + 1,
                wait=wait,
                error=str(e),
            )
            time.sleep(wait)
    return None  # unreachable, satisfies type checker


async def get_jobs_without_skills(
    db_client: Client,
    batch_size: int = 500,
    processed_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Query ready jobs with no job_skills entries.

    Args:
        db_client: Supabase client.
        batch_size: Number of jobs per batch.
        processed_ids: IDs already processed this run (avoids re-fetching).

    Returns:
        List of job dicts with id, title, description_plain.
    """
    exclude_ids: set[int] = set(processed_ids) if processed_ids else set()

    # Paginate the exclusion list to avoid a single massive query
    page_size = 5000
    offset = 0
    while True:
        result = _call_with_retry(
            "fetch_existing_skills",
            lambda o=offset: (
                db_client.table("job_skills")
                .select("job_id")
                .range(o, o + page_size - 1)
                .execute()
            ),
        )
        if not result.data:
            break
        for row in result.data:
            exclude_ids.add(row["job_id"])
        if len(result.data) < page_size:
            break
        offset += page_size

    # Supabase .not_.in_() needs a non-empty list
    exclude_list = list(exclude_ids) if exclude_ids else [0]

    result = _call_with_retry(
        "fetch_jobs_without_skills",
        lambda: (
            db_client.table("jobs")
            .select("id, title, description_plain")
            .eq("status", "ready")
            .not_.in_("id", exclude_list)
            .limit(batch_size)
            .execute()
        ),
    )
    return list(result.data) if result.data else []


async def upsert_skill(
    db_client: Client,
    skill_name: str,
) -> int:
    """Get or create a skill by name.

    Args:
        db_client: Supabase client.
        skill_name: Canonical skill name.

    Returns:
        Skill ID.
    """
    result = _call_with_retry(
        "select_skill",
        lambda: (
            db_client.table("skills")
            .select("id")
            .eq("name", skill_name)
            .limit(1)
            .execute()
        ),
    )
    if result.data:
        return int(result.data[0]["id"])

    insert_result = _call_with_retry(
        "insert_skill",
        lambda: db_client.table("skills").insert({"name": skill_name}).execute(),
    )
    return int(insert_result.data[0]["id"])


async def insert_job_skills(
    db_client: Client,
    job_id: int,
    skill_ids: list[int],
) -> None:
    """Bulk insert job_skills entries.

    Args:
        db_client: Supabase client.
        job_id: Job ID.
        skill_ids: List of skill IDs to associate.
    """
    rows = [
        {
            "job_id": job_id,
            "skill_id": sid,
            "confidence": 1.0,
            "is_required": True,
        }
        for sid in skill_ids
    ]
    if rows:
        _call_with_retry(
            "upsert_job_skills",
            lambda: db_client.table("job_skills").upsert(rows).execute(),
        )


async def populate_job_skills(
    db_client: Client,
    matcher: SpaCySkillMatcher,
    batch_size: int = 500,
) -> dict[str, int]:
    """Backfill job_skills for all ready jobs missing skill extraction.

    Args:
        db_client: Supabase client.
        matcher: Initialized SpaCySkillMatcher.
        batch_size: Jobs per batch.

    Returns:
        Dict with processing stats: jobs_processed, skills_extracted, errors.
    """
    stats = {"jobs_processed": 0, "skills_extracted": 0, "errors": 0}
    processed_ids: set[int] = set()

    while True:
        jobs = await get_jobs_without_skills(db_client, batch_size, processed_ids)
        if not jobs:
            break

        for job in jobs:
            try:
                text = f"{job.get('title', '')} {job.get('description_plain', '')}"
                skill_names = matcher.extract(text)

                skill_ids = []
                for name in skill_names:
                    sid = await upsert_skill(db_client, name)
                    skill_ids.append(sid)

                await insert_job_skills(db_client, job["id"], skill_ids)

                processed_ids.add(job["id"])
                stats["jobs_processed"] += 1
                stats["skills_extracted"] += len(skill_ids)

                if stats["jobs_processed"] % 100 == 0:
                    logger.info(
                        "populate.progress",
                        jobs_processed=stats["jobs_processed"],
                        skills_extracted=stats["skills_extracted"],
                    )
            except Exception as e:
                processed_ids.add(job["id"])
                stats["errors"] += 1
                logger.error("populate.error", job_id=job["id"], error=str(e))

    logger.info("populate.complete", **stats)
    return stats
