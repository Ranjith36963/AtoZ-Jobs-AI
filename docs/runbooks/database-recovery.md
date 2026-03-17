# Database Recovery Runbook

How to recover from migration failures, data issues, and database problems.

---

## Single Migration Rollback

Every migration has a corresponding `_down.sql` file.

```bash
# Example: Roll back migration 019 (search facets)
psql $DATABASE_URL -f supabase/migrations/20260301000019_search_facets_down.sql

# Example: Roll back migration 018 (AI audit log)
psql $DATABASE_URL -f supabase/migrations/20260301000018_ai_audit_log_down.sql
```

**Impact of rolling back Phase 3 migrations:**
- Migration 019 (search facets): Filter sidebar shows empty counts. Search still works.
- Migration 018 (AI audit log): Audit logging stops. Search and explanations still work.

**Impact of rolling back Phase 2 migrations:**
- Migrations 010-017: Skills, dedup, salary prediction, user profiles stop working. `search_jobs_v2()` may fail. `search_jobs()` (Phase 1) still works.

**Impact of rolling back Phase 1 migrations:**
- Migrations 001-009: Database returns to empty state. Full data loss (unless restored from backup).

## Full Migration Chain Reset (Local Only)

```bash
# Drops all tables and re-applies all 19 migrations from scratch
just reset

# Verify
just health
```

**Never run `just reset` on production.** Use individual rollbacks or PITR instead.

## Supabase Point-in-Time Recovery (PITR)

For catastrophic failures where individual rollbacks are insufficient.

1. Go to Supabase Dashboard → Database → Backups
2. Select "Point in Time Recovery"
3. Choose a timestamp **before** the problematic migration was applied
4. Restore creates a new database branch — verify before switching

**RTO:** < 4 hours
**RPO:** Depends on PITR granularity (Supabase Pro: continuous)

## Common Scenarios

### Failed Migration (syntax error)

```bash
# 1. Fix the SQL file
# 2. Roll back the partial migration if needed
psql $DATABASE_URL -f supabase/migrations/XXXXXX_description_down.sql

# 3. Re-apply
supabase db push
```

### Corrupted Materialized View

```bash
# Drop and recreate
psql $DATABASE_URL -c "DROP MATERIALIZED VIEW IF EXISTS mv_search_facets;"
psql $DATABASE_URL -f supabase/migrations/20260301000019_search_facets.sql

# Or just refresh
psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_facets;"
```

### RLS Policy Missing (security issue)

```bash
# 1. Verify RLS is enabled
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# 2. If a table has rowsecurity = false:
psql $DATABASE_URL -c "ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;"

# 3. Add appropriate policy (see supabase/CLAUDE.md for patterns)
```

### Index Corruption or Missing

```bash
# Rebuild HNSW index (may take several minutes on large tables)
psql $DATABASE_URL -c "REINDEX INDEX CONCURRENTLY idx_jobs_embedding;"

# Rebuild GIN index
psql $DATABASE_URL -c "REINDEX INDEX CONCURRENTLY idx_jobs_search_vector;"

# Verify indexes exist
psql $DATABASE_URL -c "SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;"
```

### Queue Stuck (pgmq)

```bash
# Check queue status
psql $DATABASE_URL -c "SELECT * FROM pgmq.metrics();"

# Purge a queue (DESTRUCTIVE — messages are lost)
psql $DATABASE_URL -c "SELECT pgmq.purge('queue_name');"

# Delete and recreate a queue
psql $DATABASE_URL -c "SELECT pgmq.drop_queue('queue_name');"
psql $DATABASE_URL -c "SELECT pgmq.create('queue_name');"
```

### VACUUM / ANALYZE

```bash
# If queries are slow after bulk operations
psql $DATABASE_URL -c "VACUUM ANALYZE jobs;"
psql $DATABASE_URL -c "VACUUM ANALYZE skills;"
psql $DATABASE_URL -c "VACUUM ANALYZE job_skills;"
```

## Verification After Recovery

```bash
# 1. Check all tables exist
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"

# 2. Check RLS enabled on all tables
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# 3. Check pipeline health
just health

# 4. Test search
psql $DATABASE_URL -c "SELECT COUNT(*) FROM search_jobs_v2(query_text := 'developer');"

# 5. Check materialized views
psql $DATABASE_URL -c "SELECT * FROM mv_search_facets LIMIT 5;"
```

## References

- `supabase/CLAUDE.md` — Migration conventions and index types
- `docs/phase-1/GATES.md §4` — Phase 1 rollback procedures
- `docs/phase-2/GATES.md §4` — Phase 2 rollback procedures
- `docs/phase-3/GATES.md §4` — Phase 3 rollback procedures
