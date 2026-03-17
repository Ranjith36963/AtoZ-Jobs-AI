# AtoZ Jobs AI — Architecture

## System Overview

UK AI-powered job search engine combining semantic search (embeddings) with structured SQL filters.

## Components

### Pipeline (Python)
- **Collectors**: 11 sources — 4 paid APIs (Reed, Adzuna, Jooble, Careerjet) + 7 free APIs (Arbeitnow, RemoteOK, Jobicy, Himalayas, Remotive, DevITjobs, Landing.jobs) with circuit breaker pattern
- **Processing**: Salary normalization, location geocoding, category mapping, seniority extraction, skill extraction (regex + ESCO dictionary)
- **Embeddings**: Gemini embedding-001 (768-dim) with OpenAI fallback
- **Compute**: Modal serverless (6 scheduled cron functions + 7 callable functions)

### Database (Supabase PostgreSQL)
- **Extensions**: pgvector (HNSW), PostGIS (geography), pg_trgm (fuzzy), pgmq (queues), pg_cron
- **Tables**: sources, companies, jobs, skills, job_skills, user_profiles, sic_industry_map, ai_audit_log
- **Search**: Hybrid RRF via search_jobs_v2() combining full-text search (tsvector) + semantic search (halfvec cosine), with cross-encoder re-ranking
- **Security**: Row-Level Security on every table

### Web (Next.js 16)
- **Hosting**: Cloudflare Pages (OpenNext adapter)
- **API**: tRPC for search, direct Supabase client for reads
- **AI**: GPT-4o-mini match explanations via Vercel AI SDK (budget-capped)
- **Auth**: Supabase anon key (RLS enforced)
- **Monitoring**: Sentry (errors), PostHog (analytics), Helicone (LLM costs)
- **Compliance**: EU AI Act audit logging (ai_audit_log table)

## Data Flow

```
API Sources → Collectors → pgmq Queues → Processing Pipeline → Embeddings → Ready Jobs
                                                                                 ↓
User Search Query → Embed Query → search_jobs_v2() [RRF: FTS + Semantic + Geo + Re-rank] → Results
```

## State Machine

```
raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready
                                                                    ↓
ready → expired → archived → deleted (hard delete after 180 days)
```

## Queue Flow

| Queue | Input Status | Output Status | Next Queue |
|---|---|---|---|
| parse_queue | raw | parsed | normalize_queue |
| normalize_queue | parsed | normalized | dedup_queue |
| dedup_queue | normalized | (gate only) | geocode_queue |
| geocode_queue | normalized | geocoded | embed_queue |
| embed_queue | geocoded | ready | (done) |
| dead_letter_queue | any failed | (unchanged) | auto-retry after 6h |

## Key Design Decisions

See `docs/adr/` for Architecture Decision Records.

- **Embeddings capture semantic intent, SQL filters handle factual constraints** (salary, location, type)
- **RRF (k=50)** combines FTS + semantic rankings without weight tuning
- **Pre-filter CTE** eliminates geographically distant jobs before expensive vector search
- **Rule-based extraction only** in pipeline (regex + ESCO dictionary, no LLM, no Instructor). LLM used only in web layer for match explanations (GPT-4o-mini).
- **raw_data JSONB** preserved on every job for reprocessing when logic improves
