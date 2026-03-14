"""ESCO data seeder (PLAYBOOK §1.6).

Seeds esco_skills table and skills table from ESCO CSV, API, or dictionary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.skills.dictionary_builder import build_dictionary
from src.skills.esco_loader import load_esco_csv

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()


def _esco_data_to_rows(
    esco_data: dict[str, dict[str, str | list[str]]],
) -> list[dict[str, str | list[str]]]:
    """Convert esco_data dict to list of DB rows."""
    rows: list[dict[str, str | list[str]]] = []
    for uri, skill_data in esco_data.items():
        rows.append(
            {
                "concept_uri": uri,
                "preferred_label": str(skill_data["preferred_label"]),
                "alt_labels": skill_data.get("alt_labels", []),
                "skill_type": str(skill_data.get("skill_type", "")),
                "description": str(skill_data.get("description", "")),
            }
        )
    return rows


async def _upsert_esco_rows(
    rows: list[dict[str, str | list[str]]],
    db_client: Client,
) -> int:
    """Batch upsert ESCO rows into esco_skills table."""
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        db_client.table("esco_skills").upsert(batch).execute()
        total_inserted += len(batch)
        logger.info("seed_esco.progress", inserted=total_inserted, total=len(rows))

    logger.info("seed_esco.complete", total_inserted=total_inserted)
    return total_inserted


async def seed_esco_skills(csv_path: str, db_client: Client) -> int:
    """Bulk insert ESCO skills from CSV into esco_skills table.

    Args:
        csv_path: Path to ESCO skills_en.csv.
        db_client: Supabase client.

    Returns:
        Number of rows inserted.
    """
    esco_data = load_esco_csv(csv_path)
    rows = _esco_data_to_rows(esco_data)
    return await _upsert_esco_rows(rows, db_client)


async def seed_esco_from_api(db_client: Client) -> int:
    """Download ESCO skills from the EU REST API and seed esco_skills table.

    Fetches all ~14,500 skills via paginated API calls. Used when the
    CSV file is not available locally.

    Args:
        db_client: Supabase client.

    Returns:
        Number of rows inserted.
    """
    from src.skills.esco_api import fetch_all_esco_skills

    logger.info("seed_esco.api_download_start")
    esco_data = await fetch_all_esco_skills()
    logger.info("seed_esco.api_download_complete", skills_fetched=len(esco_data))

    rows = _esco_data_to_rows(esco_data)
    return await _upsert_esco_rows(rows, db_client)


async def seed_skills_table(
    db_client: Client,
    esco_csv_path: str | None = None,
) -> int:
    """Seed skills table with canonical skills from all sources.

    Args:
        db_client: Supabase client.
        esco_csv_path: Path to ESCO CSV. If None, uses Phase 1 dict + UK entries.

    Returns:
        Number of skills upserted.
    """
    dictionary = build_dictionary(esco_csv_path)
    canonical_names = sorted(set(dictionary.values()))

    rows = [{"name": name} for name in canonical_names]

    # Batch upsert
    batch_size = 1000
    total = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        db_client.table("skills").upsert(batch, on_conflict="name").execute()
        total += len(batch)
        logger.info("seed_skills.progress", upserted=total, total=len(rows))

    logger.info("seed_skills.complete", total_skills=total)
    return total
