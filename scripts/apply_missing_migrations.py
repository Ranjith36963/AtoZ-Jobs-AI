"""Apply missing Phase 2 migrations and seed data.

Fixes gaps found in the database:
1. Migration 014: RLS policies for esco_skills and sic_industry_map (DDL - needs manual apply)
2. Migration 015: find_fuzzy_duplicates() function (DDL - needs manual apply)
3. Seed esco_skills table with sample ESCO data via REST API
4. Seed skills table with dictionary builder canonical names via REST API

Usage:
    cd pipeline && uv run python ../scripts/apply_missing_migrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add pipeline src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from supabase import create_client


def get_client() -> object:
    """Create Supabase client from .env."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        # Try loading from .env file
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
        sys.exit(1)

    return create_client(url, key)


def seed_esco_skills(client: object) -> int:
    """Seed esco_skills table with ESCO sample data."""
    from src.skills.esco_loader import load_esco_csv

    csv_path = Path(__file__).parent.parent / "pipeline" / "src" / "tests" / "fixtures" / "esco_sample.csv"
    if not csv_path.exists():
        print(f"WARNING: ESCO sample CSV not found at {csv_path}")
        return 0

    esco_data = load_esco_csv(str(csv_path))
    rows = []
    for uri, skill_data in esco_data.items():
        rows.append({
            "concept_uri": uri,
            "preferred_label": skill_data["preferred_label"],
            "alt_labels": skill_data.get("alt_labels", []),
            "skill_type": skill_data.get("skill_type", ""),
            "description": skill_data.get("description", ""),
        })

    if rows:
        client.table("esco_skills").upsert(rows).execute()
        print(f"  Seeded {len(rows)} ESCO skills")

    return len(rows)


def seed_skills_table(client: object) -> int:
    """Seed skills table with canonical skill names from dictionary builder."""
    from src.skills.dictionary_builder import build_dictionary

    # Build without full ESCO CSV (use Phase 1 + UK entries)
    dictionary = build_dictionary(None)
    canonical_names = sorted(set(dictionary.values()))

    rows = [{"name": name} for name in canonical_names]

    # Batch upsert
    batch_size = 500
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table("skills").upsert(batch, on_conflict="name").execute()
        total += len(batch)

    print(f"  Seeded {total} canonical skills")
    return total


def check_and_report(client: object) -> dict[str, bool]:
    """Check database state and report gaps."""
    results: dict[str, bool] = {}

    # Check esco_skills count
    resp = client.table("esco_skills").select("concept_uri", count="exact").limit(0).execute()
    count = resp.count if resp.count is not None else 0
    results["esco_skills_has_data"] = count > 0
    print(f"  esco_skills: {count} rows")

    # Check skills count
    resp = client.table("skills").select("id", count="exact").limit(0).execute()
    count = resp.count if resp.count is not None else 0
    results["skills_has_data"] = count > 0
    print(f"  skills: {count} rows")

    # Check sic_industry_map
    resp = client.table("sic_industry_map").select("sic_section", count="exact").limit(0).execute()
    count = resp.count if resp.count is not None else 0
    results["sic_industry_map_has_data"] = count > 0
    print(f"  sic_industry_map: {count} rows")

    # Check find_fuzzy_duplicates function
    try:
        client.rpc("find_fuzzy_duplicates", {"target_job_id": -1}).execute()
        results["find_fuzzy_duplicates_exists"] = True
        print("  find_fuzzy_duplicates(): EXISTS")
    except Exception:
        results["find_fuzzy_duplicates_exists"] = False
        print("  find_fuzzy_duplicates(): MISSING")

    # Check search_jobs_v2 function
    try:
        client.rpc("search_jobs_v2", {}).execute()
        results["search_jobs_v2_exists"] = True
        print("  search_jobs_v2(): EXISTS")
    except Exception:
        results["search_jobs_v2_exists"] = False
        print("  search_jobs_v2(): MISSING")

    return results


