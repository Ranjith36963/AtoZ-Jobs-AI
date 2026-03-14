-- Migration 015: find_fuzzy_duplicates SQL function (SPEC §4.2)
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
