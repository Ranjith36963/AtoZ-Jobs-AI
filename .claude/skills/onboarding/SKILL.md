# Onboarding Skill

New session setup checklist. Run this when starting fresh or onboarding a new developer.

## Prerequisites Check

Verify all tools are installed before proceeding:

```bash
docker --version          # Docker (for Supabase local)
node --version            # Node.js 20+
python3 --version         # Python 3.12+
uv --version              # uv (Python package manager)
pnpm --version            # pnpm (Node package manager)
just --version            # just (command runner)
supabase --version        # Supabase CLI
modal --version           # Modal CLI (optional — pipeline only)
```

All required except Modal (only needed for pipeline deployment).

## Environment Setup

### Step 1: Environment variables

```bash
cp .env.example .env
```

Fill in required values:
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` — from `supabase start` output
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` — from `supabase start` output
- `REED_API_KEY` — from Reed API registration (required for collection)
- `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` — from Adzuna developer portal
- `GOOGLE_API_KEY` — for Gemini embeddings

Optional:
- `OPENAI_API_KEY` — embedding fallback + AI explanations
- `COMPANIES_HOUSE_API_KEY` — company enrichment
- `NEXT_PUBLIC_POSTHOG_KEY` — analytics
- `NEXT_PUBLIC_SENTRY_DSN` — error tracking

### Step 2: Start local Supabase

```bash
supabase start
```

Note the output — it contains the URL, anon key, and service role key. Copy these into `.env`.

### Step 3: Apply migrations and seed

```bash
just reset    # Apply all migrations (000001 through latest)
just seed     # Load minimal seed data (sources, skills taxonomy)
just health   # Verify database is healthy
```

### Step 4: Install dependencies

```bash
# Pipeline
cd pipeline && uv sync

# Web
cd web && pnpm install
```

### Step 5: Verify everything works

```bash
# Pipeline tests
cd pipeline && uv run pytest -x

# Web tests
cd web && pnpm test

# Web dev server
cd web && pnpm dev
# Visit http://localhost:3000
```

## Quick Verification One-Liner

```bash
just health && cd pipeline && uv run pytest -x && cd ../web && pnpm test && pnpm typecheck
```

## Common Issues

| Problem | Solution |
|---------|----------|
| Port 54322 in use | `supabase stop` then `supabase start` |
| `pnpm install` fails | `rm -rf web/node_modules && pnpm store prune && pnpm install` |
| Migrations fail | Check ordering in `supabase/migrations/` — must be sequential |
| `just` command not found | Install: `cargo install just` or `brew install just` |
| Python version mismatch | Use `pyenv` or `uv python install 3.12` |
| Supabase CLI outdated | `brew upgrade supabase` or `npm update -g supabase` |

## Project Orientation

After setup, read these files to understand the codebase:

1. `CLAUDE.md` — project conventions and code style
2. `docs/architecture.md` — system design and data flow
3. `STATUS.md` — current project status and phase
4. `DEPENDENCIES.md` — external services and rate limits

## Related

- `.claude/skills/health-check/SKILL.md` — detailed health check procedures
- `.claude/skills/seed-data/SKILL.md` — seed data tiers and backfill scripts
