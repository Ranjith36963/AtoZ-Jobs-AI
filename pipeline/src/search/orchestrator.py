"""Search orchestrator combining RRF + cross-encoder re-ranking (SPEC.md §6).

Main search endpoint: embed query -> search_jobs_v2 -> cross-encoder rerank.
Gracefully degrades if reranker unavailable.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import structlog

from src.profiles.handler import get_profile_embedding
from src.search.reranker import rerank

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()

EmbedFn = Callable[[str], Awaitable[list[float]]]


async def search(
    query: str,
    db_client: Client,
    embed_fn: EmbedFn | None = None,
    user_id: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute full search pipeline: embed -> RRF -> rerank -> personalize.

    Args:
        query: User search text.
        db_client: Supabase client.
        embed_fn: Async function to embed text -> list[float].
        user_id: Optional UUID for personalization via profile embedding.
        filters: Search filter parameters.

    Returns:
        Dict with results, total count, and latency_ms.
    """
    start_time = time.time()
    filters = filters or {}

    # 1. Embed query
    query_embedding = None
    if query and embed_fn:
        try:
            query_embedding = await embed_fn(query)
        except Exception:
            logger.exception("search.embed_failed")

    # 1b. Fetch user profile embedding for personalization boost
    profile_embedding: list[float] | None = None
    if user_id:
        try:
            profile_embedding = await get_profile_embedding(user_id, db_client)
        except Exception:
            logger.warning("search.profile_fetch_failed", user_id=user_id)

    # 2. Call search_jobs_v2 via RPC
    rpc_params: dict[str, Any] = {
        "query_text": query or None,
        "query_embedding": query_embedding,
        "search_lat": filters.get("search_lat"),
        "search_lng": filters.get("search_lng"),
        "radius_miles": filters.get("radius_miles", 25),
        "include_remote": filters.get("include_remote", True),
        "min_salary": filters.get("min_salary"),
        "max_salary": filters.get("max_salary"),
        "work_type_filter": filters.get("work_type_filter"),
        "category_filter": filters.get("category_filter"),
        "skill_filters": filters.get("skill_filters"),
        "exclude_duplicates": filters.get("exclude_duplicates", True),
        "match_count": 50,
    }

    rpc_result = db_client.rpc("search_jobs_v2", rpc_params).execute()
    search_results: list[dict[str, Any]] = list(rpc_result.data or [])  # type: ignore[arg-type]
    total = len(search_results)

    # 3. Cross-encoder rerank (graceful degradation)
    if query and search_results:
        try:
            reranked = rerank(query, search_results, top_k=20)
            search_results = reranked
        except Exception:
            logger.warning("search.rerank_failed_graceful_degradation")
            # Return RRF results without re-ranking
            search_results = search_results[:20]
    else:
        search_results = search_results[:20]

    # 4. Profile-based personalization boost (optional)
    has_personalization = False
    if profile_embedding and search_results:
        try:
            search_results = _apply_profile_boost(search_results, profile_embedding)
            has_personalization = True
        except Exception:
            logger.warning("search.personalization_failed")

    latency_ms = (time.time() - start_time) * 1000

    logger.info(
        "search.complete",
        query=query,
        total_rrf=total,
        returned=len(search_results),
        latency_ms=round(latency_ms, 1),
        has_reranking="rerank_score" in (search_results[0] if search_results else {}),
        has_personalization=has_personalization,
    )

    return {
        "results": search_results,
        "total": total,
        "latency_ms": round(latency_ms, 1),
    }


def _apply_profile_boost(
    results: list[dict[str, Any]],
    profile_embedding: list[float],
) -> list[dict[str, Any]]:
    """Boost search results that align with user profile embedding.

    Uses cosine similarity between profile and job embeddings to add a
    small personalization bonus to the final score.

    Args:
        results: Search results with optional 'embedding' field.
        profile_embedding: User profile embedding (768-dim).

    Returns:
        Re-sorted results with profile_boost score added.
    """
    import numpy as np

    prof = np.array(profile_embedding, dtype=np.float32)
    prof_norm = np.linalg.norm(prof)
    if prof_norm == 0:
        return results

    prof = prof / prof_norm

    for result in results:
        job_emb = result.get("embedding")
        if job_emb and isinstance(job_emb, list):
            job_vec = np.array(job_emb, dtype=np.float32)
            job_norm = np.linalg.norm(job_vec)
            if job_norm > 0:
                similarity = float(np.dot(prof, job_vec / job_norm))
                # Small boost: 10% weight for personalization
                result["profile_boost"] = max(0.0, similarity) * 0.1
            else:
                result["profile_boost"] = 0.0
        else:
            result["profile_boost"] = 0.0

    # Re-sort: use existing score (rerank_score or rrf_score) + profile_boost
    def sort_key(r: dict[str, Any]) -> float:
        base = float(r.get("rerank_score", r.get("rrf_score", 0.0)))
        return base + float(r.get("profile_boost", 0.0))

    results.sort(key=sort_key, reverse=True)
    return results
