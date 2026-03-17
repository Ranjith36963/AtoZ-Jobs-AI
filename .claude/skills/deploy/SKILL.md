---
name: deploy
description: >
  Manually invoked with /deploy. Runs pre-flight safety checks
  and deploys pipeline (Modal) or web (Cloudflare Pages).
invoke: manual
---

# Deploy Command

Deploy pipeline (Modal) or web (Cloudflare Pages) with pre-flight safety checks.

## Usage

```
/deploy pipeline    — deploy Modal serverless functions
/deploy web         — deploy Next.js to Cloudflare Pages
/deploy all         — deploy both (pipeline first, then web)
```

## Process

### 1. Pre-flight gate

Run the security-auditor agent for a go/no-go verdict:
- Security audit (no secrets, RLS enforced)
- Dependency audit (no critical/high CVEs)
- All tests pass (pipeline + web)
- Type check clean (mypy + TypeScript)
- Lint clean (ruff + ESLint)
- Build succeeds (bundle within limits)

Run these quality checks directly:

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

**If any gate fails:** Stop immediately. Show failing gates. Do not proceed.

### 2. Confirm with user

Display the gate verdict and ask for explicit confirmation before proceeding.

### 3. Deploy

#### Pipeline (Modal)

```bash
cd pipeline && modal deploy src/modal_app.py
```

Verify: 6 cron functions registered (fetch_reed, fetch_adzuna, fetch_aggregators, fetch_free_apis, process_queues, daily_maintenance).

#### Web (Cloudflare Pages)

```bash
cd web && pnpm build && pnpm build:cf
```

Then deploy via wrangler or Cloudflare Pages Git integration.

### 4. Post-deploy verification

Run the status-reporter agent to verify system health after deployment:
- Database: `just health`
- Pipeline: check Modal dashboard for function status
- Web: load production URL, check for errors

## Guards

- **Never deploy without passing the gate.** No `--force` or `--skip-checks` flags.
- **Never deploy without user confirmation.** Always ask before executing deploy commands.
- **Pipeline deploys before web** (when deploying `all`) because web depends on pipeline APIs.

## References

- `.claude/agents/security-auditor.md` — pre-flight security + dependency + performance audit
- `.claude/agents/status-reporter.md` — post-deploy verification
- `docs/phase-1/PLAYBOOK.md` §5.2 — Modal deploy details
- `docs/phase-3/PLAYBOOK.md` §5.2 — Cloudflare deploy details
