-- Rollback 009: Remove pipeline processing columns

ALTER TABLE jobs DROP COLUMN IF EXISTS failed_stage;
ALTER TABLE jobs DROP COLUMN IF EXISTS structured_summary;
