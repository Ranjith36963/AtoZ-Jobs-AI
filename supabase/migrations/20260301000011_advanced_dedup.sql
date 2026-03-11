-- Migration 011: Advanced Dedup Infrastructure (Phase 2, Stage 2)
-- Adds fuzzy dedup columns and indexes to jobs table

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS canonical_id BIGINT REFERENCES jobs(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_score FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description_hash TEXT;  -- MinHash signature stored as hex

-- GIN trigram indexes for fuzzy matching (title already has one from Phase 1)
CREATE INDEX idx_jobs_company_trgm ON jobs USING gin(company_name gin_trgm_ops);

-- B-tree for canonical_id lookups
CREATE INDEX idx_jobs_canonical ON jobs(canonical_id) WHERE canonical_id IS NOT NULL;

-- Partial index: only non-duplicate ready jobs for search
CREATE INDEX idx_jobs_ready_not_dup ON jobs(status, is_duplicate) WHERE status = 'ready' AND is_duplicate = FALSE;

-- Composite dedup scoring function
CREATE OR REPLACE FUNCTION compute_duplicate_score(
    title_sim FLOAT,         -- pg_trgm similarity on title
    company_match BOOLEAN,   -- exact or fuzzy company match
    location_km FLOAT,       -- distance between locations in km
    salary_overlap FLOAT,    -- 0-1 overlap ratio
    date_diff_days INT       -- days between posting dates
) RETURNS FLOAT
LANGUAGE sql IMMUTABLE AS $$
SELECT
    (title_sim * 0.35) +
    (CASE WHEN company_match THEN 0.25 ELSE 0.0 END) +
    (CASE WHEN location_km <= 5 THEN 0.15 WHEN location_km <= 25 THEN 0.08 ELSE 0.0 END) +
    (salary_overlap * 0.15) +
    (CASE WHEN date_diff_days <= 7 THEN 0.10 WHEN date_diff_days <= 14 THEN 0.05 ELSE 0.0 END);
$$;
