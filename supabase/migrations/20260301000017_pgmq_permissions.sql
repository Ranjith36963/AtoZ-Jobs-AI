-- Migration 017: Grant pgmq schema permissions to service_role
-- Fixes: 'permission denied for schema pgmq' (error 42501) when
-- the after_job_insert trigger calls pgmq.send() via PostgREST.

GRANT USAGE ON SCHEMA pgmq TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pgmq TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pgmq TO service_role;

-- Ensure future pgmq objects are also accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA pgmq
    GRANT EXECUTE ON FUNCTIONS TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA pgmq
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
