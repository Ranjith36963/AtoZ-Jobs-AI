SELECT cron.unschedule('refresh-search-facets');
SELECT cron.unschedule('refresh-salary-histogram');
DROP MATERIALIZED VIEW IF EXISTS mv_salary_histogram;
DROP MATERIALIZED VIEW IF EXISTS mv_search_facets;
