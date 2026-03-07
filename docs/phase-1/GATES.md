# AtoZ Jobs AI — Phase 1 Quality Gates

**How to verify it works. Pass/fail criteria for every stage.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and PLAYBOOK.md (how).

---

## 1. Stage Gates — Pass/Fail Criteria

### 1.1 Gate 1: Foundation (Week 1)

Run these checks before completing Stage 1 (Foundation) on `data-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| F1 | Migration chain | `supabase db reset` | Completes with zero errors. All 5 migrations applied in order. |
| F2 | Rollback chain | Run each `down.sql` in reverse, then `supabase db reset` again | Each down.sql succeeds. Full up chain still succeeds after. |
| F3 | Tables exist | `\dt` in psql | 5 tables: `sources`, `companies`, `jobs`, `skills`, `job_skills` |
| F4 | Column types | `\d jobs` | All 40+ columns with correct types. `embedding HALFVEC(768)`. `location GEOGRAPHY(POINT,4326)`. `employment_type TEXT[]`. `search_vector TSVECTOR` (generated). |
| F5 | Constraints | Insert duplicate `(source_id, external_id)` | Raises unique violation error. |
| F6 | Indexes | `\di` | HNSW (`idx_jobs_embedding`), GIN×2 (`idx_jobs_search_vector`, `idx_jobs_title_trgm`), GIST (`idx_jobs_location`), B-tree×5 (status, salary, category, date_posted, source_external). |
| F7 | Queues operational | `SELECT pgmq.send('parse_queue', '{"test": true}')` | Returns message ID for all 6 queues: `parse_queue`, `normalize_queue`, `dedup_queue`, `geocode_queue`, `embed_queue`, `dead_letter_queue`. |
| F8 | Cron jobs | `SELECT * FROM cron.job` | 3 jobs: `reindex-hnsw-monthly`, `expire-stale-jobs`, and at least 1 fetch schedule. |
| F9 | pipeline_health view | `SELECT * FROM pipeline_health` | Returns 1 row with 14 columns. All counts = 0 on empty DB. `db_size_bytes > 0`. |
| F10 | RLS enforced | Connect as anon role, `SELECT count(*) FROM jobs WHERE status = 'raw'` | Returns 0 rows (even after inserting a raw job via service_role). |
| F11 | RLS allows ready | Insert a `status='ready'` job via service_role, query as anon | Returns 1 row. |
| F12 | Seed data | `just seed` (Tier 1) | 4 sources inserted. All `is_active = true`. |
| F13 | Autovacuum | `SELECT reloptions FROM pg_class WHERE relname = 'jobs'` | Contains `autovacuum_vacuum_scale_factor=0.01`. |

**FAIL gate:** Any item fails → fix before merge. No exceptions.

### 1.2 Gate 2: Collection (Week 2)

Run these checks before completing Stage 2 (Collection) on `data-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| C1 | Reed adapter | `uv run pytest tests/test_reed.py` | Maps mock JSON fixture to `JobBase` with zero validation errors. Tests pagination (`resultsToSkip`), `totalResults` boundary, HTML stripping. |
| C2 | Adzuna adapter | `uv run pytest tests/test_adzuna.py` | Extracts `latitude`/`longitude` directly. Maps `salary_is_predicted`. Category tag → internal mapping. |
| C3 | Jooble adapter | `uv run pytest tests/test_jooble.py` | Paginates until empty results array. Handles no `totalResults` field. |
| C4 | Careerjet adapter | `uv run pytest tests/test_careerjet.py` | Passes `user_ip` and `user_agent` in v4 format. Structured salary fields extracted. |
| C5 | Circuit breaker | `uv run pytest tests/test_circuit_breaker.py` | 3 consecutive 500s → OPEN. After 300s → HALF_OPEN. 1 success → CLOSED. 429 does NOT trip breaker. |
| C6 | Rate limit handler | `uv run pytest tests/test_rate_limit.py` | 429 response → reads `Retry-After` header → sleeps → retries. Max 3 retries → raises `MaxRetriesExceeded`. |
| C7 | Content hash | `uv run pytest tests/test_content_hash.py` | `SHA-256(lowercase(title) + normalize(company) + normalize(location))`. Identical inputs → identical hashes. Different inputs → different hashes. |
| C8 | UPSERT idempotency | Insert same `(source_id, external_id)` twice | First insert succeeds. Second updates `date_crawled`, no duplicate row created. |
| C9 | Schema validation | Feed malformed JSON (null title, missing external_id) | `ValidationError` raised. Job not inserted. |
| C10 | Edge cases | Empty results, timeout, malformed JSON, pagination boundary (exactly 100 results) | All handled without crash. Logged via structlog. |
| C11 | Coverage | `uv run pytest --cov=src/collectors --cov-fail-under=85` | ≥85% line coverage on collectors/. |
| C12 | Modal deploy | `cd pipeline && modal run src/modal_app.py::fetch_reed` | Fetches ≥1 page of jobs from Reed API. Jobs appear in DB with `status='raw'`. |
| C13 | Pipeline health | `SELECT jobs_ingested_last_hour FROM pipeline_health` | > 0 after first collection run. |

