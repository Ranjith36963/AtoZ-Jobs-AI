"""Tests for queue runner (SPEC.md §3.2, Gate P20–P21)."""

import pytest

from src.models.errors import DuplicateError
from src.processing.queue_runner import (
    handle_failure,
    process_dedup,
    process_normalize,
    process_parse,
    process_summary,
    run_pipeline_sync,
)


def _make_job_data(**overrides: object) -> dict[str, object]:
    """Create minimal valid job data for testing."""
    base: dict[str, object] = {
        "title": "Senior Python Developer",
        "description": "Build amazing software with Python and AWS",
        "description_plain": "Build amazing software with Python and AWS",
        "company_name": "Acme Corp",
        "external_id": "12345",
        "source_name": "reed",
        "source_url": "https://example.com/job/12345",
        "location_raw": "London",
        "salary_min": 50000,
        "salary_max": 70000,
        "salary_raw": None,
        "salary_period": None,
        "category_raw": "IT & Telecoms",
        "employment_type": ["full_time"],
        "content_hash": "abc123def456",
        "status": "raw",
    }
    base.update(overrides)
    return base


class TestProcessParse:
    """Parse stage: validate required fields."""

    def test_valid_job_parsed(self) -> None:
        data = _make_job_data()
        result = process_parse(data)
        assert result["status"] == "parsed"

    def test_missing_title_fails(self) -> None:
        data = _make_job_data(title="")
        with pytest.raises(ValueError, match="title"):
            process_parse(data)

    def test_missing_external_id_fails(self) -> None:
        data = _make_job_data(external_id="")
        with pytest.raises(ValueError, match="external_id"):
            process_parse(data)


class TestProcessNormalize:
    """Normalize stage: salary, category, seniority, skills."""

    def test_salary_normalized(self) -> None:
        data = _make_job_data(status="parsed")
        result = process_normalize(data)
        assert result["salary_annual_min"] == 50_000
        assert result["salary_annual_max"] == 70_000

    def test_category_mapped(self) -> None:
        data = _make_job_data(
            status="parsed", source_name="reed", category_raw="IT & Telecoms"
        )
        result = process_normalize(data)
        assert result["category"] == "Technology"

    def test_seniority_extracted(self) -> None:
        data = _make_job_data(status="parsed", title="Senior Python Developer")
        result = process_normalize(data)
        assert result["seniority_level"] == "Senior"

    def test_skills_extracted(self) -> None:
        data = _make_job_data(
            status="parsed",
            description_plain="Python developer with AWS and Docker experience",
        )
        result = process_normalize(data)
        skills = result["extracted_skills"]
        assert isinstance(skills, list)
        skill_names = [s[0] for s in skills]
        assert "Python" in skill_names
        assert "AWS" in skill_names

    def test_status_set_to_normalized(self) -> None:
        data = _make_job_data(status="parsed")
        result = process_normalize(data)
        assert result["status"] == "normalized"


class TestProcessDedup:
    """Dedup gate: check content hash."""

    def test_unique_passes(self) -> None:
        data = _make_job_data(content_hash="unique_hash")
        result = process_dedup(data, {"other_hash"})
        assert result["content_hash"] == "unique_hash"

    def test_duplicate_raises(self) -> None:
        data = _make_job_data(content_hash="existing_hash")
        with pytest.raises(DuplicateError):
            process_dedup(data, {"existing_hash"})


class TestProcessSummary:
    """Summary builder integration."""

    def test_summary_generated(self) -> None:
        data = _make_job_data(
            seniority_level="Senior",
            category="Technology",
            extracted_skills=[("Python", 1.0), ("AWS", 1.0)],
            employment_type=["full_time"],
            location_type="onsite",
            location_city="London",
            location_region="Greater London",
        )
        result = process_summary(data)
        summary = str(result["structured_summary"])
        assert "Title: Senior Python Developer" in summary
        assert "Seniority: Senior" in summary
        assert "Skills: Python, AWS" in summary


class TestHandleFailure:
    """Failure handling and DLQ routing (Gate P21)."""

    def test_retry_incremented(self) -> None:
        data = _make_job_data(retry_count=0)
        result = handle_failure(data, ValueError("test"), "parse")
        assert result["retry_count"] == 1
        assert result["last_error"] == "test"
        assert result["failed_stage"] == "parse"

    def test_dlq_after_max_retries(self) -> None:
        data = _make_job_data(retry_count=2)
        result = handle_failure(data, ValueError("final"), "geocode")
        assert result["retry_count"] == 3  # equals MAX_RETRIES
        assert result["failed_stage"] == "geocode"

    def test_accumulative_retries(self) -> None:
        data = _make_job_data(retry_count=1)
        result = handle_failure(data, ValueError("err"), "embed")
        assert result["retry_count"] == 2


class TestFullPipeline:
    """Full pipeline: raw → parsed → normalized → dedup → summary (Gate P20)."""

    def test_full_pipeline_success(self) -> None:
        data = _make_job_data()
        result = run_pipeline_sync(data, existing_hashes=set())
        assert result["status"] == "normalized"
        assert "structured_summary" in result
        assert result.get("salary_annual_min") is not None
        assert result.get("category") is not None

    def test_pipeline_duplicate_skipped(self) -> None:
        data = _make_job_data(content_hash="known_hash")
        result = run_pipeline_sync(data, existing_hashes={"known_hash"})
        assert result["status"] == "duplicate"

    def test_pipeline_invalid_job(self) -> None:
        data = _make_job_data(title="")
        result = run_pipeline_sync(data)
        assert result.get("failed_stage") == "parse"
        assert result.get("retry_count", 0) >= 1
