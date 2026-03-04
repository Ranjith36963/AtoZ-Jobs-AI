# AtoZ Jobs AI — Phase 3 Quality Gates

**How to verify it works. Pass/fail criteria for every stage.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and PLAYBOOK.md (how).

---

## 1. Stage Gates — Pass/Fail Criteria

### 1.1 Gate 1: Foundation (Week 9)

Run these checks before completing Stage 1 (Foundation) on `display-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| F1 | Next.js version | `pnpm list next` | `next@>=16.1.6`. CVE-2025-66478 patched. |
| F2 | Security audit | `pnpm audit` | Zero critical vulnerabilities. |
| F3 | Dev server starts | `pnpm dev` | Starts in < 3 seconds with Turbopack. No errors. |
| F4 | TypeScript strict | `pnpm typecheck` | Zero errors. `strict: true` in tsconfig.json. |
| F5 | Supabase types | Check `web/types/database.ts` | Contains all tables: `sources`, `companies`, `jobs`, `skills`, `job_skills`, `esco_skills`, `user_profiles`, `ai_decision_audit_log`. |
| F6 | tRPC health | `GET /api/trpc/facets.counts` | Returns valid JSON (empty array is OK). No 500 error. |
| F7 | Server Supabase client | Import and call `createClient()` in a server component | Returns Supabase client without error. |
| F8 | Browser Supabase client | Import and call `createClient()` in a client component | Returns Supabase client without error. |
| F9 | Admin client isolation | Check `web/lib/supabase/admin.ts` | Uses `SUPABASE_SERVICE_ROLE_KEY`. Not importable from any client component. |
| F10 | Sentry integration | Throw test error in page component | Error appears in Sentry dashboard within 30 seconds. |
| F11 | PostHog integration | Load homepage | Page view event appears in PostHog dashboard. |
| F12 | Layout renders | `pnpm dev` → load homepage | Header, hero, footer all visible. Skip link visible on Tab. |
| F13 | Migration 011 | `supabase db reset` | `ai_decision_audit_log` table exists with all columns from SPEC.md §1.1. |
| F14 | Migration 012 | `SELECT * FROM mv_search_facets` | Returns rows (empty OK on fresh DB). No SQL error. |
| F15 | Salary histogram | `SELECT * FROM mv_salary_histogram` | Returns rows (empty OK). No SQL error. |
| F16 | Migration rollback | Run `down.sql` for 012, 011, then `supabase db reset` | Each down succeeds. Full chain re-applies cleanly. |
| F17 | CF Pages build | `pnpm build:cf` | OpenNext build completes. No errors. |
| F18 | Worker bundle size | Check `.open-next/` output | Total worker bundle < 3 MiB. |
| F19 | CF Pages deploy | `wrangler pages deploy` | Site accessible at `<project>.pages.dev`. Homepage renders. |
| F20 | Environment vars | Check Cloudflare dashboard | All env vars from SPEC.md §5.2 set. |
| F21 | Keyboard navigation | Tab through homepage | Every interactive element has visible focus ring. |

**FAIL gate:** F1–F9, F13–F16, F17–F18 are hard failures. F10–F12, F19–F21 are soft (expected to pass, fix in Stage 2 if needed).

### 1.2 Gate 2: Search Interface (Week 10)

Run these checks before completing Stage 2 (Search Interface) on `display-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| S1 | Search input | Type "Python developer" + Enter | tRPC query fires. Results or empty state shown. No crash. |
| S2 | Location autocomplete | Type "SW1A" in location field | Postcode suggestions appear within 200ms. Selecting one populates lat/lng. |
| S3 | Radius selector | Select each option (5/10/25/50/100) | URL updates with `radius=` param. Search re-fires. |
| S4 | Job cards render | Search returns results | Each card shows: title, company, salary badge, location, work type, skills (max 5). |
| S5 | Salary badge variants | Check cards with real/predicted/missing salary | Green badge for real, amber for predicted with "est." label, grey for missing. |
| S6 | Skills pills | Check card with skills | Skills display as badges. Max 5 shown. "+N more" for overflow. ESCO links on detail page. |
| S7 | Filter sidebar (desktop) | Load search page at > 1024px | Sidebar renders with all 6 filter groups. Counts match `mv_search_facets`. |
| S8 | Filter sidebar (mobile) | Load search page at < 640px | "Filters" button with count badge. Drawer opens with Apply/Reset. |
| S9 | Salary range slider | Interact with slider | `role="slider"` present. `aria-valuemin`, `aria-valuemax`, `aria-valuenow` update. Keyboard arrows work. |
| S10 | URL state sync | Apply filters, copy URL, paste in new tab | Same filters applied. Results match. |
| S11 | Empty state | Search for nonsense query | "No jobs match your search" message. Suggestions to broaden filters. |
| S12 | Pagination | Search with > 20 results | Page 1 shows 20 results. "Next" navigates to page 2. URL updates with `page=2`. |
| S13 | Job detail page | Click a job card | Job detail page loads with all 10 sections from PLAYBOOK.md §2.5. |
| S14 | Company info | Check job with enriched company | SIC industry label, company status, creation date displayed. |
| S15 | Match explanation | Load job detail for top search result | Explanation streams via AI SDK. AIDisclosure badge visible. |
| S16 | Related jobs | Scroll to bottom of job detail | 5 related jobs shown as compact cards. Clicking navigates to detail. |
| S17 | Apply button | Click "Apply" on job detail | Opens `source_url` in new tab. `rel="noopener noreferrer"` set. PostHog click event logged. |
| S18 | Skeleton loading | Throttle network to Slow 3G, search | Skeleton cards visible during loading. No layout shift when results appear. |
| S19 | JSON-LD | View page source on job detail | Valid `application/ld+json` script tag. All required JobPosting fields present. |
| S20 | Meta tags | Check `<head>` on job detail | `<title>`, `<meta description>`, OG tags populated with job data. |
| S21 | tRPC search.query | Run 5 test queries from §2 | All return typed results. No 500 errors. Latency < 3s. |
| S22 | tRPC search.related | Call with valid job ID | Returns 5 results with similarity ordering. |
| S23 | tRPC facets.counts | Call procedure | Returns 4 facet types with counts. |
| S24 | Audit log: search | Perform a search, check `ai_decision_audit_log` | Row created with `decision_type='search_ranking'`. |
| S25 | Audit log: explanation | View job detail, check audit log | Row created with `decision_type='match_explanation'`, `token_count` populated. |
| S26 | Coverage: web | `pnpm test --coverage` | ≥ 60% line coverage. |
| S27 | OpenAI spending cap | Check OpenAI dashboard → Settings → Limits | Monthly budget set to $50/month. |
| S28 | Budget guard fallback | Set `MONTHLY_SOFT_CAP_USD = 0` temporarily, call `/api/explain` | Returns fallback text instead of calling LLM. Reset cap after test. |