def print_ddl_instructions() -> None:
    """Print SQL that must be applied manually for DDL operations."""
    print("\n" + "=" * 70)
    print("MANUAL DDL REQUIRED")
    print("=" * 70)
    print("""
The following SQL must be run via the Supabase SQL Editor (Dashboard):

-- =============================================
-- Migration 014: Phase 2 RLS Policies
-- =============================================

-- esco_skills: public read, service role write
CREATE POLICY IF NOT EXISTS "Public can read esco_skills"
    ON esco_skills FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Service role writes esco_skills"
    ON esco_skills FOR ALL USING (auth.role() = 'service_role');

-- sic_industry_map: public read, service role write
CREATE POLICY IF NOT EXISTS "Public can read sic_industry_map"
    ON sic_industry_map FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Service role writes sic_industry_map"
    ON sic_industry_map FOR ALL USING (auth.role() = 'service_role');

-- =============================================
-- Migration 015: find_fuzzy_duplicates function
-- =============================================

CREATE OR REPLACE FUNCTION find_fuzzy_duplicates(target_job_id BIGINT)
RETURNS TABLE (
    candidate_id BIGINT,
    title_sim FLOAT,
    company_sim FLOAT,
    distance_km FLOAT,
    dup_score FLOAT
)
LANGUAGE sql STABLE AS $$
SELECT
    j2.id AS candidate_id,
    similarity(j1.title, j2.title)::FLOAT AS title_sim,
    similarity(j1.company_name, j2.company_name)::FLOAT AS company_sim,
    COALESCE(
        ST_Distance(j1.location::geography, j2.location::geography) / 1000.0,
        0
    )::FLOAT AS distance_km,
    compute_duplicate_score(
        similarity(j1.title, j2.title),
        similarity(j1.company_name, j2.company_name) > 0.5,
        COALESCE(
            ST_Distance(j1.location::geography, j2.location::geography) / 1000.0,
            0
        ),
        CASE
            WHEN j1.salary_annual_max IS NOT NULL AND j2.salary_annual_max IS NOT NULL
            THEN 1.0 - ABS(j1.salary_annual_max - j2.salary_annual_max)
                / GREATEST(j1.salary_annual_max, j2.salary_annual_max, 1)
            ELSE 0.0
        END,
        COALESCE(
            ABS(EXTRACT(EPOCH FROM j1.date_posted - j2.date_posted) / 86400)::INT,
            30
        )
    )::FLOAT AS dup_score
FROM jobs j1, jobs j2
WHERE j1.id = target_job_id
  AND j2.id != j1.id
  AND j2.status = 'ready'
  AND j2.is_duplicate IS NOT TRUE
  AND j1.title % j2.title
  AND similarity(j1.title, j2.title) >= 0.6
ORDER BY dup_score DESC
LIMIT 10;
$$;
""")
    print("=" * 70)
    print("Copy and paste the above SQL into the Supabase SQL Editor at:")
    print("https://supabase.com/dashboard/project/uskvwcyimfnienizneih/sql/new")
    print("=" * 70)


def main() -> None:
    """Run all gap-fixing operations."""
    print("AtoZ Jobs AI — Apply Missing Migrations & Seed Data")
    print("=" * 55)

    client = get_client()

    # Step 1: Check current state
    print("\n[1/4] Checking current database state...")
    state = check_and_report(client)

    # Step 2: Seed esco_skills if empty
    print("\n[2/4] Seeding esco_skills table...")
    if not state["esco_skills_has_data"]:
        seed_esco_skills(client)
    else:
        print("  Already has data, skipping")

    # Step 3: Seed skills table
    print("\n[3/4] Seeding skills table...")
    if not state["skills_has_data"]:
        seed_skills_table(client)
    else:
        print("  Already has data, skipping")

    # Step 4: Print DDL instructions for manual apply
    print("\n[4/4] Checking DDL requirements...")
    needs_ddl = not state["find_fuzzy_duplicates_exists"]
    if needs_ddl:
        print_ddl_instructions()
    else:
        print("  All DDL already applied")

    # Final verification
    print("\n[VERIFY] Re-checking database state...")
    check_and_report(client)

    print("\nDone!")


if __name__ == "__main__":
    main()
