# AtoZ Jobs AI — Phase 1 Playbook

**How to build it. Stage-by-stage Claude Code instructions.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and GATES.md (verification).

---

## 0. Before You Start

### 0.1 Prerequisites

- Docker Desktop running (for Supabase local)
- Node.js 20+ and `pnpm` installed globally
- Python 3.12+ and `uv` installed (`pip install uv`)
- Supabase CLI installed (`npx supabase init` or `brew install supabase`)
- `just` installed (`brew install just` or `cargo install just`)
- Claude Code installed and authenticated
- GitHub repo created (empty)
- API keys ready: Reed, Adzuna, Jooble, Careerjet, Google (Gemini)

### 0.2 The Workflow (Every Task)

From the Claude Code Bible — follow this religiously:

```
/clear                                          ← Clean context
ultrathink and plan [task]. Do NOT code yet.    ← Plan first
[review plan, challenge assumptions]            ← Human checks
Implement the plan.                             ← Code
uv run pytest / pnpm test                       ← Tests must pass
git add -A && git commit                        ← Conventional commit
```

### 0.3 When to /clear and /compact

| Trigger | Action |
|---|---|
| Starting a new stage (Foundation → Collection → Processing → Maintenance) | `/clear` |
| Switching between Python and TypeScript work | `/clear` |
| Context getting long (>50 turns) | `/compact 'Focus on [current task]'` |
| After completing and committing a major file | `/compact` |
| Claude starts hallucinating or repeating itself | `/clear` and restart with refined prompt |

---

## 1. Stage 1: Foundation (Week 1)

**Branch:** `data-phase` (created once, used for all Phase 1 stages)

```bash
git checkout -b data-phase
```

### 1.1 Create Monorepo Structure

**Prompt to Claude Code:**

```
Create the following directory structure. Do not create any code files yet, only directories and config files.

repo/
├── CLAUDE.md
├── justfile
├── .gitignore
├── .env.example
├── pipeline/
│   ├── CLAUDE.md
│   ├── pyproject.toml
│   └── src/
│       ├── __init__.py
│       ├── collectors/
│       ├── processing/
│       ├── embeddings/
│       ├── skills/
│       ├── models/
│       ├── maintenance/
│       └── tests/
│           └── fixtures/
├── web/
│   ├── CLAUDE.md
│   ├── package.json
│   └── src/
├── supabase/
│   ├── migrations/
│   ├── seed.sql
│   └── config.toml
├── docs/
│   ├── phase-1/
│   │   ├── SPEC.md
│   │   ├── PLAYBOOK.md
│   │   └── GATES.md
│   ├── architecture.md
│   ├── adr/
│   └── STATUS.md
└── .claude/
    ├── settings.json
    ├── agents/
    │   ├── security-auditor.md
    │   └── architecture-reviewer.md
    ├── skills/
    │   ├── testing-patterns/SKILL.md
    │   ├── migration-safety/SKILL.md
    │   └── api-conventions/SKILL.md
    ├── rules/
    │   ├── security-critical.md
    │   └── test-standards.md
    └── commands/
        ├── pr-review.md
        └── fix-issue.md
```

### 1.2 Create CLAUDE.md (Root)

**CRITICAL: Apply Doc 11 authority corrections.** The CLAUDE.md content from Doc 6 has 3 stale lines that MUST be corrected:

| Doc 6 says | Correct for Phase 1 (Doc 11) |
|---|---|
| "Instructor for structured LLM extraction, never raw prompts" | "Rule-based extraction only. No LLM. No Instructor in Phase 1." |
| "Direct OpenAI/Anthropic SDK calls, NEVER LangChain" | "google-genai for embeddings. OpenAI as fallback only. No LLM calls." |
| "LLM failures: retry → model cascade (Claude Sonnet → GPT-4o-mini → cached)" | "Embedding failures: retry → Gemini → OpenAI fallback → skip embedding" |

**Prompt to Claude Code:**

```
Create CLAUDE.md with the following content. This is under 120 lines. Every line is deliberate.

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
```

