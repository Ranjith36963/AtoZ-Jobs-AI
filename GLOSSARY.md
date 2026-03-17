# AtoZ Jobs AI — Glossary

Domain terminology for agents and developers working on this codebase.

---

## Job Market

| Term | Definition | Where Used |
|------|-----------|------------|
| **ESCO** | European Skills, Competences, Qualifications and Occupations taxonomy. 13,939 skills in `esco_skills` table. | `pipeline/src/skills/`, `supabase/migrations/000010` |
| **SIC Code** | Standard Industrial Classification — 5-digit code classifying company business activity. Maps to section letters A–U. | `pipeline/src/enrichment/companies_house.py` |
| **Seniority Level** | Job experience tier: junior, mid, senior, lead, executive. Extracted from title/description via regex. | `pipeline/src/processing/seniority.py`, `jobs.seniority_level` |
| **Employment Type** | Contract classification: full_time, part_time, contract, permanent, temporary, internship. Array column. | `jobs.employment_type` |
| **Location Type** | Work arrangement: remote, hybrid, onsite. Extracted from job description. | `jobs.location_type` |
| **Visa Sponsorship** | Whether employer sponsors UK work visas: yes, no, unknown. | `jobs.visa_sponsorship` |
| **DWP** | Department for Work and Pensions — UK government agency. Target users include DWP claimants. | Phase 3 SPEC §10.2 |

## Pipeline

| Term | Definition | Where Used |
|------|-----------|------------|
| **State Machine** | Job processing lifecycle: `raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready`. | `docs/architecture.md`, `jobs.status` |
| **DLQ** | Dead Letter Queue — failed jobs land here for auto-retry after 6 hours. | `dead_letter_queue` in pgmq |
| **Content Hash** | SHA-256 of `title + company + location + description`. Used for exact dedup. | `jobs.content_hash` |
| **MinHash/LSH** | Locality-Sensitive Hashing via datasketch + xxhash. Used for fuzzy dedup with composite scoring (threshold 0.65). | `pipeline/src/dedup/` |
| **Raw Data** | Original API response stored as JSONB. Never discarded — enables reprocessing. | `jobs.raw_data` |
| **Circuit Breaker** | Pattern protecting against cascading API failures. 3 failures → OPEN, 300s recovery → HALF_OPEN. 429s exempt. | `pipeline/src/collectors/circuit_breaker.py` |
| **Collector** | Module that fetches jobs from an external API. 4 paid (Reed, Adzuna, Jooble, Careerjet) + 7 free. | `pipeline/src/collectors/` |
| **Queue** | pgmq message queue. 6 queues: parse, normalize, dedup, geocode, embed, dead_letter. | `supabase/migrations/000004` |

## Search & Embeddings

| Term | Definition | Where Used |
|------|-----------|------------|
| **RRF** | Reciprocal Rank Fusion (k=50) — combines FTS + semantic rankings without weight tuning. | `search_jobs()`, `search_jobs_v2()` |
| **halfvec** | PostgreSQL pgvector type — half-precision 768-dimensional vector. Halves storage vs full float. | `jobs.embedding` column |
| **HNSW** | Hierarchical Navigable Small World — approximate nearest neighbour index for vector search. | `idx_jobs_embedding` index |
| **FTS** | Full-Text Search — PostgreSQL tsvector/tsquery with GIN index. | `jobs.search_vector` column |
| **Semantic Search** | Vector similarity search using cosine distance on embeddings. | `search_jobs()`, `search_jobs_v2()` |
| **Cross-Encoder** | `ms-marco-MiniLM-L-6-v2` model that scores query-document relevance. Used for re-ranking top results. | `pipeline/src/modal_app.py` (search endpoint) |
| **Re-ranking** | Second-pass scoring of search results using cross-encoder for better relevance ordering. | Phase 2 SPEC §8 |
| **Pre-filter CTE** | Common Table Expression that eliminates geographically distant jobs before expensive vector search. | `search_jobs()` |
| **search_jobs()** | Phase 1 hybrid search function. RRF combining FTS + semantic + geo. Preserved in Phase 2+. | `supabase/migrations/000008` |
| **search_jobs_v2()** | Phase 2 enhanced search. 12 params, 18 return fields, skill/category/salary/dedup filters. | `supabase/migrations/000013` |

## ML Models

