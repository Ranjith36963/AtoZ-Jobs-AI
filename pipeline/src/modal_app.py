"""Modal serverless app with scheduled cron functions (PLAYBOOK §2.6, Phase 2).

Cron functions:
- fetch_reed: Every 30 min
- fetch_adzuna: Every 60 min
- fetch_aggregators: Every 2 hours (Jooble + Careerjet combined)
- fetch_free_apis: Every 3 hours (7 free sources, no API keys)
- process_queues: Every 15 min
- daily_maintenance: Daily at 3 AM (includes monthly_reindex on day 1)

Phase 2 adds non-cron functions callable via Modal CLI/API:
- seed_esco: One-time ESCO taxonomy load
- backfill_job_skills: Skills extraction backfill
- backfill_dedup: Advanced deduplication backfill
- train_salary_model: Monthly salary model training
- enrich_companies: Nightly Companies House enrichment
- predict_salaries: Nightly salary prediction
- search: Web endpoint for search_jobs_v2 + cross-encoder re-ranking
"""

import os
from datetime import datetime, timezone
from typing import Any

import modal

app = modal.App("atoz-jobs-pipeline")

# Modal Volume for persisting salary model between train and predict invocations
model_volume = modal.Volume.from_name("atoz-model-store", create_if_missing=True)
MODEL_VOLUME_PATH = "/model-store"

# Known jobs table columns — used to filter out in-memory-only fields before DB update.
# Avoids PostgREST 400 errors from keys like extracted_skills, structured_summary, failed_stage.
_JOBS_TABLE_COLUMNS = {
    "id",
    "source_id",
    "external_id",
    "source_url",
    "title",
    "description",
    "description_plain",
    "company_id",
    "company_name",
    "location_raw",
    "location_city",
    "location_region",
    "location_postcode",
    "location_type",
    "location",
    "employment_type",
    "seniority_level",
    "visa_sponsorship",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "salary_raw",
    "salary_annual_min",
    "salary_annual_max",
    "salary_is_predicted",
    "salary_predicted_min",
    "salary_predicted_max",
    "salary_confidence",
    "salary_model_version",
    "category",
    "category_raw",
    "contract_type",
    "soc_code",
    "esco_occupation_uri",
    "date_posted",
    "date_expires",
    "date_crawled",
    "status",
    "retry_count",
    "last_error",
    "embedding",
    "content_hash",
    "raw_data",
    "canonical_id",
    "is_duplicate",
    "duplicate_score",
    "description_hash",
}


def _strip_non_db_fields(job_data: dict[str, object]) -> dict[str, object]:
    """Remove keys not in the jobs table to prevent PostgREST errors."""
    return {k: v for k, v in job_data.items() if k in _JOBS_TABLE_COLUMNS}


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Phase 1 dependencies
        "httpx",
        "pydantic",
        "google-genai",
        "structlog",
        "numpy",
        "supabase",
        "postgrest",
        "beautifulsoup4",
        # Phase 2 dependencies
        "spacy>=3.7",
        "datasketch>=1.6",
        "xxhash>=3.0",
        "xgboost>=2.0",
        "scikit-learn>=1.4",
        "sentence-transformers>=2.2",
        "fastapi[standard]",
    )
    .run_commands(
        "python -m spacy download en_core_web_sm",
    )
    .add_local_python_source("src")
)


def _get_db() -> Any:
    """Initialize Supabase client from environment (service role for server-side ops)."""
    from supabase import create_client

    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _resolve_source_ids(db_client: Any, source_names: set[str]) -> dict[str, int]:
    """Look up or create source records, returning {name: id} mapping."""
    mapping: dict[str, int] = {}
    for name in source_names:
        result = (
            db_client.table("sources").select("id").eq("name", name).limit(1).execute()
        )
        if result.data:
            mapping[name] = int(result.data[0]["id"])
        else:
            insert_result = (
                db_client.table("sources")
                .insert({"name": name, "is_active": True})
                .execute()
            )
            mapping[name] = int(insert_result.data[0]["id"])
    return mapping


