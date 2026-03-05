"""OpenAI fallback embedding (SPEC.md §4.3).

Activated only if Gemini returns >10% error rate over a 1-hour window.
Lazy-initializes the OpenAI client.
"""

import os

import numpy as np
import structlog

logger = structlog.get_logger()

OPENAI_MODEL = "text-embedding-3-small"
OPENAI_DIMS = 768
OPENAI_BATCH_SIZE = 100

_openai_client: object | None = None


def _get_openai_client() -> object:
    """Lazy-initialize OpenAI client."""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI

            _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        except ImportError:
            raise RuntimeError("openai package not installed for fallback")
    return _openai_client


async def embed_batch_openai(texts: list[str]) -> list[list[float]]:
    """Embed texts via OpenAI text-embedding-3-small (768 dims)."""
    client = _get_openai_client()
    try:
        response = client.embeddings.create(  # type: ignore[union-attr]
            model=OPENAI_MODEL,
            input=texts,
            dimensions=OPENAI_DIMS,
        )
        vectors: list[list[float]] = []
        for item in response.data:  # type: ignore[union-attr]
            vec = np.array(item.embedding, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec.tolist())
        return vectors
    except Exception as e:
        logger.error("openai_embed_error", error=str(e))
        raise
