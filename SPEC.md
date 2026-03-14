# AtoZ Jobs AI — Phase 3 Specification

**What we build and why. Every line implementation-ready.**

Version: 1.0 · March 2026 · Authority: Doc 11 (Conflict Resolution) supersedes all prior docs.

Phase 3 monthly cost delta: **~$2–5/month** (LLM explanations + domain). Total running cost: **~$34–35/month**.

---

## 0. What Phase 3 Inherits

Phase 1 delivered: `jobs` table (40+ columns, halfvec(768), tsvector), 4 API collectors on Modal, `search_jobs()` with RRF, pipeline processing (salary, location, category, embedding), RLS policies, ~$31/month.

Phase 2 delivered: `skills` + `job_skills` populated via SpaCy PhraseMatcher with ESCO, `esco_skills` table (13,939 rows), pg_trgm fuzzy dedup with composite scoring, MinHash/LSH, XGBoost salary prediction (`salary_predicted_min`/`max` with confidence), Companies House enrichment (SIC codes, company status), cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2 on Modal), match explanations via GPT-4o-mini streamed through Vercel AI SDK, `user_profiles` table with RLS, `search_jobs_v2()` with 18 return fields + skill/category/salary/dedup filters, materialized views (`mv_skill_demand`, `mv_skill_cooccurrence`), ~$33–36/month total.

**Phase 3 consumes all of the above through:**

- `search_jobs_v2()` — the single database function the frontend calls
- Modal `/search` HTTP endpoint — embeds query, calls search_jobs_v2, re-ranks, generates explanations
- Direct Supabase client reads — job detail, facet counts, related jobs
- Vercel AI SDK `useChat()` — streams match explanations to the browser

---

## 1. Database Migrations (Phase 3)

### 1.1 Migration 011: AI Decision Audit Log (EU AI Act Compliance)

```sql
-- EU AI Act Article 12: automatic logging of all AI decisions
CREATE TABLE ai_decision_audit_log (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,

    -- What happened
    decision_type   TEXT NOT NULL,
    -- Values: 'search_ranking', 'match_explanation', 'salary_prediction',
    --         'skill_extraction', 'dedup_decision', 'profile_match'

    -- Who/what made the decision
    model_provider  TEXT NOT NULL,         -- 'gemini', 'openai', 'xgboost', 'rule_based', 'cross_encoder'
    model_version   TEXT NOT NULL,         -- 'gemini-embedding-001', 'gpt-4o-mini', 'ms-marco-MiniLM-L-6-v2'

    -- Input (hashed for privacy — never store raw PII)
    input_hash      TEXT NOT NULL,         -- SHA-256 of input text
    input_summary   TEXT,                  -- Non-PII summary: "query: Python developer, location: London"

    -- Output
    output_summary  TEXT NOT NULL,         -- "returned 20 results, top: Senior Python Dev at TechCo"
    confidence      FLOAT,                -- Model confidence score (0–1)

    -- Context
    user_id         UUID,                  -- NULL for anonymous searches
    job_id          BIGINT,                -- Related job if applicable
    session_id      TEXT,                  -- Browser session for grouping

    -- Performance
    latency_ms      INT,                   -- Processing time
    token_count     INT,                   -- LLM tokens used (NULL for non-LLM)
    cost_usd        NUMERIC(8,6),          -- Estimated cost

    -- Human oversight (Article 14)
    requires_review BOOLEAN DEFAULT FALSE, -- Flag for manual review
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     TEXT,
    review_outcome  TEXT                   -- 'approved', 'corrected', 'rejected'
);

-- Indexes for compliance queries
CREATE INDEX idx_audit_created ON ai_decision_audit_log(created_at DESC);
CREATE INDEX idx_audit_type ON ai_decision_audit_log(decision_type);
CREATE INDEX idx_audit_user ON ai_decision_audit_log(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_review ON ai_decision_audit_log(requires_review) WHERE requires_review = TRUE;

-- RLS: service_role writes, no public reads
ALTER TABLE ai_decision_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to audit log"
    ON ai_decision_audit_log FOR ALL
    USING (auth.role() = 'service_role');

-- No anon/authenticated access — audit logs are internal only
```

### 1.2 Migration 012: Search Facet Materialized Views

