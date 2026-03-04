# AtoZ Jobs AI — Phase 3 Playbook

**How to build it. Stage-by-stage Claude Code instructions.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and GATES.md (verification).

---

## 0. Before You Start

### 0.1 Prerequisites

- Phase 1 + Phase 2 complete (all gate checks passing, `v0.2.0` tag applied)
- Node.js 20+ and `pnpm` installed globally
- `supabase` CLI installed and linked to production project
- Cloudflare account created (free tier)
- `wrangler` CLI installed (`pnpm add -g wrangler`)
- PostHog account created (free tier)
- Sentry account created (Developer plan)
- Modal `/search` endpoint deployed and accessible (from Phase 2)
- API keys ready: OpenAI (for LLM explanations), Helicone, Sentry DSN, PostHog key

### 0.2 The Workflow (Every Task)

From the Claude Code Bible — follow this religiously:

```
/clear                                          ← Clean context
ultrathink and plan [task]. Do NOT code yet.    ← Plan first
[review plan, challenge assumptions]            ← Human checks
Implement the plan.                             ← Code
pnpm test / pnpm typecheck                      ← Tests must pass
git add -A && git commit                        ← Conventional commit
```

### 0.3 When to /clear and /compact

| Trigger | Action |
|---|---|
| Starting a new stage (Foundation → Search → Performance → Compliance) | `/clear` |
| Switching between server and client components | `/clear` |
| Context getting long (>50 turns) | `/compact 'Focus on [current task]'` |
| After completing and committing a major component | `/compact` |
| Claude starts hallucinating or repeating itself | `/clear` and restart with refined prompt |

---

## 1. Stage 1: Web App Foundation (Week 9)

**Branch:** `display-phase`

```bash
git checkout display-phase
```

### 1.1 Create Next.js App

**Prompt to Claude Code:**

```
Create the Next.js 16 web app inside the existing monorepo at web/.

pnpm create next-app@latest web --typescript --tailwind --eslint --app --turbopack --no-src-dir

CRITICAL: Pin next@>=16.1.6 to patch CVE-2025-66478 (CVSS 10.0 RCE).
Verify: pnpm audit shows no critical vulnerabilities.

package.json should include:
  next: "^16.1.6"
  react: "^19"
  typescript: "^5.5"
  tailwindcss: "^4"

Do NOT install any other packages yet. Verify: pnpm dev starts successfully.
```

### 1.2 Install Core Dependencies

**Prompt to Claude Code:**

```
Install Phase 3 dependencies in web/:

pnpm add @trpc/server @trpc/client @trpc/react-query @trpc/next superjson
pnpm add @supabase/ssr @supabase/supabase-js
pnpm add ai @ai-sdk/openai @ai-sdk/react
pnpm add zod
pnpm add @sentry/nextjs
pnpm add posthog-js

pnpm add -D vitest @testing-library/react @testing-library/jest-dom
pnpm add -D @playwright/test
pnpm add -D supabase

Verify: pnpm typecheck passes with zero errors.
```

### 1.3 Generate Supabase Types

**Prompt to Claude Code:**

```
Generate TypeScript types from the Supabase schema.

npx supabase gen types typescript --project-id <PROJECT_REF> > web/types/database.ts

This file must include ALL tables from Phase 1+2:
  sources, companies, jobs, skills, job_skills, esco_skills, user_profiles,
  ai_decision_audit_log (after migration 011 applied)

Verify: the Database type includes all expected tables and columns.
Create web/types/index.ts that re-exports Database and adds our custom types:
  SearchResult, JobDetail, FacetCounts (from SPEC.md §4.6)
```

### 1.4 Create Supabase Clients

**Prompt to Claude Code:**

```
Create Supabase client files exactly as specified in SPEC.md §5.1:

web/lib/supabase/server.ts — createServerClient using cookies() from next/headers
web/lib/supabase/browser.ts — createBrowserClient for client components

Both must be typed with Database generic.
Only NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY used.
SUPABASE_SERVICE_ROLE_KEY used ONLY in API routes (never in components).

Create web/lib/supabase/admin.ts for service_role operations (audit logging):
  Uses SUPABASE_SERVICE_ROLE_KEY directly. Server-only.

Write TDD tests in web/__tests__/supabase-client.test.ts:
1. Server client creates without error
2. Browser client creates without error
3. Admin client uses service_role key

Run: pnpm test
```