**FAIL gate:** S1–S6, S10, S13, S15, S19, S21–S25, S27–S28 are hard failures. S7–S9, S11–S12, S14, S16–S18, S20, S26 are soft.

### 1.3 Gate 3: Performance and Caching (Week 11)

Run these checks before completing Stage 3 (Performance) on `display-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| P1 | ISR: job detail | Load `/jobs/[id]` twice. Check response headers. | Second load serves from cache (cache HIT header). |
| P2 | ISR: revalidation | Load cached job detail page. Wait 31 minutes. Load again. | Stale page served immediately. Background revalidation fires. Next load has fresh content. |
| P3 | ISR: homepage | Load `/` twice | Second load from cache. Revalidates after 1 hour. |
| P4 | Search is dynamic | Load `/search?q=test` twice with different DB data | Both responses reflect current DB state. NOT cached. |
| P5 | HNSW index scan | `EXPLAIN ANALYZE` on `search_jobs_v2(query_text := 'developer', query_embedding := ...)` | Plan shows "Index Scan using idx_jobs_embedding". NOT "Seq Scan". |
| P6 | Search P95 latency | Run 50 searches, measure P95 | `search_jobs_v2()` P95 < 80ms. |
| P7 | Full search latency | Time: embed query + search_jobs_v2 + rerank + explanation | Total < 3 seconds including streaming explanation start. |
| P8 | PgBouncer active | Check Supabase connection pooler dashboard | Transaction mode active. Connection count stable. |
| P9 | FCP on 3G | Lighthouse with simulated Slow 3G on homepage | First Contentful Paint < 1.8s. |
| P10 | Lighthouse: Performance | Run Lighthouse on homepage, search, job detail | All pages ≥ 90 Performance score. |
| P11 | Lighthouse: Accessibility | Run Lighthouse on all pages | All pages ≥ 95 Accessibility score. |
| P12 | CLS | Check Lighthouse on all pages | Cumulative Layout Shift < 0.1 on all pages. |
| P13 | Bundle size | Check `next build` output | Main JS bundle < 200KB gzipped. |
| P14 | Worker bundle | Check OpenNext output | Worker bundle < 3 MiB. |
| P15 | TTFB | Load job detail page from different region | TTFB < 200ms (Cloudflare edge cache). |

**FAIL gate:** P1, P4–P6, P10–P11, P14 are hard failures. P2–P3, P7–P9, P12–P13, P15 are soft.

### 1.4 Gate 4: Compliance and Launch (Week 12)

Run these checks before squash-merging `display-phase` → `main`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| L1 | Transparency page | Load `/transparency` | All 7 sections from SPEC.md §9.4 present. Plain English. No jargon. |
| L2 | AI Disclosure: search | Perform a search | "Results ranked by AI" disclosure visible. |
| L3 | AI Disclosure: explanation | View job detail with explanation | "AI-generated" badge visible next to explanation. |
| L4 | AI Disclosure: predicted salary | View job with predicted salary | "est." label with tooltip explaining prediction. |
| L5 | Audit log completeness | Perform 10 searches + view 5 job details | `ai_decision_audit_log` contains ≥ 15 rows with correct `decision_type` values. |
| L6 | Audit log: monthly review | Run review query from PLAYBOOK.md §4.6 | Returns aggregated stats by decision type. |
| L7 | axe-core: homepage | Run `@axe-core/playwright` on `/` | Zero critical or serious violations. |
| L8 | axe-core: search | Run on `/search?q=developer` | Zero critical or serious violations. |
| L9 | axe-core: job detail | Run on `/jobs/[id]` | Zero critical or serious violations. |
| L10 | axe-core: transparency | Run on `/transparency` | Zero critical or serious violations. |
| L11 | Skip link | Tab on any page | "Skip to main content" link visible on first Tab. Clicking it jumps past header. |
| L12 | Keyboard: search | Tab through search flow | All inputs, buttons, filters keyboard-accessible. No focus traps. |
| L13 | Keyboard: job detail | Tab through job detail | All links, buttons, skills pills keyboard-accessible. |
| L14 | Colour contrast | Lighthouse accessibility audit | All text meets 4.5:1 contrast ratio (AA). |
| L15 | Touch targets | Inspect mobile viewport | All interactive elements ≥ 48×48px. Minimum 8px spacing. |
| L16 | Reduced motion | Set `prefers-reduced-motion: reduce` | Skeleton animations disabled. No moving elements. |
| L17 | Font size | Check body text on mobile | Minimum 16px. No text smaller than 14px anywhere. |
| L18 | JSON-LD valid | Paste job detail JSON-LD into schema.org validator | Zero errors. All required JobPosting fields present. |
| L19 | Sitemap | Load `/sitemap.xml` | Valid XML. Contains job URLs. < 50K URLs. |
| L20 | Robots.txt | Load `/robots.txt` | Allows `/`. Disallows `/api/` and `/profile/`. Contains sitemap URL. |
| L21 | OG tags | Paste job URL into Facebook Sharing Debugger | Title, description, image preview render correctly. |
| L22 | Mobile: homepage | Load on iPhone SE viewport (375×667) | Single column layout. No horizontal scroll. All text readable. |
| L23 | Mobile: search | Perform search on mobile viewport | Cards full-width. Filter drawer works. |
| L24 | Mobile: job detail | Load job detail on mobile | All sections stack correctly. Apply button easily tappable. |
| L25 | Mobile: sticky search | Scroll down on search results | Search bar stays fixed at top. |

**FAIL gate:** L1–L6 (compliance) and L7–L10 (accessibility) are hard failures. L11–L25 are soft but expected to pass.

---

## 2. Test Search Queries

These 10 queries verify the full Phase 3 search pipeline end-to-end: browser → tRPC → Modal → search_jobs_v2 → re-rank → render.

### Query Reference

| # | Query | Filters | Expected behaviour |
|---|---|---|---|
| Q1 | "Python developer" | Location: London (51.5074, -0.1278), radius: 25mi | Job cards appear with Python/software jobs in London. Top 5 have AI explanations. |
| Q2 | "nurse" | Work type: Remote | Remote nursing jobs shown. No onsite jobs. Filter sidebar reflects active filter. |
| Q3 | "accountant" | Category: Finance, min salary: £40K | Finance accountant jobs ≥£40K. Salary badges show green (real) or amber (predicted). |
| Q4 | "data analyst Manchester" | Location: Manchester (53.4808, -2.2426) | Data/analytics jobs near Manchester. Skills pills show relevant skills (SQL, Python, etc.). |
| Q5 | "junior marketing" | Seniority: Junior, date: Last 7 days | Recent junior marketing roles. Seniority badge visible on cards. |
| Q6 | "chef" | No filters | Chef/hospitality jobs from all locations. Pagination if > 20 results. |
| Q7 | "AWS cloud engineer" | Skills: AWS (if skill filter available) | Cloud/DevOps jobs mentioning AWS. Skills pills highlight AWS. |
| Q8 | "" (empty query) | Category: Healthcare | Healthcare jobs listed. No crash from empty query. |
| Q9 | "softwar engeneer" (typo) | None | Semantic search catches intent despite typo. Some relevant software engineering results returned. |
| Q10 | "CIPD qualified HR manager" | None | HR jobs shown. Match explanations mention CIPD relevance. |

### Execution Method

For each query:

1. Enter query in search bar on the live site
2. Apply specified filters
3. Verify: results appear (or sensible empty state), cards render correctly, URL updates
4. Click first result → verify job detail page loads completely
5. Check match explanation streams within 3 seconds
6. Check AI disclosure badge visible

---

## 3. Go/No-Go Production Checklist

Every item must pass before declaring Phase 3 complete. Execute in order.

### 3.1 Pre-Deployment (Local Verification)

| # | Check | Command / Action | Pass criteria |
|---|---|---|---|
| G1 | Full migration chain (001–012) | `supabase db reset` | Zero errors. All 12 migrations applied. |
| G2 | Phase 1+2 functions preserved | `SELECT * FROM search_jobs(query_text := 'developer')` | Returns results. Not broken by Phase 3 migrations. |
| G3 | search_jobs_v2 preserved | `SELECT * FROM search_jobs_v2(query_text := 'developer')` | Returns 18-column results. All Phase 2 filters work. |
| G4 | Materialized views populated | `SELECT COUNT(*) FROM mv_search_facets` | > 0 rows. |
| G5 | Audit log writable | `INSERT INTO ai_decision_audit_log(...)` via service_role | Row created. Anon role cannot read. |
| G6 | TypeScript compiles | `pnpm typecheck` | Zero errors. |
| G7 | All tests pass | `pnpm test` | Zero failures. ≥ 60% coverage. |
| G8 | Lint clean | `pnpm lint` | Zero errors. |
| G9 | Build succeeds | `pnpm build` | Zero errors. |
| G10 | Bundle check | Check build output | Main JS < 200KB gzipped. Worker bundle < 3 MiB. |
| G11 | Lighthouse: Performance | Run on all 3 key pages | All ≥ 90. |
| G12 | Lighthouse: Accessibility | Run on all 3 key pages | All ≥ 95. |
| G13 | axe-core audit | Run Playwright accessibility tests | Zero critical/serious violations across all pages. |
| G14 | 10 test queries | Execute all 10 from §2 | All return results or handle gracefully. Zero errors. |
| G15 | E2E: search flow | Playwright: type query → filter → click result → see detail → apply | Full flow completes without error. |
| G16 | E2E: mobile flow | Same flow on mobile viewport | Drawer filters work. Touch targets adequate. |
| G17 | JSON-LD valid | schema.org validator | Zero errors on 3 sample job pages. |
| G18 | Sitemap valid | Load `/sitemap.xml` | Well-formed XML. Contains job URLs. |
| G19 | robots.txt correct | Load `/robots.txt` | Correct allow/disallow rules. |
| G20 | Transparency page | Load `/transparency` | All 7 sections present and readable. |
| G21 | AI disclosures visible | Navigate through site | AI disclosure on: search rankings, explanations, predicted salaries. |

### 3.2 Production Deployment

| # | Check | Action | Pass criteria |
|---|---|---|---|
| G22 | Migrations applied | `supabase db push` | Zero errors. |
| G23 | CF Pages deployed | `wrangler pages deploy` | Site accessible at production URL. |
| G24 | Custom domain | Load `https://atozjobs.ai` | Resolves. SSL valid. Homepage loads. |
| G25 | Env vars verified | Check CF dashboard | All env vars from SPEC.md §5.2 set. |
| G26 | Modal endpoint reachable | Search from production site | Results returned (Modal `/search` responds). |
| G27 | Sentry active | Trigger test error | Error appears in Sentry production project. |
| G28 | PostHog active | Load production site | Page view event in PostHog. |