```sql
-- Facet counts for the filter sidebar (refreshed every 30 minutes)
CREATE MATERIALIZED VIEW mv_search_facets AS
SELECT
    'category' AS facet_type,
    category AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY category

UNION ALL

SELECT
    'location_type' AS facet_type,
    location_type AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY location_type

UNION ALL

SELECT
    'seniority_level' AS facet_type,
    seniority_level AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY seniority_level

UNION ALL

SELECT
    'employment_type' AS facet_type,
    unnest(employment_type) AS facet_value,
    COUNT(*) AS job_count
FROM jobs
WHERE status = 'ready' AND (is_duplicate IS NOT TRUE)
GROUP BY unnest(employment_type);

CREATE UNIQUE INDEX idx_mv_facets_type_value ON mv_search_facets(facet_type, facet_value);

-- Salary histogram for range slider
CREATE MATERIALIZED VIEW mv_salary_histogram AS
SELECT
    width_bucket(
        COALESCE(salary_annual_max, salary_predicted_max),
        10000, 200000, 19
    ) AS bucket,
    COUNT(*) AS job_count,
    MIN(COALESCE(salary_annual_min, salary_predicted_min)) AS bucket_min,
    MAX(COALESCE(salary_annual_max, salary_predicted_max)) AS bucket_max
FROM jobs
WHERE status = 'ready'
  AND (is_duplicate IS NOT TRUE)
  AND COALESCE(salary_annual_max, salary_predicted_max) IS NOT NULL
GROUP BY bucket
ORDER BY bucket;

-- Schedule refreshes
SELECT cron.schedule('refresh-search-facets', '*/30 * * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_facets$$);
SELECT cron.schedule('refresh-salary-histogram', '*/30 * * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_salary_histogram$$);
```

**Down migration:**

```sql
SELECT cron.unschedule('refresh-search-facets');
SELECT cron.unschedule('refresh-salary-histogram');
DROP MATERIALIZED VIEW IF EXISTS mv_salary_histogram;
DROP MATERIALIZED VIEW IF EXISTS mv_search_facets;
DROP TABLE IF EXISTS ai_decision_audit_log;
```

---

## 2. Application Architecture

### 2.1 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Framework | Next.js 16 (App Router, Turbopack) | SSR/ISR, React Server Components, streaming |
| Hosting | Cloudflare Pages free tier (OpenNext adapter) | Unlimited bandwidth, commercial OK, $0 |
| API layer | tRPC (search/recommendations) + direct Supabase client (reads) + Server Actions (form mutations) | Visibility, type safety, debugging — per Documenso pattern |
| AI integration | Vercel AI SDK v6 (`useChat`, `generateObject`, `streamText`) | Streaming, provider abstraction, Zod validation |
| LLM proxy | LiteLLM → GPT-4o-mini | Budget controls ($50/mo cap), model switching |
| LLM observability | Helicone (free tier, 10K req/mo) | Token tracking, caching, cost monitoring |
| Type safety | `supabase gen types typescript` + `pydantic2ts` | Zero runtime type mismatches |
| Styling | Tailwind CSS v4 | Utility-first, minimal bundle |
| Testing | Vitest + @testing-library/react + Playwright | Unit + integration + E2E |
| Error tracking | Sentry (@sentry/nextjs) | 5K errors/mo free |
| Analytics | PostHog (free tier) | 1M events/mo, session recordings |
| Uptime | Better Stack (free) | 10 monitors, 3-min checks |

### 2.2 Critical Security: CVE-2025-66478

**CVSS 10.0 — Remote Code Execution via React Server Components.** Patched in Next.js 16.1.6+.

**Action:** Pin `next@>=16.1.6` in `package.json`. Verify with `pnpm audit`. The `proxy.ts` file (replacing `middleware.ts` in Next.js 16) must NOT pass unsanitised user input to server component rendering.

### 2.3 Deployment: Cloudflare Pages

**Why not Vercel Pro:** Vercel Hobby prohibits commercial use. Vercel Pro costs $20/month. Cloudflare Pages free tier allows commercial use with unlimited bandwidth.

**OpenNext adapter:** Version 1.0-beta supports Next.js 14–16 with App Router, SSR, Server Actions, ISR, and Middleware (now `proxy.ts`).

**Constraints:**

| Limit | Free tier | Workers Paid ($5/mo) |
|---|---|---|
| Worker bundle size | 3 MiB | 10 MiB |
| Function requests | 100K/day (~3M/mo) | 10M/mo |
| Build minutes | 500/mo | 5,000/mo |
| Bandwidth | Unlimited | Unlimited |

**Upgrade trigger:** If Next.js bundle exceeds 3 MiB after tree-shaking, upgrade to Workers Paid ($5/mo).

---

## 3. Page Routes and Component Tree

### 3.1 Route Map

```
app/
├── layout.tsx                  # Root layout: metadata, fonts, PostHog, Sentry
├── page.tsx                    # Homepage: hero, search bar, featured categories
├── search/
│   └── page.tsx                # Search results: cards, filters, pagination
├── jobs/
│   └── [id]/
│       └── page.tsx            # Job detail: full info, map, skills, explanation
├── profile/
│   └── page.tsx                # User profile form (requires auth)
├── transparency/
│   └── page.tsx                # EU AI Act: what AI does, models used, limitations
├── api/
│   └── trpc/
│       └── [trpc]/
│           └── route.ts        # tRPC HTTP handler
├── sitemap.xml/
│   └── route.ts                # Dynamic XML sitemap
└── robots.txt/
    └── route.ts                # Dynamic robots.txt
```

### 3.2 Component Tree

