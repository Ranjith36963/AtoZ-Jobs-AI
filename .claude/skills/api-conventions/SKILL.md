---
name: api-conventions
description: >
  Invoke when adding new tRPC routers, new API routes in web/app/api/,
  or new collector endpoints in pipeline/src/collectors/.
  Covers collector patterns, source adapters, and UPSERT conventions.
invoke: auto
---

# API Conventions Skill

## Collector Pattern
- async/await with httpx.AsyncClient
- Circuit breaker: 3 consecutive failures → OPEN, 300s recovery → HALF_OPEN
- Rate limiting: per-source sleep between requests (Reed 0.5s, others 1.0s)
- 429 responses: read Retry-After header, backoff, do NOT trip circuit breaker
- Max 3 retries with exponential backoff (2^n seconds)

## Source Adapters
- Each source has a static `to_job_base(data: dict) -> JobBase` method
- Map source-specific field names to universal JobBase schema
- Preserve original response in raw_data JSONB

## API Field Mapping Priority
1. Use structured API fields first (e.g., Reed minimumSalary/maximumSalary)
2. Fall back to text parsing if structured fields are null
3. Always store original text in raw fields (salary_raw, location_raw)

## UPSERT Pattern
- ON CONFLICT (source_id, external_id) DO UPDATE
- Update date_crawled on re-crawl
- Only update fields if content_hash changed

## Content Hash
- SHA-256 of: lowercase(title) + normalize(company) + normalize(location)
- Computed at ingestion, not a DB-generated column