### 1.3 Create .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest *)", "Bash(uv run ruff *)", "Bash(uv run mypy *)",
      "Bash(pnpm test *)", "Bash(pnpm lint *)", "Bash(pnpm typecheck)",
      "Bash(just *)", "Bash(git status *)", "Bash(git diff *)",
      "Read(./pipeline/**)", "Edit(./pipeline/**)",
      "Read(./web/**)", "Edit(./web/**)",
      "Read(./supabase/**)", "Edit(./supabase/**)",
      "Read(./docs/**)", "Edit(./docs/**)"
    ],
    "deny": [
      "Read(./.env)", "Read(./.env.*)", "Read(./.env.local)",
      "Read(./secrets/**)",
      "Bash(git push --force *)", "Bash(git reset --hard *)",
      "Bash(rm -rf *)",
      "Bash(*drop*database*)", "Bash(*truncate*)",
      "Bash(*migrate reset*--force*)", "Bash(*--production*)"
    ]
  }
}
```

### 1.4 Create .env.example

```
# === API Keys (Pipeline) ===
REED_API_KEY=                    # Basic Auth username, empty password
ADZUNA_APP_ID=                   # Query param: app_id
ADZUNA_APP_KEY=                  # Query param: app_key
JOOBLE_API_KEY=                  # In URL path
CAREERJET_AFFID=                 # Query param: affid

# === Embeddings ===
GOOGLE_API_KEY=                  # Gemini API (gemini-embedding-001)

# === Database ===
SUPABASE_URL=                    # https://<ref>.supabase.co
SUPABASE_ANON_KEY=               # Public (browser, RLS enforced)
SUPABASE_SERVICE_ROLE_KEY=       # Private (server-only, NEVER browser)
DATABASE_URL=                    # Direct PostgreSQL connection

# === Deployment ===
MODAL_TOKEN_ID=
MODAL_TOKEN_SECRET=

# === Monitoring ===
SENTRY_DSN=                      # Error tracking
NEXT_PUBLIC_POSTHOG_API_KEY=     # Product analytics (browser-safe)
```

### 1.5 Create justfile

```just
# AtoZ Jobs AI — unified commands

# === Development ===
dev-pipeline:
    cd pipeline && uv run python -m src.main

dev-web:
    cd web && pnpm dev

# === Testing ===
test:
    cd pipeline && uv run pytest
    cd web && pnpm test

test-pipeline:
    cd pipeline && uv run pytest -x --cov=src --cov-fail-under=80

test-web:
    cd web && pnpm test -- --coverage

# === Linting ===
lint:
    cd pipeline && uv run ruff check . --fix && uv run ruff format .
    cd web && pnpm lint

typecheck:
    cd pipeline && uv run mypy src/
    cd web && pnpm typecheck

# === Database ===
migrate:
    supabase db push

reset:
    supabase db reset

seed:
    supabase db reset
    psql $DATABASE_URL -f supabase/seed.sql

seed-dev:
    just seed
    cd pipeline && uv run python -m src.tests.seed_jobs

seed-perf:
    just seed
    cd pipeline && uv run python -m src.tests.seed_bulk

health:
    psql $DATABASE_URL -c "SELECT * FROM pipeline_health;"

migrate-rollback:
    @echo "Apply the most recent down.sql manually against local DB"

# === Deployment ===
deploy-pipeline:
    cd pipeline && modal deploy src/modal_app.py

deploy-web:
    cd web && pnpm build
```

### 1.6 Create pyproject.toml

```
[project]
name = "atoz-jobs-pipeline"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.28.1",
    "pydantic>=2.12",
    "google-genai>=1.0",
    "structlog>=24.0",
    "numpy>=1.26",
    "supabase>=2.0",
    "beautifulsoup4>=4.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "hypothesis>=6.0",
    "ruff>=0.8",
    "mypy>=1.13",
    "faker>=33.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["src/tests"]

[tool.ruff]
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
```

### 1.7 Initialize Supabase and Write Migrations

**Prompt to Claude Code:**

```
Initialize Supabase local dev:
  supabase init
  supabase start

Then write 5 migrations as specified in SPEC.md §1.1–1.5.
Each migration gets up.sql AND down.sql:

  supabase/migrations/
    20260301000001_extensions/up.sql + down.sql
    20260301000002_core_tables/up.sql + down.sql
    20260301000003_indexes/up.sql + down.sql
    20260301000004_queues_cron_health/up.sql + down.sql
    20260301000005_rls_policies/up.sql + down.sql

