---
paths:
  - "web/**/*.ts"
  - "web/**/*.tsx"
---

# Frontend Rules

These rules apply when working with Next.js TypeScript code.

1. **Named exports only.** Never use default exports. This ensures consistent imports and better refactoring support.

2. **Zero `any` types.** TypeScript strict mode is enabled. Use proper types from `@/types/database`, Zod schemas, or custom interfaces.

3. **tRPC for search/recommendations.** Complex queries (search, related jobs, facets) go through tRPC routers for type safety and caching.

4. **Direct Supabase client for simple reads.** Single-table lookups (job by ID, profile) use the Supabase client directly. No tRPC overhead needed.

5. **Server Actions for simple form mutations ONLY.** Profile updates, feedback forms. Never use Server Actions for search or complex queries.

6. **Zod validation at every API boundary.** All tRPC inputs, API route bodies, and Server Action inputs must be validated with Zod schemas.

7. **Anon key only in browser.** `NEXT_PUBLIC_SUPABASE_ANON_KEY` is the only Supabase key used in client components. RLS restricts access. `SUPABASE_SERVICE_ROLE_KEY` is server-only (`web/lib/supabase/admin.ts`).

8. **EU AI Act compliance.** Log all AI decisions (search rankings, explanations, salary predictions) to `ai_decision_audit_log` via service_role client. Display `<AIDisclosure>` component on every AI-generated element.

9. **WCAG 2.1 AA accessibility.** All components must be keyboard-navigable with visible focus rings. Minimum 4.5:1 contrast ratio. Touch targets >= 48x48px. Support `prefers-reduced-motion`. Include skip link on every page.

10. **ISR caching per route.** Homepage: 3600s, job detail: 1800s, transparency: 86400s, search: always dynamic (no cache).