### 1.5 Set Up tRPC

**Prompt to Claude Code:**

```
Set up tRPC for Next.js 16 App Router.

Create these files:
  web/server/trpc.ts — initTRPC with superjson transformer
  web/server/routers/index.ts — appRouter combining search, job, facets routers
  web/server/routers/search.ts — searchRouter with query and related procedures (stubs)
  web/server/routers/job.ts — jobRouter with byId procedure (stub)
  web/server/routers/facets.ts — facetsRouter with counts and salaryHistogram procedures (stubs)
  web/app/api/trpc/[trpc]/route.ts — tRPC HTTP handler for App Router
  web/lib/trpc/client.ts — tRPC React hooks provider
  web/lib/trpc/server.ts — Server-side tRPC caller

Exact Zod schemas from SPEC.md §4.2–4.4.

Stubs should return empty typed responses. We'll implement them in Stage 2.

Verify: pnpm dev → GET /api/trpc/facets.counts returns valid JSON response.
Run: pnpm typecheck
```

### 1.6 Set Up Monitoring

**Prompt to Claude Code:**

```
Configure Sentry and PostHog.

Sentry:
  npx @sentry/wizard@latest -i nextjs
  Configure with SENTRY_DSN from env.
  Verify: throw a test error in a page → appears in Sentry dashboard.

PostHog:
  Create web/lib/posthog.ts — PostHog provider component
  Wrap app layout with PostHogProvider (client component)
  Use NEXT_PUBLIC_POSTHOG_KEY from env.
  Verify: load homepage → event appears in PostHog dashboard.

Both should be wrapped in environment checks:
  if (process.env.NODE_ENV === 'production') { ... }
```

### 1.7 Create Root Layout and App Shell

**Prompt to Claude Code:**

```
Create the root layout with:

web/app/layout.tsx:
  - HTML lang="en-GB"
  - Metadata: title "AtoZ Jobs AI - UK Job Search", description
  - Inter font from next/font/google
  - Tailwind globals
  - PostHog provider (client)
  - tRPC provider (client)
  - Skip link component (WCAG 2.4.1)

web/components/layout/Header.tsx:
  - Logo (text for now: "AtoZ Jobs")
  - Nav: Home, Search, Transparency
  - Responsive: hamburger on mobile

web/components/layout/Footer.tsx:
  - Links: Transparency, Accessibility, Privacy
  - "Powered by AI" notice (EU AI Act)

web/components/layout/SkipLink.tsx:
  - Hidden link "Skip to main content"
  - Visible on focus (sr-only + focus:not-sr-only)
  - href="#main-content"

web/app/page.tsx:
  - Hero section with search bar
  - Featured categories grid (hardcoded for now, wired in Stage 2)
  - "AI-Powered UK Job Search" tagline

Verify: pnpm dev → homepage renders with header, hero, footer.
All keyboard-navigable with visible focus rings.
```

### 1.8 Write Migration 011–012

**Prompt to Claude Code:**

```
Write the Phase 3 database migrations.

supabase/migrations/011_ai_audit_log/up.sql — exact SQL from SPEC.md §1.1
supabase/migrations/011_ai_audit_log/down.sql
supabase/migrations/012_search_facets/up.sql — exact SQL from SPEC.md §1.2
supabase/migrations/012_search_facets/down.sql

Run: supabase db reset
Verify: ai_decision_audit_log table exists. mv_search_facets and mv_salary_histogram views exist.
Verify: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_facets works.
Verify: down.sql for both cleans up without error.
```

### 1.9 Deploy to Cloudflare Pages

**Prompt to Claude Code:**

```
Set up Cloudflare Pages deployment.

1. Install OpenNext adapter:
   pnpm add -D @opennextjs/cloudflare

2. Create open-next.config.ts in web/:
   export default { buildCommand: "pnpm build" }

3. Create wrangler.toml in web/:
   name = "atozjobs"
   compatibility_date = "2026-03-01"
   pages_build_output_dir = ".open-next"

4. Add build script to web/package.json:
   "build:cf": "opennextjs-cloudflare && wrangler pages deploy .open-next"

5. Test build: pnpm build:cf (should produce worker bundle)
6. Check bundle size: must be < 3 MiB
7. Deploy: wrangler pages deploy

Verify: site accessible at <project>.pages.dev
```

