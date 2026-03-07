"""Cross-encoder re-ranker using ms-marco-MiniLM (SPEC.md §6.2).

Re-ranks search results using a cross-encoder model that scores
query-document pairs for relevance. Lazy-loads the model on first use.
"""

from typing import Any

import structlog

logger = structlog.get_logger()

_model: Any = None


def get_reranker() -> Any:
    """Lazy-load cross-encoder model (singleton).

    Returns:
        CrossEncoder model instance.
    """
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512
        )
        logger.info("reranker.model_loaded", model="ms-marco-MiniLM-L-6-v2")
    return _model


def rerank(
    query: str,
    jobs: list[dict[str, Any]],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Re-rank jobs using cross-encoder relevance scoring.

    Args:
        query: User search query.
        jobs: List of job dicts from search_jobs_v2().
        top_k: Number of results to return.

    Returns:
        Top k jobs sorted by cross-encoder relevance, each with 'rerank_score'.
    """
    if not jobs or not query:
        return []

    model = get_reranker()

    pairs = [
        (
            query,
            f"{j.get('title', '')} at {j.get('company_name', '')}. "
            f"{(j.get('description_plain') or '')[:300]}",
        )
        for j in jobs
    ]

    scores = model.predict(pairs, show_progress_bar=False)

    for job, score in zip(jobs, scores):
        job["rerank_score"] = float(score)

    ranked = sorted(jobs, key=lambda j: j["rerank_score"], reverse=True)
    return ranked[:top_k]
