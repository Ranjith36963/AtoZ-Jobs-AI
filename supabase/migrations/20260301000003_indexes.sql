-- Migration 003: Indexes

-- Vector search: HNSW with cosine distance
CREATE INDEX idx_jobs_embedding ON jobs
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Query-time: SET LOCAL hnsw.ef_search = 60;

-- Full-text search: GIN on generated tsvector
CREATE INDEX idx_jobs_search_vector ON jobs USING gin(search_vector);

-- Fuzzy text: GIN trigram on title (for dedup + autocomplete)
CREATE INDEX idx_jobs_title_trgm ON jobs USING gin(title gin_trgm_ops);

-- Geospatial: GIST on geography column
CREATE INDEX idx_jobs_location ON jobs USING gist(location);

-- B-tree filters (used in search_jobs pre-filter CTE)
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_salary ON jobs(salary_annual_max) WHERE salary_annual_max IS NOT NULL;
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_jobs_date_posted ON jobs(date_posted DESC);
CREATE INDEX idx_jobs_source_external ON jobs(source_id, external_id);
-- Note: UNIQUE constraint already creates this, but explicit for clarity

-- Autovacuum tuning (HNSW death spiral prevention)
ALTER TABLE jobs SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_vacuum_cost_delay = 2,
    autovacuum_vacuum_threshold = 100,
    autovacuum_analyze_scale_factor = 0.005
);
