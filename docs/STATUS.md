# AtoZ Jobs AI — Phase 1 Status

## Current Stage: 2 — Collection (Complete)

### Stage 1: Foundation
- [x] Directory structure
- [x] CLAUDE.md (root + subdirectories)
- [x] .claude/settings.json
- [x] .env.example
- [x] justfile
- [x] pyproject.toml
- [x] Migration 001: Extensions
- [x] Migration 002: Core tables
- [x] Migration 003: Indexes
- [x] Migration 004: Queues, cron, health view
- [x] Migration 005: RLS policies
- [x] Migration 006: UK cities reference table (geocoding fallback)
- [x] Migration 007: UK cities RLS
- [x] seed.sql (4 sources + ~100 UK cities)
- [x] supabase/config.toml
- [x] .gitignore (Python + Node.js + Supabase + security patterns)
- [x] docs/architecture.md, docs/STATUS.md
- [x] docs/phase-1/ (SPEC.md, PLAYBOOK.md, GATES.md)
- [x] .claude/ agents, skills, rules, commands
- [ ] Gate 1 verification (PENDING — requires Docker + Supabase local: F1–F13)

### Stage 2: Collection
- [x] Pydantic models (JobBase + 4 source adapters) — `pipeline/src/models/job.py`
- [x] Error classes (7 types + MaxRetriesExceeded) — `pipeline/src/models/errors.py`
- [x] Circuit breaker (3-state: CLOSED→OPEN→HALF_OPEN) — `pipeline/src/collectors/circuit_breaker.py`
- [x] Rate limit handler (fetch_with_retry, Retry-After) — `pipeline/src/collectors/base.py`
- [x] Reed collector (Basic Auth, category sweep, HTML strip) — `pipeline/src/collectors/reed.py`
- [x] Adzuna collector (direct lat/lon, salary_is_predicted, 45-day expiry) — `pipeline/src/collectors/adzuna.py`
- [x] Jooble collector (POST, paginate until empty, no totalResults) — `pipeline/src/collectors/jooble.py`
- [x] Careerjet collector (v4 user_ip/user_agent, structured salary) — `pipeline/src/collectors/careerjet.py`
- [x] Modal app (5 crons, Starter limit) — `pipeline/src/modal_app.py`
- [x] Test fixtures (4 contract test JSON files)
- [x] 75 tests passing (5 test files)
- [x] Gate 2 verification: C1–C7, C9, C10 PASS
- [ ] Gate 2 infra checks: C8 (UPSERT), C11 (coverage), C12 (Modal deploy), C13 (pipeline health) — PENDING (requires DB/API keys)

### Stage 3: Processing
- [ ] Salary normalizer
- [ ] Location normalizer
- [ ] Category mapper
- [ ] Seniority extractor
- [ ] Structured summary builder
- [ ] Skill extractor + dictionary
- [ ] Embedding pipeline + fallback
- [ ] Deduplication
- [ ] Queue runner
- [ ] Gate 3 verification

### Stage 4: Maintenance
- [ ] Expiry detection
- [ ] DLQ retry
- [ ] Health logger
- [ ] search_jobs() migration
- [ ] End-to-end verification
- [ ] Gate 4 verification

## Metrics
- Total gate checks: 64
- Test queries: 10
- Go/no-go items: 20
- Performance SLAs: 8
- **Total verification items: 102**