### 1.10 Verify and Merge

```bash
pnpm test
pnpm typecheck
pnpm lint
pnpm build
git add -A
git commit -m "feat(web): Next.js 16 foundation, tRPC, Supabase client, monitoring, CF Pages deploy"
```

**`/clear` — Start fresh for Stage 2.**

---

## 2. Stage 2: Search Interface (Week 10)

**Branch:** `display-phase` (continue on same branch)

```bash
# Continue on display-phase — no new branch
```

### 2.1 Build Search Input Component

**Prompt to Claude Code:**

```
Build web/components/search/SearchInput.tsx

A search bar with:
  - Text input: placeholder "Search jobs, e.g. Python developer in London"
  - aria-label="Job search" + linked <label> (hidden but present for screen readers)
  - Submit on Enter or search button click
  - Debounced input (300ms) for type-ahead (future)

Location autocomplete (LocationAutocomplete.tsx):
  - Input: "Enter postcode or city"
  - Calls postcodes.io /postcodes/:postcode/autocomplete on keystroke (debounced 200ms)
  - Returns postcode + lat/lng for selected result
  - Falls back to /postcodes?q=:query for partial postcodes
  - NEXT_PUBLIC_POSTCODES_IO_URL env var (default: https://api.postcodes.io)

Radius selector (RadiusSelector.tsx):
  - Dropdown: 5, 10, 25, 50, 100 miles
  - Default: 25 miles
  - aria-label="Search radius"

All state synced to URL search params (for shareable searches):
  ?q=python+developer&postcode=SW1A+1AA&lat=51.5&lng=-0.12&radius=25

TDD tests:
1. SearchInput renders with correct aria attributes
2. LocationAutocomplete shows suggestions on valid postcode input
3. URL state updates when search is submitted
4. Empty query shows validation message

Run: pnpm test
```

### 2.2 Build Job Card Component

**Prompt to Claude Code:**

```
Build web/components/jobs/JobCard.tsx

Displays a single search result as a card (inside <article> tag).

Props: SearchResult from SPEC.md §4.6

Layout (mobile-first):
  Line 1: Title (h3, linked to /jobs/[id])
  Line 2: Company name
  Line 3: Salary badge (SalaryBadge.tsx) + Location + Work type badge
  Line 4: Skills pills (max 5, overflow: "+3 more")
  Line 5: Date posted (relative: "2 days ago")

SalaryBadge.tsx:
  - Real salary: green badge "£30k–£40k"
  - Predicted salary: amber badge "~£30k–£40k (est.)" with tooltip explaining prediction
  - No salary: grey badge "Salary not disclosed"

JobCardSkeleton.tsx:
  - Animated placeholder matching JobCard dimensions
  - Uses prefers-reduced-motion to disable animation

TDD tests:
1. JobCard renders all fields correctly
2. SalaryBadge shows correct variant for real/predicted/missing
3. Skills pills truncate at 5 with "+N more" badge
4. Card is wrapped in <article> with descriptive link text
5. Skeleton respects prefers-reduced-motion

Run: pnpm test
```

### 2.3 Build Filter Sidebar

**Prompt to Claude Code:**

```
Build web/components/search/FilterSidebar.tsx

A sidebar (desktop) / drawer (mobile) with filter groups.

Uses facetsRouter.counts tRPC query to load counts from mv_search_facets.

Filter groups (each in <fieldset> with <legend>):
  1. Category — checkboxes with counts, e.g. "Technology (1,234)"
  2. Work Type — radio: Remote, Hybrid, Onsite, Any
  3. Employment Type — checkboxes: Full-time, Part-time, Contract, Permanent
  4. Seniority — checkboxes: Junior, Mid, Senior, Executive
  5. Salary Range — SalaryRangeSlider.tsx (dual-handle, data from mv_salary_histogram)
  6. Date Posted — radio: Last 24h, Last 7 days, Last 30 days, Any time

SalaryRangeSlider.tsx:
  - Dual-handle slider: min and max
  - role="slider" with aria-valuemin, aria-valuemax, aria-valuenow
  - Values from mv_salary_histogram buckets
  - Displays: "£20,000 – £80,000"

Mobile: FilterSidebar renders inside a Drawer component.
  - "Filters" button shows active filter count badge
  - Full-screen drawer with "Apply" and "Reset" buttons

All filter state synced to URL search params.
Changing a filter does NOT trigger full page reload — URL updates, tRPC query re-fires.

TDD tests:
1. FilterSidebar renders all groups with correct counts
2. Selecting a filter updates URL params
3. SalaryRangeSlider has correct aria attributes
4. Mobile drawer opens/closes
5. "Reset" clears all filters

Run: pnpm test
```

