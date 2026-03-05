# AtoZ Jobs AI — Phase 1 Status

## Current Stage: 1 — Foundation

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
- [x] seed.sql
- [x] supabase/config.toml
- [x] docs/architecture.md, docs/STATUS.md
- [x] docs/phase-1/ (SPEC.md, PLAYBOOK.md, GATES.md)
- [x] .claude/ agents, skills, rules, commands
- [ ] Gate 1 verification (PENDING — requires Docker + Supabase local: F1–F13)

### Stage 2: Collection
- [ ] Pydantic models (JobBase + adapters)
- [ ] Error classes
- [ ] Circuit breaker
- [ ] Reed collector
- [ ] Adzuna collector
- [ ] Jooble collector
- [ ] Careerjet collector
- [ ] Modal app
- [ ] Gate 2 verification

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
