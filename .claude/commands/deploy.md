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

Run deploy-gate-team for go/no-go verdict:
- Security audit (no secrets, RLS enforced)
- Dependency audit (no critical/high CVEs)
- All tests pass (pipeline + web)
- Type check clean (mypy + TypeScript)
- Lint clean (ruff + ESLint)
- Build succeeds (bundle within limits)

**If NO-GO:** Stop immediately. Show failing gates. Do not proceed.

### 2. Confirm with user

Display the deploy-gate-team verdict and ask for explicit confirmation before proceeding.

### 3. Deploy

#### Pipeline (Modal)

```bash
cd pipeline && modal deploy src/modal_app.py
```

Verify: 5 cron functions registered (collect, parse, normalize, geocode, embed).

#### Web (Cloudflare Pages)

```bash
cd web && pnpm build && pnpm build:cf
```

Then deploy via wrangler or Cloudflare Pages Git integration.

### 4. Post-deploy verification

Run status-reporter to verify system health after deployment:
- Database: `just health`
- Pipeline: check Modal dashboard for function status
- Web: load production URL, check for errors

## Guards

- **Never deploy without passing the gate.** No `--force` or `--skip-checks` flags.
- **Never deploy without user confirmation.** Always ask before executing deploy commands.
- **Pipeline deploys before web** (when deploying `all`) because web depends on pipeline APIs.

## References

- `.claude/agents/deploy-gate-team.md` — pre-flight gate
- `.claude/agents/status-reporter.md` — post-deploy verification
- `docs/phase-1/PLAYBOOK.md` §5.2 — Modal deploy details
- `docs/phase-3/PLAYBOOK.md` §5.2 — Cloudflare deploy details