Copy the exact SQL from SPEC.md. Do NOT improvise.
After writing, run: supabase db reset
It must complete with zero errors.
```

**IMPORTANT:** Supabase CLI expects migrations as single files at `supabase/migrations/TIMESTAMP_name.sql`. The `up.sql` / `down.sql` convention means: commit the up.sql content as the migration file, and keep the down.sql alongside it for rollback reference. Test rollback by running down.sql manually on local.

### 1.8 Write seed.sql

```
Write supabase/seed.sql with Tier 1 reference data from SPEC.md §1.6:
- 4 sources (reed, adzuna, jooble, careerjet)
- 11 internal categories
- ~100 UK cities with lat/lon coordinates

Run: supabase db reset (which loads seed.sql automatically)
Verify: SELECT count(*) FROM sources; → 4
```

### 1.9 Verify and Merge

```bash
supabase db reset                     # Full migration chain
just health                           # pipeline_health view returns 14 columns
git add -A
git commit -m "feat(foundation): migrations, CLAUDE.md, .claude/, seed data"
```

**`/clear` — Start fresh for Stage 2. Stay on `data-phase`.**

---

## 2. Stage 2: Collection (Week 2)

**Branch:** `data-phase` (continuing from Stage 1)

### 2.1 TDD: Write Tests First

**Prompt to Claude Code:**

```
Write tests FIRST for all 4 collectors. Tests must FAIL initially.
Reference SPEC.md §2.1–2.4 for exact API contracts.

Create these test files:
  pipeline/src/tests/test_reed_collector.py
  pipeline/src/tests/test_adzuna_collector.py
  pipeline/src/tests/test_jooble_collector.py
  pipeline/src/tests/test_careerjet_collector.py
  pipeline/src/tests/test_circuit_breaker.py

For each collector, test:
1. Maps source JSON to JobBase Pydantic model correctly (unit)
2. Contract test with mock API response from tests/fixtures/{source}_response.json
3. Edge cases: empty results, 429 rate limit, 500 server error, timeout, malformed JSON
4. Pagination boundary: exactly max results per page — is there a next page?
5. content_hash is computed and stable for identical inputs

Save real API response samples to tests/fixtures/ for contract tests.
Use httpx.MockTransport for mocking.

Run: uv run pytest — all tests should FAIL.
```

### 2.2 Create Pydantic Models

**Prompt to Claude Code:**

```
Create pipeline/src/models/job.py with the JobBase Pydantic model
and source adapters exactly as specified in the project docs.

JobBase fields: source_name, external_id, source_url, title, description,
description_plain, company_name, location_raw, latitude, longitude,
salary_min, salary_max, salary_raw, salary_period, salary_currency,
salary_is_predicted, employment_type (list[str]), contract_type,
date_posted, date_expires, category_raw, raw_data (dict).

@computed_field content_hash: SHA-256 of lowercase(title|company|location).

@field_validator for not_empty on title, description, company_name.
@field_validator for salary_sanity: reject < 0 or > 1,000,000.

Then create 4 adapters: ReedJobAdapter, AdzunaJobAdapter,
JoobleJobAdapter, CareerjetJobAdapter.

Each adapter has a static to_job_base(data: dict) -> JobBase method.
Map source-specific field names to the universal schema.
See SPEC.md §2.1–2.4 for exact field mappings.
```

### 2.3 Build Collectors

**Prompt to Claude Code (one collector at a time):**

```
Build pipeline/src/collectors/reed.py

Requirements from SPEC.md §2.1:
- Base URL: https://www.reed.co.uk/api/1.0/search
- Auth: Basic Auth with API key as username, empty password
- Rate limit: max 2 req/sec (0.5s sleep between requests)
- Category sweep: iterate Reed sectors with postedWithin=1
- Pagination: resultsToTake=100, resultsToSkip for offset
- Use ReedJobAdapter.to_job_base() for each result
- UPSERT into Supabase via service_role client
- Circuit breaker: 3 failures → OPEN, 300s recovery