# Fields in JobBase that do not map directly to jobs table columns.
# latitude/longitude are handled later by the geocode pipeline stage
# (stored as a PostGIS GEOGRAPHY point, not separate columns).
_EXCLUDE_FROM_UPSERT = {"source_name", "latitude", "longitude"}


def _upsert_jobs(db_client: Any, jobs: list[Any]) -> int:
    """UPSERT collected jobs into the jobs table.

    Args:
        db_client: Supabase client.
        jobs: List of JobBase model instances.

    Returns:
        Number of jobs upserted.
    """
    import structlog

    logger = structlog.get_logger()
    if not jobs:
        return 0

    # Resolve source_name → source_id
    source_names = {j.source_name for j in jobs}
    source_map = _resolve_source_ids(db_client, source_names)

    rows: list[dict[str, object]] = []
    for j in jobs:
        row = j.model_dump(mode="json")
        row["source_id"] = source_map[j.source_name]
        for key in _EXCLUDE_FROM_UPSERT:
            row.pop(key, None)
        rows.append(row)

    batch_size = 500
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        db_client.table("jobs").upsert(
            batch, on_conflict="source_id,external_id"
        ).execute()
        total += len(batch)

    logger.info("upsert.complete", total=total)
    return total


# ---------------------------------------------------------------------------
# Phase 1: Scheduled cron functions (5 crons)
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("*/30 * * * *"),
    timeout=600,
)
async def fetch_reed() -> None:
    """Fetch jobs from Reed API every 30 minutes."""
    import httpx
    import structlog

    from src.collectors.reed import ReedCollector

    logger = structlog.get_logger()
    api_key = os.environ.get("REED_API_KEY", "")
    if not api_key:
        logger.warning("fetch_reed.skipped", reason="REED_API_KEY not set")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        collector = ReedCollector(client=client, api_key=api_key)
        jobs = await collector.fetch_all()
        logger.info("fetch_reed.collected", jobs_collected=len(jobs))

    db_client = _get_db()
    upserted = _upsert_jobs(db_client, jobs)
    logger.info("fetch_reed.complete", jobs_upserted=upserted)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("0 * * * *"),
    timeout=600,
)
async def fetch_adzuna() -> None:
    """Fetch jobs from Adzuna API every 60 minutes."""
    import httpx
    import structlog

    from src.collectors.adzuna import AdzunaCollector

    logger = structlog.get_logger()
    app_id = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        logger.warning("fetch_adzuna.skipped", reason="ADZUNA credentials not set")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        collector = AdzunaCollector(client=client, app_id=app_id, app_key=app_key)
        jobs = await collector.fetch_all()
        logger.info("fetch_adzuna.collected", jobs_collected=len(jobs))

    db_client = _get_db()
    upserted = _upsert_jobs(db_client, jobs)
    logger.info("fetch_adzuna.complete", jobs_upserted=upserted)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("0 */2 * * *"),
    timeout=900,
)
async def fetch_aggregators() -> None:
    """Fetch jobs from Jooble + Careerjet every 2 hours (combined to stay within 5-cron limit)."""
    import httpx
    import structlog

    from src.collectors.careerjet import CareerjetCollector
    from src.collectors.jooble import JoobleCollector

    logger = structlog.get_logger()
    all_jobs: list[object] = []

    # Jooble
    jooble_key = os.environ.get("JOOBLE_API_KEY", "")
    if not jooble_key:
        logger.warning("fetch_jooble.skipped", reason="JOOBLE_API_KEY not set")
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            jooble = JoobleCollector(client=client, api_key=jooble_key)
            jooble_jobs = await jooble.sweep_all()
            all_jobs.extend(jooble_jobs)
            logger.info("fetch_jooble.complete", jobs_collected=len(jooble_jobs))

    # Careerjet
    careerjet_affid = os.environ.get("CAREERJET_AFFID", "")
    if not careerjet_affid:
        logger.warning("fetch_careerjet.skipped", reason="CAREERJET_AFFID not set")
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            careerjet = CareerjetCollector(
                client=client,
                affid=careerjet_affid,
                user_ip=os.environ.get("MODAL_WORKER_IP", "0.0.0.0"),
                user_agent="AtoZ-Jobs-Pipeline/0.1",
            )
            careerjet_jobs = await careerjet.sweep_all()
            all_jobs.extend(careerjet_jobs)
            logger.info("fetch_careerjet.complete", jobs_collected=len(careerjet_jobs))

    db_client = _get_db()
    upserted = _upsert_jobs(db_client, all_jobs)
    logger.info("fetch_aggregators.complete", jobs_upserted=upserted)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("30 */3 * * *"),
    timeout=900,
)
async def fetch_free_apis() -> None:
    """Fetch jobs from 7 free API sources every 3 hours (no API keys needed).

    Sources: Arbeitnow, RemoteOK, Jobicy, Himalayas, Remotive, DevITjobs, Landing.jobs.
    Filters for UK/Remote jobs.
    """
    import httpx
    import structlog

    from src.collectors.free_apis import fetch_all_free_sources

    logger = structlog.get_logger()
    logger.info("fetch_free_apis.start")

    async with httpx.AsyncClient(timeout=30.0) as client:
        jobs = await fetch_all_free_sources(client)
        logger.info("fetch_free_apis.collected", jobs_collected=len(jobs))

    if jobs:
        db_client = _get_db()
        upserted = _upsert_jobs(db_client, jobs)
        logger.info("fetch_free_apis.complete", jobs_upserted=upserted)
    else:
        logger.warning("fetch_free_apis.no_jobs")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("*/15 * * * *"),
    timeout=600,
)
async def process_queues() -> None:
    """Process all 6 queues every 15 minutes.

    Queue flow: parse -> normalize -> dedup -> geocode -> embed
    """
    import structlog

    from src.processing.queue_runner import (
        handle_failure,
        process_dedup,
        process_normalize,
        process_parse,
        process_summary,
    )

    logger = structlog.get_logger()
    logger.info("process_queues.start")

    db_client = _get_db()

    # Fetch jobs in 'raw' status for processing
    result = (
        db_client.table("jobs").select("*").eq("status", "raw").limit(100).execute()
    )

    processed = 0
    errors = 0
    for job_data in result.data or []:
        try:
            job_data = process_parse(job_data)
            job_data = process_normalize(job_data)

            # Fetch existing hashes for dedup
            hash_result = (
                db_client.table("jobs")
                .select("content_hash")
                .not_.is_("content_hash", "null")
                .execute()
            )
            existing_hashes = {r["content_hash"] for r in (hash_result.data or [])}
            job_data = process_dedup(job_data, existing_hashes)

            if job_data.get("status") != "duplicate":
                job_data = process_summary(job_data)
                # Mark as ready — geocoding/embedding are deferred stages
                job_data["status"] = "ready"

            # Strip non-DB fields before update to avoid PostgREST errors
            db_update = _strip_non_db_fields(job_data)
            db_client.table("jobs").update(db_update).eq("id", job_data["id"]).execute()
            processed += 1
        except Exception as e:
            job_data = handle_failure(job_data, e, "process_queues")
            db_update = _strip_non_db_fields(job_data)
            db_client.table("jobs").update(db_update).eq("id", job_data["id"]).execute()
            errors += 1

    logger.info("process_queues.complete", processed=processed, errors=errors)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    schedule=modal.Cron("0 3 * * *"),
    timeout=1200,
)
async def daily_maintenance() -> None:
    """Daily maintenance at 3 AM. Monthly reindex on day 1."""
    import structlog

    logger = structlog.get_logger()
    now = datetime.now(tz=timezone.utc)

    logger.info("daily_maintenance.start", date=now.isoformat())

    db_client = _get_db()

    # Step 1: Expire jobs past date_expires (ready -> expired)
    logger.info("expiry_check.start")
    db_client.table("jobs").update({"status": "expired"}).eq("status", "ready").lt(
        "date_expires", now.isoformat()
    ).execute()
    logger.info("expiry_check.complete")

    # Step 2: Retry failed jobs (status has last_error, retry_count < 3)
    logger.info("dlq_retry.start")
    try:
        failed_result = (
            db_client.table("jobs")
            .select("id")
            .not_.is_("last_error", "null")
            .lt("retry_count", 3)
            .limit(50)
            .execute()
        )
        retried = 0
        for row in failed_result.data or []:
            db_client.table("jobs").update({"status": "raw", "last_error": None}).eq(
                "id", row["id"]
            ).execute()
            retried += 1
        logger.info("dlq_retry.complete", retried=retried)
    except Exception as e:
        logger.error("dlq_retry.failed", error=str(e))

    # Step 3: Log pipeline health metrics
    logger.info("health_check.start")
    try:
        health = db_client.from_("pipeline_health").select("*").limit(1).execute()
        if health.data:
            logger.info("health_check.metrics", **health.data[0])
    except Exception as e:
        logger.warning("health_check.skipped", error=str(e))
    logger.info("health_check.complete")

    # Monthly reindex on day 1
    if now.day == 1:
        logger.info("monthly_reindex.start")
        try:
            db_client.rpc("reindex_jobs_search", {}).execute()
        except Exception as e:
            logger.warning("monthly_reindex.skipped", error=str(e))
        logger.info("monthly_reindex.complete")

    logger.info("daily_maintenance.complete")


