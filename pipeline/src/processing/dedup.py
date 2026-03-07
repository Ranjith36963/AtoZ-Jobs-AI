"""Deduplication gate (SPEC.md §3.1).

Content hash check: if hash exists, skip (DuplicateError).
Dedup is a gate, not a transformation. Status stays 'normalized'
until geocoding completes.
"""

import structlog

from src.models.errors import DuplicateError

logger = structlog.get_logger()


def check_duplicate(
    content_hash: str,
    existing_hashes: set[str],
) -> bool:
    """Check if content_hash already exists.

    Args:
        content_hash: SHA-256 hash of normalized title|company|location.
        existing_hashes: Set of known hashes from DB.

    Returns:
        True if duplicate (should skip), False if unique.

    Raises:
        DuplicateError: If hash exists (for queue error handling).
    """
    if content_hash in existing_hashes:
        logger.debug("duplicate_detected", content_hash=content_hash[:16])
        raise DuplicateError(
            f"Duplicate job: content_hash={content_hash[:16]}...",
            source="dedup",
        )
    return False


def compute_dedup_decision(
    content_hash: str,
    existing_hashes: set[str],
) -> str:
    """Determine dedup outcome without raising.

    Returns:
        'unique' — pass through to geocode_queue
        'duplicate' — skip silently
        'update' — same external_id, different hash → reprocess
    """
    if content_hash in existing_hashes:
        return "duplicate"
    return "unique"
