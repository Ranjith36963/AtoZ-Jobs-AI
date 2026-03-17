# ADR 0001: Semantic Embeddings + Hybrid RRF Search Over Pure Keyword Search

**Status:** Accepted
**Date:** 2026-03-01 (Phase 1)
**Deciders:** Project lead

## Context

AtoZ Jobs AI needs to match job seekers with relevant UK jobs. Pure keyword search (SQL `LIKE` or full-text search) fails to capture semantic intent — a search for "Python developer" misses postings titled "Software Engineer" that require Python. Job descriptions use inconsistent terminology, abbreviations, and varied phrasing across 11 API sources.

## Decision

Use **Gemini embedding-001** (768-dimensional vectors stored as `halfvec`) combined with **Reciprocal Rank Fusion (RRF, k=50)** to merge full-text search and semantic search rankings.

### Architecture

1. **Embedding pipeline stage:** Every job gets a 768-dim Gemini embedding computed from `title + description_plain + location_city + category`
2. **Storage:** `halfvec(768)` column with HNSW index (`idx_jobs_embedding`, `vector_cosine_ops`)
3. **Search function:** `search_jobs()` runs both FTS (tsvector + GIN) and semantic (HNSW cosine) in parallel CTEs, then merges with RRF
4. **Pre-filter CTE:** Eliminates geographically distant jobs before vector search to reduce cost
5. **Fallback chain:** Gemini → OpenAI `text-embedding-3-small` → skip embedding

### Key Insight

> Embeddings capture semantic intent. SQL filters handle factual constraints (salary, location, type).

## Consequences

### Positive
- Semantic understanding: "Python developer" matches "Software Engineer" requiring Python
- Typo resilience: embeddings capture meaning despite spelling errors (Phase 3 test Q9)
- RRF avoids manual weight tuning between FTS and semantic scores
- halfvec halves storage compared to full float vectors

### Negative
- **pgvector dependency:** Requires PostgreSQL with pgvector extension (Supabase provides this)
- **Embedding pipeline stage:** Every job must be embedded before becoming `ready`
- **Fallback chain needed:** Gemini outages require OpenAI fallback, adding complexity
- **HNSW tuning:** `ef_search` parameter affects recall vs speed tradeoff (60 in Phase 1, 100 in Phase 3)

### Cost
- Gemini embedding-001: Free tier covers ~100K embeddings/month
- OpenAI fallback: Pay-per-use, only triggered on Gemini failure
- Storage: ~1.5KB per halfvec(768) per job

## References
- Phase 1 SPEC §4 (Embedding Pipeline)
- `docs/architecture.md` (Search data flow)
- `supabase/migrations/20260301000008_search_jobs.sql` (search_jobs function)
