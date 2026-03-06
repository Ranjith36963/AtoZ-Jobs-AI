"""Tests for expiry detection (GATES.md M1-M6, SPEC.md §6).

TDD: Write tests first, confirm they fail, then implement.
"""

from datetime import datetime, timedelta, timezone


from src.maintenance.expiry import (
    ADZUNA_EXPIRY_DAYS,
    JOOBLE_CAREERJET_EXPIRY_DAYS,
    archive_expired,
    check_expiry,
    hard_delete_candidates,
    mark_disappeared,
)

NOW = datetime.now(tz=timezone.utc)


def _make_job(
    source_name: str = "reed",
    status: str = "ready",
    date_posted: datetime | None = None,
    date_expires: datetime | None = None,
    date_crawled: datetime | None = None,
    external_id: str = "job-1",
    job_id: int = 1,
) -> dict[str, object]:
    return {
        "id": job_id,
        "external_id": external_id,
        "source_name": source_name,
        "status": status,
        "date_posted": (date_posted or NOW - timedelta(days=5)).isoformat(),
        "date_expires": date_expires.isoformat() if date_expires else None,
        "date_crawled": (date_crawled or NOW).isoformat(),
        "title": "Test Job",
        "company_name": "Test Co",
    }


# ── M1: Reed job with past expirationDate → expired ──


