-- Migration 010: Skills Taxonomy Tables (Phase 2, Stage 1)
-- Populates the skills table with ESCO taxonomy data
-- skills table already exists from Phase 1 Migration 002

CREATE TABLE esco_skills (
    concept_uri     TEXT PRIMARY KEY,
    preferred_label TEXT NOT NULL,
    alt_labels      TEXT[],
    skill_type      TEXT,           -- 'skill/competence', 'knowledge'
    description     TEXT,
    isco_group      TEXT            -- ISCO-08 group code for occupation mapping
);

-- Index for text search on skill names (autocomplete + fuzzy match)
CREATE INDEX idx_esco_skills_label_trgm ON esco_skills USING gin(preferred_label gin_trgm_ops);

-- Add additional columns for Phase 2 enrichment
ALTER TABLE skills ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'esco';
ALTER TABLE skills ADD COLUMN IF NOT EXISTS aliases TEXT[];

-- Materialized view: top skills by demand
CREATE MATERIALIZED VIEW mv_skill_demand AS
SELECT
    s.id,
    s.name,
    s.skill_type,
    s.esco_uri,
    COUNT(js.job_id) AS job_count,
    COUNT(js.job_id) FILTER (WHERE j.date_posted > NOW() - INTERVAL '30 days') AS jobs_last_30d,
    COUNT(js.job_id) FILTER (WHERE j.date_posted > NOW() - INTERVAL '7 days') AS jobs_last_7d,
    ROUND(AVG(j.salary_annual_max) FILTER (WHERE j.salary_annual_max IS NOT NULL), 0) AS avg_salary,
    ARRAY_AGG(DISTINCT j.location_region) FILTER (WHERE j.location_region IS NOT NULL) AS top_regions
FROM skills s
JOIN job_skills js ON js.skill_id = s.id
JOIN jobs j ON j.id = js.job_id AND j.status = 'ready'
GROUP BY s.id, s.name, s.skill_type, s.esco_uri
ORDER BY job_count DESC;

CREATE UNIQUE INDEX idx_mv_skill_demand_id ON mv_skill_demand(id);

-- Materialized view: skill co-occurrence (which skills appear together)
CREATE MATERIALIZED VIEW mv_skill_cooccurrence AS
SELECT
    js1.skill_id AS skill_a,
    js2.skill_id AS skill_b,
    COUNT(*) AS cooccurrence_count
FROM job_skills js1
JOIN job_skills js2 ON js1.job_id = js2.job_id AND js1.skill_id < js2.skill_id
GROUP BY js1.skill_id, js2.skill_id
HAVING COUNT(*) >= 10
ORDER BY cooccurrence_count DESC;

CREATE INDEX idx_mv_skill_cooccurrence_a ON mv_skill_cooccurrence(skill_a);
CREATE INDEX idx_mv_skill_cooccurrence_b ON mv_skill_cooccurrence(skill_b);

-- Schedule materialized view refresh (daily at 3 AM)
SELECT cron.schedule('refresh-skill-demand', '0 3 * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_demand$$);
SELECT cron.schedule('refresh-skill-cooccurrence', '0 3 * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_cooccurrence$$);
