# AtoZ Jobs AI — Pipeline

Python data pipeline: collectors, processing, embeddings, skills extraction.

## Commands
- uv run pytest: Run all tests
- uv run pytest -x: Stop on first failure
- uv run pytest --cov=src --cov-fail-under=80: Coverage check
- uv run ruff check . --fix: Lint and auto-fix
- uv run ruff format .: Format code
- uv run mypy src/: Type check

## Code Style
- Python 3.12+, Pydantic v2 for ALL data models
- async/await for all I/O (httpx, database, embeddings)
- Rule-based extraction only. No LLM. No Instructor in Phase 1.
- google-genai for embeddings. OpenAI as fallback only. No LLM calls.
- Type hints on every function. No Any types.
- Docstrings on public functions only (Google style)

## Testing
- TDD: Write tests first, confirm they fail, then implement
- Compare against pre-computed expectations, never function output
- Include sad paths: null, empty, timeout, rate limit, malformed data, auth expiry
- pytest + pytest-asyncio + hypothesis (property-based)
- Coverage: 80% minimum

## Error Handling
- Every function handling external input: handle null, empty, timeout, malformed, rate limit
- Retry 3x with exponential backoff, then DLQ
- Embedding failures: retry → Gemini → OpenAI fallback → skip embedding

## Architecture
State machine: raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready
6 queues: parse_queue → normalize_queue → dedup_queue → geocode_queue → embed_queue + dead_letter_queue

## Pipeline Rules

1. **State transitions must follow the state machine.** `raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready`. Never skip a state or transition backwards.
2. **Preserve raw_data JSONB.** Never discard, modify, or overwrite the original API response stored in `jobs.raw_data`. This enables reprocessing when extraction logic improves.
3. **async/await for ALL I/O.** No synchronous HTTP calls, database queries, or file I/O. Use `httpx.AsyncClient`, async Supabase client, and `aiofiles`.
4. **Pydantic v2 for all data models.** Every data structure passed between functions must be a Pydantic BaseModel. No plain dicts for structured data.
5. **Circuit breaker pattern for external APIs.** 3 consecutive failures → OPEN state. 300 seconds recovery → HALF_OPEN. 429 responses are exempt (do not trip the breaker).
6. **Retry 3x with exponential backoff, then DLQ.** Failed jobs get 3 retries. After 3 failures, send to `dead_letter_queue`. DLQ auto-retries after 6 hours.
7. **Embedding fallback chain.** Gemini embedding-001 (primary) → OpenAI text-embedding-3-small (fallback) → skip embedding (job stays at `geocoded` status).
8. **No LLM calls in pipeline.** Pipeline uses rule-based extraction only (regex + ESCO dictionary, XGBoost for salary prediction). LLM is used only in the web layer for match explanations (Phase 3).
9. **Type hints on every function.** No `Any` types. Use specific types from Pydantic models, typing module, or custom types.
10. **Google-style docstrings on public functions only.** Internal/private functions do not need docstrings.