After building, run: uv run pytest src/tests/test_reed_collector.py
All tests must PASS.
```

Repeat for Adzuna, Jooble, Careerjet. Key differences per source:

**Adzuna:** Extract `latitude`/`longitude` directly from response. `salary_is_predicted` flag. Category via `category.tag`. 50 results/page. 1s sleep.

**Jooble:** POST request with API key in URL path. No `totalResults` — paginate until empty. Keyword sweep instead of category sweep. 1s sleep.

**Careerjet:** GET request to v4 endpoint. `affid`, `user_ip`, `user_agent` required. Use `httpx` directly (Python 2 library deprecated). 1s sleep.

### 2.4 Build Circuit Breaker

```
Build pipeline/src/collectors/circuit_breaker.py

3 states: CLOSED → OPEN → HALF_OPEN
failure_threshold = 3
recovery_timeout = 300 seconds
Failures: httpx.TimeoutError, HTTPStatusError (5xx), connection errors
429 does NOT trip — triggers Retry-After backoff instead.
```

### 2.5 Build Error Classes

```
Create pipeline/src/models/errors.py with 7 error types from SPEC.md:
- ValidationError (retry=False)
- RateLimitError (retry=True, max 3, backoff=Retry-After header)
- TimeoutError (retry=True, max 3, backoff=2^n seconds)
- ParseError (retry=False, alert if >5% of source)
- EmbeddingError (retry=True, max 3, cascade to fallback)
- GeocodingError (retry=True, max 2, fallback to city table)
- DuplicateError (retry=False, skip silently)
```

### 2.6 Create Modal App

**Prompt to Claude Code:**

```
Create pipeline/src/modal_app.py with 7 scheduled functions.
Exact spec from Doc 9:

app = modal.App("atoz-jobs-pipeline")

Image: debian_slim(python_version="3.12") + 7 pip packages:
httpx, pydantic, google-genai, structlog, numpy, supabase, beautifulsoup4

Secrets: modal.Secret.from_name("atoz-env")

Functions:
1. fetch_reed:     Cron("*/30 * * * *")
2. fetch_adzuna:   Cron("0 * * * *")
3. fetch_jooble:   Cron("0 */2 * * *")
4. fetch_careerjet: Cron("30 */2 * * *")
5. process_queues: Cron("*/15 * * * *")
6. daily_maintenance: Cron("0 3 * * *")
7. monthly_reindex: Cron("0 3 1 * *")

NOTE: Modal Starter allows 5 deployed crons. Consolidate:
- Combine fetch_jooble + fetch_careerjet into one function (fetch_aggregators)
- That gives: fetch_reed, fetch_adzuna, fetch_aggregators, process_queues, daily_maintenance = 5
- monthly_reindex can be triggered inside daily_maintenance on day 1.
```

### 2.7 Verify and Merge

```bash
uv run pytest --cov=src/collectors --cov-fail-under=85
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(pipeline): 4 collectors with circuit breaker and Modal deploy"
```

**`/clear` — Start fresh for Stage 3. Stay on `data-phase`.**

---

## 3. Stage 3: Processing (Week 3)

**Branch:** `data-phase` (continuing from Stage 2)

### 3.1 TDD: Write Tests First

**Prompt to Claude Code:**

```
Write tests FIRST for all processors. Tests must FAIL initially.

Files:
  pipeline/src/tests/test_salary_normalizer.py
  pipeline/src/tests/test_location_normalizer.py
  pipeline/src/tests/test_category_mapper.py
  pipeline/src/tests/test_seniority.py
  pipeline/src/tests/test_structured_summary.py
  pipeline/src/tests/test_skill_extractor.py
  pipeline/src/tests/test_embeddings.py
  pipeline/src/tests/test_dedup.py

Salary tests: all 12 patterns from SPEC.md §3.3.
  "£25,000 - £30,000" → min=25000, max=30000
  "£300 per day" → annual_min=75600, annual_max=75600 (252 days)
  "£15-£20 per hour" → annual range using 1950 hours
  "Competitive" → NULL, NULL
  Sanity: reject < 10000 or > 500000

Location tests: all 10 cases from SPEC.md §3.4.
  "London" → city=London, region=Greater London, Central London coords
  "Remote" → location_type=remote, no geometry
  "Hybrid - Leeds" → location_type=hybrid, geocode Leeds

