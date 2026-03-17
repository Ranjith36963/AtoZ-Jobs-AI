---
name: migration-safety
description: >
  Invoke when any task involves supabase/migrations/, schema changes,
  ALTER TABLE, new columns, DROP commands, or RLS policy changes.
  Provides migration rules, verification sequence, and rollback patterns.
invoke: auto
---

# Migration Safety Skill

## Rules
- Every up.sql has a corresponding down.sql — no exceptions
- One logical change per migration (don't mix table creation with function creation)
- Never modify a deployed migration — create a new one instead
- Use CREATE INDEX CONCURRENTLY for indexes on tables with data
- Add columns as NULL first → populate → add NOT NULL constraint

## Verification Sequence
1. `supabase db reset` — full up chain, zero errors
2. Run the new migration's down.sql — zero errors
3. `supabase db reset` again — chain still works after rollback
4. `just seed` — data loads correctly after re-apply

## Naming Convention
- Format: `YYYYMMDDHHMMSS_description/up.sql` + `down.sql`
- Example: `20260301000001_extensions/up.sql`

## Rollback Patterns
- DROP TABLE IF EXISTS (reverse dependency order)
- DROP INDEX IF EXISTS
- DROP FUNCTION IF EXISTS
- DROP TRIGGER IF EXISTS ... ON table
- DROP VIEW IF EXISTS
- DROP POLICY IF EXISTS ... ON table
- ALTER TABLE ... DISABLE ROW LEVEL SECURITY