**FAIL gate:** C1–C9 are hard failures. C10–C13 are soft (can fix in processing stage if needed, but should pass).

### 1.3 Gate 3: Processing (Week 3)

Run these checks before completing Stage 3 (Processing) on `data-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| P1 | Salary: all 12 patterns | `uv run pytest tests/test_salary.py` | Each of the 12 patterns from SPEC.md §3.3 produces correct `salary_annual_min`/`salary_annual_max`. Day rate × 252. Hourly × 1950. Monthly × 12. |
| P2 | Salary: sanity check | Feed `salary_annual = 5000` and `salary_annual = 600000` | Both rejected (set to NULL). Only 10,000–500,000 accepted. |
| P3 | Salary: API fields priority | Reed job with `minimumSalary=30000` and `salary_raw='£25k-£35k'` | Uses API field (30000), not regex parse. |
| P4 | Salary: property test | `@given(st.text())` via Hypothesis | Salary parser never raises unhandled exception on arbitrary input. |
| P5 | Location: 8 cases | `uv run pytest tests/test_location.py` | All 8 location patterns from SPEC.md §3.4 resolve correctly: London → Central London coords, Remote → `location_type='remote'` + no geometry, etc. |
| P6 | Location: geocoding priority | Adzuna job with lat/lon provided | Uses Adzuna coordinates directly. Does NOT call postcodes.io. |
| P7 | Location: postcodes.io | Job with postcode `SW1A 1AA` | Returns correct lat/lon from postcodes.io bulk endpoint. |
| P8 | Location: fallback | Job with city `Manchester` and no postcode | Falls back to pre-populated city table. Returns Manchester coords (53.4808, -2.2426). |
| P9 | Category: Reed mapping | All Reed sectors from SPEC.md §3.5 | Each maps to correct internal category. `IT & Telecoms` → `Technology`. |
| P10 | Category: Adzuna mapping | All Adzuna tags | `it-jobs` → `Technology`. `healthcare-nursing-jobs` → `Healthcare`. |
| P11 | Category: keyword inference | Jooble job titled `Senior Python Developer` | Inferred as `Technology` via keyword `developer`. |
| P12 | Category: fallback | Job title `Office Assistant` (no keyword match) | Falls back to `Other`. |
| P13 | Seniority extraction | `uv run pytest tests/test_seniority.py` | `Senior Python Developer` → `Senior`. `Data Analyst` → `Not specified`. `CTO` → `Executive`. `Graduate Trainee` → `Junior`. |
| P14 | Structured summary | `uv run pytest tests/test_summary.py` | Generates 6-field template. No Summary or Requirements field. All fields populated from rule-based extraction. |
| P15 | Skill extraction | `uv run pytest tests/test_skills.py` | `Python developer with AWS experience` → at least `['Python', 'AWS']`. Max 15 skills. `confidence = 1.0` for exact matches. |
| P16 | Embeddings: Gemini | `uv run pytest tests/test_embeddings.py` | Returns 768-dimensional vector. `np.linalg.norm(vec) ≈ 1.0` (re-normalized). |
| P17 | Embeddings: fallback | Mock Gemini failure → automatic fallback | Switches to OpenAI `text-embedding-3-small`. Returns same 768 dimensions. |
| P18 | Dedup: hash match | Two jobs with identical title+company+location | Same `content_hash`. Second is skipped silently (`DuplicateError`, no retry). |
| P19 | Dedup: UPSERT | Job with changed `content_hash` | Updates fields. Status resets to `parsed` for reprocessing. |
| P20 | Queue runner | `uv run pytest tests/test_queue_runner.py` | Full flow: raw → parsed → normalized → dedup gate → geocoded → embedded → ready. |
| P21 | DLQ routing | Job fails geocoding 3 times | `retry_count = 3`. Job enters `dead_letter_queue`. |
| P22 | Coverage: processing | `uv run pytest --cov=src/processing --cov-fail-under=90` | ≥90% line coverage on processing/. |
| P23 | Coverage: embeddings | `uv run pytest --cov=src/embeddings --cov-fail-under=85` | ≥85% line coverage on embeddings/. |
| P24 | Pipeline health | `SELECT ready_without_embedding FROM pipeline_health` | = 0 after processing completes. |

**FAIL gate:** P1–P21 are hard failures. P22–P24 are soft but expected to pass.

### 1.4 Gate 4: Maintenance + Verification (Week 4)

Run these checks before completing Stage 4 (Maintenance) on `data-phase`. Final: squash-merge `data-phase` → `main`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| M1 | Expiry: Reed | Insert Reed job with past `expirationDate` | `status = 'expired'` after expiry cron runs. |
| M2 | Expiry: Adzuna default | Insert Adzuna job, `date_posted` = 46 days ago, no `date_expires` | `status = 'expired'` after expiry cron (45-day default). |
| M3 | Expiry: Jooble/Careerjet | Insert Jooble job, `date_posted` = 31 days ago | `status = 'expired'` after expiry cron (30-day default). |
| M4 | Re-verification | Job disappears from API for 2 consecutive fetch cycles | Marked `status = 'expired'`. |
| M5 | Archival | Expired job older than 90 days | `status = 'archived'` after expiry cron. |
| M6 | Hard delete | Insert archived job with `date_crawled` > 180 days ago, run cleanup | Job deleted (CASCADE removes job_skills entries). |
| M7 | DLQ auto-retry | Job in DLQ for > 6 hours with `retry_count < 5` | Re-enqueued to original queue based on `failed_stage`. |
| M8 | DLQ exhausted | Job in DLQ with `retry_count = 5` | Stays in DLQ. NOT re-enqueued. |
| M9 | Health alerts | `jobs_ingested_last_hour = 0` | Alert logged (structlog CRITICAL level). |
| M10 | search_jobs() | Run all 10 test queries from §2 below | All return results or handle gracefully. Zero SQL errors. |
| M11 | E2E pipeline | `fetch → process → embed → search` on 100 real jobs | ≥50 jobs reach `status = 'ready'`. `search_jobs()` returns results. |
| M12 | Performance | `EXPLAIN ANALYZE` on Q1 from §2 | Execution time < 50ms on seeded data. HNSW index scan visible in plan. |
| M13 | Coverage: total | `uv run pytest --cov=src --cov-fail-under=80` | ≥80% line coverage across entire pipeline. |
| M14 | Lint + types | `uv run ruff check . && uv run mypy src/` | Zero errors. |

**FAIL gate:** All 14 items are hard failures. Phase 1 is not complete until every item passes.

---

## 2. Test Search Queries

These 10 queries exercise every parameter of `search_jobs()`. Run against local DB seeded with Tier 2 data (1K+ synthetic jobs) or after first real collection run.

### Query Reference

| # | Description | Parameters | Expected behaviour |
|---|---|---|---|
| Q1 | Keyword + geo + semantic | `query_text='Python developer'`, `query_embedding=<embed('Python developer')>`, `search_lat=51.5074`, `search_lng=-0.1278`, `radius_miles=25` | Both FTS and semantic CTEs fire. RRF combines rankings. Returns Python/software jobs within 25mi of Central London. |
| Q2 | Remote only | `query_text='nurse'`, `include_remote=true`, `work_type_filter` excludes onsite | Returns nursing/healthcare jobs flagged as `remote` or `nationwide`. No geo filter applied. |
| Q3 | Semantic only | `query_embedding=<embed('machine learning engineer')>` (no `query_text`) | Only semantic CTE fires. FTS CTE returns empty. RRF degrades to semantic-only ranking. |
| Q4 | FTS only | `query_text='solicitor'` (no `query_embedding`) | Only FTS CTE fires. Semantic CTE returns empty. RRF degrades to FTS-only ranking. |
| Q5 | Geo + salary filter | `query_text='data analyst'`, `search_lat=53.4808`, `search_lng=-2.2426`, `min_salary=40000` | Returns data/analytics jobs near Manchester with `salary_annual_max >= 40000`. Tests salary filter + geo filter combined. |
| Q6 | Work type filter | `query_text='teacher'`, `search_lat=52.4862`, `search_lng=-1.8904`, `work_type_filter='hybrid'` | Only hybrid education jobs near Birmingham. Tests `work_type_filter` parameter. |
| Q7 | Empty search | All defaults (no text, no embedding, no geo) | Returns 0 results or empty set. No crash. No SQL error. Tests null-parameter handling. |
| Q8 | Keyword, no location | `query_text='chef'` (no lat/lng) | No geo filter applied. Returns chef/hospitality jobs from all locations. Tests that missing lat/lng skips ST_DWithin. |
| Q9 | Custom match_count | `query_text='senior software engineer'`, `query_embedding=<embed(...)>`, `match_count=5` | Returns exactly 5 results. Tests LIMIT propagation through both CTEs. |
| Q10 | All filters combined | `query_text='accountant'`, `query_embedding=<embed('accountant')>`, `search_lat=55.9533`, `search_lng=-3.1883`, `radius_miles=50`, `min_salary=50000`, `include_remote=false` | Onsite/hybrid accountant jobs within 50mi of Edinburgh, salary ≥£50k. Remote/nationwide excluded. Tests all filter parameters simultaneously. |

### Parameter Coverage Matrix

| Parameter | Exercised in queries |
|---|---|
| `query_text` | Q1, Q2, Q4, Q5, Q6, Q8, Q9, Q10 |
| `query_embedding` | Q1, Q3, Q5, Q9, Q10 |
| `search_lat` / `search_lng` | Q1, Q5, Q6, Q10 |
| `radius_miles` | Q1 (default 25), Q10 (explicit 50) |
| `include_remote` | Q2 (true), Q10 (false) |
| `min_salary` | Q5, Q10 |
| `work_type_filter` | Q6 |
| `match_count` | Q9 (explicit 5), all others (default 20) |
| `rrf_k` | All (default 50) |
| Null parameters | Q7 (all null), Q3 (no text), Q4 (no embedding), Q8 (no geo) |
| Single-CTE degradation | Q3 (semantic only), Q4 (FTS only) |

### Test Execution SQL

```sql
-- Q1: Python developer in London (FTS only — embedding requires app code)
SELECT * FROM search_jobs(
    query_text := 'Python developer',
    search_lat := 51.5074,
    search_lng := -0.1278,
    radius_miles := 25
);

