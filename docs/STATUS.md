# AtoZ Jobs AI — Phase 1 Status

**Last updated:** 2026-03-05

## Current Stage: 3 — Processing (Code Complete)

---

### Stage 1: Foundation — CODE COMPLETE (25/25), GATES PENDING (0/13)

#### Code Deliverables (all done)
- [x] Directory structure (pipeline/src/{collectors,processing,embeddings,skills,models,maintenance,tests/fixtures}, web/src, supabase/, docs/, .claude/)
- [x] CLAUDE.md (root + pipeline/ + web/)
- [x] .claude/settings.json (allow/deny permissions)
- [x] .claude/agents/ (security-auditor.md, architecture-reviewer.md)
- [x] .claude/skills/ (testing-patterns, migration-safety, api-conventions)
- [x] .claude/rules/ (security-critical.md, test-standards.md)
- [x] .claude/commands/ (pr-review.md, fix-issue.md)
- [x] .env.example (13 env vars documented)
- [x] justfile (all commands: dev, test, lint, migrate, seed, deploy)
- [x] pipeline/pyproject.toml (Python 3.12, all deps, pytest config)
- [x] .gitignore (252 lines — Python + Node.js + Supabase + security patterns)
- [x] supabase/config.toml
- [x] Migration 001: Extensions (vector, postgis, pg_trgm) + down.sql
- [x] Migration 002: Core tables (sources, companies, jobs, skills, job_skills) + down.sql
- [x] Migration 003: Indexes (HNSW, GIN x2, GIST, B-tree x5, autovacuum) + down.sql
- [x] Migration 004: Queues (6), cron jobs (2), trigger, pipeline_health view + down.sql
- [x] Migration 005: RLS policies (5 tables, public read + service write) + down.sql
- [x] Migration 006: UK cities reference table (geocoding fallback) + down.sql
- [x] Migration 007: UK cities RLS + down.sql
- [x] seed.sql (4 sources + ~100 UK cities with coordinates)
- [x] docs/architecture.md
- [x] docs/STATUS.md
- [x] docs/phase-1/ (SPEC.md, PLAYBOOK.md, GATES.md)
- [x] docs/adr/.gitkeep (ready for ADRs)
- [x] web/src/.gitkeep (ready for Next.js)

#### Gate 1 Checks (all require local Docker + Supabase)
- [ ] F1: `supabase db reset` succeeds with all migrations
- [ ] F2: Rollback chain (each down.sql in reverse, then reset)
- [ ] F3: 5 tables exist with correct columns (`\dt`)
- [ ] F4: Column types verified (`\d jobs` — HALFVEC, GEOGRAPHY, TEXT[], TSVECTOR)
- [ ] F5: UNIQUE constraint on (source_id, external_id)
- [ ] F6: All indexes visible (`\di` — HNSW, GIN x2, GIST, B-tree x5)
- [ ] F7: 6 queues operational (`pgmq.send` returns message ID)
- [ ] F8: Cron jobs visible in `cron.job`
- [ ] F9: pipeline_health view returns 14 columns
- [ ] F10: RLS — anon key blocks `status='raw'` jobs
- [ ] F11: RLS — anon key allows `status='ready'` jobs
- [ ] F12: 4 sources seeded with `is_active=true`
- [ ] F13: Autovacuum settings on jobs table verified

**To verify:** Run `supabase start` locally with Docker, then execute gate checks.

---

### Stage 2: Collection — CODE COMPLETE (21/21), GATES 10/13 PASS