### 2.4 Build Search Results Page

**Prompt to Claude Code:**

```
Build web/app/search/page.tsx

Server component that reads URL search params and renders search results.

Flow:
  1. Read all filter params from URL (q, lat, lng, radius, category, etc.)
  2. Call tRPC search.query with params (server-side)
  3. Render: FilterSidebar (left) + SearchResultsGrid (right)
  4. SearchResultsGrid shows JobCards or skeletons while loading
  5. Pagination at bottom (URL-based: ?page=2)

SearchResultsGrid.tsx:
  - Maps search results to JobCard components
  - Shows count: "Showing 1-20 of 1,234 jobs"
  - Empty state: "No jobs match your search. Try broadening your filters."
  - Error state: "Something went wrong. Please try again."

Implement the tRPC search.query procedure (was a stub):
  1. POST to Modal /search endpoint with: { query, user_id, filters }
  2. Parse response into SearchResult[]
  3. Log to ai_decision_audit_log via admin Supabase client
  4. Return typed results + total count + latency

Mobile layout: single column, filters in drawer.
Desktop layout: sidebar + results grid.

TDD tests:
1. Search page renders results for a mock query
2. Empty results show empty state message
3. Pagination renders correct page numbers
4. URL state persists through navigation

Run: pnpm test
```

### 2.5 Build Job Detail Page

**Prompt to Claude Code:**

```
Build web/app/jobs/[id]/page.tsx

Static page with ISR (revalidate = 1800 seconds).

Implement tRPC job.byId procedure:
  Direct Supabase query joining jobs + companies + job_skills + skills.
  Returns JobDetail type from SPEC.md §4.6.

Page content:
  1. Title + company name
  2. Salary breakdown (SalaryBadge with full details)
  3. Location with embedded map (static Cloudflare map image, linked to Google Maps)
  4. Employment type + seniority badges
  5. Company info card (CompanyInfo.tsx):
     - SIC codes → industry label
     - Company status (active/dissolved)
     - Date of creation
     - Website link
  6. Full job description (sanitised HTML via DOMPurify)
  7. Skills with ESCO links (SkillsPills.tsx):
     - Each skill links to ESCO URI if available
     - Required vs preferred distinction
  8. Match explanation (MatchExplanation.tsx):
     - Streams via useChat hook from /api/explain
     - Shows AIDisclosure component
     - Loading skeleton during stream
  9. Related jobs (RelatedJobs.tsx):
     - tRPC search.related with jobId
     - 5 compact job cards
  10. Apply button (ApplyButton.tsx):
      - Links to source_url (external redirect)
      - Tracks click in PostHog
      - Opens in new tab with rel="noopener noreferrer"

SEO:
  - generateMetadata from SPEC.md §8.2
  - JobPostingJsonLd component from SPEC.md §8.1

TDD tests:
1. Job detail page renders all sections
2. CompanyInfo shows SIC industry label
3. SkillsPills renders with ESCO links
4. ApplyButton opens in new tab
5. JSON-LD output matches schema.org spec

Run: pnpm test
```

### 2.6 Build Match Explanation API Route

**Prompt to Claude Code:**

```
Build web/app/api/explain/route.ts

Exact implementation from SPEC.md §6.1:
  - Uses Vercel AI SDK v6 streamText
  - GPT-4o-mini via @ai-sdk/openai
  - Helicone proxy if HELICONE_API_KEY is set
  - Logs to ai_decision_audit_log (fire-and-forget)
  - Returns streaming response

Rate limiting:
  - Max 5 explanation requests per search (enforced client-side)
  - Max 50 tokens output per explanation
  - If LLM fails: return fallback text "This job matches your search based on [skills/location]."

TDD tests:
1. Valid request returns streaming response
2. Missing fields return 400
3. LLM failure returns fallback text
4. Audit log entry created

Run: pnpm test
```

### 2.7 Implement Facets Router

**Prompt to Claude Code:**

