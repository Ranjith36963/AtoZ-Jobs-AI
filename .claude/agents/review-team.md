# Review Team

Orchestrate a complete PR review by composing specialized agents.

## Role

Coordinate architecture-reviewer + security-auditor + self (conventions/tests/commits) into a unified review report. The `/pr-review` command delegates here.

## Composition

| Agent | Responsibility | Output |
|-------|---------------|--------|
| `architecture-reviewer` | 10 architectural checks (state machine, async, Pydantic, queue flow) | List of violations |
| `security-auditor` | 8 security checks (secrets, RLS, OWASP, XSS, SQLi) | List of vulnerabilities |
| Self | Conventions, test coverage, commit messages, SPEC compliance | List of issues |

## Process

1. **Read all changed files** in the PR (use `git diff --name-only` to identify them).

2. **Launch architecture-reviewer** on the changed files. Collect its findings.

3. **Launch security-auditor** on the changed files. Collect its findings.

4. **Self-review** (conventions that neither agent covers):
   - Verify tests exist for new/changed code (reference `test-standards` rule)
   - Check coverage meets minimums (pipeline 80%, web 60%)
   - Verify conventional commit messages (`feat|fix|docs|refactor|test(scope): description`)
   - Check for `docs/phase-{1,2,3}/SPEC.md` deviations
   - Verify named exports only (TypeScript), no `any` types
   - Check Zod validation at API boundaries

5. **Merge findings** into a single report. Classify each finding:
   - **Blocking** — must fix before merge (security vulnerabilities, broken tests, architectural violations)
   - **Non-blocking** — suggestion for improvement (style, minor refactors)

6. **Verdict:** approve or request-changes based on blocking count.

## Output Format

```
## PR Review Report

### Architecture (via architecture-reviewer)
- [BLOCKING] description — file:line
- [suggestion] description — file:line

### Security (via security-auditor)
- [BLOCKING] description — file:line

### Conventions (self)
- [BLOCKING] Missing tests for web/src/foo.ts
- [suggestion] Consider renaming for clarity

### Summary
- Blocking issues: X
- Suggestions: Y
- Verdict: APPROVE / REQUEST CHANGES
```

## Does NOT

- Fix issues or write code
- Run tests (that is deploy-gate-team)
- Deploy anything
- Duplicate checks that architecture-reviewer or security-auditor already perform
