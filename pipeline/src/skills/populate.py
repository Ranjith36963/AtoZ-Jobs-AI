"""Job skills population (SPEC.md §3.3).

Backfills job_skills for all ready jobs missing skill extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from src.skills.spacy_matcher import SpaCySkillMatcher

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()


async def get_jobs_without_skills(
    db_client: Client,
    batch_size: int = 500,
) -> list[dict[str, Any]]:
    """Query ready jobs with no job_skills entries.

    Args:
        db_client: Supabase client.
        batch_size: Number of jobs per batch.

    Returns:
        List of job dicts with id, title, description_plain.
    """
    existing = db_client.table("job_skills").select("job_id").execute().data
    existing_ids = [row["job_id"] for row in existing] if existing else []

    result = (
        db_client.table("jobs")
        .select("id, title, description_plain")
        .eq("status", "ready")
        .not_.in_("id", existing_ids)
        .limit(batch_size)
        .execute()
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
    # Try to find existing
    result = (
        db_client.table("skills").select("id").eq("name", skill_name).limit(1).execute()
    )
    if result.data:
        return int(result.data[0]["id"])

    # Insert new skill
    insert_result = db_client.table("skills").insert({"name": skill_name}).execute()
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
        db_client.table("job_skills").upsert(rows).execute()


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

    while True:
        jobs = await get_jobs_without_skills(db_client, batch_size)
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

                stats["jobs_processed"] += 1
                stats["skills_extracted"] += len(skill_ids)

                if stats["jobs_processed"] % 100 == 0:
                    logger.info(
                        "populate.progress",
                        jobs_processed=stats["jobs_processed"],
                        skills_extracted=stats["skills_extracted"],
                    )
            except Exception as e:
                stats["errors"] += 1
                logger.error("populate.error", job_id=job["id"], error=str(e))

    logger.info("populate.complete", **stats)
    return stats
