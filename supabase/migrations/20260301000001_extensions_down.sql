-- Rollback Migration 001: Extensions

DROP EXTENSION IF EXISTS pg_trgm;
DROP EXTENSION IF EXISTS postgis;
DROP EXTENSION IF EXISTS vector;
