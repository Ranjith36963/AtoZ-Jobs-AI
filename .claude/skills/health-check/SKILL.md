---
name: health-check
description: >
  Invoke after deployments, when investigating issues, before declaring
  a phase complete, or when asked to check system health.
  Runs database, pipeline, web, and search health checks.
invoke: auto
---

# Health Check Skill

Run a comprehensive health check across all AtoZ Jobs AI components.

## When to Use

- After deployments
- When investigating issues
- Before declaring a phase complete
- During routine monitoring

## Checks

### 1. Database Health

```bash
# Pipeline health view (queue depths, status counts)
just health

# Migration status (all 19 should be applied)
supabase db remote commit

# RLS verification (all tables should have rowsecurity = true)
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"

# Materialized view freshness
psql $DATABASE_URL -c "SELECT schemaname, matviewname FROM pg_matviews WHERE schemaname = 'public';"

# Queue depths
psql $DATABASE_URL -c "SELECT * FROM pgmq.metrics();"

# Job status distribution
psql $DATABASE_URL -c "SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC;"
```

### 2. Pipeline Health

```bash
# Run pipeline tests
cd pipeline && uv run pytest -x

# Type check
cd pipeline && uv run mypy src/

# Lint
cd pipeline && uv run ruff check .

# Check Modal function status (requires Modal CLI)
modal app list
```

### 3. Web Health

```bash
# Run tests
cd web && pnpm test

# Type check
cd web && pnpm typecheck

# Lint
cd web && pnpm lint

# Production build
cd web && pnpm build

# Bundle size check (main JS < 200KB gzipped, worker < 3 MiB)
# Check output of pnpm build for sizes
```

### 4. Search Verification

```bash
# Test search_jobs (Phase 1)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM search_jobs(query_text := 'developer', match_limit := 5);"

# Test search_jobs_v2 (Phase 2)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM search_jobs_v2(query_text := 'developer', match_limit := 5);"

# Check HNSW index is used
psql $DATABASE_URL -c "EXPLAIN SELECT * FROM search_jobs_v2(query_text := 'developer');"
```

### 5. External Services

| Service | Check | Expected |
|---------|-------|----------|
| Supabase | `just health` | Returns rows |
| Modal | Modal dashboard | Functions scheduled |
| Cloudflare | Load production URL | Page renders |
| Sentry | Check dashboard | No spike in errors |
| PostHog | Check dashboard | Events flowing |

## Quick One-Liner

```bash
just health && cd pipeline && uv run pytest -x && cd ../web && pnpm test && pnpm typecheck && pnpm build
```

## Related

- `DEPENDENCIES.md` — External service details and rate limits
- `docs/runbooks/incident-response.md` — What to do when checks fail
- `docs/runbooks/database-recovery.md` — Database-specific recovery
