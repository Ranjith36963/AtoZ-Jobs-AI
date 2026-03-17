---
name: pr-review
description: >
  Manually invoked with /pr-review. Reviews a pull request for
  code quality, security, and architectural consistency.
invoke: manual
---

# PR Review Command

Review a pull request for code quality, security, and architectural consistency.

## Steps

1. Read all changed files in the PR (`git diff --name-only`)
2. Check against CLAUDE.md conventions (root + subdirectory)
3. Run the security-auditor agent on changed files (covers security, architecture, dependencies, and performance checks)
4. Verify tests exist for new/changed code
5. Check coverage meets minimums (80% pipeline, 60% web)
6. Verify conventional commit messages (`feat|fix|docs|refactor|test(scope): description`)
7. Check for `docs/phase-{1,2,3}/SPEC.md` deviations

## Self-review checklist (conventions)

- Named exports only (TypeScript), no `any` types
- Zod validation at every API boundary
- Pydantic v2 models for all pipeline data structures
- async/await for all I/O operations
- raw_data JSONB preserved on every job
- No LLM calls in pipeline (rule-based extraction only)

## Classify findings

- **Blocking** — must fix before merge (security vulnerabilities, broken tests, architectural violations)
- **Non-blocking** — suggestion for improvement (style, minor refactors)

## Output

- List of issues (blocking vs. non-blocking)
- Suggested fixes for each issue
- Overall assessment: APPROVE / REQUEST CHANGES