```
components/
├── search/
│   ├── SearchInput.tsx         # Natural language input + location autocomplete + radius
│   ├── LocationAutocomplete.tsx # postcodes.io typeahead
│   ├── RadiusSelector.tsx      # Dropdown: 5/10/25/50/100 miles
│   ├── FilterSidebar.tsx       # All filters with facet counts
│   ├── FilterChip.tsx          # Active filter badge with remove
│   ├── SalaryRangeSlider.tsx   # Dual-handle range from mv_salary_histogram
│   ├── DatePostedFilter.tsx    # 24h/7d/30d/any
│   └── SearchResultsGrid.tsx   # Job cards grid with skeleton loading
├── jobs/
│   ├── JobCard.tsx             # Title, company, salary, location, skills, match
│   ├── JobCardSkeleton.tsx     # Loading placeholder
│   ├── JobDetail.tsx           # Full job view
│   ├── SalaryBadge.tsx         # Real vs predicted salary display
│   ├── SkillsPills.tsx         # Skill badges with ESCO links
│   ├── MatchExplanation.tsx    # Streamed AI explanation (useChat)
│   ├── RelatedJobs.tsx         # 5 similar jobs via vector similarity
│   ├── CompanyInfo.tsx         # Companies House data card
│   └── ApplyButton.tsx         # External redirect to source_url
├── layout/
│   ├── Header.tsx              # Logo, nav, auth button
│   ├── Footer.tsx              # Links, transparency page, accessibility
│   ├── MobileNav.tsx           # Hamburger menu for mobile
│   └── SkipLink.tsx            # WCAG: skip to main content
├── ui/
│   ├── Badge.tsx               # Reusable badge component
│   ├── Skeleton.tsx            # Animated skeleton loader
│   ├── Pagination.tsx          # Page navigation with URL state
│   └── AIDisclosure.tsx        # "AI-powered" notice (EU AI Act Article 50)
└── seo/
    ├── JobPostingJsonLd.tsx     # schema.org/JobPosting structured data
    └── MetaTags.tsx             # Dynamic OG/Twitter meta
```

---

## 4. tRPC Router Implementation

### 4.1 Router Structure

```typescript
// web/src/server/trpc.ts
import { initTRPC } from '@trpc/server';
import superjson from 'superjson';

const t = initTRPC.create({ transformer: superjson });
export const router = t.router;
export const publicProcedure = t.procedure;

// web/src/server/routers/index.ts
import { router } from '../trpc';
import { searchRouter } from './search';
import { jobRouter } from './job';
import { facetsRouter } from './facets';

export const appRouter = router({
  search: searchRouter,
  job: jobRouter,
  facets: facetsRouter,
});

export type AppRouter = typeof appRouter;
```

### 4.2 Search Router

```typescript
// web/src/server/routers/search.ts
import { z } from 'zod';
import { publicProcedure, router } from '../trpc';

const searchInputSchema = z.object({
  q: z.string().min(1).max(500),
  lat: z.number().optional(),
  lng: z.number().optional(),
  radius: z.number().min(1).max(200).default(25),
  minSalary: z.number().optional(),
  maxSalary: z.number().optional(),
  workType: z.enum(['remote', 'hybrid', 'onsite']).optional(),
  category: z.string().optional(),
  seniority: z.string().optional(),
  skills: z.array(z.string()).optional(),
  datePosted: z.enum(['24h', '7d', '30d']).optional(),
  excludeDuplicates: z.boolean().default(true),
  page: z.number().min(1).default(1),
  pageSize: z.number().min(1).max(50).default(20),
});

export const searchRouter = router({
  query: publicProcedure
    .input(searchInputSchema)
    .query(async ({ input }) => {
      // 1. Call Modal /search endpoint (embeds query, calls search_jobs_v2, re-ranks)
      // 2. Log to ai_decision_audit_log (EU AI Act Article 12)
      // 3. Return typed results
      // See §4.5 for data flow
    }),

  related: publicProcedure
    .input(z.object({
      jobId: z.number(),
      limit: z.number().min(1).max(10).default(5),
    }))
    .query(async ({ input }) => {
      // Direct Supabase: cosine similarity on embedding column
      // SELECT id, title, company_name, location_city,
      //   embedding <=> (SELECT embedding FROM jobs WHERE id = $1) AS distance
      // FROM jobs WHERE status = 'ready' AND id != $1
      // ORDER BY distance LIMIT $2
    }),
});
```

### 4.3 Job Router

```typescript
// web/src/server/routers/job.ts
export const jobRouter = router({
  byId: publicProcedure
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      // Direct Supabase read — NOT tRPC-proxied search
      // Fetches: job fields + company data + skills (JOIN job_skills + skills)
      // Returns full job detail shape (see §4.6)
    }),
});
```

### 4.4 Facets Router

```typescript
// web/src/server/routers/facets.ts
export const facetsRouter = router({
  counts: publicProcedure
    .query(async () => {
      // Read from mv_search_facets materialized view
      // Returns: { categories: [...], workTypes: [...], seniorities: [...], employmentTypes: [...] }
    }),

  salaryHistogram: publicProcedure
    .query(async () => {
      // Read from mv_salary_histogram materialized view
      // Returns: { buckets: [{ min, max, count }], totalWithSalary, totalWithout }
    }),
});
```

### 4.5 Search Data Flow

