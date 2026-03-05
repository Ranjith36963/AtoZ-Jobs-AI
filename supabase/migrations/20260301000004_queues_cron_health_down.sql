-- Rollback Migration 004: Queues, Cron, and Health View

DROP VIEW IF EXISTS pipeline_health;

SELECT cron.unschedule('expire-stale-jobs');
SELECT cron.unschedule('reindex-hnsw-monthly');

DROP TRIGGER IF EXISTS after_job_insert ON jobs;
DROP FUNCTION IF EXISTS enqueue_for_parsing();

SELECT pgmq.drop_queue('dead_letter_queue');
SELECT pgmq.drop_queue('embed_queue');
SELECT pgmq.drop_queue('geocode_queue');
SELECT pgmq.drop_queue('dedup_queue');
SELECT pgmq.drop_queue('normalize_queue');
SELECT pgmq.drop_queue('parse_queue');
