"""Modal serverless app with 5 scheduled cron functions (PLAYBOOK §2.6).

Modal Starter allows 5 deployed crons, so we consolidate:
- fetch_reed: Every 30 min
- fetch_adzuna: Every 60 min
- fetch_aggregators: Every 2 hours (Jooble + Careerjet combined)
- process_queues: Every 15 min
- daily_maintenance: Daily at 3 AM (includes monthly_reindex on day 1)
"""

import os
from datetime import datetime, timezone

import modal

app = modal.App("atoz-jobs-pipeline")

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "httpx",
    "pydantic",
    "google-genai",
    "structlog",
    "numpy",
    "supabase",
    "beautifulsoup4",
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

    Queue flow: parse → normalize → dedup → geocode → embed
    """
    import structlog

    logger = structlog.get_logger()
    logger.info("process_queues.start")

    # TODO: Implement queue processing in Stage 3
    # - Read from parse_queue → run parsers → write to normalize_queue
    # - Read from normalize_queue → normalize salary/location → dedup_queue
    # - Read from dedup_queue → content_hash check → geocode_queue
    # - Read from geocode_queue → postcodes.io → embed_queue
    # - Read from embed_queue → Gemini embedding → mark ready

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

    # TODO: Implement in Stage 4
    # - Expire jobs past date_expires (ready → expired)
    # - Retry dead_letter_queue items older than 6 hours
    # - Update pipeline_health materialized view

    # Monthly reindex on day 1
    if now.day == 1:
        logger.info("monthly_reindex.start")
        # TODO: Rebuild HNSW index, vacuum analyze
        logger.info("monthly_reindex.complete")

    logger.info("daily_maintenance.complete")
