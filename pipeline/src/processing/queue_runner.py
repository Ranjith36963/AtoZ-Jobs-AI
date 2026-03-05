"""Queue runner — wires all 6 processing queues (SPEC.md §3.2).

Each stage: read batch from pgmq → process → update job status → enqueue next.
On failure: increment retry_count, log last_error, if retry_count >= 3 → DLQ.
"""

import structlog

from src.models.errors import DuplicateError, PipelineError
from src.processing.category import map_category
from src.processing.dedup import compute_dedup_decision
from src.processing.salary import normalize_salary
from src.processing.seniority import extract_seniority
from src.processing.summary import build_summary
from src.skills.extractor import extract_skills

logger = structlog.get_logger()

MAX_RETRIES = 3


def process_parse(job_data: dict[str, object]) -> dict[str, object]:
    """Parse stage: extract description_plain, validate fields.

    Input status: raw → Output status: parsed
    """
    # In Phase 1, parsing is done at collection time by adapters.
    # This stage validates the data is properly formed.
    required = ["title", "description", "company_name", "external_id"]
    for field in required:
        if not job_data.get(field):
            raise ValueError(f"Missing required field: {field}")

    job_data["status"] = "parsed"
    return job_data


def process_normalize(job_data: dict[str, object]) -> dict[str, object]:
    """Normalize stage: salary, category, seniority.

    Input status: parsed → Output status: normalized
    """
    title = str(job_data.get("title", ""))
    source_name = str(job_data.get("source_name", ""))

    # Salary normalization
    annual_min, annual_max = normalize_salary(
        salary_min=float(job_data["salary_min"])
        if job_data.get("salary_min") is not None
        else None,
        salary_max=float(job_data["salary_max"])
        if job_data.get("salary_max") is not None
        else None,
        salary_raw=str(job_data.get("salary_raw", "")) or None,
        salary_period=str(job_data.get("salary_period", "")) or None,
    )
    job_data["salary_annual_min"] = annual_min
    job_data["salary_annual_max"] = annual_max

    # Category mapping
    job_data["category"] = map_category(
        source_name=source_name,
        category_raw=str(job_data.get("category_raw", "")) or None,
        title=title,
    )

    # Seniority extraction
    job_data["seniority_level"] = extract_seniority(title)

    # Skill extraction
    description_plain = str(job_data.get("description_plain", ""))
    skills = extract_skills(description_plain)
    job_data["extracted_skills"] = skills

    job_data["status"] = "normalized"
    return job_data


def process_dedup(
    job_data: dict[str, object],
    existing_hashes: set[str],
) -> dict[str, object]:
    """Dedup gate: check content_hash against existing jobs.

    Input status: normalized → Output: unchanged (gate only)
    Raises DuplicateError if duplicate.
    """
    content_hash = str(job_data.get("content_hash", ""))
    decision = compute_dedup_decision(content_hash, existing_hashes)

    if decision == "duplicate":
        raise DuplicateError(
            f"Duplicate: {content_hash[:16]}...",
            source="dedup",
        )

    return job_data


def process_summary(job_data: dict[str, object]) -> dict[str, object]:
    """Build structured summary for embedding.

    Called after geocoding, before embedding.
    """
    skills_raw = job_data.get("extracted_skills", [])
    skill_names: list[str] = []
    if isinstance(skills_raw, list):
        for s in skills_raw:
            if isinstance(s, tuple) and len(s) >= 1:
                skill_names.append(str(s[0]))
            elif isinstance(s, str):
                skill_names.append(s)

    employment_type = job_data.get("employment_type", [])
    if isinstance(employment_type, str):
        employment_type = [employment_type]

    summary = build_summary(
        title=str(job_data.get("title", "")),
        seniority_level=str(job_data.get("seniority_level", "Not specified")),
        company_name=str(job_data.get("company_name", "")),
        industry=str(job_data.get("category", "Unknown")),
        skills=skill_names,
        employment_type=list(employment_type) if employment_type else None,
        location_type=str(job_data.get("location_type", "onsite")),
        location_city=str(job_data.get("location_city", "")) or None,
        location_region=str(job_data.get("location_region", "")) or None,
    )
    job_data["structured_summary"] = summary
    return job_data


def handle_failure(
    job_data: dict[str, object],
    error: Exception,
    stage: str,
) -> dict[str, object]:
    """Handle processing failure: increment retry, route to DLQ if exhausted.

    Returns updated job_data with retry_count, last_error, and failed_stage.
    """
    retry_count = int(job_data.get("retry_count", 0)) + 1
    job_data["retry_count"] = retry_count
    job_data["last_error"] = str(error)
    job_data["failed_stage"] = stage

    if retry_count >= MAX_RETRIES:
        logger.error(
            "job_to_dlq",
            job_id=job_data.get("id"),
            stage=stage,
            retry_count=retry_count,
            error=str(error),
        )
    else:
        logger.warning(
            "job_retry",
            job_id=job_data.get("id"),
            stage=stage,
            retry_count=retry_count,
            error=str(error),
        )

    return job_data


def run_pipeline_sync(
    job_data: dict[str, object],
    existing_hashes: set[str] | None = None,
) -> dict[str, object]:
    """Run full processing pipeline synchronously (for testing).

    raw → parsed → normalized → dedup → summary → ready-for-embedding
    Geocoding and embedding are async and handled separately.
    """
    if existing_hashes is None:
        existing_hashes = set()

    try:
        job_data = process_parse(job_data)
    except (ValueError, PipelineError) as e:
        return handle_failure(job_data, e, "parse")

    try:
        job_data = process_normalize(job_data)
    except (ValueError, PipelineError) as e:
        return handle_failure(job_data, e, "normalize")

    try:
        job_data = process_dedup(job_data, existing_hashes)
    except DuplicateError:
        job_data["status"] = "duplicate"
        return job_data

    try:
        job_data = process_summary(job_data)
    except (ValueError, PipelineError) as e:
        return handle_failure(job_data, e, "summary")

    return job_data
