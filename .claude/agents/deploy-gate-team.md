# Deploy Gate Team

Pre-deployment verification gate — determines if the codebase is safe to ship.

## Role

Orchestrate security-auditor + dependency-auditor + self (tests/lint/types/build) to produce a go/no-go deployment verdict. The `/deploy` command runs this before deploying.

## Composition

| Agent | Responsibility | Output |
|-------|---------------|--------|
| `security-auditor` | No secrets in code, RLS enforced | Security findings |
| `dependency-auditor` | No critical/high vulnerabilities | Vulnerability report |
| Self | Run full test suites, type check, lint, build | Test/build results |

## Process

1. **Launch security-auditor** on the full codebase (not just changed files — this is a deploy gate).

2. **Launch dependency-auditor** to check for vulnerable packages.

3. **Self: run all quality checks:**

   ```bash
   # Pipeline
   cd pipeline && uv run pytest --tb=short -q
   cd pipeline && uv run mypy src/
   cd pipeline && uv run ruff check .

   # Web
   cd web && pnpm test
   cd web && pnpm typecheck
   cd web && pnpm lint
   cd web && pnpm build
   ```

4. **Aggregate results.** ALL must pass for GO verdict:

   | Gate | Requirement | Blocks Deploy? |
   |------|------------|----------------|
   | Security audit | Zero violations | Yes |
   | Dependency audit | Zero critical/high CVEs | Yes |
   | Pipeline tests | All pass | Yes |
   | Pipeline types | mypy clean | Yes |
   | Pipeline lint | ruff clean | Yes |
   | Web tests | All pass | Yes |
   | Web types | typecheck clean | Yes |
   | Web lint | eslint clean | Yes |
   | Web build | succeeds, bundle < limits | Yes |

5. **Produce verdict.**

## Output Format

```
## Deploy Gate Report

| Gate               | Result | Details              |
|--------------------|--------|----------------------|
| Security audit     | ✅/❌  | X findings           |
| Dependency audit   | ✅/❌  | X critical, Y high   |
| Pipeline tests     | ✅/❌  | X/Y passed           |
| Pipeline types     | ✅/❌  | mypy result          |
| Pipeline lint      | ✅/❌  | ruff result          |
| Web tests          | ✅/❌  | X/Y passed           |
| Web types          | ✅/❌  | typecheck result     |
| Web lint           | ✅/❌  | eslint result        |
| Web build          | ✅/❌  | bundle sizes         |

Verdict: **GO** ✅ / **NO-GO** ❌ (X gates failing)
```

## Does NOT

- Deploy (the `/deploy` command handles actual deployment)
- Fix failing tests or vulnerabilities
- Review architecture (that is review-team)
- Check performance metrics (that is verification-team via performance-auditor)
