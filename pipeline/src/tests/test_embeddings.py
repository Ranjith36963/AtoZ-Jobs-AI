"""Tests for embedding pipeline (SPEC.md §4.2–4.3, Gates P16–P17).

Mocks Gemini API to avoid real API calls in tests.
"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.embeddings import embed, fallback


class _FakeEmbedding:
    """Mock embedding result."""

    def __init__(self, dims: int = 768) -> None:
        vec = np.random.randn(dims).astype(np.float32)
        self.values = vec.tolist()


class _FakeEmbedResult:
    """Mock embed_content response."""

    def __init__(self, count: int = 1, dims: int = 768) -> None:
        self.embeddings = [_FakeEmbedding(dims) for _ in range(count)]


class TestGeminiEmbedding:
    """Gemini embedding pipeline (Gate P16)."""

    @pytest.mark.asyncio
    async def test_embed_batch_returns_768_dims(self) -> None:
        """Returns 768-dimensional vector."""
        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = _FakeEmbedResult(count=1)

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                vectors = await embed.embed_batch(["Test text"])

        assert len(vectors) == 1
        assert len(vectors[0]) == 768

    @pytest.mark.asyncio
    async def test_embed_batch_normalized(self) -> None:
        """Re-normalization: np.linalg.norm(vec) ≈ 1.0."""
        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = _FakeEmbedResult(count=1)

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                vectors = await embed.embed_batch(["Test text"])

        norm = np.linalg.norm(vectors[0])
        assert math.isclose(norm, 1.0, abs_tol=1e-5)

    @pytest.mark.asyncio
    async def test_embed_batch_multiple(self) -> None:
        """Batch of 3 texts → 3 vectors."""
        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = _FakeEmbedResult(count=3)

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                vectors = await embed.embed_batch(["Text 1", "Text 2", "Text 3"])

        assert len(vectors) == 3
        for v in vectors:
            assert len(v) == 768

    @pytest.mark.asyncio
    async def test_embed_all_batching(self) -> None:
        """embed_all splits into batches of 100."""
        texts = [f"Text {i}" for i in range(150)]
        mock_client = MagicMock()

        # First call: 100 items, second call: 50 items
        mock_client.models.embed_content.side_effect = [
            _FakeEmbedResult(count=100),
            _FakeEmbedResult(count=50),
        ]

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    vectors = await embed.embed_all(texts)

        assert len(vectors) == 150
        assert mock_client.models.embed_content.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_batch_retry_on_rate_limit(self) -> None:
        """429/RESOURCE_EXHAUSTED → retry with backoff."""
        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = [
            Exception("429 RESOURCE_EXHAUSTED"),
            _FakeEmbedResult(count=1),
        ]

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    vectors = await embed.embed_batch(["Test"])

        assert len(vectors) == 1
        assert mock_client.models.embed_content.call_count == 2


class TestOpenAIFallback:
    """OpenAI fallback (Gate P17)."""

    @pytest.mark.asyncio
    async def test_fallback_returns_768_dims(self) -> None:
        """OpenAI text-embedding-3-small returns 768 dimensions."""
        mock_embedding = MagicMock()
        mock_embedding.embedding = np.random.randn(768).tolist()

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = mock_response

        with patch.object(fallback, "_openai_client", mock_openai):
            vectors = await fallback.embed_batch_openai(["Test text"])

        assert len(vectors) == 1
        assert len(vectors[0]) == 768

    @pytest.mark.asyncio
    async def test_fallback_normalized(self) -> None:
        """OpenAI vectors are re-normalized."""
        mock_embedding = MagicMock()
        mock_embedding.embedding = np.random.randn(768).tolist()

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = mock_response

        with patch.object(fallback, "_openai_client", mock_openai):
            vectors = await fallback.embed_batch_openai(["Test text"])

        norm = np.linalg.norm(vectors[0])
        assert math.isclose(norm, 1.0, abs_tol=1e-5)


class TestEmbeddingEdgeCases:
    """Sad paths."""

    @pytest.mark.asyncio
    async def test_embed_batch_max_retries_exceeded(self) -> None:
        """All retries exhausted → RuntimeError."""
        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = Exception("Server error")

        with patch.object(embed, "_client", mock_client):
            with patch.object(embed, "_get_client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(Exception):
                        await embed.embed_batch(["Test"])
