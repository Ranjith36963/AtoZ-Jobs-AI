-- AtoZ Jobs AI: Apply missing DDL migrations
-- Run this in the Supabase SQL Editor:
-- https://supabase.com/dashboard/project/uskvwcyimfnienizneih/sql/new
--
-- Missing migrations: 014 (Phase 2 RLS) and 015 (find_fuzzy_duplicates)
-- All other migrations (001-013) are already applied.

-- =============================================
-- Migration 014: Phase 2 RLS Policies
-- =============================================

-- esco_skills: ESCO taxonomy reference table (read-only for public)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'esco_skills' AND policyname = 'Public can read esco_skills'
    ) THEN
        CREATE POLICY "Public can read esco_skills"
            ON esco_skills FOR SELECT USING (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'esco_skills' AND policyname = 'Service role writes esco_skills'
    ) THEN
        CREATE POLICY "Service role writes esco_skills"
            ON esco_skills FOR ALL USING (auth.role() = 'service_role');
    END IF;
END $$;

-- sic_industry_map: SIC code → industry section mapping (read-only for public)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sic_industry_map' AND policyname = 'Public can read sic_industry_map'
    ) THEN
        CREATE POLICY "Public can read sic_industry_map"
            ON sic_industry_map FOR SELECT USING (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sic_industry_map' AND policyname = 'Service role writes sic_industry_map'
    ) THEN
        CREATE POLICY "Service role writes sic_industry_map"
            ON sic_industry_map FOR ALL USING (auth.role() = 'service_role');
    END IF;
END $$;


-- =============================================
-- Migration 015: find_fuzzy_duplicates function
-- =============================================
-- Used by pipeline/src/dedup/fuzzy_matcher.py via db_client.rpc()
-- Depends on: pg_trgm (ext), PostGIS (ext), compute_duplicate_score (migration 011)

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

-- Verify
SELECT 'RLS policies applied' AS status
WHERE EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'esco_skills' AND policyname = 'Public can read esco_skills')
  AND EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'sic_industry_map' AND policyname = 'Public can read sic_industry_map');

SELECT 'find_fuzzy_duplicates created' AS status
WHERE EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'find_fuzzy_duplicates');
