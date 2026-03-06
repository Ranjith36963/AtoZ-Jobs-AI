-- Rollback Migration 003: Indexes

-- Reset autovacuum to defaults
ALTER TABLE jobs RESET (
    autovacuum_vacuum_scale_factor,
    autovacuum_vacuum_cost_delay,
    autovacuum_vacuum_threshold,
    autovacuum_analyze_scale_factor
);

DROP INDEX IF EXISTS idx_jobs_source_external;
DROP INDEX IF EXISTS idx_jobs_date_posted;
DROP INDEX IF EXISTS idx_jobs_category;
DROP INDEX IF EXISTS idx_jobs_salary;
DROP INDEX IF EXISTS idx_jobs_status;
DROP INDEX IF EXISTS idx_jobs_location;
DROP INDEX IF EXISTS idx_jobs_title_trgm;
DROP INDEX IF EXISTS idx_jobs_search_vector;
DROP INDEX IF EXISTS idx_jobs_embedding;
