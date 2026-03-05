-- Migration 001: Extensions
-- Enable required PostgreSQL extensions

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector: halfvec(768), HNSW
CREATE EXTENSION IF NOT EXISTS postgis;     -- PostGIS: geography(POINT, 4326), ST_DWithin
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- Trigram: fuzzy text matching, GIN indexes
CREATE EXTENSION IF NOT EXISTS pgmq;       -- pgmq: lightweight message queues
CREATE EXTENSION IF NOT EXISTS pg_cron;     -- pg_cron: scheduled jobs
