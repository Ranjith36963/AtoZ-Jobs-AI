---
paths:
  - "pipeline/**/*.py"
---

# Pipeline Rules

These rules apply when working with Python pipeline code.

1. **State transitions must follow the state machine.** `raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready`. Never skip a state or transition backwards.

2. **Preserve raw_data JSONB.** Never discard, modify, or overwrite the original API response stored in `jobs.raw_data`. This enables reprocessing when extraction logic improves.

3. **async/await for ALL I/O.** No synchronous HTTP calls, database queries, or file I/O. Use `httpx.AsyncClient`, async Supabase client, and `aiofiles`.

4. **Pydantic v2 for all data models.** Every data structure passed between functions must be a Pydantic BaseModel. No plain dicts for structured data.

5. **Circuit breaker pattern for external APIs.** 3 consecutive failures → OPEN state. 300 seconds recovery → HALF_OPEN. 429 responses are exempt (do not trip the breaker).

6. **Retry 3x with exponential backoff, then DLQ.** Failed jobs get 3 retries. After 3 failures, send to `dead_letter_queue`. DLQ auto-retries after 6 hours.

7. **Embedding fallback chain.** Gemini embedding-001 (primary) → OpenAI text-embedding-3-small (fallback) → skip embedding (job stays at `geocoded` status).

8. **No LLM calls in pipeline.** Phase 1-2 uses rule-based extraction only (regex, SpaCy PhraseMatcher, XGBoost). LLM is used only in the web layer for match explanations (Phase 3).

9. **Type hints on every function.** No `Any` types. Use specific types from Pydantic models, typing module, or custom types.

10. **Google-style docstrings on public functions only.** Internal/private functions do not need docstrings.
