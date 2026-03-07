# AtoZ Jobs AI — Project Status

---

## Phase 2: Search & Match

**Status:** Code Complete
**Completion Date:** 2026-03-07
**Branch:** `search-match-phase` (merged into `claude/merge-main-search-match-xQtG0`)
**Tag:** v0.2.0

### Metrics

| Metric | Value |
|--------|-------|
| Tests | 620 passed, 0 failed |
| Total coverage | 87% |
| Ruff | 0 errors |
| Mypy | 0 errors (87 source files) |
| Files created | 21/21 from PLAYBOOK Appendix A |
| Migrations | 4 Phase 2 (010-013) verified against SPEC.md |

### Gate Check Scorecard (122 items)

```
Gate 1 (Skills)     :  5 PASS, 11 SKIP,  0 FAIL
Gate 2 (Dedup)      :  5 PASS, 11 SKIP,  0 FAIL
Gate 3 (Salary)     : 10 PASS,  8 SKIP,  0 FAIL
Gate 4 (Re-ranking) :  7 PASS, 11 SKIP,  0 FAIL
Search Queries      :  1 PASS, 14 SKIP,  0 FAIL
Go/No-Go            :  3 PASS, 27 SKIP,  0 FAIL
SLAs                :  0 PASS,  9 SKIP,  0 FAIL
─────────────────────────────────────────────────
TOTAL               : 31 PASS, 91 SKIP,  0 FAIL
```

**0 failures.** 91 items skipped — breakdown:

| Skip Reason | Count | Resolution |
|-------------|-------|------------|
| No management token | 42 | Provide `~/.supabase/access-token` and re-run `phase2_gate_checks.py` |
| Production deployment | 17 | Run `modal deploy`, `modal run` per GATES.md G14-G23 |
| Post-deployment monitoring | 7 | Monitor 24h after deploy (G24-G30) |
| Supabase CLI required | 8 | Rollback testing requires `supabase db reset` |
| Manual review | 3 | D13-D14 (dedup precision), R11 (re-ranking comparison) |
| Modal/live endpoint | 5 | S2-S9 SLAs, R15 E2E latency |
| Multi-user auth / live data | 3 | R4, R13, S15 |

### What Phase 2 Adds

| Stage | Component | Key Technology |
|-------|-----------|----------------|
| 1 | Skills Extraction & Taxonomy | SpaCy PhraseMatcher (LOWER+ORTH), ESCO v1.2.1, 450+ UK patterns |
| 2 | Advanced Deduplication | pg_trgm fuzzy, MinHash/LSH (datasketch+xxhash), composite 0.65 threshold |
| 3 | Salary Prediction | XGBoost, TF-IDF (500) + region one-hot (12) + seniority ordinal |
| 3 | Company Enrichment | Companies House API, SIC code mapping (21 sections A-U) |
| 4 | Cross-Encoder Re-ranking | ms-marco-MiniLM-L-6-v2, graceful degradation to RRF |
| 4 | User Profiles | Gemini embedding-001 (768-dim halfvec), RLS-protected |
| 4 | search_jobs_v2() | 12 params, 18 return fields, duplicate exclusion, skill filters |

### Migrations (Phase 2)

| # | File | Content |
|---|------|---------|
| 010 | `20260301000010_skills_taxonomy.sql` | esco_skills table, mv_skill_demand, mv_skill_cooccurrence, pg_cron |
| 011 | `20260301000011_advanced_dedup.sql` | canonical_id, is_duplicate, compute_duplicate_score() |
| 012 | `20260301000012_salary_company.sql` | salary prediction columns, sic_industry_map (21 rows) |
| 013 | `20260301000013_user_profiles_search_v2.sql` | user_profiles with RLS, search_jobs_v2() |

### Production Verification Steps

To complete the remaining 91 skipped checks:
1. Place Supabase access token at `~/.supabase/access-token`
2. Run: `cd pipeline && uv run python -m src.tests.phase2_gate_checks`
3. Deploy Modal: `modal deploy pipeline/src/modal_app.py`
4. Run backfills per GATES.md G17-G22
5. Monitor 24h for G24-G30

---

## Phase 1: Data Pipeline

**Status:** COMPLETE
**Completion Date:** 2026-03-06
**Tag:** v0.1.0
**Branch:** data-phase → main

### Metrics

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

### Gate Scorecard

- Gate 1: Foundation (F1-F13) — 13 PASS
- Gate 2: Collection (C1-C13) — 13 PASS
- Gate 3: Processing (P1-P24) — 24 PASS
- Gate 4: Maintenance (M1-M14) — 14 PASS
- Search Queries Q1-Q10 — 10 PASS
- Go/No-Go G1-G20 — 20 PASS
- Performance SLAs S1-S8 — 6 PASS / 2 N/A

### Architecture Delivered

- 4 API collectors (Reed, Adzuna, Jooble, Careerjet) with circuit breaker
- 6-stage pipeline (parse → normalize → dedup → geocode → embed → ready)
- Hybrid search: RRF combining FTS (tsvector) + semantic (HNSW cosine) + geo (PostGIS)
- 5 Modal cron functions + 3 pg_cron jobs
- 9 Supabase migrations with rollbacks
- RLS enforced on all tables
- Dead letter queue with auto-retry

---

## Next Steps

Phase 3: Display — Next.js web application with tRPC search API.
