-- Migration 009: Add pipeline processing columns
-- structured_summary: rule-based 6-field job summary (Gate P14)
-- failed_stage: tracks which pipeline stage failed for DLQ routing (Gate M7)

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS structured_summary TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS failed_stage TEXT;
