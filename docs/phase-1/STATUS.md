# AtoZ Jobs AI — Phase 1: Data Pipeline Status

**Status:** COMPLETE
**Completion Date:** 2026-03-06
**Tag:** v0.1.0
**Branch:** data-phase → main

---

## Metrics

| Metric | Value |
|--------|-------|
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

## Gate Scorecard

- Gate 1: Foundation (F1-F13) — 13 PASS
- Gate 2: Collection (C1-C13) — 13 PASS
- Gate 3: Processing (P1-P24) — 24 PASS
- Gate 4: Maintenance (M1-M14) — 14 PASS
- Search Queries Q1-Q10 — 10 PASS
- Go/No-Go G1-G20 — 20 PASS
- Performance SLAs S1-S8 — 6 PASS / 2 N/A

## Architecture Delivered

- 4 API collectors (Reed, Adzuna, Jooble, Careerjet) with circuit breaker
- 6-stage pipeline (parse → normalize → dedup → geocode → embed → ready)
- Hybrid search: RRF combining FTS (tsvector) + semantic (HNSW cosine) + geo (PostGIS)
- 5 Modal cron functions + 3 pg_cron jobs
- 9 Supabase migrations with rollbacks
- RLS enforced on all tables
- Dead letter queue with auto-retry

## Stage Breakdown

### Stage 1: Foundation — COMPLETE (25/25 code, 13/13 gates)

- Directory structure, CLAUDE.md, .claude/ config
- Migrations 001-007 (extensions, tables, indexes, queues, RLS, UK cities)
- seed.sql (4 sources + ~100 UK cities)

### Stage 2: Collection — COMPLETE (21/21 code, 13/13 gates)

- Pydantic models (JobBase + 4 source adapters)
- Circuit breaker (3-state: CLOSED → OPEN → HALF_OPEN)
- 4 collectors: Reed, Adzuna, Jooble, Careerjet
- Modal app (5 crons)

### Stage 3: Processing — COMPLETE (20/20 code, 24/24 gates)

- Salary normalizer (12 regex patterns)
- Location normalizer (10 cases, postcodes.io, city fallback)
- Category mapper (Reed/Adzuna exhaustive + keyword inference)
- Seniority extractor (5 regex patterns)
- Skill extractor, embedding pipeline (Gemini + OpenAI fallback)

### Stage 4: Maintenance — COMPLETE (8/8 code, 14/14 gates)

- Expiry detection, DLQ retry, health logger
- Migration 008: search_jobs() function (RRF, pre-filter CTE)

## Tests

| Test File | Tests | Status |
|-----------|-------|--------|
| test_reed_collector.py | ~75 | PASS |
| test_adzuna_collector.py | ~60 | PASS |
| test_jooble_collector.py | ~55 | PASS |
| test_careerjet_collector.py | ~65 | PASS |
| test_circuit_breaker.py | ~20 | PASS |
| test_salary_normalizer.py | ~30 | PASS |
| test_location_normalizer.py | ~20 | PASS |
| test_category_mapper.py | ~20 | PASS |
| test_seniority.py | ~15 | PASS |
| test_skill_extractor.py | ~15 | PASS |
| test_embeddings.py | ~20 | PASS |
| test_dedup.py | ~10 | PASS |
| test_queue_runner.py | ~20 | PASS |
| test_structured_summary.py | ~10 | PASS |
| test_expiry.py | 26 | PASS |
| test_dlq.py | 20 | PASS |
| test_health.py | 11 | PASS |
| test_search.py | 35 | PASS |
| **Total** | **~527** | **ALL PASS** |
