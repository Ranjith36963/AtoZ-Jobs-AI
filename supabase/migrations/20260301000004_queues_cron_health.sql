-- Migration 004: Queues, Cron, and Health View

-- 5 processing queues + 1 dead letter queue = 6 total
SELECT pgmq.create('parse_queue');
SELECT pgmq.create('normalize_queue');
SELECT pgmq.create('dedup_queue');
SELECT pgmq.create('geocode_queue');
SELECT pgmq.create('embed_queue');
SELECT pgmq.create('dead_letter_queue');

-- Auto-enqueue new jobs for parsing
CREATE OR REPLACE FUNCTION enqueue_for_parsing() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pgmq.send('parse_queue', jsonb_build_object('job_id', NEW.id));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_job_insert AFTER INSERT ON jobs
    FOR EACH ROW WHEN (NEW.status = 'raw')
    EXECUTE FUNCTION enqueue_for_parsing();

-- Monthly HNSW reindex (3 AM on 1st of each month)
SELECT cron.schedule(
    'reindex-hnsw-monthly',
    '0 3 1 * *',
    $$REINDEX INDEX CONCURRENTLY idx_jobs_embedding$$
);

-- Daily expiry (2 AM)
SELECT cron.schedule(
    'expire-stale-jobs',
    '0 2 * * *',
    $$
    UPDATE jobs SET status = 'expired', last_error = 'auto-expired'
    WHERE status = 'ready'
      AND date_expires IS NOT NULL
      AND date_expires < NOW();

    UPDATE jobs SET status = 'expired', last_error = 'default-45d-expired'
    WHERE status = 'ready'
      AND date_expires IS NULL
      AND date_posted < NOW() - INTERVAL '45 days';

    UPDATE jobs SET status = 'archived'
    WHERE status = 'expired'
      AND date_crawled < NOW() - INTERVAL '90 days';
    $$
);

-- Refresh planner statistics every 6 hours for optimal search_jobs() query plans
SELECT cron.schedule(
    'refresh-job-stats',
    '30 */6 * * *',
    $$ANALYZE jobs$$
);

-- Pipeline health monitoring view
CREATE VIEW pipeline_health AS
SELECT
    -- Ingestion metrics
    COUNT(*) FILTER (WHERE date_crawled > NOW() - INTERVAL '1 hour')
        AS jobs_ingested_last_hour,
    COUNT(*) FILTER (WHERE date_crawled > NOW() - INTERVAL '24 hours')
        AS jobs_ingested_last_24h,
    -- Processing metrics
    COUNT(*) FILTER (WHERE status = 'raw')        AS queue_raw,
    COUNT(*) FILTER (WHERE status = 'parsed')      AS queue_parsed,
    COUNT(*) FILTER (WHERE status = 'normalized')  AS queue_normalized,
    COUNT(*) FILTER (WHERE status = 'geocoded')    AS queue_geocoded,
    COUNT(*) FILTER (WHERE status = 'ready')       AS total_ready,
    COUNT(*) FILTER (WHERE status = 'expired')     AS total_expired,
    -- Failure rate
    COUNT(*) FILTER (WHERE retry_count > 0)        AS jobs_with_retries,
    COUNT(*) FILTER (WHERE retry_count >= 3)       AS jobs_in_dlq,
    -- Data quality
    COUNT(*) FILTER (WHERE embedding IS NULL AND status = 'ready')
        AS ready_without_embedding,
    COUNT(*) FILTER (WHERE salary_annual_min IS NULL AND status = 'ready')
        AS ready_without_salary,
    COUNT(*) FILTER (WHERE location IS NULL
        AND location_type != 'remote' AND status = 'ready')
        AS ready_without_location,
    -- Storage
    pg_database_size(current_database()) AS db_size_bytes
FROM jobs;
