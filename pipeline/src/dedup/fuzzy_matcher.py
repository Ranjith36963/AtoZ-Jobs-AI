"""Fuzzy duplicate matching with pg_trgm and composite scoring (SPEC.md §4.2-4.3).

Implements Stage 2 of the 3-stage dedup architecture:
- pg_trgm fuzzy matching on title/company
- Composite duplicate scoring (5 weighted signals)
- Canonical selection (keep richest version)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()

# Decision threshold: score >= 0.65 -> mark as duplicate
DUPLICATE_THRESHOLD = 0.65

# pg_trgm similarity thresholds
TITLE_SIMILARITY_THRESHOLD = 0.6
COMPANY_SIMILARITY_THRESHOLD = 0.5


def compute_local_duplicate_score(
    title_sim: float,
    company_match: bool,
    location_km: float,
    salary_overlap: float,
    date_diff_days: int,
) -> float:
    """Compute composite duplicate score (mirrors SQL function).

    Weights: title(0.35) + company(0.25) + location(0.15) + salary(0.15) + date(0.10) = 1.0

    Args:
        title_sim: pg_trgm similarity on title (0-1).
        company_match: Whether company names match (fuzzy or exact).
        location_km: Distance between locations in km.
        salary_overlap: Salary overlap ratio (0-1).
        date_diff_days: Days between posting dates.

    Returns:
        Composite score between 0 and 1.
    """
    score = title_sim * 0.35

    if company_match:
        score += 0.25

    if location_km <= 5:
        score += 0.15
    elif location_km <= 25:
        score += 0.08

    score += salary_overlap * 0.15

    if date_diff_days <= 7:
        score += 0.10
    elif date_diff_days <= 14:
        score += 0.05

    return score


def pick_canonical(job_a: dict[str, Any], job_b: dict[str, Any]) -> tuple[int, int]:
    """Select canonical (keep) and duplicate (discard) from a pair.

    Returns (canonical_id, duplicate_id). Keeps the richer version.

    Args:
        job_a: First job dict with id, salary_annual_max, location_city,
               description_plain, embedding fields.
        job_b: Second job dict.

    Returns:
        Tuple of (canonical_id, duplicate_id).
    """

    def richness(j: dict[str, Any]) -> int:
        score = 0
        score += 1 if j.get("salary_annual_max") else 0
        score += 1 if j.get("location_city") else 0
        score += len(j.get("description_plain", "") or "") // 100
        score += 1 if j.get("embedding") is not None else 0
        return score

    if richness(job_a) >= richness(job_b):
        return job_a["id"], job_b["id"]
    return job_b["id"], job_a["id"]


async def find_fuzzy_candidates(
    job_id: int,
    db_client: Client,
) -> list[dict[str, Any]]:
    """Find fuzzy duplicate candidates for a job using pg_trgm.

    Args:
        job_id: ID of the job to find candidates for.
        db_client: Supabase client.

    Returns:
        List of candidate dicts with id, title_sim, company_sim, dup_score.
    """
    # Query for fuzzy candidates using the SQL function
    # Threshold is enforced in the SQL function via explicit >= 0.6 check
    result = db_client.rpc(
        "find_fuzzy_duplicates",
        {
            "target_job_id": job_id,
        },
    ).execute()

    candidates = []
    for row in result.data or []:
        if row.get("dup_score", 0) >= DUPLICATE_THRESHOLD:
            candidates.append(row)

    return candidates


async def mark_duplicate(
    duplicate_id: int,
    canonical_id: int,
    score: float,
    db_client: Client,
) -> None:
    """Mark a job as a duplicate of another.

    Args:
        duplicate_id: ID of the job to mark as duplicate.
        canonical_id: ID of the canonical (kept) version.
        score: Composite duplicate score.
        db_client: Supabase client.
    """
    db_client.table("jobs").update(
        {
            "is_duplicate": True,
            "canonical_id": canonical_id,
            "duplicate_score": score,
        }
    ).eq("id", duplicate_id).execute()

    logger.info(
        "dedup.marked",
        duplicate_id=duplicate_id,
        canonical_id=canonical_id,
        score=round(score, 3),
    )
