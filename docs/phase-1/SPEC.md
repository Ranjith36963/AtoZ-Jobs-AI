# AtoZ Jobs AI — Phase 1 Specification

**What we build and why. Every line implementation-ready.**

Version: 1.0 · March 2026 · Authority: Doc 11 (Conflict Resolution) supersedes all prior docs.

Monthly budget: **~$31/month** (79% reduction from original $142–150 estimate).

---

## 1. Database Schema

### 1.1 Extensions (Migration 001)

```sql
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector: halfvec(768), HNSW
CREATE EXTENSION IF NOT EXISTS postgis;     -- PostGIS: geography(POINT, 4326), ST_DWithin
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- Trigram: fuzzy text matching, GIN indexes
-- pgmq and pg_cron are pre-installed on Supabase Pro
```

### 1.2 Tables (Migration 002)

```sql
CREATE TABLE sources (
    id          SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL UNIQUE,
    api_base_url TEXT,
    is_active   BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    config      JSONB DEFAULT '{}'
);

CREATE TABLE companies (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    website         TEXT,
    industry        TEXT,
    company_size    TEXT,
    sic_code        TEXT,
    metadata        JSONB DEFAULT '{}'
);

CREATE TABLE jobs (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source_id       SMALLINT NOT NULL REFERENCES sources(id),
    external_id     TEXT NOT NULL,
    source_url      TEXT NOT NULL,

    -- Core fields (schema.org/JobPosting aligned)
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    description_plain TEXT,
    company_id      BIGINT REFERENCES companies(id),
    company_name    TEXT NOT NULL,

    -- Location
    location_raw    TEXT,
    location_city   TEXT,
    location_region TEXT,
    location_postcode TEXT,
    location_type   TEXT DEFAULT 'onsite',  -- 'onsite','remote','hybrid','nationwide'
    location        GEOGRAPHY(POINT, 4326),

    -- Employment
    employment_type TEXT[],                 -- '{full_time,permanent}'
    seniority_level TEXT,
    visa_sponsorship TEXT,                  -- 'yes','no','unknown'

    -- Salary (normalized to annual GBP)
    salary_min          NUMERIC(12,2),
    salary_max          NUMERIC(12,2),
    salary_currency     CHAR(3) DEFAULT 'GBP',
    salary_period       TEXT DEFAULT 'annual',
    salary_raw          TEXT,
    salary_annual_min   NUMERIC(12,2),
    salary_annual_max   NUMERIC(12,2),
    salary_is_predicted BOOLEAN DEFAULT FALSE,

    -- Classification
    category            TEXT,
    soc_code            TEXT,
    esco_occupation_uri TEXT,

    -- Dates
    date_posted     TIMESTAMPTZ NOT NULL,
    date_expires    TIMESTAMPTZ,
    date_crawled    TIMESTAMPTZ DEFAULT now(),

    -- Processing state
    status          TEXT DEFAULT 'raw',
    -- Valid values: raw, parsed, normalized, geocoded, embedded, ready, expired, archived
    retry_count     INT DEFAULT 0,
    last_error      TEXT,

    -- Search infrastructure
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title,'')), 'A') ||
        setweight(to_tsvector('english', coalesce(company_name,'')), 'B') ||
        setweight(to_tsvector('english', coalesce(description_plain,'')), 'C')
    ) STORED,
    embedding       HALFVEC(768),

    -- Deduplication
    content_hash    TEXT,

    -- Raw preservation
    raw_data        JSONB,

    UNIQUE(source_id, external_id)
);

CREATE TABLE skills (
    id          INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL UNIQUE,
    esco_uri    TEXT,
    lightcast_id TEXT,
    skill_type  TEXT,        -- 'hard','soft','knowledge'
    category    TEXT
);

CREATE TABLE job_skills (
    job_id      BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id    INT REFERENCES skills(id),
    confidence  FLOAT,
    is_required BOOLEAN DEFAULT true,
    PRIMARY KEY (job_id, skill_id)
);
```

**Design decisions:**

- `content_hash` is computed at ingestion as `SHA-256(lowercase(title) + normalize(company) + normalize(location))` — not a DB-generated column because it needs the raw API data before normalization.
- `search_vector` is a generated stored column — PostgreSQL maintains it automatically on any INSERT/UPDATE. No trigger needed.
- `employment_type` uses `TEXT[]` because the vocabulary is small and fixed. Skills use a junction table because they number in thousands and need analytics queries.
- `raw_data JSONB` preserves original API responses for reprocessing when extraction logic improves.

### 1.3 Indexes (Migration 003)

```sql
-- Vector search: HNSW with cosine distance
CREATE INDEX idx_jobs_embedding ON jobs
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Query-time: SET LOCAL hnsw.ef_search = 60;

-- Full-text search: GIN on generated tsvector
CREATE INDEX idx_jobs_search_vector ON jobs USING gin(search_vector);

-- Fuzzy text: GIN trigram on title (for dedup + autocomplete)
CREATE INDEX idx_jobs_title_trgm ON jobs USING gin(title gin_trgm_ops);

-- Geospatial: GIST on geography column
CREATE INDEX idx_jobs_location ON jobs USING gist(location);

-- B-tree filters (used in search_jobs pre-filter CTE)
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_salary ON jobs(salary_annual_max) WHERE salary_annual_max IS NOT NULL;
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_jobs_date_posted ON jobs(date_posted DESC);
CREATE INDEX idx_jobs_source_external ON jobs(source_id, external_id);
-- Note: UNIQUE constraint already creates this, but explicit for clarity

-- Autovacuum tuning (HNSW death spiral prevention)
ALTER TABLE jobs SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_vacuum_cost_delay = 2,
    autovacuum_vacuum_threshold = 100,
    autovacuum_analyze_scale_factor = 0.005
);
```

