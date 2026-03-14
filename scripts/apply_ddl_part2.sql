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
    tgt2.id AS candidate_id,
    similarity(tgt1.title, tgt2.title)::FLOAT AS title_sim,
    similarity(tgt1.company_name, tgt2.company_name)::FLOAT AS company_sim,
    COALESCE(
        ST_Distance(tgt1.location::geography, tgt2.location::geography) / 1000.0,
        0
    )::FLOAT AS distance_km,
    compute_duplicate_score(
        similarity(tgt1.title, tgt2.title),
        similarity(tgt1.company_name, tgt2.company_name) > 0.5,
        COALESCE(
            ST_Distance(tgt1.location::geography, tgt2.location::geography) / 1000.0,
            0
        ),
        CASE
            WHEN tgt1.salary_annual_max IS NOT NULL AND tgt2.salary_annual_max IS NOT NULL
            THEN 1.0 - ABS(tgt1.salary_annual_max - tgt2.salary_annual_max)
                / GREATEST(tgt1.salary_annual_max, tgt2.salary_annual_max, 1)
            ELSE 0.0
        END,
        COALESCE(
            ABS(EXTRACT(EPOCH FROM tgt1.date_posted - tgt2.date_posted) / 86400)::INT,
            30
        )
    )::FLOAT AS dup_score
FROM jobs tgt1, jobs tgt2
WHERE tgt1.id = target_job_id
  AND tgt2.id != tgt1.id
  AND tgt2.status = 'ready'
  AND tgt2.is_duplicate IS NOT TRUE
  AND tgt1.title % tgt2.title
  AND similarity(tgt1.title, tgt2.title) >= 0.6
ORDER BY dup_score DESC
LIMIT 10;
$$;