### 3.3 Post-Deployment Verification

| # | Check | Action | Pass criteria |
|---|---|---|---|
| G29 | Search works | Type "developer" on production site | Results appear within 3 seconds. |
| G30 | ISR active | Load job detail page twice | Cache HIT on second load. |
| G31 | Explanations stream | View top result detail | AI explanation streams within 3 seconds. |
| G32 | Audit logging | Check `ai_decision_audit_log` table | Rows appearing for production searches. |
| G33 | Mobile works | Load on real mobile device | Full flow: search → filter → detail → apply. |
| G34 | SEO indexable | `curl -I https://atozjobs.ai` | Returns 200. No `X-Robots-Tag: noindex`. |

### 3.4 24-Hour Monitoring

| # | Metric | Check | Pass criteria |
|---|---|---|---|
| G35 | Error rate | Sentry | < 1% of page loads produce errors. |
| G36 | Search latency | PostHog + Sentry Performance | P95 total search (including render) < 5 seconds. |
| G37 | ISR cache hits | Cloudflare Analytics | > 50% cache hit rate on job detail pages. |
| G38 | Audit log volume | `SELECT COUNT(*) FROM ai_decision_audit_log WHERE created_at > now() - interval '24 hours'` | Rows growing. No gaps > 1 hour. |
| G39 | Worker errors | Cloudflare Pages dashboard | Zero worker exceptions. |
| G40 | LLM cost | Helicone dashboard | < $1 in first 24 hours (proportional to traffic). |