```
User types query
    ↓
SearchInput component → URL state update (shareable)
    ↓
tRPC search.query mutation
    ↓
Next.js API route (server-side):
    1. Call Modal /search HTTP endpoint:
       POST https://<modal-url>/search
       Body: { query, user_id?, filters }
       Modal internally:
         a. Embed query via Gemini embedding-001
         b. Call search_jobs_v2() with query_text + query_embedding + filters → top 50
         c. Cross-encoder re-rank → top 20
         d. If user_id: factor profile embedding
    2. Log to ai_decision_audit_log via service_role
    3. Return top 20 results to browser
    ↓
Browser renders JobCards
    ↓
For top 5 results: separate useChat() stream for match explanations
    POST /api/explain
    → LiteLLM → GPT-4o-mini → streamed tokens
    → Log each explanation to ai_decision_audit_log
```

### 4.6 Data Shapes

```typescript
// From search_jobs_v2() — the 18 fields returned by the DB function
interface SearchResult {
  id: number;
  title: string;
  company_name: string;
  description_plain: string;
  location_city: string | null;
  location_region: string | null;
  location_type: string;
  salary_annual_min: number | null;
  salary_annual_max: number | null;
  salary_predicted_min: number | null;
  salary_predicted_max: number | null;
  salary_is_predicted: boolean;
  employment_type: string[];
  seniority_level: string | null;
  category: string | null;
  date_posted: string; // ISO 8601
  source_url: string;
  rrf_score: number;
  // Added by cross-encoder (Modal):
  rerank_score?: number;
  // Added by client-side streaming:
  explanation?: string;
}

// Job detail (direct Supabase read + joins)
interface JobDetail extends SearchResult {
  description: string;        // Full HTML description
  location_raw: string | null;
  location_postcode: string | null;
  location_lat: number | null;
  location_lng: number | null;
  salary_raw: string | null;
  salary_currency: string;
  salary_period: string;
  salary_confidence: number | null;
  visa_sponsorship: string;
  date_expires: string | null;
  date_crawled: string;
  // Company enrichment
  company: {
    name: string;
    sic_codes: string[] | null;
    company_status: string | null;
    date_of_creation: string | null;
    website: string | null;
  } | null;
  // Skills
  skills: Array<{
    name: string;
    esco_uri: string | null;
    skill_type: string;
    confidence: number;
    is_required: boolean;
  }>;
}

// Facet counts
interface FacetCounts {
  categories: Array<{ value: string; count: number }>;
  workTypes: Array<{ value: string; count: number }>;
  seniorities: Array<{ value: string; count: number }>;
  employmentTypes: Array<{ value: string; count: number }>;
}
```

---

## 5. Supabase Client Setup

### 5.1 Server vs Browser Clients

```typescript
// web/src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import type { Database } from '@/types/database';

export function createClient() {
  const cookieStore = cookies();
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options));
        },
      },
    }
  );
}

// web/src/lib/supabase/browser.ts
import { createBrowserClient } from '@supabase/ssr';
import type { Database } from '@/types/database';

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

### 5.2 Environment Variables

| Variable | Prefix | Scope | Where |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `NEXT_PUBLIC_` | Browser + Server | Cloudflare env |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `NEXT_PUBLIC_` | Browser + Server | Cloudflare env |
| `SUPABASE_SERVICE_ROLE_KEY` | None | Server only | Cloudflare env (encrypted) |
| `MODAL_SEARCH_URL` | None | Server only | Cloudflare env |
| `OPENAI_API_KEY` | None | Server only | Cloudflare env |
| `LITELLM_API_KEY` | None | Server only | Cloudflare env |
| `HELICONE_API_KEY` | None | Server only | Cloudflare env |
| `SENTRY_DSN` | `NEXT_PUBLIC_` | Browser + Server | Cloudflare env |
| `NEXT_PUBLIC_POSTHOG_KEY` | `NEXT_PUBLIC_` | Browser | Cloudflare env |
| `POSTCODES_IO_URL` | `NEXT_PUBLIC_` | Browser | Default: `https://api.postcodes.io` |

**Rule:** Only `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SENTRY_DSN`, `POSTHOG_KEY`, and `POSTCODES_IO_URL` get the `NEXT_PUBLIC_` prefix. Everything else is server-only. Never expose `SERVICE_ROLE_KEY` or any API key to the browser.

---

## 6. Vercel AI SDK v6 Integration

### 6.1 Match Explanation Streaming

```typescript
// web/src/app/api/explain/route.ts
import { streamText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';

const openai = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.HELICONE_API_KEY
    ? 'https://oai.helicone.ai/v1'
    : undefined,
  headers: process.env.HELICONE_API_KEY
    ? { 'Helicone-Auth': `Bearer ${process.env.HELICONE_API_KEY}` }
    : undefined,
});

export async function POST(req: Request) {
  const { query, job, profile } = await req.json();

  const result = streamText({
    model: openai('gpt-4o-mini'),
    maxTokens: 100,
    temperature: 0.3,
    prompt: `You are a UK careers advisor. Explain in 2-3 sentences why this job matches the user's search.

