# Local Development Setup

How to set up and run AtoZ Jobs AI locally.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | Latest | Required for Supabase local |
| Node.js | 20+ | `nvm install 20` |
| Python | 3.12+ | System or `pyenv install 3.12` |
| pnpm | Latest | `npm install -g pnpm` |
| uv | Latest | `pip install uv` |
| just | Latest | `cargo install just` or `brew install just` |
| Supabase CLI | Latest | `brew install supabase/tap/supabase` |

## Quick Start

```bash
# 1. Clone and enter repo
git clone <repo-url> && cd AtoZ-Jobs-AI

# 2. Copy environment variables
cp .env.example .env
# Fill in real values (see .env.example for descriptions)

# 3. Start Supabase local
supabase start

# 4. Reset database (applies all 19 migrations + seed)
just reset
just seed

# 5. Verify database health
just health

# 6. Install and run pipeline tests
cd pipeline
uv sync
uv run pytest -x
cd ..

# 7. Install and run web
cd web
pnpm install
pnpm dev          # Starts at http://localhost:3000
pnpm test         # Run tests
cd ..
```

## Running Components

### Pipeline

```bash
cd pipeline
uv run pytest                              # All tests
uv run pytest -x                           # Stop on first failure
uv run pytest --cov=src --cov-fail-under=80  # Coverage check
uv run ruff check . --fix                  # Lint
uv run ruff format .                       # Format
uv run mypy src/                           # Type check
```

For local Modal development:
```bash
modal serve src/modal_app.py    # Interactive mode (runs functions locally)
modal deploy src/modal_app.py   # Deploy to Modal cloud
```

### Web

```bash
cd web
pnpm dev          # Dev server (http://localhost:3000)
pnpm test         # Vitest
pnpm lint         # ESLint
pnpm typecheck    # TypeScript strict
pnpm build        # Production build
```

### Database

```bash
just migrate          # Push migrations to Supabase
just reset            # Full reset (all 19 migrations)
just seed             # Reset + load seed data
just seed-dev         # Seed + Python test jobs
just seed-perf        # Seed + bulk test data
just health           # Check pipeline_health view
just migrate-rollback # Manual rollback
```

## Environment Variables

See `.env.example` for the complete list. Minimum required for local development:

| Variable | Required For |
|----------|-------------|
| `SUPABASE_URL` | Pipeline + Web |
| `SUPABASE_SERVICE_ROLE_KEY` | Pipeline + Web server |
| `NEXT_PUBLIC_SUPABASE_URL` | Web |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Web |
| `GOOGLE_API_KEY` | Pipeline embeddings |

When running Supabase locally, the URL defaults to `http://localhost:54321` and keys are provided by `supabase start`.

## Common Issues

| Issue | Solution |
|-------|----------|
| `supabase start` fails | Ensure Docker is running. Try `supabase stop && supabase start`. |
| Migration chain fails | Run `just reset` to apply the full chain from scratch. |
| Port 54321 in use | Stop other Supabase instances: `supabase stop --all` |
| `pnpm dev` fails | Check Node.js version (20+). Run `pnpm install` first. |
| Pipeline tests timeout | Ensure `SUPABASE_URL` points to local instance. |
| Modal functions fail locally | Use `modal serve` for interactive testing. Check `atoz-env` secret. |

## Detailed Setup Guides

- Phase 1 pipeline setup: `docs/phase-1/PLAYBOOK.md §0.1, §1.1`
- Phase 2 additions: `docs/phase-2/PLAYBOOK.md §0.1`
- Phase 3 web setup: `docs/phase-3/PLAYBOOK.md §0.1, §1.1–1.2`
