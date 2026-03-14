"""Enrichment orchestrator: Companies House + salary prediction (SPEC.md §5.2).

Combines company enrichment via Companies House API with XGBoost salary
prediction for jobs missing salary data.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog
import xgboost as xgb

from src.enrichment.companies_house import (
    get_company_profile,
    search_company,
    sic_to_section,
)
from src.salary.features import build_features
from src.salary.trainer import predict_salary

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()

# Rate limit: 600 req/5min = 2 req/sec -> sleep 0.5s between requests
RATE_LIMIT_DELAY = 0.5


async def enrich_companies(
    db_client: Client,
    api_key: str,
    batch_size: int = 100,
) -> dict[str, int]:
    """Enrich companies with Companies House data.

    Args:
        db_client: Supabase client.
        api_key: Companies House API key.
        batch_size: Number of companies per batch.

    Returns:
        Stats dict with enriched/skipped/failed counts.
    """
    stats: dict[str, int] = {"enriched": 0, "skipped": 0, "failed": 0}

    companies = (
        db_client.table("companies")
        .select("id, name")
        .is_("enriched_at", "null")
        .limit(batch_size)
        .execute()
        .data
    )

    if not companies:
        logger.info("enrichment.no_companies_to_enrich")
        return stats

    logger.info("enrichment.starting", count=len(companies))

    for company in companies:
        try:
            search_result = await search_company(company["name"], api_key)

            if search_result is None:
                stats["skipped"] += 1
                logger.debug(
                    "enrichment.no_match",
                    company_name=company["name"],
                )
                continue

            company_number = search_result["company_number"]
            profile = await get_company_profile(company_number, api_key)

            sic_codes = profile.get("sic_codes", [])
            industry_section = sic_to_section(sic_codes[0]) if sic_codes else "S"

            update_data: dict[str, Any] = {
                "companies_house_number": company_number,
                "sic_codes": sic_codes,
                "company_status": profile.get("company_status"),
                "date_of_creation": profile.get("date_of_creation"),
                "registered_address": profile.get("registered_office_address"),
                "enriched_at": datetime.now(tz=timezone.utc).isoformat(),
            }

            db_client.table("companies").update(update_data).eq(
                "id", company["id"]
            ).execute()

            stats["enriched"] += 1
            logger.info(
                "enrichment.enriched",
                company_name=company["name"],
                company_number=company_number,
                industry_section=industry_section,
            )

        except Exception:
            stats["failed"] += 1
            logger.exception(
                "enrichment.error",
                company_name=company["name"],
            )

        # Rate limiting between requests
        await asyncio.sleep(RATE_LIMIT_DELAY)

    logger.info("enrichment.complete", **stats)
    return stats


async def predict_missing_salaries(
    db_client: Client,
    model: xgb.Booster,
    model_version: str = "v1.0",
    batch_size: int = 500,
) -> dict[str, int]:
    """Predict salaries for jobs missing salary data.

    Args:
        db_client: Supabase client.
        model: Trained XGBoost model.
        model_version: Model version string.
        batch_size: Number of jobs per batch.

    Returns:
        Stats dict with predicted/failed counts.
    """
    stats: dict[str, int] = {"predicted": 0, "failed": 0}

    jobs = (
        db_client.table("jobs")
        .select("id, title, location_region, category, seniority, description_plain")
        .is_("salary_annual_max", "null")
        .is_("salary_predicted_max", "null")
        .eq("status", "ready")
        .limit(batch_size)
        .execute()
        .data
    )

    if not jobs:
        logger.info("salary_prediction.no_jobs")
        return stats

    logger.info("salary_prediction.starting", count=len(jobs))

    try:
        features, _ = build_features(jobs)
        predictions = predict_salary(model, features)

        for job, prediction in zip(jobs, predictions):
            try:
                db_client.table("jobs").update(
                    {
                        "salary_predicted_min": prediction["predicted_min"],
                        "salary_predicted_max": prediction["predicted_max"],
                        "salary_confidence": prediction["confidence"],
                        "salary_model_version": model_version,
                    }
                ).eq("id", job["id"]).execute()

                stats["predicted"] += 1
            except Exception:
                stats["failed"] += 1
                logger.exception(
                    "salary_prediction.update_error",
                    job_id=job["id"],
                )

    except Exception:
        stats["failed"] += len(jobs)
        logger.exception("salary_prediction.batch_error")

    logger.info("salary_prediction.complete", **stats)
    return stats
