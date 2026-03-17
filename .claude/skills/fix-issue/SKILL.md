---
name: fix-issue
description: >
  Manually invoked with /fix-issue. Follows TDD workflow to fix
  a GitHub issue with proper testing and conventional commits.
invoke: manual
---

# Fix Issue Command

Fix a GitHub issue following the project workflow.

## Steps

1. Read the issue description and any linked context
2. Identify affected files and understand current implementation
3. Write failing tests first (TDD)
4. Implement the fix
5. Run full test suite: `uv run pytest` (pipeline) or `pnpm test` (web)
6. Run linting: `uv run ruff check . --fix` and `uv run mypy src/`
7. Commit with conventional message referencing the issue: `fix(scope): description (#issue)`

## Post-implementation verification

After the fix is implemented:
- Read the original requirement and verify the implementation addresses ALL requirements
- Check edge cases mentioned in the requirement are handled
- Verify error handling follows project patterns (retry 3x → DLQ for pipeline, Zod → typed error for web)
- Run the tdd-enforcer agent to verify TDD compliance

## Rules

- One logical change per commit
- Preserve raw_data JSONB on every job
- Follow error handling patterns from CLAUDE.md
- Review for OWASP Top 10 if touching auth/input/data code
