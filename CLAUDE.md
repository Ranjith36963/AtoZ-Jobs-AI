# AtoZ Jobs AI

UK AI-powered job search engine. Python pipeline (uv) + Next.js web app (pnpm) + Supabase (PostgreSQL).

## Commands — Pipeline (pipeline/)
- uv run pytest: Run all Python tests
- uv run pytest -x: Stop on first failure
- uv run ruff check . --fix: Lint and auto-fix
- uv run ruff format .: Format code
- uv run mypy src/: Type check

## Commands — Web (web/)
- pnpm dev: Start dev server
- pnpm test: Run vitest
- pnpm lint: ESLint check
- pnpm typecheck: TypeScript strict check
- pnpm build: Production build

## Commands — Database (root)
- just migrate: Run supabase db push
- just reset: Run supabase db reset (verifies full migration chain)
- just seed: Load seed data
- just seed-dev: Seed + sample jobs for development
- just seed-perf: Seed + 10K+ jobs for load testing
- just health: Query pipeline_health view
- just migrate-rollback: Apply latest down.sql manually
- just deploy-pipeline: Deploy Modal functions
- just deploy-web: Build web for deployment

## Architecture
See @docs/architecture.md for system design.
See @docs/adr/ for architecture decision records.

State machine: raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready
6 queues: parse_queue → normalize_queue → dedup_queue → geocode_queue → embed_queue + dead_letter_queue
Key insight: embeddings capture semantic intent, SQL filters handle factual constraints.

## Code Style — Python
- Python 3.12+, Pydantic v2 for ALL data models
- async/await for all I/O (httpx, database, embeddings)
- Rule-based extraction only. No LLM. No Instructor in Phase 1.
- google-genai for embeddings. OpenAI as fallback only. No LLM calls.
- Type hints on every function. No Any types.
- Docstrings on public functions only (Google style)

## Code Style — TypeScript
- TypeScript strict mode, zero `any` types
- Named exports only, never default exports
- tRPC for complex logic (search, recommendations), direct Supabase client for simple reads
- Server Actions for simple form mutations ONLY
- Zod validation at every API boundary

## Testing
- TDD: Write tests first, confirm they fail, then implement
- Compare against pre-computed expectations, never function output
- Include sad paths: null, empty, timeout, rate limit, malformed data, auth expiry
- Python: pytest + pytest-asyncio + hypothesis (property-based)
- TypeScript: vitest + @testing-library/react
- Coverage: 80% pipeline, 60% web minimum

## Database
- ALL queries use parameterized statements (Supabase client handles this)
- Migrations: write manually for functions/RLS/complex logic, use `supabase db diff` for DDL
- Every migration MUST have a corresponding rollback in the down.sql file
- NEVER modify production via Dashboard once live
- Row-Level Security enforced on every table

## Error Handling
- Every function handling external input: handle null, empty, timeout, malformed, rate limit
- Pipeline: retry 3x with exponential backoff, then DLQ
- Embedding failures: retry → Gemini → OpenAI fallback → skip embedding
- Web: Zod validation → typed error response → user-friendly message

## Security
- NEVER hardcode secrets. Always .env files (gitignored)
- NEVER commit API keys, tokens, or passwords
- After writing auth/input/data code, review for OWASP Top 10
- Supabase RLS enforced on every table — no exceptions

## Phase 2 Additions
- **Skills**: Regex + ESCO dictionary matching (~147 patterns), dictionary_builder for pattern generation
- **Dedup**: pg_trgm fuzzy matching + MinHash/LSH (datasketch, xxhash) + composite scoring (threshold 0.65)
- **Salary**: XGBoost prediction with TF-IDF + one-hot region/category + ordinal seniority features
- **Enrichment**: Companies House API client with SIC code → section letter (A-U) mapping
- **Search**: search_jobs_v2() with 12 params, 18 return fields, duplicate exclusion, skill filters
- **Re-ranking**: cross-encoder/ms-marco-MiniLM-L-6-v2 for query-document relevance scoring
- **Profiles**: user_profiles table with RLS, 768-dim Gemini embeddings for personalization
- **Migrations**: 000010 (skills taxonomy), 000011 (advanced dedup), 000012 (salary/company), 000013 (user profiles/search_v2), 000014 (phase2 RLS), 000015 (fuzzy duplicates function), 000016 (category_raw/contract_type), 000017 (pgmq permissions)

## Phase 3 Additions
- **Web**: Next.js 16 on Cloudflare Pages, tRPC search, Supabase SSR
- **AI Explanations**: GPT-4o-mini match explanations via Vercel AI SDK (budget-capped $45/mo)
- **EU AI Act**: ai_audit_log table for transparency compliance
- **Search Facets**: Aggregated counts for filters (category, location, type)
- **Monitoring**: Sentry (errors), PostHog (analytics), Helicone (LLM cost tracking)
- **Migrations**: 000018 (ai_audit_log), 000019 (search_facets)

## Critical Rules
- When uncertain, state uncertainty. Present tradeoffs, do not choose silently.
- For complex tasks, plan before coding. Do not implement without approved plan.
- One logical change per commit. Conventional commit messages.
- Preserve raw_data JSONB on every job — enables reprocessing when logic improves.