### 1.4 Queues, Cron, and Health View (Migration 004)

```sql
-- 5 processing queues + 1 dead letter queue = 6 total
SELECT pgmq.create('parse_queue');
SELECT pgmq.create('normalize_queue');
SELECT pgmq.create('dedup_queue');
SELECT pgmq.create('geocode_queue');
SELECT pgmq.create('embed_queue');
SELECT pgmq.create('dead_letter_queue');

-- Auto-enqueue new jobs for parsing
CREATE OR REPLACE FUNCTION enqueue_for_parsing() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pgmq.send('parse_queue', jsonb_build_object('job_id', NEW.id));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_job_insert AFTER INSERT ON jobs
    FOR EACH ROW WHEN (NEW.status = 'raw')
    EXECUTE FUNCTION enqueue_for_parsing();

-- Monthly HNSW reindex (3 AM on 1st of each month)
SELECT cron.schedule(
    'reindex-hnsw-monthly',
    '0 3 1 * *',
    $$REINDEX INDEX CONCURRENTLY idx_jobs_embedding$$
);

-- Daily expiry (2 AM)
SELECT cron.schedule(
    'expire-stale-jobs',
    '0 2 * * *',
    $$
    UPDATE jobs SET status = 'expired', last_error = 'auto-expired'
    WHERE status = 'ready'
      AND date_expires IS NOT NULL
      AND date_expires < NOW();

    UPDATE jobs SET status = 'expired', last_error = 'default-45d-expired'
    WHERE status = 'ready'
      AND date_expires IS NULL
      AND date_posted < NOW() - INTERVAL '45 days';

    UPDATE jobs SET status = 'archived'
    WHERE status = 'expired'
      AND date_crawled < NOW() - INTERVAL '90 days';
    $$
);

-- Pipeline health monitoring view
CREATE VIEW pipeline_health AS
SELECT
    -- Ingestion metrics
    COUNT(*) FILTER (WHERE date_crawled > NOW() - INTERVAL '1 hour')
        AS jobs_ingested_last_hour,
    COUNT(*) FILTER (WHERE date_crawled > NOW() - INTERVAL '24 hours')
        AS jobs_ingested_last_24h,
    -- Processing metrics
    COUNT(*) FILTER (WHERE status = 'raw')        AS queue_raw,
    COUNT(*) FILTER (WHERE status = 'parsed')      AS queue_parsed,
    COUNT(*) FILTER (WHERE status = 'normalized')  AS queue_normalized,
    COUNT(*) FILTER (WHERE status = 'geocoded')    AS queue_geocoded,
    COUNT(*) FILTER (WHERE status = 'ready')       AS total_ready,
    COUNT(*) FILTER (WHERE status = 'expired')     AS total_expired,
    -- Failure rate
    COUNT(*) FILTER (WHERE retry_count > 0)        AS jobs_with_retries,
    COUNT(*) FILTER (WHERE retry_count >= 3)       AS jobs_in_dlq,
    -- Data quality
    COUNT(*) FILTER (WHERE embedding IS NULL AND status = 'ready')
        AS ready_without_embedding,
    COUNT(*) FILTER (WHERE salary_annual_min IS NULL AND status = 'ready')
        AS ready_without_salary,
    COUNT(*) FILTER (WHERE location IS NULL
        AND location_type != 'remote' AND status = 'ready')
        AS ready_without_location,
    -- Storage
    pg_database_size(current_database()) AS db_size_bytes
FROM jobs;
```

**Alert thresholds (log after every pipeline run):**

- `jobs_ingested_last_hour = 0` for 3 consecutive hours → investigate API keys, circuit breaker state
- `jobs_in_dlq > 100` → check `last_error` patterns, investigate source quality
- `ready_without_embedding > 0` → check Gemini API key, rate limits

### 1.5 Row-Level Security (Migration 005)

```sql
ALTER TABLE jobs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources    ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies  ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills     ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skills ENABLE ROW LEVEL SECURITY;

-- Public read: anyone can read ready jobs (anon key)
CREATE POLICY "Public can read ready jobs"
    ON jobs FOR SELECT USING (status = 'ready');

-- Service role: pipeline can read/write everything (service_role key)
CREATE POLICY "Service role full access to jobs"
    ON jobs FOR ALL USING (auth.role() = 'service_role');

-- Public read: reference tables
CREATE POLICY "Public can read sources"    ON sources    FOR SELECT USING (true);
CREATE POLICY "Public can read companies"  ON companies  FOR SELECT USING (true);
CREATE POLICY "Public can read skills"     ON skills     FOR SELECT USING (true);
CREATE POLICY "Public can read job_skills" ON job_skills FOR SELECT USING (true);

-- Service role write: reference tables
CREATE POLICY "Service role writes sources"    ON sources    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes companies"  ON companies  FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes skills"     ON skills     FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes job_skills" ON job_skills FOR ALL USING (auth.role() = 'service_role');
```

