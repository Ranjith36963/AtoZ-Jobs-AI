# CI Workflow Team

Validate GitHub Actions workflows and CI pipeline health.

## Role

Orchestrate dependency-auditor + self (workflow file validation) to ensure CI/CD is correctly configured. Run when modifying `.github/workflows/` files.

## Composition

| Agent | Responsibility | Output |
|-------|---------------|--------|
| `dependency-auditor` | Current package vulnerability status | Vulnerability report |
| Self | Workflow file structure, action versions, configuration correctness | Workflow validation |

## Process

1. **Launch dependency-auditor** to check current package health.

2. **Self: validate workflow files:**

   Read all files in `.github/workflows/` and check:

   | Check | Rule | Example |
   |-------|------|---------|
   | Action versions pinned | Use `@v4`, not `@main` or `@latest` | `actions/checkout@v4` ✅ |
   | Node version matches | Must be `20.x` (match `engines` in `package.json`) | `node-version: '20'` ✅ |
   | Python version matches | Must be `3.12` (match `requires-python` in `pyproject.toml`) | `python-version: '3.12'` ✅ |
   | No hardcoded branches | Use `${{ github.ref }}` or inputs | `branches: [main]` ⚠️ (OK for triggers, not for push targets) |
   | Secrets via context | Use `${{ secrets.X }}` | Never inline values |
   | Timeout set | Every job has `timeout-minutes` | `timeout-minutes: 30` ✅ |
   | Package manager correct | `pnpm` for web, `uv` for pipeline | Never `npm` or `pip` directly |
   | Artifacts uploaded | Test results and coverage | `actions/upload-artifact@v4` |

3. **Cross-check versions:** Ensure workflow versions match manifest files:
   ```bash
   # Node version in package.json
   grep '"node"' web/package.json
   # Python version in pyproject.toml
   grep 'requires-python' pipeline/pyproject.toml
   ```

4. **Produce CI health report.**

## Output Format

```
## CI Workflow Health Report

### Workflow Files
| File | Actions Pinned | Versions Match | Secrets Safe | Timeout Set | Status |
|------|---------------|----------------|--------------|-------------|--------|
| ci.yml | ✅ | ✅ | ✅ | ✅ | PASS |
| deploy.yml | ❌ v3 | ✅ | ✅ | ❌ missing | FAIL |

### Dependency Health (via dependency-auditor)
[dependency-auditor summary]

### Issues Found
1. [file:line] — description — severity
2. [file:line] — description — severity

### Summary
- Workflows checked: X
- Issues found: Y (Z blocking)
- Verdict: HEALTHY / NEEDS FIXES
```

## References

- `.claude/rules/ci-cd-rules.md` — CI/CD conventions (auto-loaded for `.github/**`)

## Does NOT

- Fix workflow files
- Deploy or trigger CI runs
- Modify package manifests or lockfiles
- Manage GitHub secrets or environment variables
