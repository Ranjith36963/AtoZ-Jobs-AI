# Contributing to AtoZ Jobs AI

Guidelines for humans and AI agents.

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-stable. Merge via squash from phase branches. |
| `data-phase` | Phase 1 development (merged → main as v0.1.0) |
| `search-match-phase` | Phase 2 development (merged → main as v0.2.0) |
| `display-phase` | Phase 3 development (merged → main as v0.3.0) |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation changes |

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(web): add salary range slider to filter sidebar
fix(pipeline): handle null salary in Reed API response
docs: add ADR for embedding model selection
refactor(pipeline): extract circuit breaker to separate module
test(web): add accessibility tests for job card component
```

**Scopes:** `pipeline`, `web`, `supabase`, `ci`, or omit for cross-cutting changes.

**One logical change per commit.** Don't mix features with refactors.

## Development Workflow

```
1. Write tests first (TDD)
2. Confirm tests fail
3. Implement the feature
4. Run lint + typecheck + tests
5. Commit with conventional message
```

### Pipeline (Python)

```bash
cd pipeline
uv run pytest -x              # Stop on first failure
uv run ruff check . --fix     # Lint
uv run ruff format .          # Format
uv run mypy src/              # Type check
```

### Web (TypeScript)

```bash
cd web
pnpm test                     # Vitest
pnpm lint                     # ESLint
pnpm typecheck                # TypeScript strict
pnpm build                    # Production build
```

### Database

```bash
just reset                    # Full migration chain
just seed                     # Load seed data
just health                   # Check pipeline health
```

## Pull Request Process

1. Create PR with descriptive title
2. Use `.claude/commands/pr-review.md` for AI-assisted review
3. All CI checks must pass: tests, lint, typecheck, build
4. Coverage minimums: pipeline 80%, web 60%
5. Squash merge to target branch

## Code Style

- **Python:** Python 3.12+, Pydantic v2, async/await for I/O, no `Any` types, Google-style docstrings on public functions only
- **TypeScript:** Strict mode, zero `any`, named exports only, Zod at API boundaries
- **SQL:** RLS on every table, parameterized queries only, up.sql + down.sql for every migration

## Security Checklist

Before every PR:

- [ ] No hardcoded secrets (use `.env`)
- [ ] RLS policies on any new tables
- [ ] Parameterized queries (no string concatenation)
- [ ] Input validation at API boundaries
- [ ] OWASP Top 10 review for auth/input code

## Claude Code Commands

| Command | Purpose |
|---------|---------|
| `/fix-issue` | Investigate and fix a GitHub issue |
| `/pr-review` | Review a pull request |

See `.claude/commands/` for full details.
