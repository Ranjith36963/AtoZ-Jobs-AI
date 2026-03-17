---
paths:
  - ".github/**"
---

# CI/CD Rules

These rules apply when working with GitHub Actions workflows and CI/CD configuration.

1. **Pin all GitHub Actions to specific versions.** Use `actions/checkout@v4`, never `@main` or `@latest`. Unpinned actions are a supply chain risk.

2. **Pin Node.js version to 20.x.** Must match the `engines` field in `web/package.json`. Use `node-version: '20'` in workflow files.

3. **Pin Python version to 3.12.** Must match `requires-python` in `pipeline/pyproject.toml`. Use `python-version: '3.12'` in workflow files.

4. **Never hardcode branch names as push targets.** Use `${{ github.ref }}` or workflow inputs. Branch names in `on.push.branches` triggers are acceptable.

5. **Reference secrets via `${{ secrets.X }}`.** Never inline secret values. Never echo secrets to logs.

6. **Set `timeout-minutes` on every job.** Default: 30 minutes. Prevents runaway workflows from consuming unlimited minutes.

7. **Use correct package managers.** `pnpm` for web (never `npm`), `uv` for pipeline (never `pip` directly). Install with `--frozen-lockfile` / `--frozen` to ensure reproducibility.

8. **Upload test artifacts.** Use `actions/upload-artifact@v4` for test results and coverage reports so they survive job failures.
