"""Gemini embedding pipeline (SPEC.md §4.2).

Uses gemini-embedding-001 with 768 dimensions.
Re-normalizes after MRL dimension truncation.
"""

import asyncio

import numpy as np
import structlog
from google import genai
from google.genai import types

logger = structlog.get_logger()

GEMINI_MODEL = "gemini-embedding-001"
GEMINI_BATCH_SIZE = 100
GEMINI_DIMS = 768
MAX_RETRIES = 5

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazy-initialize Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed up to GEMINI_BATCH_SIZE texts. Returns normalized 768-dim vectors."""
    client = _get_client()
    for attempt in range(MAX_RETRIES):
        try:
            result = await asyncio.to_thread(
                client.models.embed_content,
                model=GEMINI_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=GEMINI_DIMS),
            )
            vectors: list[list[float]] = []
            for emb in result.embeddings or []:
                vec = np.array(emb.values, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm  # Re-normalize after MRL truncation
                vectors.append(vec.tolist())
            return vectors
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = min(2**attempt * 2, 60)
                logger.warning("gemini_rate_limited", attempt=attempt, wait=wait)
                await asyncio.sleep(wait)
                continue
            logger.error("gemini_embed_error", error=error_str, attempt=attempt)
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2**attempt)
    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries")


async def embed_all(texts: list[str]) -> list[list[float]]:
    """Embed any number of texts in batches with rate limiting."""
    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), GEMINI_BATCH_SIZE):
        batch = texts[i : i + GEMINI_BATCH_SIZE]
        vectors = await embed_batch(batch)
        all_vectors.extend(vectors)
        if i + GEMINI_BATCH_SIZE < len(texts):
            await asyncio.sleep(0.5)  # Rate limit on free tier
    return all_vectors