**Key principle:** Frontend (anon key) can ONLY read `status='ready'` jobs and reference tables. Pipeline (service_role key) can read/write everything — used only in server-side Python. The anon key is safe for browser because RLS restricts what it can see.

### 1.6 Seed Data

```sql
-- Tier 1: Reference data (seed.sql, committed to git)
INSERT INTO sources (name, api_base_url, is_active) VALUES
    ('reed',      'https://www.reed.co.uk/api/1.0',            true),
    ('adzuna',    'https://api.adzuna.com/v1/api/jobs/gb',      true),
    ('jooble',    'https://jooble.org/api',                     true),
    ('careerjet', 'https://search.api.careerjet.net/v4',        true);
```

Tier 2 (seed_jobs.py): Faker-generated 1,000–5,000 realistic UK jobs. Command: `just seed:dev`.
Tier 3 (seed_bulk.py): 500K jobs via PostgreSQL `COPY`. Command: `just seed:perf`. Never run against production.

---

## 2. API Contracts

### 2.1 Reed API

| Field | Value |
|---|---|
| Base URL | `https://www.reed.co.uk/api/1.0/search` |
| Auth | Basic Auth: API key as username, empty string as password |
| Rate limit | Max 2 requests/second (self-imposed; Jobseeker API not explicitly limited) |
| Pagination | `resultsToTake` (max 100), `resultsToSkip` (offset). Response includes `totalResults`. |
| Fetch frequency | Every 30 minutes |
| Coverage strategy | Category sweep: iterate all Reed sectors with `postedWithin=1` (last 24 hours) |

**Key response fields:**

| Field | Type | Maps to |
|---|---|---|
| `jobId` | int | `external_id` |
| `employerId` | int | company dedup |
| `jobTitle` | string | `title` |
| `jobDescription` | string (HTML) | `description` → strip tags → `description_plain` |
| `locationName` | string | `location_raw` |
| `minimumSalary` | number or null | `salary_min` (annual) |
| `maximumSalary` | number or null | `salary_max` (annual) |
| `currency` | string | `salary_currency` |
| `expirationDate` | ISO date | `date_expires` (Reed provides this directly) |
| `date` | ISO date | `date_posted` |
| `jobUrl` | string | `source_url` |
| `partTime` / `fullTime` | bool | `employment_type` array |
| `contractType` | string | `employment_type` array (permanent/contract/temp) |

### 2.2 Adzuna API

| Field | Value |
|---|---|
| Base URL | `https://api.adzuna.com/v1/api/jobs/gb/search/{page}` |
| Auth | Query params: `app_id` + `app_key` |
| Rate limit | Free tier: ~250–500 calls/day. 1-second sleep between requests. |
| Pagination | `results_per_page` (max 50). Page number in URL path, starting at 1. |
| Fetch frequency | Every 60 minutes |
| Coverage strategy | Category + date sweep: fetch categories endpoint, then sweep each with `max_days_old=1`, `sort_by=date` |

**Key response fields:**

