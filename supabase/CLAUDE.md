# AtoZ Jobs AI — Database (Supabase)

Conventions for migrations, SQL, and database operations.

## Migration Naming

All migrations live in `supabase/migrations/` as flat SQL files:

```
20260301000001_extensions.sql          + _down.sql
20260301000002_core_tables.sql         + _down.sql
...
20260301000019_search_facets.sql       + _down.sql
```

**Format:** `YYYYMMDDXXXXXX_description.sql` with matching `_down.sql` rollback.

## Migration Inventory

| Range | Phase | Count | Contents |
|-------|-------|-------|----------|
| 000001–000009 | Phase 1 | 9 | Extensions, core tables, indexes, queues/cron/health, RLS, UK cities, search_jobs, pipeline columns |
| 000010–000017 | Phase 2 | 8 | Skills taxonomy, advanced dedup, salary/company, user profiles/search_v2, Phase 2 RLS, fuzzy duplicates, category/contract type, pgmq permissions |
| 000018–000019 | Phase 3 | 2 | AI audit log (EU AI Act), search facets materialized views |

**Total: 19 migrations (38 files including down migrations)**

## Extensions

| Extension | Purpose | Migration |
|-----------|---------|-----------|
| pgvector | Vector similarity search (halfvec, HNSW) | 000001 |
| PostGIS | Geographic queries (geography Point) | 000001 |
| pg_trgm | Trigram fuzzy text matching | 000001 |
| pgmq | Message queues for pipeline | 000004 |
| pg_cron | Scheduled jobs (materialized view refresh) | 000004 |

## RLS Policy Patterns

Every table MUST have RLS enabled. Standard patterns:

```sql
-- Public read (anon role)
CREATE POLICY "Anon can read ready jobs"
    ON table_name FOR SELECT
    USING (status = 'ready');

-- Service role full access
CREATE POLICY "Service role full access"
    ON table_name FOR ALL
    USING (auth.role() = 'service_role');

-- User owns their data
CREATE POLICY "Users manage own profile"
    ON user_profiles FOR ALL
    USING (auth.uid() = user_id);
```

## Index Conventions

| Type | Index | Use |
|------|-------|-----|
| HNSW | `vector_cosine_ops` | Vector similarity on `jobs.embedding` |
| GIN | `tsvector_ops` | Full-text search on `jobs.search_vector` |
| GIN | `gin_trgm_ops` | Trigram fuzzy matching on text columns |
| GIST | `geography_ops` | Spatial queries on `jobs.location_point` |
| B-tree | Standard | Primary keys, foreign keys, status columns |

For populated tables, use `CREATE INDEX CONCURRENTLY` to avoid locking.

## Commands

```bash
just migrate          # supabase db push
just reset            # supabase db reset (full chain verification)
just seed             # Reset + load seed data
just seed-dev         # Seed + Python test jobs
just seed-perf        # Seed + bulk test data
just health           # Query pipeline_health view
just migrate-rollback # Apply down.sql manually
```

## Rules

1. Every `up.sql` MUST have a corresponding `down.sql`
2. Every table MUST have RLS enabled with appropriate policies
3. Never modify a deployed migration — create a new one
4. Add columns as NULL first → populate → add NOT NULL constraint
5. Parameterized queries only — no string concatenation in SQL
6. Preserve `raw_data` JSONB — never drop or truncate this column

## Related

- `@.claude/skills/migration-safety/SKILL.md` — Migration safety checklist
- `@.claude/rules/security-critical.md` — RLS enforcement rules
- `@.claude/rules/database-rules.md` — Path-scoped database rules