User searched for: ${query}
${profile ? `User profile: ${profile}` : ''}

Job: ${job.title} at ${job.company_name}
Location: ${job.location_city || 'Not specified'}
Skills required: ${job.skills?.join(', ') || 'Not specified'}
Salary: ${job.salary_annual_min ? `£${job.salary_annual_min}–£${job.salary_annual_max}` : 'Not disclosed'}

Be specific about skill matches and location relevance. Be honest about gaps. Keep it under 50 words.`,
  });

  // Log to audit table (fire-and-forget, non-blocking)
  logAuditEntry({
    decision_type: 'match_explanation',
    model_provider: 'openai',
    model_version: 'gpt-4o-mini',
    input_hash: hashInput(query + job.id),
    input_summary: `query: ${query}, job: ${job.title}`,
    output_summary: 'streamed explanation',
    job_id: job.id,
  });

  return result.toDataStreamResponse();
}
```

### 6.1.1 LLM Budget Enforcement

Three layers prevent uncapped OpenAI spend:

**Layer 1 — OpenAI dashboard hard cap (external):** Set a $50/month spending cap in the OpenAI dashboard under Settings → Limits → Monthly budget. This is the last line of defence — OpenAI rejects all API calls once the cap is hit, returning HTTP 429.

**Layer 2 — Application-level pre-call check:** Before every `/api/explain` call, query the current month's spend from the audit log. If the running total exceeds $45, skip the LLM call and return fallback text immediately.

```typescript
// web/src/lib/llm/budget-guard.ts
import { createAdminClient } from '@/lib/supabase/admin';

const MONTHLY_SOFT_CAP_USD = 45;

export async function isLLMBudgetExhausted(): Promise<boolean> {
  const supabase = createAdminClient();
  const startOfMonth = new Date();
  startOfMonth.setDate(1);
  startOfMonth.setHours(0, 0, 0, 0);

  const { data } = await supabase
    .from('ai_decision_audit_log')
    .select('cost_usd')
    .eq('decision_type', 'match_explanation')
    .gte('created_at', startOfMonth.toISOString());

  const totalCost = (data ?? []).reduce(
    (sum, row) => sum + (Number(row.cost_usd) || 0),
    0
  );

  return totalCost >= MONTHLY_SOFT_CAP_USD;
}

// Used in /api/explain/route.ts before calling streamText:
const budgetExhausted = await isLLMBudgetExhausted();
if (budgetExhausted) {
  return new Response(
    JSON.stringify({ fallback: true, text: generateFallbackExplanation(query, job) }),
    { headers: { 'Content-Type': 'application/json' } }
  );
}
```

**Layer 3 — Helicone observability (monitoring):** Helicone tracks per-request token counts and cost in real time. Use its dashboard for daily spend visibility and alerting — but it does not enforce caps.

### 6.2 Client-Side useChat Hook

```typescript
// In MatchExplanation.tsx
import { useChat } from '@ai-sdk/react';

export function MatchExplanation({ query, job, profile }: Props) {
  const { messages, isLoading } = useChat({
    api: '/api/explain',
    body: { query, job, profile },
    initialMessages: [],
  });

  if (isLoading) return <Skeleton className="h-12 w-full" />;

  const explanation = messages.find(m => m.role === 'assistant')?.content;
  if (!explanation) return null;

  return (
    <div role="region" aria-label="AI match explanation">
      <AIDisclosure />
      <p className="text-sm text-gray-600">{explanation}</p>
    </div>
  );
}
```

---

## 7. ISR and Caching Configuration

### 7.1 Revalidation Strategy

| Route | Revalidation | Reason |
|---|---|---|
| `/` (homepage) | 1 hour (3600s) | Featured categories, stats change slowly |
| `/search` | Dynamic (no cache) | Every search is unique; filters in URL |
| `/jobs/[id]` | 30 minutes (1800s) | Job data updates infrequently; descriptions stable |
| `/transparency` | 24 hours (86400s) | Static compliance page |
| `/sitemap.xml` | 6 hours (21600s) | New jobs appear via pipeline |

### 7.2 Implementation

```typescript
// app/jobs/[id]/page.tsx
export const revalidate = 1800; // 30 minutes

export async function generateStaticParams() {
  // Pre-generate top 1000 most-viewed jobs
  const supabase = createClient();
  const { data } = await supabase
    .from('jobs')
    .select('id')
    .eq('status', 'ready')
    .order('date_posted', { ascending: false })
    .limit(1000);
  return data?.map(j => ({ id: String(j.id) })) ?? [];
}

// app/page.tsx
export const revalidate = 3600; // 1 hour

// Search is always dynamic — filters make every request unique
// app/search/page.tsx has NO revalidate export (SSR on every request)
```

### 7.3 Cloudflare Pages ISR

OpenNext adapter translates Next.js ISR to Cloudflare's Cache API. Pages are served from Cloudflare's edge CDN with `stale-while-revalidate`. No additional configuration needed beyond the `revalidate` exports.

---

## 8. SEO Configuration

