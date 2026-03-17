# Seed Data Skill

Procedures for seeding the database at different scales and for different purposes.

## Prerequisites

Migrations must be applied first: `just reset`

## Seed Tiers

### Tier 1: Production seed (`just seed`)

Minimal data required for the system to function:
- **sources** table: 4 paid API sources (Reed, Adzuna, Jooble, Careerjet) + 7 free sources
- **skills** table: ESCO skill taxonomy (~450+ entries from PhraseMatcher dictionary)
- **categories**: Standard UK job category mapping

Use for: fresh installs, production bootstrapping, CI environments.

### Tier 2: Development seed (`just seed-dev`)

Tier 1 + sample jobs for development:
- 100 sample jobs across all statuses (raw, parsed, normalized, geocoded, embedded, ready)
- 10 jobs per DLQ for error testing
- Sample user profiles for search testing
- Sample companies with SIC codes

Use for: local development, manual testing, PR previews.

### Tier 3: Performance seed (`just seed-perf`)

Tier 2 + high-volume data for load testing:
- 10,000+ jobs in `ready` status with full embeddings
- 50+ distinct companies
- 100+ skill variations
- Realistic salary distributions across UK regions

Use for: performance benchmarking, search tuning, index verification.

## ESCO Taxonomy Seeding

The skills table is populated from ESCO CSV data via the dictionary builder:

```bash
cd pipeline && uv run python -m src.skills.dictionary_builder
```

This produces ~450+ patterns in two layers:
- **LOWER patterns**: case-insensitive matching (e.g., "python", "javascript")
- **ORTH patterns**: case-sensitive matching (e.g., "AWS", "SQL", "API")

## Backfill Scripts

After changing extraction logic, re-process existing jobs:

| Script | Purpose | Command |
|--------|---------|---------|
| `backfill_job_skills` | Re-extract skills for existing jobs | `cd pipeline && uv run python -m src.scripts.backfill_job_skills` |
| `backfill_dedup` | Run dedup on normalized jobs | `cd pipeline && uv run python -m src.scripts.backfill_dedup` |
| `train_salary` | Train XGBoost on existing salary data | `cd pipeline && uv run python -m src.scripts.train_salary` |
| `predict_salaries` | Predict missing salaries | `cd pipeline && uv run python -m src.scripts.predict_salaries` |

## Verification

After any seeding:

```bash
just health
```

Check:
- Job counts per status match expected tier
- Skills table populated (450+ rows for ESCO)
- No constraint violations in logs
- Queue depths at zero (seed data should not enqueue)

## Related

- `.claude/skills/migration-safety/SKILL.md` — run migrations before seeding
- `.claude/rules/database-rules.md` — database constraints that seed data must satisfy
