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

## Phase 3: Display Layer

**Status:** Code Complete
**Completion Date:** 2026-03-15
**Branch:** `display-phase` (developed on `claude/plan-nextjs-frontend-KSU0h`)
**Tag:** v0.3.0

### Metrics

| Metric | Value |
|--------|-------|
| Source files (TS/TSX) | 80 |
| Test files | 18 |
| Tests | 127 passed, 0 failed |
| TypeScript strict | 0 errors |
| ESLint | 0 errors |
| Routes | 8 (5 static, 3 dynamic) |
| Components | 25 |
| Migrations | 2 Phase 3 (018-019) |
| Next.js version | 16.1.6 (CVE-2025-66478 patched) |

### Gate Check Scorecard (149 items)

```
Gate 1 (Foundation)  : 18 PASS,  3 SKIP,  0 FAIL
Gate 2 (Search)      : 27 PASS,  1 SKIP,  0 FAIL
Gate 3 (Performance) :  6 PASS,  9 SKIP,  0 FAIL
Gate 4 (Compliance)  : 23 PASS,  2 SKIP,  0 FAIL
Search Queries       : 10 PASS,  0 SKIP,  0 FAIL
Go/No-Go             : 16 PASS, 24 SKIP,  0 FAIL
SLAs                 :  3 PASS,  7 SKIP,  0 FAIL
─────────────────────────────────────────────────
TOTAL                :103 PASS, 46 SKIP,  0 FAIL
```

**0 failures.** 46 items skipped — breakdown:

| Skip Reason | Count | Resolution |
|-------------|-------|------------|
| Supabase DB credentials (placeholder) | 14 | Set real anon/service keys in .env.local |
| Cloudflare Pages deployment | 8 | Run `pnpm build:cf` + `wrangler pages deploy` |
| Production traffic monitoring | 10 | Monitor 24h after deploy (Sentry, PostHog) |
| Lighthouse on deployed site | 7 | Run `pnpm lhci autorun` against production URL |
| OpenAI dashboard access | 1 | Set $50/month spending cap |
| Modal endpoint credentials | 2 | Set MODAL_SEARCH_URL env var |
| OpenNext build runtime | 4 | Run `pnpm build:cf` in Cloudflare environment |

### What Phase 3 Adds

| Stage | Component | Key Technology |
|-------|-----------|----------------|
| 1 | Foundation | Next.js 16 App Router, Turbopack, tRPC, Supabase SSR |
| 1 | Monitoring | Sentry error tracking, PostHog analytics |
| 1 | Deployment | Cloudflare Pages (OpenNext adapter, wrangler.toml) |
| 2 | Search UI | SearchInput, LocationAutocomplete (postcodes.io), RadiusSelector |
| 2 | Job Cards | SalaryBadge (green/amber/grey), SkillsPills (ESCO links, +N more) |
| 2 | Filters | FilterSidebar (6 groups), SalaryRangeSlider (ARIA), mobile drawer |
| 2 | Job Detail | 10 sections, DOMPurify sanitization, CompanyInfo, RelatedJobs |
| 2 | LLM | GPT-4o-mini explanations, 3-layer budget guard ($45 soft/$50 hard) |
| 3 | ISR | 30min job detail, 1hr homepage, 24hr transparency, dynamic search |
| 3 | Performance | HNSW ef_search=100, dynamic imports, Lighthouse CI |
| 4 | Compliance | EU AI Act (Article 12/13/14/50), transparency page, audit logging |
| 4 | Accessibility | WCAG 2.1 AA, axe-core Playwright tests, skip link, focus rings |
| 4 | SEO | JobPosting JSON-LD, sitemap (50K), robots.txt, OG meta tags |

### Migrations (Phase 3)

| # | File | Content |
|---|------|---------|
| 018 | `20260301000018_ai_audit_log.sql` | ai_decision_audit_log (EU AI Act Article 12), RLS (service_role only) |
| 019 | `20260301000019_search_facets.sql` | mv_search_facets, mv_salary_histogram, pg_cron refreshes |

### Deviations (Documented)

1. Default exports on Next.js pages (framework requirement)
2. Manual fetch instead of useChat (AI SDK v6 migration)
3. search.related uses category match (not cosine similarity)
4. Search page renders as static shell (dynamic via client-side tRPC)

### Production Verification Steps

To complete the remaining 46 skipped checks:
1. Set real Supabase keys in web/.env.local
2. Run: `supabase db push` for migrations 018-019
3. Deploy: `pnpm build:cf && wrangler pages deploy .open-next`
4. Set Cloudflare env vars (SPEC §5.2)
5. Set OpenAI $50/month spending cap
6. Run: `pnpm lhci autorun` against production URL
7. Monitor 24h for G35-G40

---

## Next Steps

Phase 3 is code-complete. Remaining work:
- Deploy to Cloudflare Pages with real credentials
- Run Lighthouse CI against production site
- Monitor first 24 hours of production traffic
- Merge display-phase → main with squash commit
