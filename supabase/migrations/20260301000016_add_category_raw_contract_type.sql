-- Migration 016: Add category_raw and contract_type columns to jobs table
-- These fields are populated by all collectors (Reed, Adzuna, free APIs)
-- but were missing from the schema, causing PostgREST PGRST204 errors on upsert.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category_raw TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS contract_type TEXT;
