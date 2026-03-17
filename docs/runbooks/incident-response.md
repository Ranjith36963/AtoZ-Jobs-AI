# Incident Response Runbook

What to do when things break. Consolidated from Phase 1–3 GATES.md §4.

---

## Severity Levels

| Level | Definition | Response Time |
|-------|-----------|---------------|
| **P1 — Critical** | Site down, search broken, data loss | Immediate |
| **P2 — High** | Degraded search, missing explanations, stale data | < 1 hour |
| **P3 — Medium** | Single collector failing, slow queries, UI bugs | < 4 hours |
| **P4 — Low** | Monitoring gaps, non-critical alerts | Next business day |

---

## Scenario: Web Site Down

**Symptoms:** 5xx errors, blank page, Cloudflare worker errors.

| Step | Action |
|------|--------|
| 1 | Check Cloudflare Pages dashboard for worker errors |
| 2 | Check Sentry for server-side exceptions |
| 3 | **Rollback:** `wrangler pages deploy --branch=<previous>` or use CF dashboard rollback |
| 4 | If CF Pages outage: deploy to Netlify Free (`netlify deploy`), update DNS CNAME |

**RTO:** < 5 min (CF rollback), < 1 hour (Netlify fallback)

See: Phase 3 GATES.md §4.1 (Code Rollback), §4.3 (Infrastructure Rollback)

---

## Scenario: Search Not Returning Results

**Symptoms:** Empty search results, timeout errors, slow responses.

| Step | Action |
|------|--------|
| 1 | Test directly: `SELECT * FROM search_jobs_v2(query_text := 'developer')` |
| 2 | Check HNSW index: `EXPLAIN ANALYZE` should show Index Scan, not Seq Scan |
| 3 | Check embeddings populated: `SELECT COUNT(*) FROM jobs WHERE embedding IS NOT NULL AND status = 'ready'` |
| 4 | Check Modal `/search` endpoint: is it reachable? Cold start? |
| 5 | **Fallback:** If Modal down, call `search_jobs_v2()` directly from tRPC (skip re-ranking) |
| 6 | Run `VACUUM ANALYZE jobs;` if index performance degraded |

**RTO:** < 15 min

See: Phase 1 GATES.md §7 (Error Taxonomy), Phase 2 GATES.md §6

---

## Scenario: Pipeline Stopped Processing

**Symptoms:** Queue depths growing, DLQ filling up, no new `ready` jobs.

| Step | Action |
|------|--------|
| 1 | Check `SELECT * FROM pipeline_health;` |
| 2 | Check queue depths: `SELECT queue_name, queue_length FROM pgmq.metrics()` |
| 3 | Check DLQ: `SELECT COUNT(*) FROM pgmq.read('dead_letter_queue', 0, 100)` |
| 4 | Check Modal dashboard for cron function failures |
| 5 | Check circuit breaker state — are APIs responding? |
| 6 | **Fix:** If single collector failing, it auto-recovers via circuit breaker (300s). If all failing, check `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` in Modal secrets. |
| 7 | Manual reprocessing: trigger `process_queues` via Modal CLI |

**RTO:** < 15 min (auto-recovery), < 1 hour (manual intervention)

See: Phase 1 GATES.md §4 (Rollback Procedures)

---

## Scenario: AI Explanations Failing

**Symptoms:** No match explanations, fallback text shown, `/api/explain` errors.

| Step | Action |
|------|--------|
| 1 | Check `OPENAI_API_KEY` validity |
| 2 | Check budget guard: `SELECT SUM(cost_usd) FROM ai_decision_audit_log WHERE decision_type = 'match_explanation' AND created_at > date_trunc('month', now())` |
| 3 | If budget exhausted: fallback text is expected behavior. Increase `MONTHLY_SOFT_CAP_USD` or wait for next month. |
| 4 | Check Helicone dashboard for error rates |
| 5 | **Automatic fallback:** OpenAI down → fallback text returned. Search and ranking still work independently. |

**RTO:** 0 (automatic fallback), no user-facing outage

See: Phase 3 SPEC.md §6.1.1 (Budget Enforcement), Phase 3 GATES.md §4.1

---

## Scenario: Database Migration Failure

See `docs/runbooks/database-recovery.md` for detailed procedures.

Quick reference:
- Single migration failure: Run corresponding `_down.sql`
- Phase 3 migrations (018-019): Site still works without them (no audit logging, no facets)
- Catastrophic: Supabase Point-in-Time Recovery (PITR)

---

## Scenario: Stale Data / ISR Cache Issues

**Symptoms:** Old job data showing, facets not updating, salary histogram outdated.

| Step | Action |
|------|--------|
| 1 | Check materialized views: `SELECT schemaname, matviewname FROM pg_matviews` |
| 2 | Manual refresh: `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_facets` |
| 3 | Check pg_cron jobs: `SELECT * FROM cron.job` (should show 30-min refresh schedule) |
| 4 | ISR cache: job detail revalidates every 30 min automatically |
| 5 | Force ISR revalidation: redeploy to CF Pages clears all caches |

---

## Monitoring Dashboards

| Service | What to Check | URL/Access |
|---------|--------------|------------|
| Sentry | Error rates, traces | Sentry dashboard |
| PostHog | Page views, search events | PostHog dashboard |
| Cloudflare | Worker errors, bandwidth, cache hits | CF Pages dashboard |
| Modal | Function logs, cron status | Modal dashboard |
| Helicone | LLM token usage, cost | Helicone dashboard |
| Supabase | DB connections, query performance | Supabase dashboard |

## 24-Hour Post-Deploy Monitoring

After any production deployment, monitor for 24 hours:

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Error rate | < 1% | Sentry |
| Search P95 | < 5s (total) | Sentry Performance |
| ISR cache hits | > 50% | CF Analytics |
| Audit log volume | Growing, no gaps > 1h | SQL query |
| Worker errors | Zero | CF Pages dashboard |
| LLM cost | < $1/day | Helicone |

See: Phase 3 GATES.md §3.4 (24-Hour Monitoring)
