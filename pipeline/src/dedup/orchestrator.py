"""Dedup orchestrator — combines all 3 dedup stages (SPEC.md §4.1).

Stage 1: SHA-256 content_hash (Phase 1, already built)
Stage 2: pg_trgm fuzzy matching
Stage 3: MinHash/LSH near-duplicate detection
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.dedup.fuzzy_matcher import (
    DUPLICATE_THRESHOLD,
    compute_local_duplicate_score,
    find_fuzzy_candidates,
    mark_duplicate,
    pick_canonical,
)
from src.dedup.minhash import build_lsh_index, compute_minhash, find_lsh_candidates

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()


async def run_advanced_dedup(
    db_client: Client,
    batch_size: int = 1000,
    use_minhash: bool = True,
) -> dict[str, int]:
    """Run advanced dedup pipeline on all ready, non-duplicate jobs.

    Combines pg_trgm fuzzy matching (Stage 2) and MinHash/LSH (Stage 3).
    Marks duplicates with composite score >= 0.65.

    Args:
        db_client: Supabase client.
        batch_size: Jobs per query batch.
        use_minhash: Whether to run MinHash/LSH stage (can be slow).

    Returns:
        Dict with stats: total_scanned, fuzzy_candidates, minhash_candidates,
        duplicates_marked, errors.
    """
    stats = {
        "total_scanned": 0,
        "fuzzy_candidates": 0,
        "minhash_candidates": 0,
        "duplicates_marked": 0,
        "errors": 0,
    }

    # Fetch all ready, non-duplicate jobs
    result = (
        db_client.table("jobs")
        .select(
            "id, title, company_name, description_plain, salary_annual_max, location_city, embedding, date_posted"
        )
        .eq("status", "ready")
        .eq("is_duplicate", False)
        .limit(batch_size)
        .execute()
    )
    jobs = result.data or []
    stats["total_scanned"] = len(jobs)

    if not jobs:
        logger.info("dedup.no_jobs")
        return stats

    # Stage 2: pg_trgm fuzzy matching
    for job in jobs:
        try:
            candidates = await find_fuzzy_candidates(job["id"], db_client)
            stats["fuzzy_candidates"] += len(candidates)

            for candidate in candidates:
                score = candidate.get("dup_score", 0)
                if score >= DUPLICATE_THRESHOLD:
                    canonical_id, duplicate_id = pick_canonical(job, candidate)
                    await mark_duplicate(duplicate_id, canonical_id, score, db_client)
                    stats["duplicates_marked"] += 1
        except Exception as e:
            stats["errors"] += 1
            logger.error("dedup.fuzzy_error", job_id=job["id"], error=str(e))

    # Stage 3: MinHash/LSH
    if use_minhash:
        try:
            lsh = build_lsh_index(jobs)

            for job in jobs:
                desc = str(job.get("description_plain", ""))
                if not desc.strip():
                    continue

                mh = compute_minhash(desc)
                lsh_candidates = find_lsh_candidates(lsh, str(job["id"]), mh)
                stats["minhash_candidates"] += len(lsh_candidates)

                # For each MinHash candidate, compute composite score
                for cand_id_str in lsh_candidates:
                    cand_job = next(
                        (j for j in jobs if str(j["id"]) == cand_id_str), None
                    )
                    if cand_job is None:
                        continue

                    # Compute local composite score with available data
                    title_sim = _simple_similarity(
                        str(job.get("title", "")),
                        str(cand_job.get("title", "")),
                    )
                    company_match = (
                        str(job.get("company_name", "")).lower()
                        == str(cand_job.get("company_name", "")).lower()
                    )

                    score = compute_local_duplicate_score(
                        title_sim=title_sim,
                        company_match=company_match,
                        location_km=0.0,  # Approximate; real geo done in SQL
                        salary_overlap=0.0,
                        date_diff_days=30,
                    )

                    if score >= DUPLICATE_THRESHOLD:
                        canonical_id, duplicate_id = pick_canonical(job, cand_job)
                        await mark_duplicate(
                            duplicate_id, canonical_id, score, db_client
                        )
                        stats["duplicates_marked"] += 1

        except Exception as e:
            stats["errors"] += 1
            logger.error("dedup.minhash_error", error=str(e))

    logger.info("dedup.complete", **stats)
    return stats


def _simple_similarity(a: str, b: str) -> float:
    """Simple character-level trigram similarity (approximates pg_trgm).

    Args:
        a: First string.
        b: Second string.

    Returns:
        Similarity score between 0 and 1.
    """
    if not a or not b:
        return 0.0

    a_lower = a.lower()
    b_lower = b.lower()

    if a_lower == b_lower:
        return 1.0

    a_trigrams = set()
    for i in range(len(a_lower) - 2):
        a_trigrams.add(a_lower[i : i + 3])

    b_trigrams = set()
    for i in range(len(b_lower) - 2):
        b_trigrams.add(b_lower[i : i + 3])

    if not a_trigrams or not b_trigrams:
        return 0.0

    intersection = a_trigrams & b_trigrams
    union = a_trigrams | b_trigrams
    return len(intersection) / len(union)