#### Code Deliverables (all done)
- [x] Pydantic models (JobBase + 4 source adapters) — `pipeline/src/models/job.py`
- [x] Error classes (7 types + MaxRetriesExceeded) — `pipeline/src/models/errors.py`
- [x] Circuit breaker (3-state: CLOSED > OPEN > HALF_OPEN) — `pipeline/src/collectors/circuit_breaker.py`
- [x] Rate limit handler (fetch_with_retry, Retry-After) — `pipeline/src/collectors/base.py`
- [x] Reed collector (Basic Auth, category sweep, HTML strip, 0.5s sleep) — `pipeline/src/collectors/reed.py`
- [x] Adzuna collector (direct lat/lon, salary_is_predicted, 45-day expiry) — `pipeline/src/collectors/adzuna.py`
- [x] Jooble collector (POST, paginate until empty, no totalResults) — `pipeline/src/collectors/jooble.py`
- [x] Careerjet collector (v4 user_ip/user_agent, structured salary) — `pipeline/src/collectors/careerjet.py`
- [x] Modal app (5 crons, Starter limit) — `pipeline/src/modal_app.py`
- [x] Test fixtures — `pipeline/src/tests/fixtures/{reed,adzuna,jooble,careerjet}_response.json`
- [x] 75 tests passing across 5 test files
- [x] Test coverage ~88% (Gate C11 threshold: 85%)

#### Gate 2 Checks
- [x] C1: Reed adapter maps fixture JSON to JobBase (pagination, HTML strip)
- [x] C2: Adzuna adapter extracts lat/lon directly, maps salary_is_predicted
- [x] C3: Jooble paginates until empty results array
- [x] C4: Careerjet passes user_ip/user_agent in v4 format
- [x] C5: Circuit breaker — 3 consecutive 500s > OPEN > 300s > HALF_OPEN > success > CLOSED
- [x] C6: Rate limit — 429 reads Retry-After, max 3 retries > MaxRetriesExceeded
- [x] C7: Content hash — SHA-256(lower(title)+normalize(company)+normalize(location)), stable + case-insensitive
- [ ] C8: UPSERT idempotency — *requires live Supabase DB*
- [x] C9: Schema validation — malformed JSON (null title, missing external_id) raises ValidationError
- [x] C10: Edge cases — empty results, timeout, malformed JSON handled without crash
- [x] C11: Coverage >= 85% — PASS (~88%)
- [ ] C12: Modal deploy — *requires Modal account + API keys*
- [ ] C13: pipeline_health.jobs_ingested_last_hour > 0 — *requires DB + real API call*

**To verify C8:** Insert same (source_id, external_id) twice via service_role, confirm no duplicate.
**To verify C12:** `modal deploy pipeline/src/modal_app.py` with secrets configured.
**To verify C13:** Run first collection, then `SELECT jobs_ingested_last_hour FROM pipeline_health`.

---

### Stage 3: Processing — CODE COMPLETE (20/20), GATES PENDING

#### Code Deliverables (all done)
- [x] Salary normalizer (12 regex patterns, constants: 252/1950/12) — `pipeline/src/processing/salary.py`
- [x] Location normalizer (10 cases, postcodes.io, city fallback) — `pipeline/src/processing/location.py`
- [x] Category mapper (Reed/Adzuna exhaustive + keyword inference) — `pipeline/src/processing/category.py`
- [x] Seniority extractor (5 regex patterns) — `pipeline/src/processing/seniority.py`
- [x] Structured summary builder (6-field template, no LLM) — `pipeline/src/processing/summary.py`
- [x] Skill dictionary (~150 UK skills placeholder) — `pipeline/src/skills/dictionary.py`
- [x] Skill extractor (tokenize, match, cap at 15) — `pipeline/src/skills/extractor.py`
- [x] Embedding pipeline (Gemini embedding-001, 768-dim, re-normalize) — `pipeline/src/embeddings/embed.py`
- [x] Embedding fallback (OpenAI text-embedding-3-small) — `pipeline/src/embeddings/fallback.py`
- [x] Deduplication gate (content_hash check) — `pipeline/src/processing/dedup.py`
- [x] Queue runner (wire all 6 queues) — `pipeline/src/processing/queue_runner.py`

#### Tests (all done — 300 total tests passing)
- [x] test_salary_normalizer.py (12 patterns + sanity + property-based)
- [x] test_location_normalizer.py (10 cases + postcodes.io mock)
- [x] test_category_mapper.py (Reed + Adzuna + keyword inference)
- [x] test_seniority.py (5 levels + 'Not specified')
- [x] test_structured_summary.py (6-field template)
- [x] test_skill_extractor.py (dictionary match, max 15, confidence)
- [x] test_embeddings.py (768-dim, re-normalize, fallback)
- [x] test_dedup.py (hash match, hash mismatch, UPSERT)
- [x] test_queue_runner.py (full pipeline: raw > normalized > dedup > summary)

