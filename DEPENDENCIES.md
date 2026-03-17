# AtoZ Jobs AI — External Dependencies

All external services, APIs, rate limits, and fallback chains.

---

## Job APIs (Paid — 4 sources)

| Source | Base URL | Auth | Rate Limit | Pagination |
|--------|----------|------|------------|------------|
| **Reed** | `https://www.reed.co.uk/api/1.0/search` | HTTP Basic Auth (key as username) | 0.5s sleep between requests | `resultsToSkip` offset, `resultsToTake=100` |
| **Adzuna** | `https://api.adzuna.com/v1/api/jobs/gb/search/{page}` | Query params: `app_id` + `app_key` | 1.0s sleep between requests | Page number in URL path, `results_per_page=50` |
| **Jooble** | `https://jooble.org/api/{API_KEY}` | API key in URL path | 1.0s sleep between requests | `page` field in POST body, ~20 results/page |
| **Careerjet** | `https://search.api.careerjet.net/v4/query` | `affid` query param + `user_ip` + `user_agent` anti-fraud | 1.0s sleep between requests | `page` param, `pagesize=50` |

**Collection strategies:**
- Reed: 15-sector category sweep, `postedWithin=1`
- Adzuna: 23-category sweep, `max_days_old=1`, `sort_by=date`
- Jooble: 15-keyword sweep, location="UK"
- Careerjet: 10 keywords x 9 locations matrix, `locale_code=en_GB`

## Job APIs (Free — 7 sources)

| Source | Auth | Notes |
|--------|------|-------|
| Arbeitnow | None | Public API, UK filter |
| RemoteOK | None | Remote jobs only |
| Jobicy | None | Remote jobs |
| Himalayas | None | Remote jobs |
| Remotive | None | Remote jobs |
| DevITjobs | None | Tech jobs |
| Landing.jobs | None | Tech jobs |

**File:** `pipeline/src/collectors/free_apis.py`

## Circuit Breaker

**File:** `pipeline/src/collectors/circuit_breaker.py`

| Parameter | Value |
|-----------|-------|
| Failure threshold | 3 consecutive failures |
| Recovery timeout | 300 seconds (5 minutes) |
| States | CLOSED → OPEN → HALF_OPEN → CLOSED |
| 429 handling | **Exempt** — rate limit responses do NOT trip the breaker |

## Embedding Models

| Provider | Model | Dimensions | Role | Batch | Sleep |
|----------|-------|-----------|------|-------|-------|
| **Google** | `embedding-001` (google-genai) | 768 | Primary | 100 items/batch | 0.5s between batches |
| **OpenAI** | `text-embedding-3-small` | 768 | Fallback only | — | — |

**Fallback chain:** Retry Gemini → OpenAI fallback → skip embedding (job stays at `geocoded` status)

**Env:** `GOOGLE_API_KEY` (primary), `OPENAI_API_KEY` (fallback)

## LLM (Phase 3 only — explanations)

| Provider | Model | Use | Budget |
|----------|-------|-----|--------|
| **OpenAI** | GPT-4o-mini | Match explanations (streamed) | $50/mo hard cap (OpenAI dashboard), $45 soft cap (app-level) |

**Proxy:** Helicone (optional, 10K req/mo free) for token tracking and cost monitoring.

**NOT used for:** extraction, processing, search, or any pipeline operation.

## Companies House API

**File:** `pipeline/src/enrichment/companies_house.py`

| Parameter | Value |
|-----------|-------|
| Base URL | `https://api.company-information.service.gov.uk` |
| Auth | HTTP Basic Auth (key as username) |
| Rate limit | 600 requests per 5 minutes |
| 429 handling | Respects `Retry-After` header |
| Endpoints | `/search/companies`, `/company/{number}` |
| SIC mapping | 5-digit code → section letter (A–U) |

## ML Models

| Model | Use | Config |
|-------|-----|--------|
| **XGBoost** | Salary prediction | max_depth=6, 200 rounds, TF-IDF + one-hot region/category + ordinal seniority |
| **SpaCy en_core_web_sm** | Skills extraction | PhraseMatcher with two layers (LOWER + ORTH), ~450+ patterns from ESCO |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Search re-ranking | Query-document relevance scoring on Modal |

## Infrastructure

### Supabase (PostgreSQL)

| Parameter | Value |
|-----------|-------|
| Plan | Pro + Small compute |
| DB port (local) | 54322 |
| API port (local) | 54321 |
| DB major version | 17 |
| Extensions | pgvector, PostGIS, pg_trgm, pgmq, pg_cron |
| Connection pooling | PgBouncer (transaction mode, included with Pro) |
| Cost | $30/month |

### Modal (Serverless Compute)

| Function | Schedule | Timeout |
|----------|----------|---------|
| `fetch_reed` | `*/30 * * * *` (every 30 min) | 600s |
| `fetch_adzuna` | `0 * * * *` (every hour) | 600s |
| `fetch_aggregators` | `0 */2 * * *` (every 2 hours) | 900s |
| `fetch_free_apis` | `30 */3 * * *` (every 3 hours) | 900s |
| `process_queues` | `*/15 * * * *` (every 15 min) | 600s |
| `daily_maintenance` | `0 3 * * *` (daily 3 AM) | 1200s |

**App name:** `atoz-jobs-pipeline`
**Secrets:** `atoz-env` (all env vars bundled)
**Plan:** Starter ($30 free credit/month, ~$8-10 actual usage)

### Cloudflare Pages

| Parameter | Value |
|-----------|-------|
| Project name | `atozjobs` |
| Adapter | OpenNext |
| Worker bundle limit | 3 MiB (free tier) |
| Build minutes | 500/month (free tier) |
| Bandwidth | Unlimited |

### Monitoring

| Service | Plan | Key Env Var |
|---------|------|-------------|
| **PostHog** | Free (1M events/mo) | `NEXT_PUBLIC_POSTHOG_KEY` |
| **Sentry** | Developer (5K errors/mo) | `NEXT_PUBLIC_SENTRY_DSN` |
| **Helicone** | Free (10K req/mo) | `HELICONE_API_KEY` |
| **Better Stack** | Free (10 monitors) | — |

PostHog API host: `https://eu.i.posthog.com`
Sentry traces sample rate: 10%

## Monthly Cost Breakdown

| Item | Cost |
|------|------|
| Supabase Pro + Small | $30.00 |
| Modal Starter | $0.00 (free credit covers usage) |
| Gemini embeddings | $0.00 (free tier) |
| GPT-4o-mini explanations | ~$2.25 (10K searches x 5 explanations) |
| Cloudflare Pages | $0.00 (free tier) |
| Sentry, PostHog, Helicone | $0.00 (free tiers) |
| Domain | ~$1.00 (~$12/year) |
| **Total** | **~$33–35/month** |
