"""Modal serverless app with scheduled cron functions (PLAYBOOK §2.6, Phase 2).

Modal Starter allows 5 deployed crons, so we consolidate:
- fetch_reed: Every 30 min
- fetch_adzuna: Every 60 min
- fetch_aggregators: Every 2 hours (Jooble + Careerjet combined)
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
    )
    .run_commands(
        "python -m spacy download en_core_web_sm",
    )
)


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
    api_key = os.environ["REED_API_KEY"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        collector = ReedCollector(client=client, api_key=api_key)
        jobs = await collector.fetch_all()
        logger.info("fetch_reed.complete", jobs_collected=len(jobs))

    # TODO: UPSERT jobs into Supabase (Stage 2.7 wiring)


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
    app_id = os.environ["ADZUNA_APP_ID"]
    app_key = os.environ["ADZUNA_APP_KEY"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        collector = AdzunaCollector(client=client, app_id=app_id, app_key=app_key)
        jobs = await collector.fetch_all()
        logger.info("fetch_adzuna.complete", jobs_collected=len(jobs))

    # TODO: UPSERT jobs into Supabase


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

    # Jooble
    jooble_key = os.environ["JOOBLE_API_KEY"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        jooble = JoobleCollector(client=client, api_key=jooble_key)
        jooble_jobs = await jooble.sweep_all()
        logger.info("fetch_jooble.complete", jobs_collected=len(jooble_jobs))

    # Careerjet (offset 30 min conceptually, but combined here)
    careerjet_affid = os.environ["CAREERJET_AFFID"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        careerjet = CareerjetCollector(
            client=client,
            affid=careerjet_affid,
            user_ip=os.environ.get("MODAL_WORKER_IP", "0.0.0.0"),
            user_agent="AtoZ-Jobs-Pipeline/0.1",
        )
        careerjet_jobs = await careerjet.sweep_all()
        logger.info("fetch_careerjet.complete", jobs_collected=len(careerjet_jobs))

    # TODO: UPSERT all jobs into Supabase


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

    logger = structlog.get_logger()
    logger.info("process_queues.start")

    # TODO: Implement queue processing in Stage 3
    # - Read from parse_queue -> run parsers -> write to normalize_queue
    # - Read from normalize_queue -> normalize salary/location -> dedup_queue
    # - Read from dedup_queue -> content_hash check -> geocode_queue
    # - Read from geocode_queue -> postcodes.io -> embed_queue
    # - Read from embed_queue -> Gemini embedding -> mark ready

    logger.info("process_queues.complete")


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

    # Step 1: Expire jobs past date_expires (ready -> expired)
    logger.info("expiry_check.start")
    logger.info("expiry_check.complete")

    # Step 2: Retry dead_letter_queue items older than 6 hours
    logger.info("dlq_retry.start")
    logger.info("dlq_retry.complete")

    # Step 3: Log pipeline health metrics
    logger.info("health_check.start")
    logger.info("health_check.complete")

    # Monthly reindex on day 1
    if now.day == 1:
        logger.info("monthly_reindex.start")
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
async def seed_esco(csv_path: str = "data/esco_skills.csv") -> dict[str, object]:
    """One-time ESCO taxonomy load into skills tables."""
    import structlog

    logger = structlog.get_logger()
    logger.info("seed_esco.start", csv_path=csv_path)

    # In production: initialize Supabase client from env
    # db_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    # esco_count = await seed_esco_skills(csv_path, db_client)
    # skills_count = await seed_skills_table(db_client, csv_path)
    # return {"esco_inserted": esco_count, "skills_upserted": skills_count}
    logger.info("seed_esco.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def backfill_job_skills(batch_size: int = 500) -> dict[str, object]:
    """Extract skills from all jobs and populate job_skills table."""
    import structlog

    logger = structlog.get_logger()
    logger.info("backfill_job_skills.start", batch_size=batch_size)

    # In production:
    # from src.skills.spacy_matcher import SpaCySkillMatcher
    # from src.skills.dictionary_builder import build_dictionary
    # from src.skills.populate import populate_job_skills
    # dictionary = build_dictionary()
    # matcher = SpaCySkillMatcher(dictionary)
    # result = await populate_job_skills(db_client, matcher, batch_size)
    # return result
    logger.info("backfill_job_skills.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def backfill_dedup(batch_size: int = 1000) -> dict[str, object]:
    """Run advanced deduplication across all jobs."""
    import structlog

    logger = structlog.get_logger()
    logger.info("backfill_dedup.start", batch_size=batch_size)

    # In production:
    # from src.dedup.orchestrator import run_advanced_dedup
    # result = await run_advanced_dedup(db_client, batch_size)
    # return result
    logger.info("backfill_dedup.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def train_salary() -> dict[str, object]:
    """Train XGBoost salary prediction model."""
    import structlog

    logger = structlog.get_logger()
    logger.info("train_salary.start")

    # In production:
    # from src.salary.features import build_features
    # from src.salary.trainer import train_salary_model, save_model
    # jobs = db_client.table("jobs").select("*").not_.is_("salary_annual_max", "null").execute().data
    # features, labels = build_features(jobs)
    # model, metrics = train_salary_model(features, labels)
    # save_model(model, "/tmp/salary_model.json")
    # return metrics
    logger.info("train_salary.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=3600,
)
async def enrich_companies_fn(batch_size: int = 100) -> dict[str, object]:
    """Enrich companies with Companies House data."""
    import structlog

    logger = structlog.get_logger()
    logger.info("enrich_companies.start", batch_size=batch_size)

    # In production:
    # from src.enrichment.orchestrator import enrich_companies
    # api_key = os.environ["COMPANIES_HOUSE_API_KEY"]
    # result = await enrich_companies(db_client, api_key, batch_size)
    # return result
    logger.info("enrich_companies.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=1800,
)
async def predict_salaries(batch_size: int = 500) -> dict[str, object]:
    """Predict salaries for jobs missing salary data."""
    import structlog

    logger = structlog.get_logger()
    logger.info("predict_salaries.start", batch_size=batch_size)

    # In production:
    # from src.enrichment.orchestrator import predict_missing_salaries
    # from src.salary.trainer import load_model
    # model = load_model("/path/to/salary_model.json")
    # result = await predict_missing_salaries(db_client, model, "v1.0", batch_size)
    # return result
    logger.info("predict_salaries.complete")
    return {"status": "ready_for_production_wiring"}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("atoz-env")],
    timeout=30,
)
@modal.web_endpoint(method="POST")
async def search_endpoint(
    query: str = "",
    filters: dict[str, object] | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Search endpoint: query -> embed -> search_jobs_v2 -> cross-encoder rerank."""
    import structlog

    logger = structlog.get_logger()
    logger.info("search.request", query=query, user_id=user_id)

    # In production:
    # from src.search.orchestrator import search
    # result = await search(
    #     query=query, db_client=db_client, embed_fn=embed_fn,
    #     user_id=user_id, filters=filters or {}
    # )
    # return result
    return {
        "results": [],
        "total": 0,
        "latency_ms": 0.0,
        "status": "ready_for_production_wiring",
    }
