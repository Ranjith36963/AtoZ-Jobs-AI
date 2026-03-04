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