Category tests:
  Reed "IT & Telecoms" → "Technology"
  Adzuna "it-jobs" → "Technology"
  Title "Senior Python Developer" → "Technology" (keyword inference)
  Title "Executive Chef" → "Hospitality"
  Title "Office Manager" → "Other" (no match)

Seniority tests:
  "Junior Python Developer" → "Junior"
  "Senior Data Engineer" → "Senior"
  "Head of Engineering" → "Executive"
  "Data Analyst" → "Not specified"

Summary tests: verify 6-field template output (NO Summary field, NO Requirements field)

Skill tests:
  "Python developer with AWS experience" → extracts at least ['Python', 'AWS']

Embedding tests: mock Gemini API, verify 768-dim output, verify re-normalization.

Dedup tests: same title+company+location → same hash → second is skipped.

Use hypothesis @given(st.text()) for salary parser — must never raise unhandled exception.

Run: uv run pytest — all new tests should FAIL.
```

### 3.2 Build Processors (Order Matters)

Build in this exact order — each depends on the previous:

**3.2.1 Salary Normalizer**

```
Build pipeline/src/processing/salary.py

Constants: UK_WORKING_DAYS_PER_YEAR = 252, UK_WORKING_HOURS_PER_YEAR = 1950, UK_MONTHS_PER_YEAR = 12
12 regex patterns from SPEC.md §3.3.
Priority: structured API fields first → parse salary_raw text → sanity check (10K–500K).
Run tests: uv run pytest src/tests/test_salary_normalizer.py
```

**3.2.2 Location Normalizer**

```
Build pipeline/src/processing/location.py

10 cases from SPEC.md §3.4.
Geocoding pipeline: Adzuna lat/lon → extract UK postcode → postcodes.io bulk → city table → fallback.
postcodes.io: POST /postcodes, batch of 100, 200ms delay, max 3 retries.
Run tests: uv run pytest src/tests/test_location_normalizer.py
```

**3.2.3 Category Mapper**

```
Build pipeline/src/processing/category.py

Reed → internal mapping table (11 categories).
Adzuna → internal mapping table.
Jooble/Careerjet → title keyword inference with pre-compiled regex patterns.
~50 keywords across 10 categories. Default: 'Other'.
Run tests: uv run pytest src/tests/test_category_mapper.py
```

**3.2.4 Seniority Extractor**

```
Build pipeline/src/processing/seniority.py

5 regex patterns against job title. Default: 'Not specified'.
Run tests: uv run pytest src/tests/test_seniority.py
```

**3.2.5 Structured Summary Builder**

```
Build pipeline/src/processing/summary.py

6-field template from SPEC.md §3.7. NO Summary field. NO Requirements field. NO LLM.
All fields are rule-based. Input: normalized job dict. Output: text string for embedding.
Run tests: uv run pytest src/tests/test_structured_summary.py
```

**3.2.6 Skill Extractor**

```
Build pipeline/src/skills/extractor.py and pipeline/src/skills/dictionary.py

dictionary.py: placeholder SKILLS_DICT with ~100 common skills for now.
  Full ESCO + SkillNER merge is a separate ~4 hour task (see SPEC.md §3.8).
  Start with: Python, JavaScript, React, AWS, SQL, Docker, Kubernetes,
  Project Management, ACCA, CIMA, CSCS, NMC, CIPD, DBS check, etc.

extractor.py: tokenize description_plain, case-insensitive lookup against dict,
  order by frequency, cap at 15 skills, confidence=1.0 for exact matches.
Run tests: uv run pytest src/tests/test_skill_extractor.py
```

**3.2.7 Embedding Pipeline**

```
Build pipeline/src/embeddings/embed.py and pipeline/src/embeddings/fallback.py

embed.py: exact code from SPEC.md §4.2 (Gemini embedding-001).
fallback.py: OpenAI text-embedding-3-small, lazy init, 768 dims.
Fallback trigger: >10% Gemini error rate over 1 hour.
Run tests: uv run pytest src/tests/test_embeddings.py
```

**3.2.8 Deduplication**

```
Build pipeline/src/processing/dedup.py

