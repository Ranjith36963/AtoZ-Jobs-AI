# ADR 0003: Supabase Row-Level Security on Every Table

**Status:** Accepted
**Date:** 2026-03-01 (Phase 1)
**Deciders:** Project lead

## Context

AtoZ Jobs AI uses Supabase, which exposes a REST API accessible from the browser using an anonymous (`anon`) key. This key is embedded in frontend JavaScript and visible to anyone inspecting the page source. Without row-level access control, any browser client could read, modify, or delete all data in every table.

## Decision

**Enable Row-Level Security (RLS) on every table, without exception.** Define policies that:

1. **Anon role (browser):** Read-only access to `ready` jobs and public data
2. **Service role (server):** Full access for pipeline operations, audit logging, and admin tasks
3. **Authenticated role:** Read/write own profile data only (Phase 2+)

### RLS Policy Patterns

```sql
-- Public read for ready jobs
CREATE POLICY "Anon can read ready jobs"
    ON jobs FOR SELECT
    USING (status = 'ready');

-- Service role full access
CREATE POLICY "Service role full access"
    ON jobs FOR ALL
    USING (auth.role() = 'service_role');

-- User owns their profile
CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);
```

### Tables with RLS (all 19 migrations)

| Phase | Tables | Policy Pattern |
|-------|--------|---------------|
| Phase 1 | `jobs`, `sources`, `companies` | Anon reads ready/active, service_role writes |
| Phase 1 | `skills`, `job_skills` | Anon reads all, service_role writes |
| Phase 2 | `esco_skills` | Anon reads all, service_role writes |
| Phase 2 | `user_profiles` | Authenticated reads/writes own, service_role all |
| Phase 3 | `ai_decision_audit_log` | Service role only — no public access |

## Consequences

### Positive
- **Browser-safe anon key:** Key exposure is harmless because RLS restricts access
- **Defense in depth:** Even if API is miscalled, data access is limited
- **No custom auth middleware:** Supabase handles authorization at the database level
- **Audit compliance:** EU AI Act audit logs are service_role-only — no public reads

### Negative
- **Every migration needs RLS policies:** Forgetting to add policies creates a security hole
- **Service role key must stay server-side:** Leaking it bypasses all RLS
- **Debugging complexity:** Failed queries may silently return empty sets (RLS filtering, not errors)
- **Testing overhead:** Tests must verify both anon and service_role access patterns

### Rules (Enforced)

1. Every new table MUST have `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
2. Every new table MUST have at least one policy
3. `SUPABASE_SERVICE_ROLE_KEY` MUST never appear in browser/frontend code
4. `NEXT_PUBLIC_SUPABASE_ANON_KEY` is the ONLY key used in browser

See `.claude/rules/security-critical.md` for enforcement.

## References
- Phase 1 SPEC §1.5 (RLS policies)
- Phase 2 SPEC §2.4 (Phase 2 RLS)
- Phase 3 SPEC §1.1 (Audit log RLS — service_role only)
- `supabase/migrations/20260301000005_rls_policies.sql` (Phase 1 RLS)
- `supabase/migrations/20260301000014_phase2_rls.sql` (Phase 2 RLS)
- `.claude/rules/security-critical.md` (Non-negotiable security rules)