# ---------------------------------------------------------------------------
# Phase 2: Non-cron functions (callable via Modal CLI / API)
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=1800,
)
async def seed_esco(csv_path: str = "data/esco_skills.csv") -> dict[str, Any]:
    """One-time ESCO taxonomy load into skills tables.

    Priority: CSV file > ESCO REST API > dictionary-only fallback.
    The ESCO API downloads ~14,500 skills when the CSV is not available.
    """
    import os

    import structlog

    from src.skills.seed_esco import (
        seed_esco_from_api,
        seed_esco_skills,
        seed_skills_table,
    )

    logger = structlog.get_logger()
    logger.info("seed_esco.start", csv_path=csv_path)

    db_client = _get_db()

    # Seed esco_skills table: CSV > API > skip
    esco_count = 0
    effective_csv: str | None = csv_path
    if os.path.exists(csv_path):
        esco_count = await seed_esco_skills(csv_path, db_client)
    else:
        logger.warning("seed_esco.csv_not_found", path=csv_path)
        effective_csv = None
        # Fallback: download from ESCO REST API
        try:
            esco_count = await seed_esco_from_api(db_client)
        except Exception as e:
            logger.error("seed_esco.api_fallback_failed", error=str(e))

    # Seed skills table from dictionary (works with or without CSV)
    skills_count = await seed_skills_table(db_client, effective_csv)

    logger.info(
        "seed_esco.complete", esco_inserted=esco_count, skills_upserted=skills_count
    )
    return {"esco_inserted": esco_count, "skills_upserted": skills_count}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def backfill_job_skills(batch_size: int = 500) -> dict[str, Any]:
    """Extract skills from all jobs and populate job_skills table."""
    import structlog

    from src.skills.dictionary_builder import build_dictionary
    from src.skills.populate import populate_job_skills
    from src.skills.spacy_matcher import SpaCySkillMatcher

    logger = structlog.get_logger()
    logger.info("backfill_job_skills.start", batch_size=batch_size)

    db_client = _get_db()
    dictionary = build_dictionary()
    matcher = SpaCySkillMatcher(dictionary)
    result = await populate_job_skills(db_client, matcher, batch_size)

    logger.info("backfill_job_skills.complete", **result)
    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def backfill_dedup(batch_size: int = 1000) -> dict[str, Any]:
    """Run advanced deduplication across all jobs."""
    import structlog

    from src.dedup.orchestrator import run_advanced_dedup

    logger = structlog.get_logger()
    logger.info("backfill_dedup.start", batch_size=batch_size)

    db_client = _get_db()
    result = await run_advanced_dedup(db_client, batch_size)

    logger.info("backfill_dedup.complete", **result)
    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    volumes={MODEL_VOLUME_PATH: model_volume},
    timeout=3600,
)
async def train_salary() -> dict[str, Any]:
    """Train XGBoost salary prediction model and persist to Modal Volume."""
    import numpy as np
    import structlog

    from src.salary.features import build_features
    from src.salary.trainer import save_model, train_salary_model

    logger = structlog.get_logger()
    logger.info("train_salary.start")

    db_client = _get_db()

    # Fetch jobs with salary data for training
    jobs_result = (
        db_client.table("jobs")
        .select("*")
        .not_.is_("salary_annual_max", "null")
        .eq("status", "ready")
        .execute()
    )
    jobs = jobs_result.data or []

    if len(jobs) < 100:
        logger.warning("train_salary.insufficient_data", job_count=len(jobs))
        return {
            "status": "skipped",
            "reason": "insufficient_data",
            "job_count": len(jobs),
        }

    features, labels = build_features(jobs)
    model, metrics = train_salary_model(np.array(features), np.array(labels))

    model_path = f"{MODEL_VOLUME_PATH}/salary_model.json"
    save_model(model, model_path)
    model_volume.commit()

    logger.info("train_salary.complete", **metrics)
    return metrics


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def enrich_companies_fn(batch_size: int = 100) -> dict[str, Any]:
    """Enrich companies with Companies House data."""
    import structlog

    from src.enrichment.orchestrator import enrich_companies

    logger = structlog.get_logger()
    logger.info("enrich_companies.start", batch_size=batch_size)

    db_client = _get_db()
    api_key = os.environ.get("COMPANIES_HOUSE_API_KEY", "")
    if not api_key:
        logger.warning(
            "enrich_companies.skipped", reason="COMPANIES_HOUSE_API_KEY not set"
        )
        return {"status": "skipped", "reason": "api_key_not_set"}

    result = await enrich_companies(db_client, api_key, batch_size)

    logger.info("enrich_companies.complete", **result)
    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    volumes={MODEL_VOLUME_PATH: model_volume},
    timeout=1800,
)
async def predict_salaries(batch_size: int = 500) -> dict[str, Any]:
    """Predict salaries for jobs missing salary data using persisted model."""
    import structlog

    from src.enrichment.orchestrator import predict_missing_salaries
    from src.salary.trainer import load_model

    logger = structlog.get_logger()
    logger.info("predict_salaries.start", batch_size=batch_size)

    db_client = _get_db()
    model_path = f"{MODEL_VOLUME_PATH}/salary_model.json"

    try:
        model_volume.reload()
        model = load_model(model_path)
    except Exception:
        logger.error("predict_salaries.model_not_found", path=model_path)
        return {"status": "error", "reason": "model_not_found"}

    result = await predict_missing_salaries(db_client, model, "v1.0", batch_size)

    logger.info("predict_salaries.complete", **result)
    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=30,
)
@modal.fastapi_endpoint(method="POST")
async def search_endpoint(
    query: str = "",
    filters: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Search endpoint: query -> embed -> search_jobs_v2 -> cross-encoder rerank."""
    import structlog

    from src.embeddings.embed import embed_all
    from src.search.orchestrator import search

    logger = structlog.get_logger()
    logger.info("search.request", query=query, user_id=user_id)

    if not query:
        return {"results": [], "total": 0, "latency_ms": 0.0}

    db_client = _get_db()

    async def _embed_fn(text: str) -> list[float]:
        results = await embed_all([text])
        return results[0] if results else []

    result = await search(
        query=query,
        db_client=db_client,
        embed_fn=_embed_fn,
        user_id=user_id,
        filters=filters or {},
    )
    return result