### 8.1 schema.org/JobPosting JSON-LD

```typescript
// components/seo/JobPostingJsonLd.tsx
export function JobPostingJsonLd({ job }: { job: JobDetail }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: job.title,
    description: job.description_plain,
    datePosted: job.date_posted,
    validThrough: job.date_expires || undefined,
    employmentType: job.employment_type?.map(t => t.toUpperCase()) || undefined,
    hiringOrganization: {
      '@type': 'Organization',
      name: job.company_name,
      sameAs: job.company?.website || undefined,
    },
    jobLocation: job.location_type === 'remote'
      ? undefined
      : {
          '@type': 'Place',
          address: {
            '@type': 'PostalAddress',
            addressLocality: job.location_city || undefined,
            addressRegion: job.location_region || undefined,
            postalCode: job.location_postcode || undefined,
            addressCountry: 'GB',
          },
        },
    jobLocationType: job.location_type === 'remote' ? 'TELECOMMUTE' : undefined,
    baseSalary: (job.salary_annual_min || job.salary_predicted_min)
      ? {
          '@type': 'MonetaryAmount',
          currency: job.salary_currency || 'GBP',
          value: {
            '@type': 'QuantitativeValue',
            minValue: job.salary_annual_min || job.salary_predicted_min,
            maxValue: job.salary_annual_max || job.salary_predicted_max,
            unitText: 'YEAR',
          },
        }
      : undefined,
    skills: job.skills?.map(s => s.name).join(', ') || undefined,
    directApply: false, // We redirect to source
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

### 8.2 Dynamic Meta Tags

```typescript
// app/jobs/[id]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const job = await getJobById(params.id);
  if (!job) return { title: 'Job Not Found' };

  const salary = job.salary_annual_min
    ? `£${Math.round(job.salary_annual_min / 1000)}k–£${Math.round(job.salary_annual_max / 1000)}k`
    : 'Salary not disclosed';

  return {
    title: `${job.title} at ${job.company_name} | AtoZ Jobs`,
    description: `${job.title} in ${job.location_city || 'UK'}. ${salary}. ${job.skills?.slice(0, 5).map(s => s.name).join(', ') || ''}`,
    openGraph: {
      title: `${job.title} - ${job.company_name}`,
      description: job.description_plain?.slice(0, 160),
      type: 'website',
    },
  };
}
```

### 8.3 XML Sitemap

```typescript
// app/sitemap.xml/route.ts
export async function GET() {
  const supabase = createServiceClient();
  const { data: jobs } = await supabase
    .from('jobs')
    .select('id, date_posted')
    .eq('status', 'ready')
    .order('date_posted', { ascending: false })
    .limit(50000); // Google sitemap limit

  const urls = jobs?.map(j => `
    <url>
      <loc>https://atozjobs.ai/jobs/${j.id}</loc>
      <lastmod>${j.date_posted}</lastmod>
      <changefreq>weekly</changefreq>
      <priority>0.8</priority>
    </url>`).join('') ?? '';

  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://atozjobs.ai</loc><priority>1.0</priority></url>
      <url><loc>https://atozjobs.ai/search</loc><priority>0.9</priority></url>
      <url><loc>https://atozjobs.ai/transparency</loc><priority>0.5</priority></url>
      ${urls}
    </urlset>`,
    { headers: { 'Content-Type': 'application/xml' } }
  );
}
```

---

## 9. EU AI Act Compliance

### 9.1 Classification

AtoZ Jobs AI is **HIGH-RISK under Annex III** of the EU AI Act. Annex III explicitly lists AI systems used to "recruit or select natural persons, including to place targeted job advertisements, analyze and filter job applications and to evaluate candidates." The main enforcement deadline is **August 2, 2026**.

### 9.2 Requirements Mapping

| Article | Requirement | Implementation |
|---|---|---|
| **Article 12** | Automatic logging | `ai_decision_audit_log` table logs every AI decision: search rankings, match explanations, salary predictions, skill extractions |
| **Article 14** | Human oversight | Job matches presented as "recommendations, not decisions." Override mechanism: user can dismiss/report. Review queue for flagged decisions. |
| **Article 13 + 50** | Transparency | `/transparency` page: what AI does, models used, limitations. `<AIDisclosure>` component on every AI-generated element. |
| **Article 15** | Accuracy monitoring | PostHog tracks: click-through rates per search, explanation helpfulness votes, salary prediction accuracy vs actual (when available). Monthly review dashboard. |

### 9.3 GDPR Article 22 + UK Data (Use and Access) Act 2025

- Job matches are recommendations, never automated decisions with legal effects
- Users can request explanation of any ranking decision (data in audit log)
- Right to contest: feedback mechanism on every search result
- Profile data erasure: CASCADE delete on `user_profiles` clears embedding
- No processing of protected characteristics (age, gender, ethnicity) in any model

### 9.4 Transparency Page Content

```
/transparency must include:
1. "How AI powers AtoZ Jobs" — plain English description
2. Models used: Gemini embedding-001 (search), ms-marco-MiniLM-L-6-v2 (ranking),
   GPT-4o-mini (explanations), XGBoost (salary predictions)
3. What AI decides: search result ordering, match explanations, predicted salaries
4. What AI does NOT decide: hiring, shortlisting, application success
5. Known limitations: search quality depends on job description quality,
   salary predictions have ±£5–8K MAE, explanations may occasionally be generic
6. How to contest: contact email + feedback mechanism
7. Last updated date
```

---

## 10. WCAG 2.1 AA Accessibility

### 10.1 Component Requirements

| Component | WCAG Requirement | Implementation |
|---|---|---|
| `SkipLink` | 2.4.1 Bypass Blocks | Hidden link "Skip to main content" visible on focus |
| `SearchInput` | 1.3.1 Info and Relationships | `<label>` linked to input, `aria-describedby` for instructions |
| `FilterSidebar` | 4.1.2 Name, Role, Value | Each filter group in `<fieldset>` with `<legend>` |
| `SalaryRangeSlider` | 4.1.2 + 1.4.11 | `role="slider"`, `aria-valuemin/max/now`, `aria-label` |
| `JobCard` | 1.3.1 + 2.4.4 | `<article>` wrapper, descriptive link text (not "Click here") |
| `SkillsPills` | 1.4.1 Use of Colour | Badge has text + background contrast ≥ 4.5:1, not colour-only |
| `MatchExplanation` | 1.3.1 + 4.1.3 | `role="region"`, `aria-label`, `aria-live="polite"` for streaming |
| `Pagination` | 2.4.3 Focus Order | `aria-label="Pagination"`, `aria-current="page"` on active |
| `AIDisclosure` | Custom (EU AI Act) | Visible text "AI-generated" near every AI output |
| All interactive elements | 2.1.1 Keyboard | Tab-navigable, visible focus ring, Enter/Space activate |
| All text | 1.4.3 Contrast | Minimum 4.5:1 for normal text, 3:1 for large text |

### 10.2 DWP Claimant Accessibility

Target audience includes DWP claimants who may have lower digital literacy, visual impairments, or use assistive technology.

| Design choice | Rationale |
|---|---|
| Minimum 16px body text | Readable without zooming |
| 48×48px minimum touch targets | WCAG 2.5.5 (AAA) for motor impairment |
| High contrast mode support | `prefers-contrast: more` media query |
| Reduced motion support | `prefers-reduced-motion: reduce` — disable skeleton animations |
| Simple language (Flesch-Kincaid ≤ 8) | Plain English for all UI text |
| No CAPTCHA | Accessibility barrier; RLS + rate limiting instead |

---

## 11. Mobile-First Responsive Design

### 11.1 Breakpoints

| Breakpoint | Width | Layout |
|---|---|---|
| Mobile (default) | < 640px | Single column, stacked filters (drawer), bottom-sheet job detail |
| Tablet | 640–1024px | Two columns: filters sidebar + results |
| Desktop | > 1024px | Three columns: filters + results + preview pane |

### 11.2 Critical Mobile Patterns

- **Filter drawer:** On mobile, filters collapse into a full-screen drawer opened by a "Filters" button showing active filter count badge
- **Job cards:** Full-width cards with salary and location prominently displayed (first line after title)
- **Search bar:** Sticky at top of viewport on scroll
- **Pagination:** Infinite scroll on mobile (intersection observer), numbered pagination on desktop
- **Touch targets:** All buttons and interactive elements minimum 48×48px with 8px spacing

---

## 12. Performance Targets

### 12.1 SLAs

| Metric | Target | Alert | How to measure |
|---|---|---|---|
| search_jobs_v2() P95 | < 80ms | > 150ms | `pg_stat_statements` |
| Full search (embed + DB + rerank) | < 2s | > 3s | Sentry performance tracing |
| Page TTFB | < 200ms | > 500ms | Cloudflare Analytics |
| Job detail page load | < 300ms | > 600ms | ISR cache hit rate |
| Lighthouse Performance | ≥ 90 | < 80 | CI/CD Lighthouse audit |
| Lighthouse Accessibility | ≥ 95 | < 90 | CI/CD Lighthouse audit |
| First Contentful Paint | < 1.2s | > 2.0s | Cloudflare Web Analytics |
| Cumulative Layout Shift | < 0.1 | > 0.25 | Lighthouse |
| Bundle size (main JS) | < 200KB gzipped | > 300KB | `next build` output |
| Worker bundle (CF Pages) | < 3 MiB | > 2.5 MiB | OpenNext build output |

### 12.2 Database Optimization

```sql
-- Query-time HNSW tuning for Phase 3
SET LOCAL hnsw.ef_search = 100;  -- Up from 60 (Phase 1) for better recall
-- pgvector 0.8.0+: enable iterative scan for filtered vector search
SET LOCAL hnsw.iterative_scan = relaxed_order;
```

**Connection pooling:** Supabase PgBouncer in transaction mode. Max connections per Cloudflare worker: 1 (pooled). Supabase Pro includes PgBouncer at no extra cost.

---

## 13. Cost Calculations

### 13.1 Phase 3 Monthly Budget

| Item | Provider | Cost | Notes |
|---|---|---|---|
| Database + vectors | Supabase Pro + Small | **$30.00** | Unchanged from Phase 1+2 |
| Pipeline compute | Modal Starter | **$0.00** | ~$8–10 usage against $30 free credit |
| Embeddings | Gemini free tier | **$0.00** | Query embeddings: ~100K/month at ~50 tokens each = 5M tokens |
| LLM explanations | GPT-4o-mini | **~$2.25** | 10K searches × 5 explanations × $0.000045 |
| Frontend hosting | Cloudflare Pages free | **$0.00** | Unlimited bandwidth, commercial OK |
| Error tracking | Sentry Developer | **$0.00** | 5K errors/mo |
| Analytics | PostHog free | **$0.00** | 1M events/mo |
| LLM observability | Helicone free | **$0.00** | 10K requests/mo |
| Uptime monitoring | Better Stack free | **$0.00** | 10 monitors |
| Domain name | Registrar | **~$1.00** | ~$12/year amortized |
| **TOTAL** | | **~$33–34/mo** | |

### 13.2 Upgrade Triggers

| Trigger | Action | Cost impact |
|---|---|---|
| CF Pages bundle > 3 MiB | Workers Paid | +$5/mo |
| Searches exceed 50K/month | Increase LLM budget | +$5–10/mo |
| Revenue justifies Vercel DX | CF Pages → Vercel Pro | +$20/mo |
| Need team Sentry | Developer → Team | +$26/mo |

---

## 14. Acceptance Criteria

### Stage 1: Web App Foundation (Week 9)

- [ ] Next.js 16.1.6+ pinned; `pnpm audit` shows no critical CVEs
- [ ] Turbopack builds successfully; `pnpm dev` starts < 3 seconds
- [ ] `proxy.ts` configured (replaces `middleware.ts` from Next.js 15)
- [ ] tRPC routes respond: `GET /api/trpc/facets.counts` returns JSON
- [ ] Supabase client: browser and server variants created with correct TypeScript types
- [ ] `supabase gen types typescript` produces `database.ts` matching all Phase 1+2 tables
- [ ] Sentry captures a test error in dashboard
- [ ] PostHog tracks a test page view
- [ ] Cloudflare Pages deployment succeeds; site accessible at preview URL
- [ ] OpenNext adapter builds without errors; worker bundle < 3 MiB
- [ ] All environment variables set in Cloudflare dashboard

### Stage 2: Search Interface (Week 10)

- [ ] Search input accepts natural language queries and submits on Enter
- [ ] Location autocomplete returns results from postcodes.io within 200ms
- [ ] Radius selector offers 5/10/25/50/100 mile options
- [ ] Search results appear as job cards with: title, company, salary badge, location, skills pills
- [ ] Predicted salary badge visually distinguished from real salary
- [ ] Filter sidebar shows correct counts from `mv_search_facets`
- [ ] Salary range slider reflects `mv_salary_histogram` data
- [ ] URL updates with filter state (shareable searches)
- [ ] Job detail page loads with full description, company info, skills, apply button
- [ ] Match explanations stream for top 5 results via AI SDK
- [ ] Related jobs section shows 5 similar jobs
- [ ] Skeleton loading states render during data fetch
- [ ] Empty state handling: "No jobs match your search. Try broadening your filters."

### Stage 3: Performance and Caching (Week 11)

- [ ] ISR: job detail page serves from cache (check `x-nextjs-cache: HIT` header)
- [ ] ISR: stale page revalidates within 30 minutes
- [ ] Homepage loads in < 1.2s FCP on 3G throttle
- [ ] `EXPLAIN ANALYZE` on search_jobs_v2 shows HNSW index scan
- [ ] PgBouncer connection pooling active (check Supabase dashboard)
- [ ] Bundle size < 200KB gzipped (check `next build` output)
- [ ] Worker bundle < 3 MiB (check OpenNext output)
- [ ] Lighthouse Performance ≥ 90 on job detail page
- [ ] Lighthouse Accessibility ≥ 95 on all pages

### Stage 4: Compliance and Launch (Week 12)

- [ ] `ai_decision_audit_log` captures search rankings, explanations, salary predictions
- [ ] `/transparency` page contains all 7 required sections from §9.4
- [ ] `<AIDisclosure>` renders on every AI-generated element
- [ ] WCAG 2.1 AA: axe-core audit passes with zero critical violations
- [ ] Skip link visible on keyboard Tab
- [ ] All interactive elements keyboard-navigable
- [ ] Color contrast ≥ 4.5:1 on all text (verified with Lighthouse)
- [ ] Mobile: all touch targets ≥ 48×48px
- [ ] `prefers-reduced-motion` disables animations
- [ ] JobPosting JSON-LD validates at schema.org validator
- [ ] `sitemap.xml` contains all ready jobs
- [ ] `robots.txt` allows search engine crawling
- [ ] OG meta tags render correctly (check with Facebook Debugger)
- [ ] Full launch verification checklist passes (GATES.md)
