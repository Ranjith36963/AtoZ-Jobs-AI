# Deployment Guide

How to deploy each component to production.

---

## Overview

| Component | Platform | Command | Trigger |
|-----------|----------|---------|---------|
| Pipeline | Modal | `modal deploy src/modal_app.py` | Manual or `modal-deploy.yml` |
| Web | Cloudflare Pages | `wrangler pages deploy .open-next` | Manual or `phase3-deploy-cf.yml` |
| Database | Supabase | `supabase db push` | Manual |

## 1. Database Migrations

```bash
# Push all pending migrations to production
supabase db push

# Verify
supabase db remote commit    # Should show clean state
just health                  # Check pipeline_health view
```

**Rollback:** Apply the corresponding `_down.sql` file manually or restore from Supabase PITR.

See `docs/phase-1/PLAYBOOK.md §5.1` for detailed migration deployment.

## 2. Pipeline (Modal)

```bash
# Deploy all functions (cron + callable)
cd pipeline
modal deploy src/modal_app.py
```

**What deploys:** 6 cron functions (fetch_reed, fetch_adzuna, fetch_aggregators, fetch_free_apis, process_queues, daily_maintenance) + callable functions (seed_esco, backfill_*, search_endpoint).

**Secrets:** All env vars bundled in Modal secret `atoz-env`. Update via Modal dashboard or CLI.

**GitHub Actions:** `.github/workflows/modal-deploy.yml` (manual trigger).

See `docs/phase-1/PLAYBOOK.md §5.2` for detailed pipeline deployment.

## 3. Web (Cloudflare Pages)

```bash
cd web
pnpm build:cf                                    # OpenNext build
wrangler pages deploy .open-next --project-name atozjobs
```

**Pre-deploy checklist:**
```bash
pnpm test          # All tests pass
pnpm typecheck     # Zero TS errors
pnpm lint          # Zero lint errors
pnpm build         # Production build succeeds
```

**Bundle size:** Worker bundle must be < 3 MiB (free tier limit).

**GitHub Actions:** `.github/workflows/phase3-deploy-cf.yml` (manual trigger with environment input).

See `docs/phase-3/PLAYBOOK.md §5.2` for detailed web deployment.

## 4. Environment Variables

| Platform | Where to Set | Variables |
|----------|-------------|-----------|
| **Modal** | Modal dashboard → Secrets → `atoz-env` | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, all API keys, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `COMPANIES_HOUSE_API_KEY` |
| **Cloudflare Pages** | CF dashboard → Pages → Settings → Environment variables | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `HELICONE_API_KEY`, `MODAL_SEARCH_URL`, `SENTRY_DSN`, `NEXT_PUBLIC_POSTHOG_KEY` |
| **GitHub Actions** | Repo → Settings → Secrets | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| **Supabase** | Supabase dashboard → Settings → API | Keys are auto-generated. Expose `anon` key only. |

## 5. Post-Deploy Verification

```bash
# Database
just health

# Pipeline (check Modal dashboard)
# Verify cron functions are scheduled
# Check queue depths: SELECT * FROM pipeline_health;

# Web
# Load https://atozjobs.ai — homepage renders
# Search "developer" — results appear
# Check Sentry for errors
# Check PostHog for page views
# Run Lighthouse audit on key pages (target: Performance >= 90, Accessibility >= 95)
```

## 6. DNS Configuration

```
# Point custom domain to Cloudflare Pages
# In domain registrar, set CNAME:
atozjobs.ai     → <project>.pages.dev
www.atozjobs.ai → <project>.pages.dev

# Cloudflare auto-provisions SSL certificate
```

## Rollback Procedures

| Scenario | Action | RTO |
|----------|--------|-----|
| Bad web deployment | `wrangler pages deploy --branch=<previous>` or CF dashboard rollback | < 5 min |
| Bad migration | Apply `_down.sql` for the migration | < 5 min |
| Pipeline failure | Redeploy previous version via `modal deploy` | < 15 min |
| Full DB corruption | Supabase Point-in-Time Recovery (PITR) | < 4 hours |

See `docs/phase-*/GATES.md §4` for detailed rollback procedures per phase.