```
Implement the facetsRouter procedures (were stubs from Stage 1).

facets.counts:
  Query mv_search_facets materialized view.
  Group by facet_type: categories, workTypes, seniorities, employmentTypes.
  Return FacetCounts shape from SPEC.md §4.6.

facets.salaryHistogram:
  Query mv_salary_histogram materialized view.
  Return bucket array: [{ min, max, count }]

Both use direct Supabase anon client (read-only, RLS allows public access to materialized views).

TDD tests:
1. counts returns all 4 facet types
2. salaryHistogram returns sorted buckets
3. Empty DB returns empty arrays (not errors)

Run: pnpm test
```

### 2.8 Verify and Merge

```bash
pnpm test
pnpm typecheck
pnpm lint
pnpm build
git add -A
git commit -m "feat(web): search interface, job detail, filters, match explanations, facets"
```

**`/clear` — Start fresh for Stage 3.**

---

## 3. Stage 3: Performance and Caching (Week 11)

**Branch:** `display-phase` (continue on same branch)

```bash
# Continue on display-phase — no new branch
```

### 3.1 Configure ISR

**Prompt to Claude Code:**

```
Add ISR configuration to all page routes per SPEC.md §7.1:

app/page.tsx: export const revalidate = 3600
app/jobs/[id]/page.tsx: export const revalidate = 1800
app/transparency/page.tsx: export const revalidate = 86400
app/search/page.tsx: NO revalidate (always dynamic)

For jobs/[id]/page.tsx, add generateStaticParams:
  Pre-generate top 1000 most recent ready jobs.
  This seeds the ISR cache on deploy.

Verify with Cloudflare Pages:
  First load: MISS header
  Second load within revalidation window: HIT header
```

### 3.2 Optimize Database Queries

**Prompt to Claude Code:**

```
Add database query optimizations for Phase 3.

1. Create web/lib/db/search.ts:
   Before calling search_jobs_v2, execute:
     SET LOCAL hnsw.ef_search = 100;
     SET LOCAL hnsw.iterative_scan = relaxed_order;  -- pgvector 0.8.0+
   This improves recall for filtered vector search.

2. Run EXPLAIN ANALYZE on common queries:
   - search_jobs_v2 with keyword + location + salary filter
   - Job detail by ID (should use primary key)
   - Related jobs by vector similarity
   - Facet counts from materialized views

   All must show:
   - HNSW index scan (not sequential scan) for vector queries
   - Index scan for primary key lookups
   - < 100ms execution time

3. Verify PgBouncer is active:
   Use Supabase connection string with ?pgbouncer=true parameter.
   In transaction mode, max 1 connection per request.
```

### 3.3 Bundle Size Optimization

**Prompt to Claude Code:**

```
Optimize Next.js bundle size for Cloudflare Pages 3 MiB worker limit.

1. Run: ANALYZE=true pnpm build
   Check .next/analyze for chunk sizes.

2. Dynamic imports for heavy components:
   const MatchExplanation = dynamic(() => import('./MatchExplanation'), { ssr: false });
   const SalaryRangeSlider = dynamic(() => import('./SalaryRangeSlider'));
   const CompanyInfo = dynamic(() => import('./CompanyInfo'));

3. Tree-shake unused Supabase modules:
   Import only what's needed: { createBrowserClient } from '@supabase/ssr'

4. Check total worker bundle from OpenNext build.
   Target: < 2.5 MiB (with 0.5 MiB headroom).

5. If > 3 MiB: remove @sentry/nextjs SSR (keep client-only),
   or split into smaller route groups.
```

### 3.4 Lighthouse Audit

**Prompt to Claude Code:**

```
Set up automated Lighthouse CI.

1. Install: pnpm add -D @lhci/cli

2. Create lighthouserc.js:
   URLs to test: /, /search?q=developer, /jobs/1 (use a real job ID)
   Assertions:
     performance >= 90
     accessibility >= 95
     best-practices >= 90
     seo >= 90

3. Add to CI (GitHub Actions):
   - Build app
   - Start preview server
   - Run Lighthouse CI
   - Fail if assertions don't pass

4. Run locally: pnpm lhci autorun
   Fix any failures before committing.
```

### 3.5 Verify and Merge

