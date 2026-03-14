-- Rollback Migration 016: Remove category_raw and contract_type columns

ALTER TABLE jobs DROP COLUMN IF EXISTS contract_type;
ALTER TABLE jobs DROP COLUMN IF EXISTS category_raw;
