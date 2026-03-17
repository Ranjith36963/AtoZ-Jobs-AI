# Changelog

All notable changes to AtoZ Jobs AI.

Format follows [Keep a Changelog](https://keepachangelog.com/). Versions use [Semantic Versioning](https://semver.org/).

---

## [0.3.0] — 2026-03-15

**Phase 3: Display Layer**

### Added
- Next.js 16 frontend with App Router and Turbopack
- Cloudflare Pages deployment with OpenNext adapter
- tRPC API layer (search, job detail, facets routers)
- Supabase SSR client (server, browser, admin variants)
- Search interface with natural language input and location autocomplete (postcodes.io)
- Job cards with salary badges (real vs predicted), skills pills, and skeleton loading
- Filter sidebar with facet counts from materialized views
- Salary range slider from `mv_salary_histogram`
- Job detail pages with ISR (30-min revalidation)
- Match explanation streaming via Vercel AI SDK + GPT-4o-mini
- Cross-encoder re-ranking via Modal `/search` endpoint
- Related jobs via vector similarity
- EU AI Act compliance: `ai_decision_audit_log` table (Article 12), `<AIDisclosure>` components (Article 50), `/transparency` page (Article 13)
- WCAG 2.1 AA accessibility: skip link, keyboard navigation, 4.5:1 contrast, 48px touch targets
- schema.org/JobPosting JSON-LD, XML sitemap, robots.txt
- Sentry error tracking (10% traces), PostHog analytics
- LLM budget guard ($45 soft cap, $50 hard cap)
- Migrations 018–019: `ai_decision_audit_log`, `mv_search_facets`, `mv_salary_histogram`

### Performance
- Lighthouse Performance: 100
- Lighthouse Accessibility: 96
- 127 tests passed

---

## [0.2.0] — 2026-03-07

**Phase 2: Search & Match**

### Added
- Skills extraction via SpaCy PhraseMatcher (LOWER + ORTH layers) with ESCO taxonomy (13,939 skills)
- `skills` and `job_skills` tables with dictionary builder (~450+ patterns)
- Advanced deduplication: pg_trgm fuzzy matching + MinHash/LSH (datasketch, xxhash), composite scoring (threshold 0.65)
- XGBoost salary prediction (max_depth=6, 200 rounds) with TF-IDF + one-hot features
- Companies House enrichment: SIC codes, company status, creation date
- `search_jobs_v2()`: 12 params, 18 return fields, skill/category/salary/dedup filters
- Cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`) on Modal
- `user_profiles` table with RLS and 768-dim Gemini embeddings for personalization
- Materialized views: `mv_skill_demand`, `mv_skill_cooccurrence`
- Migrations 010–017: skills taxonomy, advanced dedup, salary/company, user profiles/search_v2, Phase 2 RLS, fuzzy duplicates, category/contract type, pgmq permissions

### Performance
- 620 tests passed
- 94% coverage

---

## [0.1.0] — 2026-03-06

**Phase 1: Data Pipeline**

### Added
- 4 API collectors: Reed, Adzuna, Jooble, Careerjet (with circuit breaker pattern)
- 7 free API collectors: Arbeitnow, RemoteOK, Jobicy, Himalayas, Remotive, DevITjobs, Landing.jobs
- 6-stage pipeline: parse → normalize → dedup → geocode → embed → ready
- 6 pgmq queues + dead letter queue with 6-hour auto-retry
- Gemini embedding-001 (768-dim halfvec) with OpenAI fallback
- Hybrid search via `search_jobs()`: RRF combining FTS + semantic + geo
- Salary normalization, location geocoding (PostGIS), category mapping, seniority extraction
- Row-Level Security on every table
- Modal serverless compute (6 cron functions)
- Supabase PostgreSQL with pgvector, PostGIS, pg_trgm, pgmq, pg_cron
- 9 migrations (001–009): extensions, core tables, indexes, queues/cron/health, RLS, UK cities, search function, pipeline columns

### Performance
- 426 tests passed
- 89% coverage
- search_jobs P95: 36ms
