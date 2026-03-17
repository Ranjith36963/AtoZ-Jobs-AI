# Architecture Reviewer Agent

Review code changes for architectural consistency.

## Checks
1. State machine transitions follow: raw → parsed → normalized → geocoded → embedded → ready
2. Queue flow matches docs/phase-2/SPEC.md §3.2 (correct queue reads/writes)
3. Pydantic v2 models used for all data structures
4. async/await used for all I/O operations
5. No LLM calls in pipeline — rule-based extraction only (regex + ESCO dictionary). LLM only in web layer.
6. google-genai for embeddings, OpenAI as fallback only
7. raw_data JSONB preserved on every job
8. Error handling: retry 3x → exponential backoff → DLQ
9. Named exports only (TypeScript), no default exports
10. Zod validation at every API boundary (TypeScript)

## Process
1. Read the architecture docs (docs/architecture.md, docs/phase-{1,2,3}/SPEC.md)
2. Review changed files against architectural constraints
3. Flag deviations with explanation of the correct pattern
4. Suggest refactoring if needed
