"""ESCO data seeder (PLAYBOOK §1.6).

Seeds esco_skills table and skills table from ESCO CSV + dictionary builder.
"""

from typing import Any

import structlog

from src.skills.dictionary_builder import build_dictionary
from src.skills.esco_loader import load_esco_csv

logger = structlog.get_logger()


async def seed_esco_skills(csv_path: str, db_client: Any) -> int:
    """Bulk insert ESCO skills into esco_skills table.

    Args:
        csv_path: Path to ESCO skills_en.csv.
        db_client: Supabase client.

    Returns:
        Number of rows inserted.
    """
    esco_data = load_esco_csv(csv_path)
    rows = []

    for uri, skill_data in esco_data.items():
        rows.append({
            "concept_uri": uri,
            "preferred_label": skill_data["preferred_label"],
            "alt_labels": skill_data.get("alt_labels", []),
            "skill_type": skill_data.get("skill_type", ""),
            "description": skill_data.get("description", ""),
        })

    # Batch insert in chunks of 1000
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        db_client.table("esco_skills").upsert(batch).execute()
        total_inserted += len(batch)
        logger.info("seed_esco.progress", inserted=total_inserted, total=len(rows))

    logger.info("seed_esco.complete", total_inserted=total_inserted)
    return total_inserted


async def seed_skills_table(
    db_client: Any,
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
        db_client.table("skills").upsert(
            batch, on_conflict="name"
        ).execute()
        total += len(batch)
        logger.info("seed_skills.progress", upserted=total, total=len(rows))

    logger.info("seed_skills.complete", total_skills=total)
    return total