-- Q4: FTS-only solicitor
SELECT * FROM search_jobs(query_text := 'solicitor');

-- Q7: Empty search (should return 0 rows, no error)
SELECT * FROM search_jobs();

-- Q8: Chef, no location
SELECT * FROM search_jobs(query_text := 'chef');

-- Q10: All filters (FTS only — embedding requires app code)
SELECT * FROM search_jobs(
    query_text := 'accountant',
    search_lat := 55.9533,
    search_lng := -3.1883,
    radius_miles := 50,
    min_salary := 50000,
    include_remote := false
);
```

**Note:** Queries using `query_embedding` (Q1, Q3, Q5, Q9, Q10) require generating an embedding via the application code first. For pure SQL testing, use FTS-only variants. For full hybrid testing, use the Python test harness.

---

## 3. Go/No-Go Production Checklist

Every item must pass before deploying Phase 1 to production. Execute in order.

### 3.1 Pre-Deployment (Local Verification)

| # | Check | Command / SQL | Pass criteria | Source doc |
|---|---|---|---|---|
| G1 | Full migration chain | `supabase db reset` | Zero errors. All migrations applied. | Doc 6, Gap 4 |
| G2 | All rollbacks work | Run each `down.sql` in reverse order, then `supabase db reset` | Each down.sql succeeds. Full chain re-applies cleanly. | Doc 6, Gap 4 |
| G3 | Pipeline test coverage | `uv run pytest --cov=src --cov-fail-under=80` | ≥80% line coverage. 0 test failures. | Doc 6, Gap 3 |
| G4 | Linting + type checks | `uv run ruff check . && uv run mypy src/` | Zero errors on both. | Doc 6, Gap 10 |
| G5 | Seed data loads | `just seed` (Tier 1 + Tier 2) | 4 sources + 1K+ synthetic jobs inserted. | Doc 6, Gap 5 |
| G6 | search_jobs() works | Run Q1, Q4, Q7, Q8 from §2 against seeded DB | Q1 returns results. Q4 returns results. Q7 returns 0 rows (no crash). Q8 returns results. | Composed from Doc 1 |
| G7 | pipeline_health view | `SELECT * FROM pipeline_health` | 14 columns returned. `total_ready > 0`. `ready_without_embedding = 0`. | Doc 5 |
| G8 | RLS verified | Query with anon key: `SELECT count(*) FROM jobs WHERE status = 'raw'` | Returns 0 rows. Query `WHERE status = 'ready'` returns > 0. | Doc 6, Gap 11 |
| G9 | Performance baseline | `EXPLAIN ANALYZE SELECT * FROM search_jobs(query_text := 'developer')` | P95 < 50ms. HNSW or GIN index scan visible in plan. | Doc 6, Gap 17 |

### 3.2 Production Deployment

| # | Step | Command | Verification | Source doc |
|---|---|---|---|---|
| G10 | Push migrations | `supabase db push` | No errors. `\dt` shows all 5 tables. | Doc 4 |
| G11 | Deploy Modal | `modal deploy pipeline/src/modal_app.py` | All cron functions visible in Modal dashboard. | Doc 9, Gap 1 |
| G12 | Verify secrets | Check Modal secrets `atoz-env` | All 10 keys present: `REED_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `JOOBLE_API_KEY`, `CAREERJET_AFFID`, `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `SENTRY_DSN`. | Doc 9 |
| G13 | First collection run | `modal run src/modal_app.py::fetch_reed` | ≥1 job inserted into production DB with `status='raw'`. | Doc 5 |
| G14 | Pipeline processes | Wait for `process_queues` cron to fire (or trigger manually) | At least 1 job reaches `status='ready'` with non-null `embedding`. | Doc 5 |
| G15 | Production health | `SELECT * FROM pipeline_health` on production | `jobs_ingested_last_hour > 0`. `ready_without_embedding = 0`. `jobs_in_dlq = 0`. | Doc 5 |
| G16 | Search works | `SELECT * FROM search_jobs(query_text := 'developer')` on production | Returns ≥1 result with `rrf_score > 0`. | Doc 1 |

### 3.3 Post-Deployment Monitoring (First 24 Hours)

| # | Alert condition | Threshold | Action | Source doc |
|---|---|---|---|---|
| G17 | Zero ingestion | `jobs_ingested_last_hour = 0` for 3 consecutive hours | Check Modal logs for errors. Verify API keys still valid. Check circuit breaker state. | Doc 5 |
| G18 | DLQ overflow | `jobs_in_dlq > 100` | Check `last_error` patterns: group by error type. If >5% of a source → investigate source quality. | Doc 5 |
| G19 | Missing embeddings | `ready_without_embedding > 0` | Check `GOOGLE_API_KEY`. Check Gemini API status. Check for 429/RESOURCE_EXHAUSTED in logs. | Doc 5 |
| G20 | Search latency | `search_jobs()` P95 > 100ms | Run `EXPLAIN ANALYZE`. Check HNSW index exists. Check dead tuple ratio (`SELECT n_dead_tup FROM pg_stat_user_tables WHERE relname = 'jobs'`). If > 10%, run `VACUUM ANALYZE jobs`. | Doc 6, Gap 17 |

**Decision point:** If G17–G20 are all clear after 24 hours, Phase 1 is **production-stable**. Tag `v0.1.0` and begin Phase 2 planning.

---

## 4. Rollback Procedures

### 4.1 Migration Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Bad migration (pre-production) | Apply `down.sql` for failed migration locally. Fix. Re-apply. `supabase db reset` must pass. | < 15 min |
| Bad migration (production) | `supabase db push` the corrected migration. If irreversible, restore from PITR. | < 30 min |
| Corrupted data from migration | Restore from Supabase PITR (Dashboard → Settings → Database → Backups). 7-day retention on Pro plan. | < 4 hours |

**Rule:** Every migration has `up.sql` + `down.sql`. Test rollback immediately after writing. Never modify a deployed migration — create a new one instead.

### 4.2 Pipeline Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Pipeline code crash | Pipeline is stateless on Modal. Jobs stay in pgmq queues until processed. Fix code, `modal deploy` again. | < 15 min |
| Bad processing logic (wrong salary parsing, etc.) | Fix code, `modal deploy`. Jobs already processed with bad logic: update `status = 'parsed'` for affected jobs to re-process. `raw_data` JSONB preserves originals. | < 30 min |
| Embedding model issue | Switch to OpenAI fallback. Re-embed affected jobs by setting `embedding = NULL, status = 'geocoded'` to re-enter embed_queue. | < 1 hour |

### 4.3 Infrastructure Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Database corruption | Restore from Supabase PITR via Dashboard. | < 4 hours |
| Modal outage | Pipeline is paused. Jobs accumulate in pgmq queues (durable). Resume when Modal recovers. Zero data loss. | 0 (wait for recovery) |
| Cloudflare Pages outage | Job data persists in Supabase. Re-deploy when CF recovers, or failover to Netlify Free. | < 1 hour |
| Total catastrophe | Supabase backup + Git repo = full reconstruction. | < 4 hours |

### 4.4 Backup & Disaster Recovery Summary

| Metric | Target | How |
|---|---|---|
| RPO (max data loss) | 24 hours | Supabase Pro daily backups (included in plan) |
| RTO (max downtime) | 4 hours | Restore from backup + re-deploy pipeline + re-deploy frontend |
| PITR retention | 7 days | Supabase Pro includes 7-day point-in-time recovery |

**What's NOT covered (acceptable for Phase 1):**

- No multi-region failover (single Supabase project in eu-west-2)
- No real-time replication (not needed until >100K users)
- No automated failover (manual restore is acceptable for solo dev)

---

## 5. Performance SLAs

These targets apply from the moment Phase 1 reaches production.

| # | Metric | Target | Alert threshold | How to measure | When to act |
|---|---|---|---|---|---|
| S1 | `search_jobs()` P95 | < 50ms | > 100ms | `EXPLAIN ANALYZE` + `pg_stat_statements` | Check HNSW index. Check dead tuple ratio. Run `VACUUM ANALYZE`. |
| S2 | Page load (TTFB) | < 200ms | > 500ms | Cloudflare Analytics / Vercel Analytics | Check ISR cache. Check Supabase connection pooler. |
| S3 | API collector per page | < 2s | > 5s | structlog timing in Modal logs | Check API status. Check network from Modal region. |
| S4 | Pipeline throughput | > 500 jobs/hour | < 200 jobs/hour | `pipeline_health` view (delta over time) | Check DLQ depth. Check API rate limits. Check Modal cold starts. |
| S5 | Embedding generation | > 100 jobs/min (batched) | < 50 jobs/min | structlog timing | Check Gemini rate limits (250K TPM). Reduce batch size. |
| S6 | Geocoding (postcodes.io) | < 200ms per batch of 100 | > 500ms | structlog timing | Self-host postcodes.io via Docker if throttled. |
| S7 | HNSW index build (500K) | < 30 min | > 60 min | One-time measurement at scale | Consider reducing `m` or `ef_construction` parameters. |
| S8 | `search_jobs()` with all filters | < 80ms P95 | > 150ms | `pg_stat_statements` | Check filter selectivity. Add partial indexes if needed. |

---

## 6. Migration Rollback Verification

Run this sequence after writing every migration, before committing.

```bash
# Step 1: Verify full up chain
supabase db reset
# Must complete with zero errors

