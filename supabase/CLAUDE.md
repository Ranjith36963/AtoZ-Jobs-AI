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

## Database Rules

1. **Every table MUST have RLS enabled.** No exceptions. Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and at least one policy in the same migration.
2. **Every up.sql MUST have a corresponding down.sql.** The down migration must cleanly reverse the up migration. Test with: `just reset` (applies full chain).
3. **Use CREATE INDEX CONCURRENTLY** for indexes on populated tables. This avoids locking the table during index creation.
4. **Add columns as NULL first.** For new columns on existing tables: add as NULL → populate data → add NOT NULL constraint in a separate migration if needed.
5. **Never modify a deployed migration.** If a migration has been applied to production, create a new migration to make changes. Never edit existing migration files.
6. **Parameterized queries only.** No string concatenation in SQL queries. The Supabase client handles parameterization automatically.
7. **Preserve raw_data JSONB.** Never DROP, TRUNCATE, or remove the `raw_data` column from the `jobs` table. It enables reprocessing when logic improves.
8. **Test the full migration chain.** After adding a new migration, run `just reset` to verify the entire chain from 000001 to the latest migration applies cleanly.
9. **Use appropriate index types.** HNSW for vectors, GIN for tsvector/trigram, GIST for geography, B-tree for standard lookups.

## Related

- `.claude/skills/migration-safety/SKILL.md` — Migration safety checklist
