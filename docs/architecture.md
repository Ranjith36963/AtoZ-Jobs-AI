# AtoZ Jobs AI — Architecture

## System Overview

UK AI-powered job search engine combining semantic search (embeddings) with structured SQL filters.

## Components

### Pipeline (Python)
- **Collectors**: 4 API sources (Reed, Adzuna, Jooble, Careerjet) with circuit breaker pattern
- **Processing**: Salary normalization, location geocoding, category mapping, seniority extraction, skill extraction
- **Embeddings**: Gemini embedding-001 (768-dim) with OpenAI fallback
- **Compute**: Modal serverless (5 scheduled cron functions)

### Database (Supabase PostgreSQL)
- **Extensions**: pgvector (HNSW), PostGIS (geography), pg_trgm (fuzzy), pgmq (queues), pg_cron
- **Tables**: sources, companies, jobs, skills, job_skills
- **Search**: Hybrid RRF combining full-text search (tsvector) + semantic search (halfvec cosine)
- **Security**: Row-Level Security on every table

### Web (Next.js)
- **Hosting**: Cloudflare Pages
- **API**: tRPC for search, direct Supabase client for reads
- **Auth**: Supabase anon key (RLS enforced)

## Data Flow

```
API Sources → Collectors → pgmq Queues → Processing Pipeline → Embeddings → Ready Jobs
                                                                                 ↓
User Search Query → Embed Query → search_jobs() [RRF: FTS + Semantic + Geo] → Results
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
- **Rule-based extraction only** in Phase 1 (no LLM, no Instructor)
- **raw_data JSONB** preserved on every job for reprocessing when logic improves
