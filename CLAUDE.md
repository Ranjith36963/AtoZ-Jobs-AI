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

## Security Rules

These rules are non-negotiable. Violations must be fixed before commit.

1. **No hardcoded secrets.** Always use .env files (gitignored). Never commit API keys, tokens, or passwords.
2. **Supabase RLS enforced on every table.** No exceptions. Anon key is browser-safe only because RLS restricts access.
3. **Service role key is server-only.** Never expose SUPABASE_SERVICE_ROLE_KEY to browser or frontend code.
4. **Parameterized queries only.** All SQL queries use parameterized statements (Supabase client handles this). No string concatenation in queries.
5. **OWASP Top 10 review** after writing any auth, input handling, or data processing code.
6. **Input validation at boundaries.** Zod (TypeScript) or Pydantic (Python) at every external input point.
7. **No raw HTML rendering** of user input or API response data without sanitization.
8. **Rate limiting** on all public-facing endpoints to prevent abuse.

## Test Standards

1. **TDD required.** Write tests first, confirm they fail, then implement.
2. **Pre-computed expectations.** Compare against known expected values, never against function output.
3. **Sad paths required.** Every test file must include: null, empty, timeout, rate limit, malformed data, auth expiry.
4. **Property-based testing.** Use hypothesis @given() for parsers (salary, location, seniority). Parser must never raise unhandled exception on arbitrary input.
5. **Coverage minimums.** Pipeline: 80%. Collectors: 85%. Processing: 90%. Web: 60%.
6. **Contract tests.** Save real API response samples to tests/fixtures/. Test adapters against these fixtures.
7. **One test file per module.** Named test_{module_name}.py.
8. **Async tests.** Use pytest-asyncio with asyncio_mode = "auto".

## CI/CD Rules

1. **Pin all GitHub Actions to specific versions.** Use `actions/checkout@v4`, never `@main` or `@latest`. Unpinned actions are a supply chain risk.
2. **Pin Node.js version to 20.x.** Must match the version used in `.github/workflows/`.
3. **Pin Python version to 3.12.** Must match `requires-python` in `pipeline/pyproject.toml`.
4. **Never hardcode branch names as push targets.** Use `${{ github.ref }}` or workflow inputs.
5. **Reference secrets via `${{ secrets.X }}`.** Never inline secret values. Never echo secrets to logs.
6. **Set `timeout-minutes` on every job.** Default: 30 minutes.
7. **Use correct package managers.** `pnpm` for web (never `npm`), `uv` for pipeline (never `pip` directly). Install with `--frozen-lockfile` / `--frozen`.
8. **Upload test artifacts.** Use `actions/upload-artifact@v4` for test results and coverage reports.

## Never Do This

- Never rotate secrets autonomously. Direct the user to rotate secrets manually with explicit confirmation at each step.
- Never run `supabase secrets set`, `doppler secrets set`, or `modal secret create` without explicit user instruction.
- Never deploy without passing all pre-flight gates and receiving explicit user confirmation.
- Never modify a deployed migration — create a new one instead.

## Agents

5 specialized sub-agents available in `.claude/agents/`:

| Agent | When to invoke |
|-------|---------------|
| `security-auditor` | PR reviews, deploy gates, security/architecture/dependency/performance audits |
| `debugger` | Investigating failures across pipeline, search, or frontend |
| `tdd-enforcer` | Validating test compliance after implementation |
| `migration-deployer` | Verifying migration safety before deploying schema changes |
| `status-reporter` | System health checks after deployments or during monitoring |

## Skills

9 skills in `.claude/skills/`:

| Skill | Invoke |
|-------|--------|
| `migration-safety` | Auto — when editing migrations or schema |
| `testing-patterns` | Auto — when writing tests |
| `api-conventions` | Auto — when adding API routes or collectors |
| `health-check` | Auto — when checking system health |
| `seed-data` | Auto — when seeding database |
| `onboarding` | Auto — when setting up dev environment |
| `deploy` | Manual — `/deploy` |
| `fix-issue` | Manual — `/fix-issue` |
| `pr-review` | Manual — `/pr-review` |

## Critical Rules

- When uncertain, state uncertainty. Present tradeoffs, do not choose silently.
- For complex tasks, plan before coding. Do not implement without approved plan.
- One logical change per commit. Conventional commit messages.
- Preserve raw_data JSONB on every job — enables reprocessing when logic improves.