---

## 4. Rollback Procedures

### 4.1 Code Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Bad deployment (site broken) | `wrangler pages deploy --branch=<previous>` or rollback in CF dashboard. | < 5 min |
| tRPC error (specific route fails) | Fix code, redeploy. If urgent: disable route with environment flag. | < 15 min |
| AI SDK streaming broken | Disable explanation streaming (return static fallback text). Redeploy. | < 15 min |
| OpenNext adapter incompatibility | Switch deployment target to Netlify Free. `netlify deploy`. | < 30 min |

### 4.2 Database Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Migration 012 breaks queries | Run `down.sql` for 012. Facets sidebar shows empty. Site still works. | < 5 min |
| Migration 011 issue | Run `down.sql` for 011. Audit logging stops. Site still works (just not logging). | < 5 min |
| Phase 3 migrations corrupt Phase 1+2 | Restore from Supabase PITR. Point-in-time to before migration push. | < 4 hours |

### 4.3 Infrastructure Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Cloudflare Pages outage | Deploy to Netlify Free. Point DNS CNAME to Netlify. | < 1 hour |
| Modal endpoint down | Search falls back to search_jobs_v2 without re-ranking (call DB directly from tRPC). No explanations. | < 15 min |
| Supabase outage | Site shows cached ISR pages. Search returns "Service temporarily unavailable." No data loss. | 0 (wait for recovery) |
| LLM provider (OpenAI) down | Explanations show fallback text. Search and ranking still work (don't depend on OpenAI). | 0 (automatic) |

---

## 5. Performance SLAs

These targets apply from the moment Phase 3 reaches production.

| # | Metric | Target | Alert | How to measure | When to act |
|---|---|---|---|---|---|
| S1 | `search_jobs_v2()` P95 | < 80ms | > 150ms | `pg_stat_statements` | Check HNSW index. Run `VACUUM ANALYZE`. Tune `hnsw.ef_search`. |
| S2 | Full search (embed + DB + rerank) | < 2s | > 3s | Sentry performance tracing | Check Modal cold start. Check network latency to Supabase. |
| S3 | Page TTFB | < 200ms | > 500ms | Cloudflare Web Analytics | Check ISR cache. Verify edge caching. |
| S4 | Job detail FCP | < 1.2s | > 2.0s | Lighthouse CI | Check bundle size. Optimize component loading. |
| S5 | Lighthouse Performance | ≥ 90 | < 80 | CI/CD Lighthouse audit | Identify and fix performance regressions. |
| S6 | Lighthouse Accessibility | ≥ 95 | < 90 | CI/CD Lighthouse audit | Run axe-core. Fix new violations. |
| S7 | ISR cache hit rate | > 50% | < 30% | Cloudflare Analytics | Check revalidation times. Pre-generate more static paths. |
| S8 | LLM cost per month | < $5 | > $10 | Helicone dashboard | Reduce explanation length. Increase caching. Limit to top 3 results. |
| S9 | CLS | < 0.1 | > 0.25 | Lighthouse | Add explicit dimensions to dynamic content areas. |
| S10 | Worker bundle size | < 3 MiB | > 2.5 MiB | OpenNext build output | Dynamic import heavy components. Remove unused dependencies. |

---

## 6. Error Taxonomy

For debugging failures caught by gate checks.

| Error type | Retry? | Impact | Recovery |
|---|---|---|---|
| `tRPCError` (400/500) | Depends | Search broken | Check server logs. Fix Zod schema or handler. |
| `SupabaseError` | Check | DB query failed | Check connection string, RLS policies, table exists. |
| `ModalEndpointError` | Yes | No re-ranking | Return search_jobs_v2 results directly (graceful degradation). |
| `OpenAIError` | Yes | No explanations | Show fallback text. Log for monitoring. |
| `PostcodesIOError` | Yes | No location autocomplete | User can manually enter postcode. Search still works. |
| `CloudflareBuildError` | No | Deploy blocked | Check bundle size, OpenNext compatibility. |
| `ISRRevalidationError` | Auto | Stale content served | Cloudflare retries automatically. Check Supabase connection. |
| `AxeCoreViolation` | No | Accessibility failure | Fix component. Must resolve before merge. |
| `LighthouseRegression` | No | Performance degraded | Identify cause. Optimize before merge. |

---

## 7. Phase 3 Completion Criteria

Phase 3 is **complete** when ALL of the following are true:

- [ ] All 21 Gate 1 (Foundation) checks pass
- [ ] All 28 Gate 2 (Search) checks pass
- [ ] All 15 Gate 3 (Performance) checks pass
- [ ] All 25 Gate 4 (Compliance) checks pass
- [ ] All 10 test search queries execute correctly on production
- [ ] All 40 go/no-go items (G1–G40) pass
- [ ] All 10 performance SLAs meet target thresholds
- [ ] Git tag `v0.3.0` applied to `main` branch
- [ ] `STATUS.md` updated with Phase 3 completion date and metrics
- [ ] `CLAUDE.md` updated with Phase 3 additions

**Total verification items: 89 gate checks + 10 queries + 40 go/no-go items + 10 SLAs = 149 verifiable items.**

When all 149 items pass: **Phase 3 is production-stable. AtoZ Jobs AI is live.**
