-- Rollback Migration 011: Advanced Dedup Infrastructure

DROP FUNCTION IF EXISTS compute_duplicate_score;
DROP INDEX IF EXISTS idx_jobs_ready_not_dup;
DROP INDEX IF EXISTS idx_jobs_canonical;
DROP INDEX IF EXISTS idx_jobs_company_trgm;
ALTER TABLE jobs DROP COLUMN IF EXISTS description_hash;
ALTER TABLE jobs DROP COLUMN IF EXISTS duplicate_score;
ALTER TABLE jobs DROP COLUMN IF EXISTS is_duplicate;
ALTER TABLE jobs DROP COLUMN IF EXISTS canonical_id;
