-- Rollback Migration 010: Skills Taxonomy Tables

SELECT cron.unschedule('refresh-skill-demand');
SELECT cron.unschedule('refresh-skill-cooccurrence');
DROP MATERIALIZED VIEW IF EXISTS mv_skill_cooccurrence;
DROP MATERIALIZED VIEW IF EXISTS mv_skill_demand;
ALTER TABLE skills DROP COLUMN IF EXISTS aliases;
ALTER TABLE skills DROP COLUMN IF EXISTS source;
DROP INDEX IF EXISTS idx_esco_skills_label_trgm;
DROP TABLE IF EXISTS esco_skills;
