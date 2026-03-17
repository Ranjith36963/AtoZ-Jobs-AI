# ADR 0002: Rule-Based Extraction Over LLM Calls

**Status:** Accepted (with Phase 3 exception)
**Date:** 2026-03-01 (Phase 1), updated 2026-03-15 (Phase 3)
**Deciders:** Project lead

## Context

The pipeline processes thousands of jobs daily, extracting structured data (salary, location, seniority, skills, categories) from free-text job descriptions. Two approaches were considered:

1. **LLM extraction:** Send each job description to GPT-4/Claude for structured parsing
2. **Rule-based extraction:** Regex patterns, SpaCy NLP, and lookup tables

## Decision

Use **rule-based extraction only** for all pipeline processing in Phase 1 and Phase 2.

### Phase 1: Pure regex
- Salary: Regex patterns for `£XX,XXX`, `£XXk`, `per annum`, ranges
- Location: Geocoding via PostGIS + UK cities lookup table
- Seniority: Regex matching title/description for junior/mid/senior/lead/executive
- Categories: Keyword-to-category mapping table

### Phase 2: SpaCy + regex
- Skills: SpaCy PhraseMatcher with two layers (LOWER for case-insensitive, ORTH for exact case like "AWS")
- ESCO taxonomy: 13,939 skills loaded into `esco_skills` table, ~450+ active patterns in dictionary builder
- Dedup: pg_trgm fuzzy matching + MinHash/LSH (datasketch, xxhash), composite scoring
- Salary prediction: XGBoost model (not LLM) with TF-IDF + one-hot features

### Phase 3 Exception

Phase 3 introduces **GPT-4o-mini for match explanations only** — streamed to the browser via Vercel AI SDK. This is NOT extraction or processing. The LLM explains why a job matches a search query, a task requiring natural language generation that rules cannot accomplish.

- Budget capped: $45 soft cap (app-level) + $50 hard cap (OpenAI dashboard)
- Max 50 tokens per explanation
- Fallback text if LLM unavailable
- All calls logged to `ai_decision_audit_log` (EU AI Act compliance)

## Consequences

### Positive
- **~$0 processing cost:** No per-token charges for extraction
- **Deterministic output:** Same input always produces same extraction
- **Fast:** Regex + SpaCy runs in milliseconds vs seconds for LLM calls
- **No API dependency:** Pipeline runs without external LLM provider
- **Testable:** Pre-computed expectations, property-based testing with Hypothesis

### Negative
- **Pattern-limited:** Only extracts skills matching dictionary patterns (~450+)
- **Maintenance burden:** New skills require manual dictionary updates
- **Brittle edge cases:** Unusual salary formats or location descriptions may be missed
- **No reasoning:** Cannot infer implicit requirements from context

### Why Not LLM

| Factor | LLM | Rule-Based |
|--------|-----|------------|
| Cost per 1000 jobs | ~$2–5 | ~$0 |
| Latency per job | 1–3s | <10ms |
| Determinism | Non-deterministic | Deterministic |
| Testability | Hard to assert | Pre-computed expectations |
| Total monthly cost | $60–150 | $0 |

At ~$33/month total budget, LLM extraction is not economically viable.

## References
- Phase 1 SPEC §3.8 ("Pure Python regex. No SpaCy. No LLM.")
- Phase 2 SPEC §3.2 (SpaCy PhraseMatcher upgrade)
- Phase 3 SPEC §6.1 (GPT-4o-mini for explanations only)
- `pipeline/src/skills/` (SpaCy extraction)
- `pipeline/src/salary/` (XGBoost prediction)
