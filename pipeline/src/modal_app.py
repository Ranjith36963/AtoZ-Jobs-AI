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
    rows = [j.model_dump() for j in jobs]
    if not rows:
        return 0

    batch_size = 500
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        db_client.table("jobs").upsert(
            batch, on_conflict="source_id,source_name"
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

            # Update job in database
            db_client.table("jobs").update(job_data).eq("id", job_data["id"]).execute()
            processed += 1
        except Exception as e:
            job_data = handle_failure(job_data, e, "process_queues")
            db_client.table("jobs").update(job_data).eq("id", job_data["id"]).execute()
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

    # Step 2: Retry dead_letter_queue items older than 6 hours
    logger.info("dlq_retry.start")
    six_hours_ago = now.timestamp() - (6 * 3600)
    dlq_result = db_client.rpc(
        "pgmq_read",
        {
            "queue_name": "dead_letter_queue",
            "vt": 0,
            "qty": 50,
        },
    ).execute()
    for msg in dlq_result.data or []:
        if msg.get("enqueued_at", 0) < six_hours_ago:
            db_client.rpc(
                "pgmq_send",
                {
                    "queue_name": "parse_queue",
                    "msg": msg.get("message", {}),
                },
            ).execute()
    logger.info("dlq_retry.complete")

    # Step 3: Log pipeline health metrics
    logger.info("health_check.start")
    health = db_client.rpc("pipeline_health", {}).execute()
    if health.data:
        logger.info("health_check.metrics", **health.data[0])
    logger.info("health_check.complete")

    # Monthly reindex on day 1
    if now.day == 1:
        logger.info("monthly_reindex.start")
        db_client.rpc("reindex_jobs_search", {}).execute()
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
    timeout=3600,
)
async def train_salary() -> dict[str, Any]:
    """Train XGBoost salary prediction model."""
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

    model_path = "/tmp/salary_model.json"
    save_model(model, model_path)

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
    api_key = os.environ["COMPANIES_HOUSE_API_KEY"]
    result = await enrich_companies(db_client, api_key, batch_size)

    logger.info("enrich_companies.complete", **result)
    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=1800,
)
async def predict_salaries(batch_size: int = 500) -> dict[str, Any]:
    """Predict salaries for jobs missing salary data."""
    import structlog

    from src.enrichment.orchestrator import predict_missing_salaries
    from src.salary.trainer import load_model

    logger = structlog.get_logger()
    logger.info("predict_salaries.start", batch_size=batch_size)

    db_client = _get_db()
    model_path = "/tmp/salary_model.json"

    try:
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
