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
- just health: Query pipeline_health view

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

## Critical Rules
- When uncertain, state uncertainty. Present tradeoffs, do not choose silently.
- For complex tasks, plan before coding. Do not implement without approved plan.
- One logical change per commit. Conventional commit messages.
- Preserve raw_data JSONB on every job — enables reprocessing when logic improves.