```bash
pnpm test
pnpm typecheck
pnpm lint
pnpm build
# Verify bundle size
# Run Lighthouse CI
git add -A
git commit -m "feat(web): ISR caching, DB optimization, bundle optimization, Lighthouse CI"
```

**`/clear` — Start fresh for Stage 4.**

---

## 4. Stage 4: Compliance and Launch (Week 12)

**Branch:** `display-phase` (continue on same branch)

```bash
# Continue on display-phase — no new branch
```

### 4.1 Build Transparency Page

**Prompt to Claude Code:**

```
Build web/app/transparency/page.tsx

Static page (ISR 24h) with all 7 sections from SPEC.md §9.4:

1. "How AI Powers AtoZ Jobs" — plain English
2. Models used — list with purpose
3. What AI decides — search ordering, explanations, salary predictions
4. What AI does NOT decide — hiring, shortlisting, application success
5. Known limitations — with specific numbers (±£5-8K salary MAE)
6. How to contest — email + feedback mechanism
7. Last updated date

Style: simple, readable, Flesch-Kincaid ≤ 8.
No jargon. No marketing.

TDD test:
1. Page renders all 7 sections
2. All headings present
3. Contact information displayed

Run: pnpm test
```

### 4.2 Add AI Disclosure Components

**Prompt to Claude Code:**

```
Build web/components/ui/AIDisclosure.tsx

EU AI Act Article 50 compliance: visible disclosure on every AI-generated element.

Variants:
  - inline: small text "AI-generated" next to content
  - badge: badge icon + "AI" with tooltip explaining what AI did
  - section: banner "This section is generated by AI. It may contain errors."

Add AIDisclosure to:
  - MatchExplanation (section variant)
  - SalaryBadge when salary_is_predicted (inline variant)
  - Search results ranking info (inline: "Results ranked by AI")

TDD tests:
1. Each variant renders correct text
2. Tooltip has accessible description (aria-describedby)
3. Disclosure visible without hover (not tooltip-only)

Run: pnpm test
```

### 4.3 WCAG 2.1 AA Audit

**Prompt to Claude Code:**

```
Run comprehensive accessibility audit.

1. Install: pnpm add -D @axe-core/playwright

2. Create tests/accessibility.spec.ts (Playwright):
   Test every page: /, /search, /jobs/[id], /transparency, /profile
   Run axe-core on each page.
   Assert: zero critical or serious violations.

3. Manual keyboard audit:
   - Tab through every page: focus visible on every interactive element
   - Enter/Space activates all buttons and links
   - Escape closes modals/drawers
   - Skip link works on every page

4. Specific component checks:
   - SalaryRangeSlider: role="slider", aria-valuemin/max/now, keyboard arrows work
   - FilterSidebar: fieldset + legend on each group
   - SearchInput: linked label, aria-describedby
   - Pagination: aria-label, aria-current on active page
   - MatchExplanation: aria-live="polite" for streaming content
   - All images: alt text (or aria-hidden if decorative)

5. Colour contrast: run Lighthouse accessibility audit.
   All text must meet 4.5:1 ratio (1.4.3 AA).

6. Reduced motion: verify prefers-reduced-motion disables animations.

Fix all failures before proceeding.
```

### 4.4 Build SEO Components

**Prompt to Claude Code:**

```
Build SEO infrastructure.

1. web/components/seo/JobPostingJsonLd.tsx — exact code from SPEC.md §8.1
   Validate output at https://validator.schema.org/

2. web/app/sitemap.xml/route.ts — exact code from SPEC.md §8.3
   Must include all ready, non-duplicate jobs (up to 50K).
   Verify: GET /sitemap.xml returns valid XML.

3. web/app/robots.txt/route.ts:
   Allow: /
   Disallow: /api/
   Disallow: /profile/
   Sitemap: https://atozjobs.ai/sitemap.xml

4. Dynamic metadata on all pages:
   - Homepage: title, description, OG tags
   - Search: title includes query ("Python developer jobs | AtoZ Jobs")
   - Job detail: from SPEC.md §8.2

TDD tests:
1. JSON-LD output passes schema.org validation
2. Sitemap contains expected URLs
3. robots.txt blocks /api/ and /profile/
4. Meta tags populate correctly

Run: pnpm test
```

### 4.5 Mobile Responsiveness

**Prompt to Claude Code:**

