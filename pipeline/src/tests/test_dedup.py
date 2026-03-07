"""Tests for deduplication gate (SPEC.md §3.1, Gates P18–P19)."""

import pytest

from src.models.errors import DuplicateError
from src.processing.dedup import check_duplicate, compute_dedup_decision


class TestDedupGate:
    """Content hash deduplication (Gate P18)."""

    def test_unique_job_passes(self) -> None:
        """New hash → passes through (not duplicate)."""
        existing = {"abc123", "def456"}
        result = check_duplicate("xyz789", existing)
        assert result is False

    def test_duplicate_raises(self) -> None:
        """Existing hash → DuplicateError raised."""
        existing = {"abc123", "def456"}
        with pytest.raises(DuplicateError):
            check_duplicate("abc123", existing)

    def test_same_title_company_location(self) -> None:
        """Two jobs with identical title+company+location → same hash → duplicate."""
        # Simulate: hash is pre-computed, same inputs produce same hash
        hash_a = "same_hash_value"
        hash_b = "same_hash_value"
        existing = {hash_a}
        with pytest.raises(DuplicateError):
            check_duplicate(hash_b, existing)

    def test_different_inputs_different_hash(self) -> None:
        """Different title → different hash → unique."""
        hash_a = "hash_for_python_dev"
        hash_b = "hash_for_java_dev"
        existing = {hash_a}
        result = check_duplicate(hash_b, existing)
        assert result is False


class TestDedupDecision:
    """compute_dedup_decision without raising."""

    def test_unique_decision(self) -> None:
        assert compute_dedup_decision("new_hash", {"old_hash"}) == "unique"

    def test_duplicate_decision(self) -> None:
        assert compute_dedup_decision("old_hash", {"old_hash"}) == "duplicate"

    def test_empty_existing(self) -> None:
        assert compute_dedup_decision("any_hash", set()) == "unique"


class TestDedupEdgeCases:
    """Sad paths."""

    def test_empty_hash(self) -> None:
        existing: set[str] = set()
        result = check_duplicate("", existing)
        assert result is False

    def test_empty_existing_set(self) -> None:
        result = check_duplicate("abc", set())
        assert result is False
