"""Search orchestrator combining RRF + cross-encoder re-ranking (SPEC.md §6).

Main search endpoint: embed query → search_jobs_v2 → cross-encoder rerank.
Gracefully degrades if reranker unavailable.
"""

import time
from typing import Any

import structlog

from src.search.reranker import rerank

logger = structlog.get_logger()


async def search(
    query: str,
    db_client: Any,
    embed_fn: Any = None,
    user_id: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute full search pipeline: embed → RRF → rerank.

    Args:
        query: User search text.
        db_client: Supabase client.
        embed_fn: Async function to embed text → list[float].
        user_id: Optional UUID for personalization.
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
    search_results = rpc_result.data or []
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

    latency_ms = (time.time() - start_time) * 1000

    logger.info(
        "search.complete",
        query=query,
        total_rrf=total,
        returned=len(search_results),
        latency_ms=round(latency_ms, 1),
        has_reranking="rerank_score" in (search_results[0] if search_results else {}),
    )

    return {
        "results": search_results,
        "total": total,
        "latency_ms": round(latency_ms, 1),
    }