content_hash check: if hash exists in DB, skip (DuplicateError).
UPSERT pattern from SPEC.md: ON CONFLICT (source_id, external_id)
  DO UPDATE SET ... WHERE jobs.content_hash != EXCLUDED.content_hash.
Run tests: uv run pytest src/tests/test_dedup.py
```

### 3.3 Wire Up Queue Runner

```
Build pipeline/src/processing/queue_runner.py

async def run_all_queues(batch_size=500):
    Read from parse_queue → run parser → enqueue to normalize_queue
    Read from normalize_queue → run normalizers → enqueue to dedup_queue
    Read from dedup_queue → run dedup check → enqueue to geocode_queue (if unique)
    Read from geocode_queue → run geocoder → enqueue to embed_queue
    Read from embed_queue → build summary → embed → update status to 'ready'

Each stage: read batch from pgmq, process, update job status, enqueue next.
On failure: increment retry_count, log last_error, if retry_count >= 3 → DLQ.
```

### 3.4 Verify and Merge

```bash
uv run pytest --cov=src/processing --cov-fail-under=90
uv run pytest --cov=src/embeddings --cov-fail-under=85
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(pipeline): salary, location, category, skills, embeddings, dedup, queue runner"
```

**`/clear` — Start fresh for Stage 4. Stay on `data-phase`.**

---

## 4. Stage 4: Maintenance + Verification (Week 4)

**Branch:** `data-phase` (continuing from Stage 3)

### 4.1 Build Expiry Detection

```
Build pipeline/src/maintenance/expiry.py

Source-specific logic from SPEC.md §6:
  Reed: use expirationDate field (provided in API response)
  Adzuna: 45 days from date_posted (no expiry field)
  Jooble/Careerjet: 30 days from date_posted (no expiry field)

Re-verification: jobs disappearing from API for 2 consecutive fetch cycles → mark expired.
Archival: expired > 90 days → status='archived'. Hard delete: archived > 180 days.
```

### 4.2 Build DLQ Retry

```
Build pipeline/src/maintenance/dlq.py

Read from dead_letter_queue where enqueued > 6 hours ago.
Route back to original queue based on msg->>'failed_stage'.
Max 5 total retries. Alert if >5% of source enters DLQ.
```

### 4.3 Build Health Logger

```
Build pipeline/src/maintenance/health.py

Query pipeline_health view. Log all 14 metrics via structlog.
Check alert conditions:
  jobs_ingested_last_hour = 0 for 3 consecutive hours → alert
  jobs_in_dlq > 100 → alert
  ready_without_embedding > 0 → alert
```

### 4.4 Create search_jobs() Migration

```
Write migration 006: CREATE OR REPLACE FUNCTION search_jobs(...)
Exact SQL from SPEC.md §5. Include the cosine distance comment.
Write corresponding down.sql: DROP FUNCTION search_jobs;

Run: supabase db reset
Verify: SELECT * FROM search_jobs('python developer'); returns no error (empty result on empty DB is OK).
```

### 4.5 End-to-End Verification

**This is the moment of truth. Run the full pipeline locally:**

```
1. supabase db reset && just seed-dev  (loads seed data with 1K synthetic jobs)
2. modal run src/modal_app.py::fetch_reed  (fetch real jobs from Reed)
3. modal run src/modal_app.py::process_queues  (process through all stages)
4. Wait 2-3 minutes for embeddings to complete
5. just health  (verify pipeline_health shows jobs_ingested > 0, ready > 0)
6. Run 10 test queries from GATES.md against local DB
7. Every query must return results or handle gracefully
```

### 4.6 Verify and Merge

```bash
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(pipeline): expiry, DLQ retry, health monitoring, search_jobs(), E2E verified"
# One squash merge of all Phase 1 work to main
git checkout main
git merge --squash data-phase
git commit -m "feat(phase-1): complete data pipeline — 4 collectors, processing, embeddings, search"
git tag v0.1.0
git branch -d data-phase
```

---

## 5. Production Deployment

### 5.1 Deploy Database

```bash
# Link to production Supabase project
supabase link --project-ref <YOUR_PROJECT_REF>

# Push all migrations
supabase db push

