---
paths:
  - "supabase/**"
  - "**/*.sql"
---

# Database Rules

These rules apply when working with SQL files or Supabase migrations.

1. **Every table MUST have RLS enabled.** No exceptions. Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and at least one policy in the same migration.

2. **Every up.sql MUST have a corresponding down.sql.** The down migration must cleanly reverse the up migration. Test with: `just reset` (applies full chain).

3. **Use CREATE INDEX CONCURRENTLY** for indexes on populated tables. This avoids locking the table during index creation.

4. **Add columns as NULL first.** For new columns on existing tables: add as NULL → populate data → add NOT NULL constraint in a separate migration if needed.

5. **Never modify a deployed migration.** If a migration has been applied to production, create a new migration to make changes. Never edit existing migration files.

6. **Parameterized queries only.** No string concatenation in SQL queries. The Supabase client handles parameterization automatically.

7. **Preserve raw_data JSONB.** Never DROP, TRUNCATE, or remove the `raw_data` column from the `jobs` table. It enables reprocessing when logic improves.

8. **Test the full migration chain.** After adding a new migration, run `just reset` to verify the entire chain from 000001 to the latest migration applies cleanly.

9. **Use appropriate index types.** HNSW for vectors, GIN for tsvector/trigram, GIST for geography, B-tree for standard lookups. See `supabase/CLAUDE.md` for conventions.