```
Verify and fix mobile responsiveness.

1. Breakpoints from SPEC.md §11.1:
   Mobile (default): < 640px — single column
   Tablet: 640–1024px — two columns
   Desktop: > 1024px — three columns

2. Critical mobile patterns:
   - Search bar sticky on scroll
   - Filter drawer (not sidebar) on mobile
   - Job cards full-width
   - Touch targets ≥ 48×48px with ≥ 8px spacing
   - Pagination: infinite scroll on mobile (IntersectionObserver)

3. Create Playwright mobile tests:
   iPhone SE (375×667) and iPad (768×1024) viewports.
   Test: search flow, filter drawer, job detail, navigation.

4. Font sizes:
   Body: 16px minimum (never smaller)
   Job title: 18px mobile, 20px desktop
   Salary: 16px bold
   Skills pills: 14px (but touch target 48px via padding)

Fix any layout issues before proceeding.
```

### 4.6 Audit Logging Verification

**Prompt to Claude Code:**

```
Verify ai_decision_audit_log captures all required events.

1. Search ranking: every tRPC search.query call logs:
   decision_type='search_ranking', model_provider='gemini' + 'cross_encoder',
   input_summary with query text (no PII), output_summary with result count.

2. Match explanation: every /api/explain call logs:
   decision_type='match_explanation', model_provider='openai',
   model_version='gpt-4o-mini', token_count, cost_usd.

3. Write integration test:
   Perform a search → verify audit rows created.
   Request explanation → verify audit row with token count.

4. Create monthly review query:
   SELECT decision_type, COUNT(*), AVG(latency_ms), SUM(cost_usd)
   FROM ai_decision_audit_log
   WHERE created_at > now() - interval '30 days'
   GROUP BY decision_type;

Run: pnpm test
```

### 4.7 Launch Verification

**Prompt to Claude Code:**

```
Run the complete launch checklist from GATES.md.

Every item in §3 (Go/No-Go) must pass.
Document results in docs/phase-3/LAUNCH_LOG.md with:
  - Check ID
  - Result (PASS/FAIL)
  - Evidence (screenshot, command output, metric)
  - Date checked
```

### 4.8 Verify and Merge

```bash
pnpm test
pnpm typecheck
pnpm lint
pnpm build
# Run Lighthouse CI
# Run axe-core accessibility audit
# Run all Playwright E2E tests
git add -A
git commit -m "feat(web): EU AI Act compliance, WCAG 2.1 AA, SEO, mobile, launch verified"
# Single squash merge to main at end of Phase 3
git checkout main
git merge --squash display-phase
git commit -m "feat(web): Phase 3 — Display layer complete"
git tag v0.3.0
```

---

## 5. Production Deployment

### 5.1 Deploy Migrations

```bash
# Push Phase 3 migrations to production
supabase db push

# Verify
supabase db remote commit  # Should show clean state

# Verify materialized views
psql $DATABASE_URL -c "SELECT * FROM mv_search_facets LIMIT 5;"
psql $DATABASE_URL -c "SELECT * FROM mv_salary_histogram LIMIT 5;"
psql $DATABASE_URL -c "SELECT * FROM ai_decision_audit_log LIMIT 1;"
```

### 5.2 Deploy to Cloudflare Pages

```bash
cd web
pnpm build:cf

# Verify bundle size
ls -la .open-next/  # Must be < 3 MiB total

# Deploy
wrangler pages deploy .open-next --project-name atozjobs

# Set environment variables in Cloudflare Dashboard:
# NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
# SUPABASE_SERVICE_ROLE_KEY, MODAL_SEARCH_URL, OPENAI_API_KEY,
# HELICONE_API_KEY, SENTRY_DSN, NEXT_PUBLIC_POSTHOG_KEY
```

### 5.3 DNS Configuration

```
# Point custom domain to Cloudflare Pages
# In domain registrar, set CNAME:
atozjobs.ai → <project>.pages.dev
www.atozjobs.ai → <project>.pages.dev

# Cloudflare auto-provisions SSL certificate
```

### 5.4 Run GATES.md Go/No-Go Checklist

Execute every item in GATES.md §3. All items must pass before declaring Phase 3 complete.

### 5.5 Monitor First 24 Hours

Watch for: 5xx errors in Sentry, search latency > 3s, audit log gaps, ISR cache misses, Cloudflare worker errors. See GATES.md §3.4 for full monitoring criteria.