# Verify
supabase db remote commit  # Should show clean state
```

### 5.2 Deploy Pipeline

```bash
# Create Modal secrets (one-time)
modal secret create atoz-env \
    REED_API_KEY=<value> \
    ADZUNA_APP_ID=<value> \
    ADZUNA_APP_KEY=<value> \
    JOOBLE_API_KEY=<value> \
    CAREERJET_AFFID=<value> \
    GOOGLE_API_KEY=<value> \
    SUPABASE_URL=<value> \
    SUPABASE_SERVICE_ROLE_KEY=<value> \
    DATABASE_URL=<value> \
    SENTRY_DSN=<value>

# Deploy
cd pipeline && modal deploy src/modal_app.py

# Verify: all crons visible in Modal dashboard
# Trigger first run manually:
modal run src/modal_app.py::fetch_reed
```

### 5.3 Run GATES.md Go/No-Go Checklist

Execute every item in GATES.md §3 (Go/No-Go Production Checklist). All 20 items must pass before declaring Phase 1 complete.

### 5.4 Monitor First 24 Hours

Watch for: zero ingestion (3 hours), DLQ overflow (>100), missing embeddings, search latency (>100ms P95). See GATES.md §3.3 for full monitoring criteria and §4 for rollback procedures.

---

## Appendix A: File Creation Order (Quick Reference)

| Order | File | Stage |
|---|---|---|
| 1 | Directory structure + configs | Foundation |
| 2 | CLAUDE.md (root + subdirectory) | Foundation |
| 3 | .claude/settings.json | Foundation |
| 4 | .env.example | Foundation |
| 5 | justfile | Foundation |
| 6 | pyproject.toml | Foundation |
| 7 | Migration 001–005 (up.sql + down.sql each) | Foundation |
| 8 | seed.sql | Foundation |
| 9 | pipeline/src/models/job.py (JobBase + adapters) | Collection |
| 10 | pipeline/src/models/errors.py | Collection |
| 11 | pipeline/src/collectors/circuit_breaker.py | Collection |
| 12 | pipeline/src/collectors/reed.py | Collection |
| 13 | pipeline/src/collectors/adzuna.py | Collection |
| 14 | pipeline/src/collectors/jooble.py | Collection |
| 15 | pipeline/src/collectors/careerjet.py | Collection |
| 16 | pipeline/src/modal_app.py | Collection |
| 17 | pipeline/src/processing/salary.py | Processing |
| 18 | pipeline/src/processing/location.py | Processing |
| 19 | pipeline/src/processing/category.py | Processing |
| 20 | pipeline/src/processing/seniority.py | Processing |
| 21 | pipeline/src/processing/summary.py | Processing |
| 22 | pipeline/src/skills/dictionary.py | Processing |
| 23 | pipeline/src/skills/extractor.py | Processing |
| 24 | pipeline/src/embeddings/embed.py | Processing |
| 25 | pipeline/src/embeddings/fallback.py | Processing |
| 26 | pipeline/src/processing/dedup.py | Processing |
| 27 | pipeline/src/processing/queue_runner.py | Processing |
| 28 | pipeline/src/maintenance/expiry.py | Maintenance |
| 29 | pipeline/src/maintenance/dlq.py | Maintenance |
| 30 | pipeline/src/maintenance/health.py | Maintenance |
| 31 | Migration 006 (search_jobs function) | Maintenance |

## Appendix B: Conventional Commit Messages

```
feat(foundation): migrations, CLAUDE.md, .claude/, seed data
feat(pipeline): add Reed collector with category sweep
feat(pipeline): add Adzuna collector with coordinate extraction
feat(pipeline): add Jooble/Careerjet collectors
feat(pipeline): salary normalizer (12 patterns, 252 days)
feat(pipeline): location normalizer with postcodes.io
feat(pipeline): category mapper (Reed + Adzuna + keyword inference)
feat(pipeline): skill extractor with ESCO dictionary
feat(pipeline): Gemini embedding pipeline with OpenAI fallback
feat(pipeline): queue runner wiring all 6 queues
feat(pipeline): expiry detection and DLQ retry
feat(pipeline): search_jobs() hybrid search function
feat(pipeline): E2E verified, production ready
```