#### Gate 3 Checks (code-verifiable)
- [x] P1: Salary — all 12 patterns produce correct annual_min/annual_max
- [x] P2: Salary sanity — values < 10K or > 500K rejected (set to NULL)
- [x] P3: Salary API fields priority — structured fields over salary_raw
- [x] P4: Salary property test — hypothesis @given(st.text()) never raises
- [x] P5: Location — 10 cases resolve correctly (London, Remote, Hybrid, etc.)
- [x] P6: Location — Adzuna uses provided lat/lon directly
- [ ] P7: Location — postcodes.io lookup — *requires network*
- [x] P8: Location — city fallback table works (Manchester coords)
- [x] P9: Category — all Reed sectors map correctly
- [x] P10: Category — all Adzuna tags map correctly
- [x] P11: Category — keyword inference (Jooble title > Technology)
- [x] P12: Category — fallback to 'Other'
- [x] P13: Seniority — Senior/Junior/Executive/Not specified all correct
- [x] P14: Structured summary — 6-field template, no Summary/Requirements
- [x] P15: Skill extraction — Python/AWS extracted, max 15, confidence=1.0
- [x] P16: Embeddings — 768-dim vectors, re-normalized (mocked Gemini)
- [x] P17: Embeddings — OpenAI fallback returns 768 dims (mocked)
- [x] P18: Dedup — same hash raises DuplicateError
- [ ] P19: Dedup UPSERT — *requires live DB*
- [x] P20: Queue runner — full flow raw > normalized > dedup > summary
- [x] P21: DLQ routing — failure handling increments retry_count
- [ ] P22: Coverage processing >= 90% — *needs verification*
- [ ] P23: Coverage embeddings >= 85% — *needs verification*
- [ ] P24: pipeline_health ready_without_embedding = 0 — *requires DB*

---

### Stage 4: Maintenance — NOT STARTED (0/8)

- [ ] Expiry detection (Reed expirationDate, Adzuna 45-day, Jooble/Careerjet 30-day) — `pipeline/src/maintenance/expiry.py`
- [ ] DLQ retry (auto-retry after 6h, max 5 retries, route by failed_stage) — `pipeline/src/maintenance/dlq.py`
- [ ] Health logger (alert thresholds, structlog CRITICAL) — `pipeline/src/maintenance/health.py`
- [ ] Migration 008: search_jobs() function (RRF, pre-filter CTE, geo + salary + work_type)
- [ ] E2E verification (100 real jobs > ready > search returns results)
- [ ] Gate 4 verification (M1-M14)
- [ ] 10 test search queries (Q1-Q10)
- [ ] Go/No-Go checklist (G1-G20)

---

## Progress Summary

| Stage | Code | Gates | Status |
|-------|------|-------|--------|
| 1. Foundation | 25/25 (100%) | 0/13 (need local DB) | Code complete |
| 2. Collection | 21/21 (100%) | 10/13 (3 need infra) | Code complete |
| 3. Processing | 20/20 (100%) | 18/24 (6 need infra) | Code complete |
| 4. Maintenance | 0/8 (0%) | 0/14 | Not started |
| **Total** | **66/74 (89%)** | **28/64 (44%)** | |

## Verification Totals (per GATES.md)

| Category | Total | Verified | Remaining |
|----------|-------|----------|-----------|
| Gate checks (F+C+P+M) | 64 | 28 | 36 |
| Test search queries | 10 | 0 | 10 |
| Go/No-Go items | 20 | 0 | 20 |
| Performance SLAs | 8 | 0 | 8 |
| **Grand total** | **102** | **28** | **74** |

## What's Blocking

All 16 unverified Stage 1+2 gates require the same thing:
1. **Docker Desktop** installed locally
2. **Supabase CLI** (`supabase start` for local PostgreSQL)
3. **API keys** in `.env` (Reed, Adzuna, Jooble, Careerjet, Google Gemini)
4. **Modal account** (for C12 deploy test only)

Stage 3 and 4 code can be built and unit-tested without infrastructure (pure Python logic).