# Step 2: Verify the new migration's down.sql
psql $DATABASE_URL < supabase/migrations/<latest>/down.sql
# Must complete with zero errors

# Step 3: Verify chain still works after rollback
supabase db reset
# Must complete with zero errors again

# Step 4: Verify data integrity after rollback + re-apply
just seed
SELECT * FROM pipeline_health;
# Must return 14 columns, no errors
```

**Migration checklist (per migration):**

| Check | Rule |
|---|---|
| Has `down.sql` | Every `up.sql` has a corresponding `down.sql`. No exceptions. |
| One logical change | Never combine table creation with function creation in same migration. |
| Concurrent indexing | Use `CREATE INDEX CONCURRENTLY` for indexes on tables with data. |
| NULL-first columns | Add columns as `NULL` first → populate → add `NOT NULL` constraint. |
| Never modify deployed | If a migration is in production, create a new migration to change it. |
| CI verification | `supabase db reset` runs in GitHub Actions on every PR. |

---

## 7. Error Taxonomy Quick Reference

For debugging failures caught by the gate checks.

| Error type | Retry? | Max retries | Backoff | Gate impact |
|---|---|---|---|---|
| `ValidationError` | No | 0 | N/A | Job skipped permanently. Log for source quality monitoring. |
| `RateLimitError` | Yes | 3 | `Retry-After` header | Temporary. Wait and retry. |
| `TimeoutError` | Yes | 3 | 2^n seconds | Temporary. Check API health if persistent. |
| `ParseError` | No | 0 | N/A | Alert if >5% of source. Likely API response format change. |
| `EmbeddingError` | Yes | 3 | 2^n seconds | Retry, then cascade to OpenAI fallback. |
| `GeocodingError` | Yes | 2 | 1s fixed | Retry, then fallback to city lookup table. |
| `DuplicateError` | No | 0 | N/A | Skip silently. Expected behaviour for aggregator sources. |

---

## 8. Phase 1 Completion Criteria

Phase 1 is **complete** when ALL of the following are true:

- [ ] All 13 Gate 1 (Foundation) checks pass
- [ ] All 13 Gate 2 (Collection) checks pass
- [ ] All 24 Gate 3 (Processing) checks pass
- [ ] All 14 Gate 4 (Maintenance) checks pass
- [ ] All 10 test search queries execute without error
- [ ] All 16 go/no-go items (G1–G16) pass
- [ ] 24-hour monitoring (G17–G20) shows no critical alerts
- [ ] All 8 performance SLAs meet target thresholds
- [ ] Git tag `v0.1.0` applied to `main` branch
- [ ] `STATUS.md` updated with completion date and metrics

**Total verification items: 64 gate checks + 10 queries + 20 go/no-go items + 8 SLAs = 102 verifiable items.**

When all 102 items pass: **Phase 1 is production-stable. Begin Phase 2 planning.**
