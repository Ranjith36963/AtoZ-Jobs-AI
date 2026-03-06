# AtoZ Jobs AI — unified commands

# === Development ===
dev-pipeline:
    cd pipeline && uv run python -m src.main

dev-web:
    cd web && pnpm dev

# === Testing ===
test:
    cd pipeline && uv run pytest
    cd web && pnpm test

test-pipeline:
    cd pipeline && uv run pytest -x --cov=src --cov-fail-under=80

test-web:
    cd web && pnpm test -- --coverage

# === Linting ===
lint:
    cd pipeline && uv run ruff check . --fix && uv run ruff format .
    cd web && pnpm lint

typecheck:
    cd pipeline && uv run mypy src/
    cd web && pnpm typecheck

# === Database ===
migrate:
    supabase db push

reset:
    supabase db reset

seed:
    supabase db reset
    psql $DATABASE_URL -f supabase/seed.sql

seed-dev:
    just seed
    cd pipeline && uv run python -m src.tests.seed_jobs

seed-perf:
    just seed
    cd pipeline && uv run python -m src.tests.seed_bulk

health:
    psql $DATABASE_URL -c "SELECT * FROM pipeline_health;"

migrate-rollback:
    @echo "Apply the most recent down.sql manually against local DB"

# === Deployment ===
deploy-pipeline:
    cd pipeline && modal deploy src/modal_app.py

deploy-web:
    cd web && pnpm build