---

## Appendix A: File Creation Order (Quick Reference)

| Order | File | Stage |
|---|---|---|
| 1 | Next.js app scaffold + package.json | Foundation |
| 2 | Core dependencies installed | Foundation |
| 3 | web/types/database.ts (generated) | Foundation |
| 4 | web/types/index.ts (custom types) | Foundation |
| 5 | web/lib/supabase/server.ts + browser.ts + admin.ts | Foundation |
| 6 | web/server/trpc.ts + routers/ (stubs) | Foundation |
| 7 | web/app/api/trpc/[trpc]/route.ts | Foundation |
| 8 | web/lib/trpc/client.ts + server.ts | Foundation |
| 9 | Sentry + PostHog setup | Foundation |
| 10 | web/app/layout.tsx + Header + Footer + SkipLink | Foundation |
| 11 | web/app/page.tsx (homepage) | Foundation |
| 12 | Migrations 011–012 | Foundation |
| 13 | Cloudflare Pages config (wrangler.toml + open-next) | Foundation |
| 14 | web/components/search/SearchInput.tsx | Search |
| 15 | web/components/search/LocationAutocomplete.tsx | Search |
| 16 | web/components/search/RadiusSelector.tsx | Search |
| 17 | web/components/jobs/JobCard.tsx + Skeleton | Search |
| 18 | web/components/jobs/SalaryBadge.tsx | Search |
| 19 | web/components/jobs/SkillsPills.tsx | Search |
| 20 | web/components/search/FilterSidebar.tsx | Search |
| 21 | web/components/search/SalaryRangeSlider.tsx | Search |
| 22 | web/app/search/page.tsx | Search |
| 23 | web/components/search/SearchResultsGrid.tsx | Search |
| 24 | web/app/jobs/[id]/page.tsx | Search |
| 25 | web/components/jobs/JobDetail.tsx + sub-components | Search |
| 26 | web/components/jobs/MatchExplanation.tsx | Search |
| 27 | web/app/api/explain/route.ts | Search |
| 28 | web/components/jobs/RelatedJobs.tsx | Search |
| 29 | Facets router implementation | Search |
| 30 | ISR configuration on all pages | Performance |
| 31 | DB query optimization (hnsw settings) | Performance |
| 32 | Bundle size optimization (dynamic imports) | Performance |
| 33 | Lighthouse CI setup | Performance |
| 34 | web/app/transparency/page.tsx | Compliance |
| 35 | web/components/ui/AIDisclosure.tsx | Compliance |
| 36 | Accessibility audit + fixes | Compliance |
| 37 | web/components/seo/JobPostingJsonLd.tsx | Compliance |
| 38 | web/app/sitemap.xml/route.ts | Compliance |
| 39 | web/app/robots.txt/route.ts | Compliance |
| 40 | Mobile responsiveness fixes | Compliance |
| 41 | Audit logging verification | Compliance |
| 42 | Launch verification | Compliance |

## Appendix B: Conventional Commit Messages

```
feat(web): Next.js 16 scaffold with Turbopack, CVE-2025-66478 patched
feat(web): tRPC routers with Zod schemas (stubs)
feat(web): Supabase server/browser/admin clients with generated types
feat(web): Sentry + PostHog monitoring integration
feat(web): root layout, header, footer, skip link
feat(web): migrations 011-012 (audit log, search facets)
feat(web): Cloudflare Pages deployment with OpenNext
feat(web): search input with location autocomplete and radius
feat(web): job cards with salary badge and skills pills
feat(web): filter sidebar with facet counts and salary slider
feat(web): search results page with URL state
feat(web): job detail page with ISR, company info, JSON-LD
feat(web): match explanation streaming via AI SDK
feat(web): related jobs via vector similarity
feat(web): ISR configuration per route
feat(web): database query optimization (hnsw.ef_search=100)
feat(web): bundle size optimization, dynamic imports
feat(web): Lighthouse CI with performance assertions
feat(web): transparency page (EU AI Act Article 13)
feat(web): AI disclosure components (Article 50)
feat(web): WCAG 2.1 AA accessibility audit passed
feat(web): schema.org/JobPosting JSON-LD, sitemap, robots.txt
feat(web): mobile responsiveness verified
feat(web): audit logging verified for all AI decisions
feat(web): launch verification complete, production ready
```