| Term | Definition | Where Used |
|------|-----------|------------|
| **Gemini embedding-001** | Google's embedding model. 768 dimensions. Primary embedding provider. Free tier. | `pipeline/src/embeddings/` |
| **text-embedding-3-small** | OpenAI embedding model. Fallback only when Gemini fails. | `pipeline/src/embeddings/` |
| **GPT-4o-mini** | OpenAI LLM used for match explanations in Phase 3. Not used for extraction/processing. | `web/app/api/explain/route.ts` |
| **XGBoost** | Gradient boosting model for salary prediction. max_depth=6, 200 rounds. | `pipeline/src/salary/` |
| **SpaCy en_core_web_sm** | NLP model for skills extraction via PhraseMatcher (LOWER + ORTH layers). | `pipeline/src/skills/` |

## Infrastructure

| Term | Definition | Where Used |
|------|-----------|------------|
| **Modal** | Serverless Python compute platform. Runs 6 cron functions + callable tasks. | `pipeline/src/modal_app.py` |
| **Supabase** | PostgreSQL-as-a-service with built-in auth, RLS, realtime, and REST API. | All database operations |
| **pgvector** | PostgreSQL extension for vector similarity search. Provides halfvec type and HNSW indexes. | `supabase/migrations/000001` |
| **PostGIS** | PostgreSQL extension for geographic data. geography(Point,4326) column for location. | `supabase/migrations/000001`, `jobs.location_point` |
| **pg_trgm** | PostgreSQL trigram extension for fuzzy text matching. Used in dedup. | `supabase/migrations/000001` |
| **pgmq** | PostgreSQL Message Queue extension. Powers all 6 pipeline queues. | `supabase/migrations/000004` |
| **pg_cron** | PostgreSQL cron scheduler. Refreshes materialized views every 30 min. | `supabase/migrations/000004`, `000019` |
| **PgBouncer** | Connection pooler included with Supabase Pro. Transaction mode. | Phase 3 SPEC §12.2 |
| **Cloudflare Pages** | Static + SSR hosting. Free tier, unlimited bandwidth, commercial OK. | `web/wrangler.toml` |
| **OpenNext** | Adapter that deploys Next.js to Cloudflare Workers. | `web/open-next.config.ts` |
| **Helicone** | LLM observability proxy. Tracks token counts, cost, caching. Free tier (10K req/mo). | `web/app/api/explain/route.ts` |
| **LiteLLM** | LLM proxy for budget controls and model switching. | Phase 3 SPEC §2.1 |

## Compliance

| Term | Definition | Where Used |
|------|-----------|------------|
| **EU AI Act** | European regulation on AI systems. AtoZ Jobs is HIGH-RISK under Annex III (employment AI). Enforcement: Aug 2, 2026. | Phase 3 SPEC §9 |
| **Article 12** | EU AI Act — automatic logging of all AI decisions. Implemented via `ai_decision_audit_log` table. | `supabase/migrations/000018` |
| **Article 14** | EU AI Act — human oversight. Job matches are "recommendations, not decisions." | Phase 3 SPEC §9.2 |
| **Article 50** | EU AI Act — transparency. `<AIDisclosure>` component on every AI-generated element. | `web/components/ui/AIDisclosure.tsx` |
| **WCAG 2.1 AA** | Web Content Accessibility Guidelines. Minimum compliance level for all pages. | Phase 3 SPEC §10, GATES §4 |
| **RLS** | Row-Level Security — PostgreSQL feature enforcing per-row access control. Enabled on every table. | All migrations, `security-critical.md` |
| **GDPR Article 22** | Right not to be subject to automated decisions with legal effect. Applies to job ranking. | Phase 3 SPEC §9.3 |

## Database Views

| Term | Definition | Where Used |
|------|-----------|------------|
| **mv_search_facets** | Materialized view with category/location_type/seniority/employment_type counts. Refreshed every 30 min. | `supabase/migrations/000019` |
| **mv_salary_histogram** | Materialized view with salary distribution buckets for range slider. Refreshed every 30 min. | `supabase/migrations/000019` |
| **mv_skill_demand** | Materialized view of skill frequency across ready jobs. | Phase 2 migration |
| **mv_skill_cooccurrence** | Materialized view of which skills appear together. | Phase 2 migration |
| **pipeline_health** | View summarizing queue depths, DLQ count, job status counts. | `supabase/migrations/000004` |
