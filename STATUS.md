# AtoZ Jobs AI — Phase 1 Status

**Status:** COMPLETE
**Completion Date:** 2026-03-06
**Tag:** v0.1.0
**Branch:** data-phase → main

---

## Metrics

| Metric | Value |
|---|---|
| Gate checks passed | 100 / 102 |
| Gate checks N/A | 2 (S2 web TTFB, S7 HNSW 500K build) |
| Gate checks failed | 0 |
| Unit tests | 426 passed, 0 failed |
| Total coverage | 89% |
| Collector coverage | 99% |
| Processing coverage | 98% |
| Embedding coverage | 85% |
| Lint (ruff) | 0 errors |
| Type check (mypy) | 0 errors, 52 files |
| Real jobs ingested | 128 (Jooble E2E) |
| search_jobs P95 | 36ms |
| search_jobs all-filters P95 | 34ms |

---

## Gate Scorecard

### Gate 1: Foundation (F1–F13) — 13 PASS

| # | Check | Result | Detail |
|---|---|---|---|
| F1 | Migration chain | PASS | All 9 migrations applied |
| F2 | Rollback chain | PASS | All 9 down.sql files present and tested |
| F3 | Tables exist (5) | PASS | sources, companies, jobs, skills, job_skills |
| F4 | Column types | PASS | HALFVEC(768), GEOGRAPHY(Point,4326), TEXT[], TSVECTOR |
| F5 | UNIQUE constraint | PASS | Insert 201, duplicate 409 |
| F6 | Indexes | PASS | 9 indexes verified via pg_indexes: HNSW, GIN x2, GIST, B-tree x5 |
| F7 | Queues operational | PASS | 6 queues verified: parse, normalize, dedup, geocode, embed, dead_letter |
| F8 | Cron jobs (3) | PASS | expire-stale-jobs, reindex-hnsw-monthly, refresh-job-stats |
| F9 | pipeline_health view | PASS | 14 columns, db_size_bytes=21,466,259 |
| F10 | RLS blocks raw | PASS | Anon returns 0 rows for status='raw' |
| F11 | RLS allows ready | PASS | Anon returns rows for status='ready' |
| F12 | Seed data (4 sources) | PASS | reed, adzuna, jooble, careerjet — all active |
| F13 | Autovacuum | PASS | scale_factor=0.01, cost_delay=2, threshold=100, analyze_scale=0.005 |

### Gate 2: Collection (C1–C13) — 13 PASS

| # | Check | Result |
|---|---|---|
| C1 | Reed adapter | PASS |
| C2 | Adzuna adapter | PASS |
| C3 | Jooble adapter | PASS |
| C4 | Careerjet adapter | PASS |
| C5 | Circuit breaker | PASS |
| C6 | Rate limit handler | PASS |
| C7 | Content hash | PASS |
| C8 | UPSERT idempotency | PASS |
| C9 | Schema validation | PASS |
| C10 | Edge cases | PASS |
| C11 | Coverage: collectors 99% | PASS |
| C12 | Modal deploy | PASS |
| C13 | Pipeline health | PASS |

### Gate 3: Processing (P1–P24) — 24 PASS

| # | Check | Result |
|---|---|---|
| P1 | Salary: 12 patterns | PASS |
| P2 | Salary: sanity check | PASS |
| P3 | Salary: API priority | PASS |
| P4 | Salary: property test | PASS |
| P5 | Location: 8 cases | PASS |
| P6 | Location: geocoding priority | PASS |
| P7 | Location: postcodes.io | PASS |
| P8 | Location: fallback | PASS |
| P9 | Category: Reed mapping | PASS |
| P10 | Category: Adzuna mapping | PASS |
| P11 | Category: keyword inference | PASS |
| P12 | Category: fallback | PASS |
| P13 | Seniority extraction | PASS |
| P14 | Structured summary | PASS |
| P15 | Skill extraction | PASS |
| P16 | Embeddings: Gemini | PASS |
| P17 | Embeddings: fallback | PASS |
| P18 | Dedup: hash match | PASS |
| P19 | Dedup: UPSERT | PASS |
| P20 | Queue runner | PASS |
| P21 | DLQ routing | PASS |
| P22 | Coverage: processing 98% | PASS |
| P23 | Coverage: embeddings 85% | PASS |
| P24 | Pipeline health | PASS |

### Gate 4: Maintenance (M1–M14) — 14 PASS

| # | Check | Result |
|---|---|---|
| M1 | Expiry: Reed | PASS |
| M2 | Expiry: Adzuna default | PASS |
| M3 | Expiry: Jooble/Careerjet | PASS |
| M4 | Re-verification | PASS |
| M5 | Archival | PASS |
| M6 | Hard delete | PASS |
| M7 | DLQ auto-retry | PASS |
| M8 | DLQ exhausted | PASS |
| M9 | Health alerts | PASS |
| M10 | search_jobs() 10 queries | PASS |
| M11 | E2E pipeline (128 jobs) | PASS |
| M12 | Performance (36ms) | PASS |
| M13 | Coverage: total 89% | PASS |
| M14 | Lint + types | PASS |

### Search Queries Q1–Q10 — 10 PASS

All 10 queries execute without SQL errors. Q9 returns exactly 5 rows (match_count=5).

### Go/No-Go G1–G20 — 20 PASS

All pre-deployment, deployment, and post-deployment monitoring checks pass.

### Performance SLAs S1–S8 — 6 PASS / 2 N/A

| # | Metric | Target | Measured | Result |
|---|---|---|---|---|
| S1 | search_jobs P95 | <50ms | 36ms | PASS |
| S2 | Page load TTFB | <200ms | N/A | N/A (Phase 2) |
| S3 | Collector per page | <2s | ~1s | PASS |
| S4 | Pipeline throughput | >500/hr | ~1440/hr | PASS |
| S5 | Embedding generation | >100/min | >200/min | PASS |
| S6 | Geocoding batch | <200ms | <200ms | PASS |
| S7 | HNSW build 500K | <30min | N/A | N/A (Phase 3) |
| S8 | search_jobs all filters | <80ms | 34ms | PASS |

---

## Architecture Delivered

- 4 API collectors (Reed, Adzuna, Jooble, Careerjet) with circuit breaker
- 6-stage processing pipeline (parse → normalize → dedup → geocode → embed → ready)
- Hybrid search: RRF combining FTS (tsvector) + semantic (HNSW cosine) + geo (PostGIS)
- 5 Modal cron functions deployed + 3 pg_cron maintenance jobs
- 9 Supabase migrations with rollbacks
- RLS enforced on all tables
- Dead letter queue with auto-retry

## Next Steps

Phase 2: Next.js web application with tRPC search API.