class TestReedExpiry:
    def test_reed_expired_by_expiration_date(self) -> None:
        """Reed job with past expirationDate should be marked expired."""
        job = _make_job(
            source_name="reed",
            date_expires=NOW - timedelta(days=1),
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_reed_not_expired_future_date(self) -> None:
        """Reed job with future expirationDate should remain ready."""
        job = _make_job(
            source_name="reed",
            date_expires=NOW + timedelta(days=10),
        )
        result = check_expiry(job)
        assert result["status"] == "ready"

    def test_reed_no_expiry_defaults_30_days(self) -> None:
        """Reed job without expirationDate uses 30-day default."""
        job = _make_job(
            source_name="reed",
            date_posted=NOW - timedelta(days=31),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_reed_no_expiry_within_30_days(self) -> None:
        """Reed job without expirationDate within 30 days stays ready."""
        job = _make_job(
            source_name="reed",
            date_posted=NOW - timedelta(days=15),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "ready"


# ── M2: Adzuna job 46 days old → expired (45-day default) ──


class TestAdzunaExpiry:
    def test_adzuna_45_day_default_expired(self) -> None:
        """Adzuna job 46 days old (no date_expires) should expire at 45-day default."""
        job = _make_job(
            source_name="adzuna",
            date_posted=NOW - timedelta(days=46),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_adzuna_within_45_days_stays_ready(self) -> None:
        """Adzuna job 44 days old should remain ready."""
        job = _make_job(
            source_name="adzuna",
            date_posted=NOW - timedelta(days=44),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "ready"

    def test_adzuna_boundary_just_under_45_days(self) -> None:
        """Adzuna job at 44 days 23 hours should still be ready."""
        job = _make_job(
            source_name="adzuna",
            date_posted=NOW - timedelta(days=44, hours=23),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "ready"

    def test_adzuna_default_days_constant(self) -> None:
        assert ADZUNA_EXPIRY_DAYS == 45


# ── M3: Jooble/Careerjet job 31 days old → expired (30-day default) ──


class TestJoobleCareerjetExpiry:
    def test_jooble_30_day_default_expired(self) -> None:
        """Jooble job 31 days old → expired."""
        job = _make_job(
            source_name="jooble",
            date_posted=NOW - timedelta(days=31),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_careerjet_30_day_default_expired(self) -> None:
        """Careerjet job 31 days old → expired."""
        job = _make_job(
            source_name="careerjet",
            date_posted=NOW - timedelta(days=31),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_jooble_within_30_days_stays_ready(self) -> None:
        """Jooble job 29 days old should remain ready."""
        job = _make_job(
            source_name="jooble",
            date_posted=NOW - timedelta(days=29),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "ready"

    def test_jooble_default_days_constant(self) -> None:
        assert JOOBLE_CAREERJET_EXPIRY_DAYS == 30


# ── M4: Re-verification — job missing 2 consecutive fetch cycles → expired ──


class TestReVerification:
    def test_mark_disappeared_first_miss(self) -> None:
        """First miss: job enters missing set but not expired yet."""
        current_ids = {"job-2", "job-3"}
        previous_ids = {"job-1", "job-2", "job-3"}
        twice_missing: set[str] = set()

        result = mark_disappeared(current_ids, previous_ids, twice_missing)
        # job-1 is missing once — should be in result for tracking
        assert "job-1" in result
        # Not yet twice-missing
        assert "job-1" not in twice_missing

    def test_mark_disappeared_second_miss(self) -> None:
        """Second consecutive miss: job should be flagged for expiry."""
        current_ids = {"job-2", "job-3"}
        previous_ids = {"job-1", "job-2", "job-3"}
        # job-1 was already missing once
        twice_missing = {"job-1"}

        result = mark_disappeared(current_ids, previous_ids, twice_missing)
        assert "job-1" in result

    def test_mark_disappeared_reappears(self) -> None:
        """Job reappears after first miss: no longer missing."""
        current_ids = {"job-1", "job-2", "job-3"}
        previous_ids = {"job-1", "job-2", "job-3"}
        twice_missing: set[str] = set()

        result = mark_disappeared(current_ids, previous_ids, twice_missing)
        assert len(result) == 0


# ── M5: Expired job >90 days old → archived ──


class TestArchiveExpired:
    def test_expired_over_90_days_archived(self) -> None:
        """Expired job with date_crawled > 90 days ago → archived."""
        job = _make_job(
            status="expired",
            date_crawled=NOW - timedelta(days=91),
        )
        result = archive_expired([job])
        assert len(result) == 1
        assert result[0]["status"] == "archived"

    def test_expired_within_90_days_stays_expired(self) -> None:
        """Expired job with date_crawled < 90 days ago stays expired."""
        job = _make_job(
            status="expired",
            date_crawled=NOW - timedelta(days=80),
        )
        result = archive_expired([job])
        assert len(result) == 0

    def test_ready_job_not_archived(self) -> None:
        """Ready job should not be archived regardless of age."""
        job = _make_job(
            status="ready",
            date_crawled=NOW - timedelta(days=100),
        )
        result = archive_expired([job])
        assert len(result) == 0


# ── M6: Archived job >180 days old → hard deleted ──


class TestHardDelete:
    def test_archived_over_180_days_returns_id(self) -> None:
        """Archived job >180 days old should return its ID for deletion."""
        job = _make_job(
            status="archived",
            date_crawled=NOW - timedelta(days=181),
            job_id=42,
        )
        result = hard_delete_candidates([job])
        assert 42 in result

    def test_archived_within_180_days_not_deleted(self) -> None:
        """Archived job <180 days old should not be deleted."""
        job = _make_job(
            status="archived",
            date_crawled=NOW - timedelta(days=170),
            job_id=42,
        )
        result = hard_delete_candidates([job])
        assert 42 not in result

    def test_expired_not_deleted(self) -> None:
        """Expired (not archived) job should not be deleted even if old."""
        job = _make_job(
            status="expired",
            date_crawled=NOW - timedelta(days=200),
            job_id=42,
        )
        result = hard_delete_candidates([job])
        assert 42 not in result


# ── Sad paths ──


class TestExpiryEdgeCases:
    def test_null_date_posted(self) -> None:
        """Job with null date_posted should not crash."""
        job = _make_job(source_name="adzuna")
        job["date_posted"] = None
        result = check_expiry(job)
        # Should handle gracefully — don't expire without date info
        assert result["status"] == "ready"

    def test_already_expired_job(self) -> None:
        """Already expired job should remain expired."""
        job = _make_job(status="expired")
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_unknown_source_uses_default(self) -> None:
        """Unknown source should use conservative default (30 days)."""
        job = _make_job(
            source_name="unknown_source",
            date_posted=NOW - timedelta(days=31),
            date_expires=None,
        )
        result = check_expiry(job)
        assert result["status"] == "expired"

    def test_empty_jobs_list_archive(self) -> None:
        """Empty list to archive returns empty."""
        result = archive_expired([])
        assert result == []

    def test_empty_jobs_list_hard_delete(self) -> None:
        """Empty list to hard_delete returns empty."""
        result = hard_delete_candidates([])
        assert result == []
