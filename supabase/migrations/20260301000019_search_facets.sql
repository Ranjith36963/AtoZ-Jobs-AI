-- Facet counts for the filter sidebar (refreshed every 30 minutes)
CREATE MATERIALIZED VIEW mv_search_facets AS
SELECT
    'category' AS facet_type,
    category AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY category

UNION ALL

SELECT
    'location_type' AS facet_type,
    location_type AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY location_type

UNION ALL

SELECT
    'seniority_level' AS facet_type,
    seniority_level AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY seniority_level

UNION ALL

SELECT
    'employment_type' AS facet_type,
    unnest(employment_type) AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY unnest(employment_type);

CREATE UNIQUE INDEX idx_mv_facets_type_value ON mv_search_facets(facet_type, facet_value);

-- Salary histogram for range slider
CREATE MATERIALIZED VIEW mv_salary_histogram AS
SELECT
    width_bucket(
        COALESCE(salary_annual_max, salary_predicted_max),
        10000, 200000, 19
    ) AS bucket,
    COUNT(*) AS job_count,
    MIN(COALESCE(salary_annual_min, salary_predicted_min)) AS bucket_min,
    MAX(COALESCE(salary_annual_max, salary_predicted_max)) AS bucket_max
FROM jobs
WHERE status = 'ready'
  AND (is_duplicate IS NOT TRUE)
  AND COALESCE(salary_annual_max, salary_predicted_max) IS NOT NULL
GROUP BY bucket
ORDER BY bucket;

-- Schedule refreshes (requires pg_cron extension)
SELECT cron.schedule('refresh-search-facets', '*/30 * * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_facets$$);
SELECT cron.schedule('refresh-salary-histogram', '*/30 * * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_salary_histogram$$);