| Field | Type | Maps to |
|---|---|---|
| `id` | string | `external_id` |
| `title` | string | `title` |
| `description` | string (plain text) | `description` / `description_plain` |
| `redirect_url` | string | `source_url` |
| `created` | ISO date | `date_posted` |
| `location.display_name` | string | `location_raw` |
| `location.area` | array | location hierarchy: `['UK','London','Central London','The City']` |
| `latitude` / `longitude` | float | **Direct coordinates — skip postcodes.io for Adzuna jobs** |
| `salary_min` / `salary_max` | number or null | `salary_min` / `salary_max` (annual GBP) |
| `salary_is_predicted` | 0 or 1 | `salary_is_predicted` (1 = Adzuna's ML estimate, not employer-stated) |
| `category.tag` | string | `category_raw` → map to internal category |
| `company.display_name` | string | `company_name` |
| `contract_type` | string or null | `employment_type` |
| `contract_time` | string or null | `employment_type` |

**No `date_expires` provided.** Use 45-day default from `date_posted`.

### 2.3 Jooble API

| Field | Value |
|---|---|
| Endpoint | `POST https://jooble.org/api/{API_KEY}` |
| Auth | API key embedded in URL path |
| Rate limit | No documented limit. 1-second sleep between requests. |
| Pagination | JSON body: `keywords`, `location`, `page` (1-indexed). ~20 results per page. **No `totalResults` returned** — paginate until results array is empty. |
| Fetch frequency | Every 2 hours |
| Coverage strategy | Keyword sweep across major job categories |

**Critical detail:** Jooble is an aggregator — expect significant overlap with Reed/Adzuna. Run deduplication aggressively via `content_hash`.

### 2.4 Careerjet API v4

| Field | Value |
|---|---|
| Endpoint | `GET https://search.api.careerjet.net/v4/query` |
| Auth | `affid` query parameter (affiliate ID from registration) |
| Rate limit | No documented limit. 1-second sleep between requests. |
| Required params | **`user_ip`** and **`user_agent`** (anti-fraud, new in v4). Pass the Modal worker's IP and a descriptive user-agent string. |
| Pagination | Standard offset/limit parameters |
| Fetch frequency | Every 2 hours (offset 30min from Jooble) |

**Critical detail:** The official Python library only supports Python 2. Use `httpx` to call the REST API directly. v4 returns structured salary fields: `salary_currency_code`, `salary_min`, `salary_max`, `salary_type`.

### 2.5 Fetch Schedule Summary

| Source | Frequency | Strategy | Results/page | Sleep between |
|---|---|---|---|---|
| Reed | Every 30 min | Category sweep, `postedWithin=1` | 100 | 0.5s |
| Adzuna | Every 60 min | Category + date sweep, `max_days_old=1` | 50 | 1.0s |
| Jooble | Every 2 hours | Keyword sweep | ~20 | 1.0s |
| Careerjet | Every 2 hours (offset 30min) | Keyword + location sweep | varies | 1.0s |

### 2.6 Circuit Breaker

All collectors share a circuit breaker pattern:

| State | Behaviour |
|---|---|
| **CLOSED** (normal) | Execute requests. Count consecutive failures. |
| **OPEN** (tripped) | Skip all requests. After `recovery_timeout` (300s), move to HALF_OPEN. |
| **HALF_OPEN** (testing) | Allow one request. If success → CLOSED. If fail → OPEN. |

**Threshold:** 3 consecutive failures trip the breaker. Failures include: `httpx.TimeoutError`, `httpx.HTTPStatusError` (5xx), connection errors. 429 responses do NOT trip the breaker — they trigger `Retry-After` backoff instead.

### 2.7 Rate Limit Handler

```python
async def fetch_with_retry(client, url, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))
                await asyncio.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutError:
            await asyncio.sleep(2 ** attempt)
    raise MaxRetriesExceeded(url)
```

---

## 3. Processing Rules

### 3.1 State Machine

```
raw → parsed → normalized → [dedup gate] → geocoded → embedded → ready
                                                                    ↓
ready → expired → archived → deleted (hard delete after 180 days)
```

**Note on dedup:** Deduplication is a gate, not a transformation. Jobs pass through to `geocode_queue` if unique, or get silently skipped if duplicate (DuplicateError). No separate "deduplicated" status in the jobs table — the status stays "normalized" until geocoding completes.

### 3.2 Queue Flow

| Queue | Reads status | Sets status on success | Next queue |
|---|---|---|---|
| `parse_queue` | `raw` | `parsed` | `normalize_queue` |
| `normalize_queue` | `parsed` | `normalized` | `dedup_queue` |
| `dedup_queue` | `normalized` | (unchanged — gate only) | `geocode_queue` |
| `geocode_queue` | `normalized` | `geocoded` | `embed_queue` |
| `embed_queue` | `geocoded` | `embedded` → `ready` | (done) |
| `dead_letter_queue` | any failed | (unchanged) | auto-retry after 6 hours |

**DLQ handling:** Auto-retry after 6 hours. Route back to the original queue based on `msg->>'failed_stage'`. Max 5 retries total. If >5% of a source's jobs enter DLQ, investigate source quality.

```sql
-- Auto-retry DLQ jobs older than 6 hours
WITH retry AS (
    SELECT * FROM pgmq.read('dead_letter_queue', 300, 50)
    WHERE enqueued_at < NOW() - INTERVAL '6 hours'
)
SELECT pgmq.send(
    CASE
        WHEN msg->>'failed_stage' = 'geocode' THEN 'geocode_queue'
        WHEN msg->>'failed_stage' = 'embed'   THEN 'embed_queue'
        ELSE 'parse_queue'
    END,
    msg || jsonb_build_object('retry_count', (msg->>'retry_count')::int + 1)
)
FROM retry
WHERE (msg->>'retry_count')::int < 5;
```

### 3.3 Salary Normalization

**Constants (Doc 9 — resolved, UK financial convention):**

```python
UK_WORKING_DAYS_PER_YEAR  = 252    # 260 weekdays - 8 UK bank holidays
UK_WORKING_HOURS_PER_YEAR = 1950   # 37.5 hours/week × 52 weeks
UK_MONTHS_PER_YEAR        = 12
```

**12 salary patterns:**

| # | Input pattern | Regex / detection | Normalization |
|---|---|---|---|
| 1 | £25,000 – £30,000 | `\d{1,3}(?:,\d{3})+` | Direct: min=25000, max=30000 |
| 2 | £25k – £30k | `\d+k` | Multiply by 1000 |
| 3 | £250–£350 per day | `per day\|daily\|day rate` | × 252 |
| 4 | £15–£20 per hour | `per hour\|hourly\|p/h` | × 1950 |
| 5 | £2,000–£3,000 per month | `per month\|monthly\|pcm` | × 12 |
| 6 | £50,000 pro rata | `pro rata` | Store as-is. Flag `salary_raw` |
| 7 | £50,000 OTE | `ote\|on target` | Store as max. Flag OTE in `salary_raw` |
| 8 | Competitive | `competitive\|attractive` | Set both to NULL. `salary_raw='Competitive'` |
| 9 | DOE / Negotiable | `doe\|negotiable\|depending` | NULL. Preserve in `salary_raw` |
| 10 | Up to £40,000 | `up to\|to \d` | min=NULL, max=40000 |
| 11 | From £25,000 | `from \d` | min=25000, max=NULL |
| 12 | £50,000 + benefits | `\d.*benefits` | min=max=50000. Ignore benefits text. |

**Salary parsing priority:**

1. Use structured API fields first (Reed: `minimumSalary`/`maximumSalary`, Adzuna: `salary_min`/`salary_max`)
2. If API fields are null, parse `salary_raw` text using regex patterns above
3. Always store the original text in `salary_raw` for audit/reprocessing
4. Flag Adzuna's `salary_is_predicted=1` with `salary_is_predicted=true`
5. **Sanity check:** reject `salary_annual < 10,000` or `> 500,000` (likely errors)

### 3.4 Location Normalization

| Input | Problem | Resolution |
|---|---|---|
| `'London'` | Too broad | Default to Central London coords. city='London', region='Greater London' |
| `'Central London'` | Not a postcode area | Map to EC/WC coordinates centroid |
| `'City of London'` | Specific area | Map to EC postcode area |
| `'London EC2'` | Partial postcode | postcodes.io outcodes endpoint: `/outcodes/EC2` |
| `'Manchester'` | City OK | Default to city centre coordinates |
| `'Near Birmingham'` | 'Near' prefix | Strip 'near', geocode 'Birmingham', set wider radius |
| `'South East'` | Region only | Set `location_region='South East England'`, no city, no point geometry |
| `'Remote'` | No physical location | Set `location_type='remote'`, no geometry. UK-wide search. |
| `'Hybrid - Leeds'` | Type + location | Extract `location_type='hybrid'`, geocode 'Leeds' |
| `'Various locations'` | Multi-site | Set `location_type='nationwide'`, no geometry |

**Geocoding pipeline (priority order):**

1. **Adzuna:** Use provided `latitude`/`longitude` directly — skip postcodes.io
2. **Extract UK postcode** via regex `[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}` → postcodes.io lookup
3. **City/town lookup** via postcodes.io places endpoint: `GET /places?q={city}`
4. **Fallback:** Pre-populated table of ~100 UK cities with coordinates
5. **No geocoding possible:** Set `location_type` from keywords, leave geometry NULL

**Postcodes.io usage:** Bulk endpoint `POST /postcodes` accepts up to 100 postcodes per request. 200ms delay between batches. No auth required. Max 3 retries with exponential backoff.

### 3.5 Category Mapping

**Reed → Internal (authoritative, Doc 5):**

| AtoZ Internal | Reed Sector | Adzuna Tag |
|---|---|---|
| Technology | IT & Telecoms | `it-jobs` |
| Finance | Accountancy, Banking & Finance | `accounting-finance-jobs` |
| Healthcare | Health & Medicine | `healthcare-nursing-jobs` |
| Engineering | Engineering | `engineering-jobs` |
| Education | Education | `teaching-jobs` |
| Sales & Marketing | Sales + Marketing & PR | `sales-jobs`, `pr-advertising-marketing-jobs` |
| Legal | Legal | `legal-jobs` |
| Construction | Construction & Property | `construction-jobs` |
| Creative & Media | Creative & Design + Media | `creative-design-jobs` |
| Hospitality | Catering & Hospitality | `hospitality-catering-jobs` |
| Other | Anything unmapped | Anything unmapped |

**Jooble/Careerjet — title keyword inference (Doc 9):**

| Category | Keywords (case-insensitive, word boundary) |
|---|---|
| Technology | software, developer, devops, data scientist, sre, frontend, backend, fullstack, cloud, cyber, sysadmin, QA, tester, IT support |
| Finance | accountant, finance, auditor, tax, payroll, bookkeeper, actuary, FCA, ACCA, CIMA, treasury |
| Healthcare | nurse, doctor, GP, pharmacist, midwife, carer, clinical, NHS, paramedic, dentist, optometrist |
| Engineering | mechanical, electrical, civil, structural, chemical engineer, CAD, BIM, surveyor, quantity surveyor |
| Education | teacher, lecturer, tutor, teaching assistant, SENCO, headteacher, professor, trainer |
| Sales & Marketing | sales, marketing, SEO, PPC, campaign, brand, account manager, business development, BDM, copywriter |
| Legal | solicitor, barrister, paralegal, legal, conveyancer, regulatory |
| Construction | construction, plumber, electrician, carpenter, bricklayer, site manager, foreman, CSCS, scaffolder |
| Creative & Media | designer, graphic, UX, UI, photographer, videographer, animator, journalist, editor, producer |
| Hospitality | chef, cook, waiter, bartender, hotel, catering, kitchen, front of house, restaurant |
| Other | Default fallback |

**Priority order:** (1) Reed/Adzuna: use exhaustive source→internal mapping. (2) Jooble/Careerjet: attempt source category match first, fall back to title keyword inference. (3) All sources: preserve original category in `raw_data` JSONB.

### 3.6 Seniority Extraction

Regex patterns against job title:

| Pattern | Seniority level |
|---|---|
| `junior\|entry\|graduate\|intern\|trainee` | Junior |
| `mid\|intermediate` | Mid |
| `senior\|sr\.` | Senior |
| `lead\|principal\|staff` | Lead |
| `head\|director\|vp\|chief\|cto\|cfo` | Executive |
| (no match) | `'Not specified'` — never guess |

**Experience years extraction:** `(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)`

### 3.7 Structured Summary Template

**6 fields. All rule-based. $0/job. Doc 8 + Doc 11 authority.**

```
Title: {title}
Seniority: {seniority_level or 'Not specified'}
Company: {company_name} ({industry or 'Unknown'})
Skills: {keyword-matched skills, max 15}
Work Type: {employment_type} | {location_type}
Location: {location_city}, {location_region}
```

**Field extraction rules:**

- **title:** Use exactly as provided by the API. Do NOT normalize — 'Senior Software Engineer' and 'Lead Developer' carry different semantic signals.
- **seniority_level:** Regex patterns from §3.6. Default 'Not specified'.
- **company + industry:** Industry from Adzuna's category field or the internal category mapping. Include both because 'Python Developer at Goldman Sachs (Financial Services)' embeds differently from 'Python Developer at Spotify (Music Technology)'.
- **skills:** Regex/set matching from ESCO dictionary (§3.8). Max 15, ordered by frequency of mention. Confidence = 1.0 for exact matches.
- **employment_type + location_type:** Combined as 'Full-time, Permanent | Hybrid' or 'Contract | Remote'.
- **location:** City + region format: 'Manchester, North West'. Remote: 'Remote, UK-wide'. Nationwide: 'Multiple locations, UK'.

**What is NOT in the template:** Summary sentences (removed — saves $50/mo LLM cost), Requirements field (removed), salary, exact postcode, contract end date. These are SQL filter material, not semantic embedding material.

### 3.8 Skill Extraction

**Method:** Pure Python regex + ESCO dictionary. No SpaCy. No LLM. (Doc 11 authority)

**Dictionary build process (~4 hours):**

1. Download ESCO v1.2.1 CSV: `skills_en.csv` (~13,939 rows) from `esco.ec.europa.eu/en/use-esco/download`
2. Parse `preferredLabel` and `altLabels` into `dict[str, str]` (lowercase key → canonical name)
3. Add ~300 UK-specific entries: GCSE, A-Level, BTEC, NVQ, CSCS, SMSTS, SIA licence, ACCA, CIMA, AAT, CIPD, DBS check, NMC registered, Full UK driving licence, etc.
4. Merge with SkillNER's embedded EMSI/Lightcast database (~25K–32K skills, MIT-licensed)
5. Deduplicate by lowercase key. Output: `pipeline/src/skills/dictionary.py` containing `SKILLS_DICT: dict[str, str]` (~10K–15K canonical skills, ~25K–35K matching patterns)

**Runtime matching:** Tokenize `description_plain`, match against dictionary with case-insensitive lookup, order by frequency of mention, cap at 15 skills per job. Store in `job_skills` junction table with `confidence = 1.0` for exact matches.

**Expected accuracy:** ~70–80%. Phase 2 upgrade path: feed Phase 1 results into SpaCy PhraseMatcher or custom NER model.

---

## 4. Embedding Pipeline

### 4.1 Model: Gemini embedding-001

| Parameter | Value |
|---|---|
| Model | `gemini-embedding-001` |
| Dimensions | 768 (native MRL support via `output_dimensionality`) |
| Batch size | 100 per request (API allows 250; use 100 for reliability) |
| Cost | $0 on free tier. $0.15/1M tokens on paid. |
| MTEB retrieval score | ~67.7 (6+ points above OpenAI 3-small at ~52) |
| Auth | `GOOGLE_API_KEY` environment variable (auto-detected by SDK) |
| SDK | `google-genai>=1.0` |
| Re-normalization | Required after MRL dimension truncation. `vec / np.linalg.norm(vec)` |

### 4.2 Production Code (Doc 11)

```python
# pipeline/src/embeddings/embed.py
import asyncio
import numpy as np
import structlog
from google import genai
from google.genai import types

logger = structlog.get_logger()

GEMINI_MODEL = "gemini-embedding-001"
GEMINI_BATCH_SIZE = 100
GEMINI_DIMS = 768
MAX_RETRIES = 5

_client = genai.Client()

async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed up to GEMINI_BATCH_SIZE texts. Returns normalized 768-dim vectors."""
    for attempt in range(MAX_RETRIES):
        try:
            result = _client.models.embed_content(
                model=GEMINI_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=GEMINI_DIMS
                ),
            )
            vectors = []
            for emb in result.embeddings:
                vec = np.array(emb.values, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm  # Re-normalize after MRL truncation
                vectors.append(vec.tolist())
            return vectors
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = min(2 ** attempt * 2, 60)
                logger.warning("gemini_rate_limited", attempt=attempt, wait=wait)
                await asyncio.sleep(wait)
                continue
            logger.error("gemini_embed_error", error=error_str, attempt=attempt)
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries")

async def embed_all(texts: list[str]) -> list[list[float]]:
    """Embed any number of texts in batches with rate limiting."""
    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), GEMINI_BATCH_SIZE):
        batch = texts[i:i + GEMINI_BATCH_SIZE]
        vectors = await embed_batch(batch)
        all_vectors.extend(vectors)
        if i + GEMINI_BATCH_SIZE < len(texts):
            await asyncio.sleep(0.5)  # Rate limit on free tier
    return all_vectors
```

### 4.3 Fallback: OpenAI text-embedding-3-small

Activate only if Gemini returns >10% error rate over a 1-hour window. Lazy-initialize the OpenAI client. OpenAI's $5 free credits cover ~500M tokens = 3.3M job embeddings.

### 4.4 Backfill Strategy

- **Batch API** for initial 500K backfill: upload JSONL, Google processes within 24 hours, $0 on free tier.
- **Real-time API** for daily 2K–5K new jobs: ~750K tokens/day at 250K TPM completes in ~3 minutes.

---

## 5. search_jobs() Function

```sql
CREATE OR REPLACE FUNCTION search_jobs(
    query_text       TEXT DEFAULT NULL,
    query_embedding  HALFVEC(768) DEFAULT NULL,
    search_lat       FLOAT DEFAULT NULL,
    search_lng       FLOAT DEFAULT NULL,
    radius_miles     FLOAT DEFAULT 25,
    include_remote   BOOLEAN DEFAULT TRUE,
    min_salary       INT DEFAULT NULL,
    work_type_filter TEXT DEFAULT NULL,
    match_count      INT DEFAULT 20,
    rrf_k            INT DEFAULT 50
)
RETURNS TABLE (id BIGINT, title TEXT, company TEXT, rrf_score FLOAT)
LANGUAGE sql AS $$
-- NOTE: Using <=> (cosine distance) with halfvec_cosine_ops index.
-- Mathematically equivalent to <#> (inner product) for normalized vectors.
-- All embeddings are re-normalized after Matryoshka dimension reduction.
WITH filtered AS (
    SELECT j.id FROM jobs j
    WHERE j.status = 'ready'
      AND (include_remote AND j.location_type IN ('remote','nationwide')
        OR j.location_type IN ('onsite','hybrid')
          AND (search_lat IS NULL OR ST_DWithin(j.location,
            ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
            radius_miles * 1609.344)))
      AND (min_salary IS NULL OR j.salary_annual_max >= min_salary)
      AND (work_type_filter IS NULL OR work_type_filter = ANY(j.employment_type))
),
fts AS (
    SELECT f.id, ROW_NUMBER() OVER(
        ORDER BY ts_rank_cd(j.search_vector, websearch_to_tsquery(query_text)) DESC
    ) AS rank FROM filtered f JOIN jobs j ON j.id = f.id
    WHERE query_text IS NOT NULL
      AND j.search_vector @@ websearch_to_tsquery(query_text)
    LIMIT match_count * 2
),
semantic AS (
    SELECT f.id, ROW_NUMBER() OVER(
        ORDER BY j.embedding <=> query_embedding
    ) AS rank FROM filtered f JOIN jobs j ON j.id = f.id
    WHERE query_embedding IS NOT NULL AND j.embedding IS NOT NULL
    LIMIT match_count * 2
)
SELECT j.id, j.title, j.company_name,
    COALESCE(1.0/(rrf_k + fts.rank), 0)
  + COALESCE(1.0/(rrf_k + semantic.rank), 0) AS rrf_score
FROM fts FULL OUTER JOIN semantic ON fts.id = semantic.id
JOIN jobs j ON j.id = COALESCE(fts.id, semantic.id)
ORDER BY rrf_score DESC LIMIT match_count;
$$;
```

**Design rationale:** Pre-filter CTE eliminates geographically distant jobs via GIST index before the expensive vector/FTS stages. RRF with k=50 combines both rankings without tuning weights. When only `query_text` or only `query_embedding` is provided, the missing CTE returns empty and RRF degrades gracefully to single-signal ranking.

---

## 6. Expiry Rules

| Source | Expiry detection | Default if no signal |
|---|---|---|
| Reed | `expirationDate` field provided directly | 30 days from `date_posted` |
| Adzuna | No expiry field | 45 days from `date_posted` |
| Jooble | No expiry field | 30 days from `date_posted` |
| Careerjet | No expiry field | 30 days from `date_posted` |

**Re-crawl detection:** When `external_id` reappears with different `content_hash`, update fields and re-process from `parsed`. When `external_id` disappears for 2 consecutive fetch cycles, mark expired (handles API pagination inconsistency).

**State transitions:** `ready → expired` (when `date_expires` passes OR re-verification finds job removed) → `archived` (after 90 days) → hard delete with CASCADE (after 180 days). Keep embeddings for 90 days after expiry for analytics.

---

## 7. Cost Calculations

### 7.1 Monthly Budget (Doc 11 — canonical)

| Item | Provider | Cost | Notes |
|---|---|---|---|
| Database + vectors | Supabase Pro + Small | **$30.00** | $25 base + $15 compute - $10 credit = $30 (2GB RAM) |
| Pipeline compute | Modal Starter | **$0.00** | ~$4.50 usage against $30 free credit |
| Embeddings | Gemini free tier | **$0.00** | ~30M tokens/mo within free limits |
| Frontend hosting | Cloudflare Pages free | **$0.00** | Unlimited bandwidth, commercial OK |
| Error tracking | Sentry Developer | **$0.00** | 5K errors/mo |
| Analytics | PostHog free | **$0.00** | 1M events/mo |
| Uptime monitoring | Better Stack free | **$0.00** | 10 monitors, 3-min checks |
| Geocoding | Postcodes.io | **$0.00** | Free, no auth |
| Domain name | Registrar | **~$1.00** | ~$12/year amortized |
| **TOTAL** | | **~$31/mo** | |

### 7.2 Storage Projections

| Component | Per job | At 200K ready | At 500K total |
|---|---|---|---|
| Core row data | ~3–5 KB | 0.6–1.0 GB | 1.5–2.5 GB |
| raw_data JSONB | ~1–2 KB | 0.2–0.4 GB | 0.5–1.0 GB |
| Embedding halfvec(768) | 1.5 KB | 0.3 GB | 0.75 GB |
| HNSW index (~2× vectors) | ~3 KB | 0.6 GB | 1.5 GB |
| tsvector + GIN index | ~0.5 KB | 0.1 GB | 0.25 GB |
| Other indexes | ~0.5 KB | 0.1 GB | 0.25 GB |
| **TOTAL** | ~10–14 KB | **~2–3 GB** | **~5–7 GB** |

Supabase Pro includes 8 GB. At 200K active + 100K expired = ~4–5 GB. Fits comfortably.

### 7.3 Upgrade Triggers

| Trigger | Action | Cost impact |
|---|---|---|
| Vectors exceed 300K or RAM > 1.8GB | Small → Medium | +$45/mo ($75 total) |
| Gemini 429s block daily processing | Free → Paid ($0.15/1M) | +$4.50/mo |
| CF Pages bundle > 3MB | Free → Workers Paid | +$5/mo |
| Revenue justifies Vercel DX | CF Pages → Vercel Pro | +$20/mo |

---

## 8. Acceptance Criteria

### Stage 1: Foundation (Week 1)

- [ ] `supabase db reset` succeeds with all 5 migrations
- [ ] All 5 tables exist with correct columns, types, and constraints
- [ ] All indexes created (HNSW, GIN×2, GIST, B-tree×5)
- [ ] All 6 queues operational: `SELECT pgmq.send('parse_queue', '{}')` returns a message ID
- [ ] `pipeline_health` view returns 14 columns with zero values
- [ ] RLS: anon key SELECT on `status='ready'` works; SELECT on `status='raw'` returns 0 rows
- [ ] Seed data: 4 sources inserted
- [ ] Rollback: each `down.sql` runs without error

### Stage 2: Collection (Week 2)

- [ ] Each collector maps source JSON to `JobBase` Pydantic model without validation errors
- [ ] Reed: fetches ≥1 page, respects 0.5s sleep, handles `totalResults` pagination
- [ ] Adzuna: fetches ≥1 category page, extracts `latitude`/`longitude`
- [ ] Jooble: paginates until empty results array
- [ ] Careerjet: passes `user_ip` and `user_agent` in v4 format
- [ ] Circuit breaker: 3 consecutive 500s → state=OPEN → 5min recovery → HALF_OPEN → success → CLOSED
- [ ] UPSERT: re-inserting same `(source_id, external_id)` updates `date_crawled`, does not create duplicate
- [ ] `content_hash` computed at ingestion; identical jobs have identical hashes
- [ ] `pipeline_health.jobs_ingested_last_hour > 0` after first run

### Stage 3: Processing (Week 3)

- [ ] Salary normalizer: all 12 patterns produce correct `salary_annual_min`/`salary_annual_max`
- [ ] Salary sanity: values <10K or >500K are rejected (set to NULL)
- [ ] Location normalizer: 'London' → Central London coords; 'Remote' → `location_type='remote'`, no geometry
- [ ] Geocoding: Adzuna jobs use provided lat/lon; Reed jobs use postcodes.io
- [ ] Category mapper: Reed IT → Technology; Adzuna `it-jobs` → Technology; unknown title → 'Other'
- [ ] Seniority: 'Senior Python Developer' → 'Senior'; 'Data Analyst' → 'Not specified'
- [ ] Structured summary: 6-field template generated for every job
- [ ] Embeddings: Gemini returns 768-dim vectors; stored as `halfvec(768)` in DB
- [ ] Re-normalization: `np.linalg.norm(vec) ≈ 1.0` for all stored vectors
- [ ] Dedup: two jobs with same title+company+location produce same `content_hash`; second is skipped
- [ ] Skill extraction: 'Python developer with AWS experience' extracts at least ['Python', 'AWS']
- [ ] Full pipeline: raw job → ready job with all fields populated
- [ ] `pipeline_health.ready_without_embedding = 0`

### Stage 4: Maintenance (Week 4)

- [ ] Expired Reed jobs (past `expirationDate`) have `status='expired'`
- [ ] Jobs older than 45 days without explicit expiry are auto-expired
- [ ] Archived jobs (expired >90 days) have `status='archived'`
- [ ] `search_jobs()` returns results for keyword-only, semantic-only, and hybrid queries
- [ ] `search_jobs()` respects all filters: location radius, min_salary, work_type, include_remote
- [ ] `EXPLAIN ANALYZE` on `search_jobs()` shows P95 < 50ms on seeded data
- [ ] Pipeline throughput: >500 jobs/hour through full processing chain
- [ ] End-to-end: fetch 100 real jobs → process → embed → search returns sensible results
