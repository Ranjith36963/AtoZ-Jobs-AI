"""Tests for cross-encoder re-ranker (SPEC.md §6.2, Gates R8-R10)."""
from typing import Any

from unittest.mock import MagicMock, patch

import numpy as np


class TestGetReranker:
    """Model loading tests."""

    def test_model_loads(self) -> None:
        """Gate R8: Model loads successfully."""
        with patch("src.search.reranker._model", None):
            with patch("sentence_transformers.CrossEncoder") as mock_ce:
                mock_model = MagicMock()
                mock_ce.return_value = mock_model

                from src.search.reranker import get_reranker

                # Reset global state
                import src.search.reranker as mod
                mod._model = None

                result = get_reranker()
                mock_ce.assert_called_once_with(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512
                )
                assert result is mock_model

    def test_singleton(self) -> None:
        """Model is loaded only once (singleton pattern)."""
        import src.search.reranker as mod

        mock_model = MagicMock()
        mod._model = mock_model

        result = mod.get_reranker()
        assert result is mock_model

        # Cleanup
        mod._model = None


class TestRerank:
    """Re-ranking tests with mocked model."""

    def _make_rerank(self) -> tuple[Any, MagicMock]:
        """Import rerank with mocked model."""
        import src.search.reranker as mod
        mock_model = MagicMock()
        mod._model = mock_model
        return mod.rerank, mock_model

    def test_relevance_ordering(self) -> None:
        """Gate R9: Relevant job scores higher than irrelevant."""
        rerank, mock_model = self._make_rerank()

        # Python dev should score higher than Chef for "Python developer" query
        mock_model.predict.return_value = np.array([0.95, 0.1, 0.6])

        jobs = [
            {"title": "Senior Python Developer", "company_name": "TechCo", "description_plain": "Python Django AWS"},
            {"title": "Head Chef", "company_name": "Restaurant", "description_plain": "Cooking kitchen"},
            {"title": "Junior Software Engineer", "company_name": "StartUp", "description_plain": "Python Flask"},
        ]

        result = rerank("Python developer", jobs)

        assert result[0]["title"] == "Senior Python Developer"
        assert result[-1]["title"] == "Head Chef"
        assert result[0]["rerank_score"] > result[-1]["rerank_score"]

        import src.search.reranker as mod
        mod._model = None

    def test_top_k(self) -> None:
        """Returns exactly top_k results."""
        rerank, mock_model = self._make_rerank()

        mock_model.predict.return_value = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])

        jobs = [{"title": f"Job {i}", "company_name": f"Co {i}", "description_plain": f"Desc {i}"} for i in range(10)]

        result = rerank("test query", jobs, top_k=5)
        assert len(result) == 5

        import src.search.reranker as mod
        mod._model = None

    def test_empty_jobs(self) -> None:
        """Empty job list → empty result."""
        rerank, mock_model = self._make_rerank()

        result = rerank("test", [])
        assert result == []

        import src.search.reranker as mod
        mod._model = None

    def test_empty_query(self) -> None:
        """Empty query → empty result."""
        rerank, mock_model = self._make_rerank()

        jobs = [{"title": "Job", "company_name": "Co", "description_plain": "Desc"}]
        result = rerank("", jobs)
        assert result == []

        import src.search.reranker as mod
        mod._model = None

    def test_rerank_score_added(self) -> None:
        """Each job dict has 'rerank_score' after re-ranking."""
        rerank, mock_model = self._make_rerank()

        mock_model.predict.return_value = np.array([0.75, 0.25])

        jobs = [
            {"title": "Job A", "company_name": "Co A", "description_plain": "Desc A"},
            {"title": "Job B", "company_name": "Co B", "description_plain": "Desc B"},
        ]

        result = rerank("test", jobs)
        assert all("rerank_score" in j for j in result)
        assert isinstance(result[0]["rerank_score"], float)

        import src.search.reranker as mod
        mod._model = None

    def test_batch_call_structure(self) -> None:
        """Model receives all pairs in a single batch call."""
        rerank, mock_model = self._make_rerank()

        mock_model.predict.return_value = np.array([0.5, 0.5, 0.5])

        jobs = [
            {"title": f"Job {i}", "company_name": f"Co {i}", "description_plain": f"Desc {i}"}
            for i in range(3)
        ]

        rerank("query", jobs)

        mock_model.predict.assert_called_once()
        pairs = mock_model.predict.call_args[0][0]
        assert len(pairs) == 3
        assert all(isinstance(p, tuple) and len(p) == 2 for p in pairs)

        import src.search.reranker as mod
        mod._model = None

    def test_missing_description(self) -> None:
        """Jobs with None description don't crash."""
        rerank, mock_model = self._make_rerank()

        mock_model.predict.return_value = np.array([0.5])

        jobs = [{"title": "Job", "company_name": "Co", "description_plain": None}]

        result = rerank("test", jobs)
        assert len(result) == 1

        import src.search.reranker as mod
        mod._model = None

    def test_fewer_jobs_than_top_k(self) -> None:
        """Fewer jobs than top_k → returns all jobs."""
        rerank, mock_model = self._make_rerank()

        mock_model.predict.return_value = np.array([0.8, 0.3])

        jobs = [
            {"title": "Job A", "company_name": "Co A", "description_plain": "A"},
            {"title": "Job B", "company_name": "Co B", "description_plain": "B"},
        ]

        result = rerank("test", jobs, top_k=20)
        assert len(result) == 2

        import src.search.reranker as mod
        mod._model = None
