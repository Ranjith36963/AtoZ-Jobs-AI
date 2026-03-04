# AtoZ Jobs AI — Phase 2 Specification

**What we build and why. Every line implementation-ready.**

Version: 1.0 · March 2026 · Authority: Doc 11 (Conflict Resolution) supersedes all prior docs.

Phase 2 monthly budget delta: **~$0/month** above Phase 1's $31 baseline (total ~$31/month). All Phase 2 processing is rule-based or uses free APIs.

Phase 1 delivered: jobs table (40+ columns, halfvec(768) embeddings, tsvector), skills + job_skills tables (empty, ready to populate), search_jobs() with RRF, pipeline on Modal, Supabase Pro with RLS, 4 API collectors, ~$31/month.

---

## 1. Phase 2 Overview

4 stages, 4 weeks (Weeks 5–8), building the intelligence layer on Phase 1's data pipeline.

| Stage | Week | What | Key deliverable |
|---|---|---|---|
| 1: Skills Extraction & Taxonomy | 5 | Populate skills + job_skills tables | SpaCy PhraseMatcher with ESCO + UK-specific entries |
| 2: Advanced Deduplication | 6 | Fuzzy + composite dedup | pg_trgm fuzzy matching + MinHash/LSH preparation |
| 3: Salary Prediction & Company Enrichment | 7 | Fill missing salaries, enrich companies | XGBoost model + Companies House integration |
| 4: Cross-Encoder Re-ranking | 8 | Relevance improvement | ms-marco-MiniLM-L-6-v2 + user profiles |

---

## 2. Database Migrations

### 2.1 Migration 007: Skills Taxonomy Tables (Stage 1)

```sql
-- Populate the skills table with ESCO taxonomy data
-- skills table already exists from Phase 1 Migration 002
-- This migration adds the ESCO taxonomy reference table and indexes

CREATE TABLE esco_skills (
    concept_uri     TEXT PRIMARY KEY,
    preferred_label TEXT NOT NULL,
    alt_labels      TEXT[],
    skill_type      TEXT,           -- 'skill/competence', 'knowledge'
    description     TEXT,
    isco_group      TEXT            -- ISCO-08 group code for occupation mapping
);

-- Index for text search on skill names (autocomplete + fuzzy match)
CREATE INDEX idx_esco_skills_label_trgm ON esco_skills USING gin(preferred_label gin_trgm_ops);

-- Add esco_uri column mapping to skills table (already has esco_uri from Phase 1)
-- Add additional columns for Phase 2 enrichment
ALTER TABLE skills ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'esco';
ALTER TABLE skills ADD COLUMN IF NOT EXISTS aliases TEXT[];

-- Materialized view: top skills by demand
CREATE MATERIALIZED VIEW mv_skill_demand AS
SELECT
    s.id,
    s.name,
    s.skill_type,
    s.esco_uri,
    COUNT(js.job_id) AS job_count,
    COUNT(js.job_id) FILTER (WHERE j.date_posted > NOW() - INTERVAL '30 days') AS jobs_last_30d,
    COUNT(js.job_id) FILTER (WHERE j.date_posted > NOW() - INTERVAL '7 days') AS jobs_last_7d,
    ROUND(AVG(j.salary_annual_max) FILTER (WHERE j.salary_annual_max IS NOT NULL), 0) AS avg_salary,
    ARRAY_AGG(DISTINCT j.location_region) FILTER (WHERE j.location_region IS NOT NULL) AS top_regions
FROM skills s
JOIN job_skills js ON js.skill_id = s.id
JOIN jobs j ON j.id = js.job_id AND j.status = 'ready'
GROUP BY s.id, s.name, s.skill_type, s.esco_uri
ORDER BY job_count DESC;

CREATE UNIQUE INDEX idx_mv_skill_demand_id ON mv_skill_demand(id);

-- Materialized view: skill co-occurrence (which skills appear together)
CREATE MATERIALIZED VIEW mv_skill_cooccurrence AS
SELECT
    js1.skill_id AS skill_a,
    js2.skill_id AS skill_b,
    COUNT(*) AS cooccurrence_count
FROM job_skills js1
JOIN job_skills js2 ON js1.job_id = js2.job_id AND js1.skill_id < js2.skill_id
GROUP BY js1.skill_id, js2.skill_id
HAVING COUNT(*) >= 10
ORDER BY cooccurrence_count DESC;

CREATE INDEX idx_mv_skill_cooccurrence_a ON mv_skill_cooccurrence(skill_a);
CREATE INDEX idx_mv_skill_cooccurrence_b ON mv_skill_cooccurrence(skill_b);

-- Schedule materialized view refresh (daily at 3 AM)
SELECT cron.schedule('refresh-skill-demand', '0 3 * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_demand$$);
SELECT cron.schedule('refresh-skill-cooccurrence', '0 3 * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_cooccurrence$$);
```

**Down migration:**

```sql
SELECT cron.unschedule('refresh-skill-demand');
SELECT cron.unschedule('refresh-skill-cooccurrence');
DROP MATERIALIZED VIEW IF EXISTS mv_skill_cooccurrence;
DROP MATERIALIZED VIEW IF EXISTS mv_skill_demand;
ALTER TABLE skills DROP COLUMN IF EXISTS aliases;
ALTER TABLE skills DROP COLUMN IF EXISTS source;
DROP INDEX IF EXISTS idx_esco_skills_label_trgm;
DROP TABLE IF EXISTS esco_skills;
```

### 2.2 Migration 008: Advanced Dedup Infrastructure (Stage 2)

```sql
-- Add fuzzy dedup columns and indexes to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS canonical_id BIGINT REFERENCES jobs(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_score FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description_hash TEXT;  -- MinHash signature stored as hex

-- GIN trigram indexes for fuzzy matching (title already has one from Phase 1)
CREATE INDEX idx_jobs_company_trgm ON jobs USING gin(company_name gin_trgm_ops);

-- B-tree for canonical_id lookups
CREATE INDEX idx_jobs_canonical ON jobs(canonical_id) WHERE canonical_id IS NOT NULL;

-- Partial index: only non-duplicate ready jobs for search
CREATE INDEX idx_jobs_ready_not_dup ON jobs(status, is_duplicate) WHERE status = 'ready' AND is_duplicate = FALSE;

-- Composite dedup scoring function
CREATE OR REPLACE FUNCTION compute_duplicate_score(
    title_sim FLOAT,         -- pg_trgm similarity on title
    company_match BOOLEAN,   -- exact or fuzzy company match
    location_km FLOAT,       -- distance between locations in km
    salary_overlap FLOAT,    -- 0-1 overlap ratio
    date_diff_days INT       -- days between posting dates
) RETURNS FLOAT
LANGUAGE sql IMMUTABLE AS $$
SELECT
    (title_sim * 0.35) +
    (CASE WHEN company_match THEN 0.25 ELSE 0.0 END) +
    (CASE WHEN location_km <= 5 THEN 0.15 WHEN location_km <= 25 THEN 0.08 ELSE 0.0 END) +
    (salary_overlap * 0.15) +
    (CASE WHEN date_diff_days <= 7 THEN 0.10 WHEN date_diff_days <= 14 THEN 0.05 ELSE 0.0 END);
$$;
```

**Down migration:**

```sql
DROP FUNCTION IF EXISTS compute_duplicate_score;
DROP INDEX IF EXISTS idx_jobs_ready_not_dup;
DROP INDEX IF EXISTS idx_jobs_canonical;
DROP INDEX IF EXISTS idx_jobs_company_trgm;
ALTER TABLE jobs DROP COLUMN IF EXISTS description_hash;
ALTER TABLE jobs DROP COLUMN IF EXISTS duplicate_score;
ALTER TABLE jobs DROP COLUMN IF EXISTS is_duplicate;
ALTER TABLE jobs DROP COLUMN IF EXISTS canonical_id;
```

### 2.3 Migration 009: Salary Prediction & Company Enrichment (Stage 3)

```sql
-- Salary prediction columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_predicted_min NUMERIC(12,2);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_predicted_max NUMERIC(12,2);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_confidence FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_model_version TEXT;

-- Company enrichment columns
ALTER TABLE companies ADD COLUMN IF NOT EXISTS companies_house_number TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS sic_codes TEXT[];
ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_status TEXT;     -- 'active','dissolved', etc.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS date_of_creation DATE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS registered_address JSONB;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

CREATE INDEX idx_companies_house_number ON companies(companies_house_number)
    WHERE companies_house_number IS NOT NULL;

-- SIC code to industry category mapping table
CREATE TABLE sic_industry_map (
    sic_section  CHAR(1) PRIMARY KEY,  -- A-U
    sic_label    TEXT NOT NULL,
    internal_category TEXT NOT NULL     -- maps to our category taxonomy
);

-- Seed SIC sections → internal categories
INSERT INTO sic_industry_map (sic_section, sic_label, internal_category) VALUES
    ('A', 'Agriculture, Forestry and Fishing', 'Agriculture'),
    ('B', 'Mining and Quarrying', 'Energy & Utilities'),
    ('C', 'Manufacturing', 'Manufacturing'),
    ('D', 'Electricity, Gas, Steam', 'Energy & Utilities'),
    ('E', 'Water Supply, Sewerage', 'Energy & Utilities'),
    ('F', 'Construction', 'Construction'),
    ('G', 'Wholesale and Retail Trade', 'Retail'),
    ('H', 'Transportation and Storage', 'Logistics & Transport'),
    ('I', 'Accommodation and Food Service', 'Hospitality'),
    ('J', 'Information and Communication', 'Technology'),
    ('K', 'Financial and Insurance', 'Finance'),
    ('L', 'Real Estate Activities', 'Property'),
    ('M', 'Professional, Scientific and Technical', 'Professional Services'),
    ('N', 'Administrative and Support Service', 'Administration'),
    ('O', 'Public Administration and Defence', 'Public Sector'),
    ('P', 'Education', 'Education'),
    ('Q', 'Human Health and Social Work', 'Healthcare'),
    ('R', 'Arts, Entertainment and Recreation', 'Creative & Media'),
    ('S', 'Other Service Activities', 'Other'),
    ('T', 'Households as Employers', 'Other'),
    ('U', 'Extraterritorial Organisations', 'Other');
```

**Down migration:**

```sql
DROP TABLE IF EXISTS sic_industry_map;
DROP INDEX IF EXISTS idx_companies_house_number;
ALTER TABLE companies DROP COLUMN IF EXISTS enriched_at;
ALTER TABLE companies DROP COLUMN IF EXISTS registered_address;
ALTER TABLE companies DROP COLUMN IF EXISTS date_of_creation;
ALTER TABLE companies DROP COLUMN IF EXISTS company_status;
ALTER TABLE companies DROP COLUMN IF EXISTS sic_codes;
ALTER TABLE companies DROP COLUMN IF EXISTS companies_house_number;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_model_version;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_confidence;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_predicted_max;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_predicted_min;
```

### 2.4 Migration 010: User Profiles & Re-ranking Support (Stage 4)

```sql
-- User profiles table (for authenticated job seekers)
CREATE TABLE user_profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    target_role     TEXT,
    skills          TEXT[],
    experience_text TEXT,
    preferred_location TEXT,
    preferred_lat   FLOAT,
    preferred_lng   FLOAT,
    work_preference TEXT,           -- 'remote','hybrid','onsite','any'
    min_salary      INT,
    profile_embedding HALFVEC(768),
    profile_text    TEXT,           -- the structured template used for embedding
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- RLS for user profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR ALL
    USING (auth.uid() = id);

CREATE POLICY "Service role full access to profiles"
    ON user_profiles FOR ALL
    USING (auth.role() = 'service_role');

-- Updated search function with re-ranking support
-- Returns expanded fields needed by cross-encoder
CREATE OR REPLACE FUNCTION search_jobs_v2(
    query_text       TEXT DEFAULT NULL,
    query_embedding  HALFVEC(768) DEFAULT NULL,
    search_lat       FLOAT DEFAULT NULL,
    search_lng       FLOAT DEFAULT NULL,
    radius_miles     FLOAT DEFAULT 25,
    include_remote   BOOLEAN DEFAULT TRUE,
    min_salary       INT DEFAULT NULL,
    max_salary       INT DEFAULT NULL,
    work_type_filter TEXT DEFAULT NULL,
    category_filter  TEXT DEFAULT NULL,
    skill_filters    TEXT[] DEFAULT NULL,
    exclude_duplicates BOOLEAN DEFAULT TRUE,
    match_count      INT DEFAULT 50,
    rrf_k            INT DEFAULT 50
)
RETURNS TABLE (
    id BIGINT,
    title TEXT,
    company_name TEXT,
    description_plain TEXT,
    location_city TEXT,
    location_region TEXT,
    location_type TEXT,
    salary_annual_min NUMERIC,
    salary_annual_max NUMERIC,
    salary_predicted_min NUMERIC,
    salary_predicted_max NUMERIC,
    salary_is_predicted BOOLEAN,
    employment_type TEXT[],
    seniority_level TEXT,
    category TEXT,
    date_posted TIMESTAMPTZ,
    source_url TEXT,
    rrf_score FLOAT
)
LANGUAGE sql AS $$
WITH filtered AS (
    SELECT j.id FROM jobs j
    WHERE j.status = 'ready'
      AND (NOT exclude_duplicates OR j.is_duplicate IS NOT TRUE)
      AND (include_remote AND j.location_type IN ('remote','nationwide')
        OR j.location_type IN ('onsite','hybrid')
          AND (search_lat IS NULL OR ST_DWithin(j.location,
            ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
            radius_miles * 1609.344)))
      AND (min_salary IS NULL OR COALESCE(j.salary_annual_max, j.salary_predicted_max) >= min_salary)
      AND (max_salary IS NULL OR COALESCE(j.salary_annual_min, j.salary_predicted_min) <= max_salary)
      AND (work_type_filter IS NULL OR work_type_filter = ANY(j.employment_type))
      AND (category_filter IS NULL OR j.category = category_filter)
      AND (skill_filters IS NULL OR EXISTS (
          SELECT 1 FROM job_skills js
          JOIN skills s ON s.id = js.skill_id
          WHERE js.job_id = j.id AND s.name = ANY(skill_filters)))
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
SELECT
    j.id, j.title, j.company_name, j.description_plain,
    j.location_city, j.location_region, j.location_type,
    j.salary_annual_min, j.salary_annual_max,
    j.salary_predicted_min, j.salary_predicted_max,
    j.salary_is_predicted,
    j.employment_type, j.seniority_level, j.category,
    j.date_posted, j.source_url,
    COALESCE(1.0/(rrf_k + fts.rank), 0)
  + COALESCE(1.0/(rrf_k + semantic.rank), 0) AS rrf_score
FROM fts FULL OUTER JOIN semantic ON fts.id = semantic.id
JOIN jobs j ON j.id = COALESCE(fts.id, semantic.id)
ORDER BY rrf_score DESC LIMIT match_count;
$$;
```

**Down migration:**

```sql
DROP FUNCTION IF EXISTS search_jobs_v2;
DROP POLICY IF EXISTS "Service role full access to profiles" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can read own profile" ON user_profiles;
DROP TABLE IF EXISTS user_profiles;
```

---

## 3. Stage 1: Skills Extraction & Taxonomy (Week 5)

### 3.1 ESCO Dataset Loading

**Source:** `https://esco.ec.europa.eu/en/use-esco/download` → CSV format → Skills pillar → English.

**File:** `skills_en.csv` (~13,939 rows). Columns: `conceptUri`, `skillType`, `preferredLabel`, `altLabels`, `description`.

**Loading strategy:**

```python
# pipeline/src/skills/esco_loader.py
import csv

def load_esco_csv(filepath: str) -> dict[str, dict]:
    """Load ESCO skills CSV into structured dict.
    Returns: {concept_uri: {preferred_label, alt_labels, skill_type, description}}
    """
    skills = {}
    with open(filepath) as f:
        for row in csv.DictReader(f):
            uri = row["conceptUri"].strip()
            preferred = row["preferredLabel"].strip()
            alt_labels = [
                a.strip() for a in row.get("altLabels", "").split("\n")
                if a.strip() and len(a.strip()) > 2
            ]
            skills[uri] = {
                "preferred_label": preferred,
                "alt_labels": alt_labels,
                "skill_type": row.get("skillType", "").strip(),
                "description": row.get("description", "").strip(),
            }
    return skills
```

**Seed the `esco_skills` table:** Bulk insert all 13,939 rows. One-time operation.

**Seed the `skills` table:** Deduplicated canonical skills (~10K–15K) from ESCO + SkillNER + UK-specific entries. Each row gets an `esco_uri` if it came from ESCO.

### 3.2 SpaCy PhraseMatcher (Phase 2 Upgrade from Phase 1 Regex)

**Why upgrade now:** Phase 1 used pure Python regex/set matching (~70–80% accuracy). Phase 2 upgrades to SpaCy PhraseMatcher for ~85–95% precision and ~65–80% recall (F1 ~75–85%). The interface is identical: `extract(text, max_skills) → list[str]`. Zero changes to calling code.

**Architecture: two-layer PhraseMatcher.**

```python
# pipeline/src/skills/spacy_matcher.py
import spacy
from spacy.matcher import PhraseMatcher

class SpaCySkillMatcher:
    """ESCO + UK-specific skill extraction via SpaCy PhraseMatcher.
    Drop-in replacement for Phase 1 SkillMatcher.
    """

    def __init__(self, skills_dict: dict[str, str]):
        """skills_dict: {lowercase_pattern: canonical_name}"""
        self.nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer"])
        self._canonical_map: dict[str, str] = {}

        # Layer 1: case-insensitive general skills
        self._lower_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        # Layer 2: case-sensitive acronyms (AWS, SQL, ACCA, CIPD)
        self._orth_matcher = PhraseMatcher(self.nlp.vocab, attr="ORTH")

        lower_patterns = []
        orth_patterns = []

        for pattern_text, canonical in skills_dict.items():
            self._canonical_map[pattern_text] = canonical
            doc = self.nlp.make_doc(pattern_text)

            if pattern_text.isupper() and len(pattern_text) <= 6:
                orth_patterns.append(doc)
            else:
                lower_patterns.append(doc)

        if lower_patterns:
            self._lower_matcher.add("SKILLS_LOWER", lower_patterns)
        if orth_patterns:
            self._orth_matcher.add("SKILLS_ORTH", orth_patterns)

    def extract(self, text: str, max_skills: int = 15) -> list[str]:
        """Extract skills from text. Returns canonical names, deduped, max 15."""
        doc = self.nlp(text)
        found: dict[str, int] = {}

        for matcher in [self._orth_matcher, self._lower_matcher]:
            for match_id, start, end in matcher(doc):
                span_text = doc[start:end].text.lower()
                if span_text in self._canonical_map:
                    canonical = self._canonical_map[span_text]
                    found[canonical] = found.get(canonical, 0) + 1

        ranked = sorted(found.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in ranked[:max_skills]]
```

**Performance:** ~5–15ms per document with 40K–60K patterns loaded. 5,000 jobs in under 2 minutes on a single CPU core. Memory: ~300–500MB including `en_core_web_sm`.

**Dictionary composition:**

| Source | Skills | Patterns (with aliases) | Status |
|---|---|---|---|
| ESCO v1.2.1 CSV | ~13,939 | ~25,000–30,000 | Free download |
| SkillNER EMSI/Lightcast bundle | ~25K–32K | ~40,000 | MIT-licensed, extract from library |
| UK-specific entries | ~300 | ~500 | Manual curation |
| **Total (deduplicated)** | **~10K–15K canonical** | **~40K–60K patterns** | |

**UK-specific entries (300+ additions not in ESCO):**

| Category | Entries |
|---|---|
| Education | GCSE, A-Level, BTEC, NVQ Level 1–7, City & Guilds, HNC, HND, QTS, PGCE, Foundation Degree |
| Construction | CSCS card, SMSTS, SSSTS, CPCS, IPAF, PASMA, Gas Safe, Part P, JIB card, ECS card |
| Security | SIA licence, SIA Door Supervision, SIA CCTV, SIA Close Protection, BS 7858 |
| Finance | ACCA, CIMA, AAT, ACA, ICAEW, CFA, CISI, FCA regulated, PRA regulated |
| HR / Management | CIPD Level 3/5/7, PRINCE2, APM, CMI, ILM, NEBOSH, IOSH |
| Safeguarding | DBS check, enhanced DBS, First Aid at Work, safeguarding certificate, food hygiene Level 2/3 |
| Health / Social | NMC registered, HCPC registered, GMC registered, GPhC, SSSC, Care Certificate |
| Driving | Full UK driving licence, Cat C, Cat CE, HGV Class 1/2, ADR, CPC, forklift licence |
| Legal | SRA regulated, CILEx, OISC Level 1–3, SQE1, SQE2, LPC, BPTC |

### 3.3 Job Skills Population

**Backfill strategy:** Process all `status = 'ready'` jobs that have no entries in `job_skills`. Run as a Modal batch job.

```python
# pipeline/src/skills/populate.py
async def populate_job_skills(batch_size: int = 500):
    """Backfill job_skills for all ready jobs missing skill extraction."""
    # 1. Query jobs with no job_skills entries
    # 2. For each batch: extract skills via SpaCySkillMatcher
    # 3. Upsert skill names into skills table (get or create)
    # 4. Bulk insert into job_skills with confidence=1.0, is_required=True
    # 5. Track progress via structlog
```

**Processing rate:** 500K jobs ÷ 10ms/job ÷ 1000 = ~83 minutes on single core. Run on Modal with parallelism for ~20 minutes.

**Skill type classification:** Map ESCO `skillType` field:
- `skill/competence` → `'hard'` if technical pattern matches, else `'soft'`
- `knowledge` → `'knowledge'`
- UK-specific entries → manually classified in dictionary build

### 3.4 Materialized Views

Two views (SQL in Migration 007 above):

**`mv_skill_demand`:** Skill name, job count (total/30d/7d), average salary, top regions. Powers the "trending skills" and "skills analytics" features.

**`mv_skill_cooccurrence`:** Pairs of skills that appear together in ≥10 jobs. Powers "related skills" recommendations.

**Refresh:** Daily at 3 AM via pg_cron. `CONCURRENTLY` to avoid locking reads.

---

## 4. Stage 2: Advanced Deduplication (Week 6)

### 4.1 Three-Stage Dedup Architecture

Phase 1 built Stage 1 (hash-based). Phase 2 adds Stages 2 and 3.

| Stage | Method | What it catches | Performance |
|---|---|---|---|
| 1 (Phase 1) | SHA-256 `content_hash` | Identical title+company+location | O(1) per job via unique constraint |
| 2 (Phase 2) | pg_trgm fuzzy matching | Rephrased titles, company name variations | ~15ms per query with GIN index |
| 3 (Phase 2) | MinHash/LSH | Near-duplicate descriptions at scale | ~30 min for 400K jobs on single core |

**Expected aggregate precision: 85–95%.**

### 4.2 pg_trgm Fuzzy Matching

**Similarity thresholds (tuned for UK job postings):**

| Field | Threshold | Rationale |
|---|---|---|
| Title | 0.6–0.7 | Default 0.3 is far too permissive. 0.6 catches "Senior Python Developer" vs "Senior Python Dev" |
| Company | 0.5–0.6 | Catches "Goldman Sachs International" vs "Goldman Sachs" |
| Description | 0.4–0.5 | Only for confirmation; never as sole signal |

**Query pattern for candidate detection:**

```sql
-- Find fuzzy duplicates for a given job
SELECT
    j2.id AS candidate_id,
    similarity(j1.title, j2.title) AS title_sim,
    similarity(j1.company_name, j2.company_name) AS company_sim,
    ST_Distance(j1.location::geography, j2.location::geography) / 1000.0 AS distance_km,
    compute_duplicate_score(
        similarity(j1.title, j2.title),
        similarity(j1.company_name, j2.company_name) > 0.5,
        ST_Distance(j1.location::geography, j2.location::geography) / 1000.0,
        CASE
            WHEN j1.salary_annual_max IS NOT NULL AND j2.salary_annual_max IS NOT NULL
            THEN 1.0 - ABS(j1.salary_annual_max - j2.salary_annual_max)
                / GREATEST(j1.salary_annual_max, j2.salary_annual_max)
            ELSE 0.0
        END,
        ABS(EXTRACT(EPOCH FROM j1.date_posted - j2.date_posted) / 86400)::INT
    ) AS dup_score
FROM jobs j1, jobs j2
WHERE j1.id = $1
  AND j2.id != j1.id
  AND j2.status = 'ready'
  AND j2.is_duplicate IS NOT TRUE
  AND j1.title % j2.title                          -- GIN index scan, threshold 0.6
  AND similarity(j1.title, j2.title) >= 0.6
ORDER BY dup_score DESC
LIMIT 10;
```

**Set pg_trgm threshold per-session:**

```sql
SET pg_trgm.similarity_threshold = 0.6;
```

### 4.3 Composite Duplicate Scoring

**Formula (from Migration 008 SQL):**

```
score = (title_similarity × 0.35)
      + (company_match × 0.25)
      + (location_proximity × 0.15)
      + (salary_overlap × 0.15)
      + (date_proximity × 0.10)
```

**Decision threshold:** `dup_score >= 0.65` → mark as duplicate.

**Duplicate resolution:** Keep the "richest" version (most non-null fields, longest description, has salary data). Set `canonical_id` on the duplicate pointing to the kept version. Set `is_duplicate = TRUE`.

```python
def pick_canonical(job_a: dict, job_b: dict) -> tuple[int, int]:
    """Returns (canonical_id, duplicate_id). Keeps richest version."""
    def richness(j: dict) -> int:
        score = 0
        score += 1 if j.get("salary_annual_max") else 0
        score += 1 if j.get("location_city") else 0
        score += len(j.get("description_plain", "")) // 100  # longer = richer
        score += 1 if j.get("embedding") is not None else 0
        return score

    if richness(job_a) >= richness(job_b):
        return job_a["id"], job_b["id"]
    return job_b["id"], job_a["id"]
```

### 4.4 MinHash/LSH Preparation

**Library:** `datasketch` with `xxhash` (faster than SHA1).

**Configuration:**

| Parameter | Value | Rationale |
|---|---|---|
| Permutations | 128 | ~0.5KB per signature |
| Bands | 10 | LSH banding |
| Rows per band | 12 | 10 × 12 = 120 (≈ 128 perms) |
| Jaccard threshold | ~0.5 | Catches ~80% of pairs above this similarity |

**Implementation:**

```python
# pipeline/src/dedup/minhash.py
from datasketch import MinHash, MinHashLSH

def compute_minhash(text: str, num_perm: int = 128) -> MinHash:
    """Compute MinHash signature for a job description."""
    m = MinHash(num_perm=num_perm, hashfunc=xxhash.xxh64_intdigest)
    # Tokenize into 3-grams (character level for robustness)
    for i in range(len(text) - 2):
        m.update(text[i:i+3].encode('utf-8'))
    return m

def build_lsh_index(jobs: list[dict], threshold: float = 0.5) -> MinHashLSH:
    """Build LSH index from job descriptions."""
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    for job in jobs:
        mh = compute_minhash(job["description_plain"])
        lsh.insert(str(job["id"]), mh)
    return lsh
```

**Processing time:** 400K jobs in ~30 minutes on single core. Store MinHash hex in `description_hash` column for incremental updates.

**Phase 2 scope:** Build the LSH index and identify candidates. Use composite scoring (§4.3) for final decision. MinHash alone is insufficient — Textkernel research confirmed that text similarity must be combined with metadata matching.

---

## 5. Stage 3: Salary Prediction & Company Enrichment (Week 7)

### 5.1 XGBoost Salary Prediction

**Training data:** Adzuna provides a `salary_is_predicted` flag. Filter to `salary_is_predicted = FALSE` AND `salary_annual_max IS NOT NULL`. Expected: ~100K+ labeled jobs after sufficient collection time.

**Features:**

| Feature | Encoding | Source |
|---|---|---|
| Job title | TF-IDF (max 500 features) | `title` column |
| Location region | One-hot (12 UK regions) | `location_region` column |
| Category | One-hot (~15 categories) | `category` column |
| Employment type | Multi-hot | `employment_type` array |
| Seniority level | Ordinal (1–5) | `seniority_level` column |
| Extracted skills count | Integer | `job_skills` count |
| Top 50 skills | Binary presence | `job_skills` join |

**Model training:**

```python
# pipeline/src/salary/trainer.py
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, median_absolute_error

def train_salary_model(features: np.ndarray, labels: np.ndarray) -> xgb.Booster:
    """Train XGBoost salary predictor. Target: salary_annual_max."""
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    params = {
        "objective": "reg:squarederror",
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "eval_metric": "mae",
    }
    model = xgb.train(
        params, dtrain,
        num_boost_round=200,
        evals=[(dtest, "test")],
        early_stopping_rounds=20,
        verbose_eval=50
    )
    # Validation
    preds = model.predict(dtest)
    mae = mean_absolute_error(y_test, preds)
    median_ae = median_absolute_error(y_test, preds)
    # Log: target MAE < £5,000, median AE < £3,000
    return model
```

**Validation criteria:**

| Metric | Target | Acceptable |
|---|---|---|
| MAE (Mean Absolute Error) | < £5,000 | < £8,000 |
| Median AE | < £3,000 | < £5,000 |
| % within 20% of actual | > 70% | > 60% |

**Prediction output:** Store in `salary_predicted_min`, `salary_predicted_max`, `salary_confidence`, `salary_model_version`. Set `salary_is_predicted = TRUE` for predicted values.

**Confidence score:** Based on distance to nearest training examples and model variance. Buckets: HIGH (>0.8), MEDIUM (0.5–0.8), LOW (<0.5).

**Re-training:** Monthly, triggered by pg_cron. Store model as serialized file on Modal volume.

### 5.2 Companies House API Integration

**Endpoint:** `https://api.company-information.service.gov.uk/`

**Auth:** Basic Auth with API key (free, register at `https://developer.company-information.service.gov.uk/`).

**Rate limit:** 600 requests per 5 minutes = 2 req/sec sustained.

**Search workflow:**

```python
# pipeline/src/enrichment/companies_house.py
import httpx

COMPANIES_HOUSE_BASE = "https://api.company-information.service.gov.uk"

async def search_company(name: str, api_key: str) -> dict | None:
    """Search Companies House by company name. Returns best match."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{COMPANIES_HOUSE_BASE}/search/companies",
            params={"q": name, "items_per_page": 5},
            auth=(api_key, ""),  # Basic Auth: key as username, empty password
            timeout=10.0
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return None
        # Return best match (first result, highest relevance)
        return items[0]

async def get_company_profile(company_number: str, api_key: str) -> dict:
    """Get full company profile by Companies House number."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{COMPANIES_HOUSE_BASE}/company/{company_number}",
            auth=(api_key, ""),
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
```

**Response parsing (key fields):**

| API field | Maps to | Column |
|---|---|---|
| `company_number` | Companies House number | `companies.companies_house_number` |
| `sic_codes[]` | Industry classification | `companies.sic_codes` |
| `company_status` | Active/dissolved/etc | `companies.company_status` |
| `date_of_creation` | Company age | `companies.date_of_creation` |
| `registered_office_address` | Full address object | `companies.registered_address` |

**SIC code → internal category mapping:** First character of 5-digit SIC code maps to section letter (A–U) via ONS standard ranges. Then section letter maps to our internal category via `sic_industry_map` table.

```python
def sic_to_section(sic_code: str) -> str:
    """Map 5-digit SIC code to section letter (A-U)."""
    code = int(sic_code[:2])
    RANGES = [
        (1, 3, 'A'), (5, 9, 'B'), (10, 33, 'C'), (35, 35, 'D'),
        (36, 39, 'E'), (41, 43, 'F'), (45, 47, 'G'), (49, 53, 'H'),
        (55, 56, 'I'), (58, 63, 'J'), (64, 66, 'K'), (68, 68, 'L'),
        (69, 75, 'M'), (77, 82, 'N'), (84, 84, 'O'), (85, 85, 'P'),
        (86, 88, 'Q'), (90, 93, 'R'), (94, 96, 'S'), (97, 98, 'T'),
        (99, 99, 'U'),
    ]
    for start, end, section in RANGES:
        if start <= code <= end:
            return section
    return 'S'  # default: Other Service Activities
```

**Enrichment strategy:** Process unique company names from the `companies` table where `enriched_at IS NULL`. Rate-limited to 2 req/sec. Batch overnight via Modal cron. Expected: ~10K–50K unique companies.

### 5.3 Cost: Stage 3

| Item | Cost | Notes |
|---|---|---|
| XGBoost training | $0 | Runs on Modal free tier (~5 min compute) |
| Companies House API | $0 | Free API, no cost |
| Model storage | $0 | Modal volume (included in free tier) |
| scikit-learn + xgboost deps | $0 | Open source |

---

## 6. Stage 4: Cross-Encoder Re-ranking (Week 8)

### 6.1 Re-ranking Pipeline

```
User query
    ↓
search_jobs_v2() returns top 50 (RRF scored)
    ↓
Cross-encoder scores each (query, job) pair
    ↓
Re-sort by cross-encoder score
    ↓
Return top 20
```

### 6.2 Cross-Encoder: ms-marco-MiniLM-L-6-v2

| Parameter | Value |
|---|---|
| Model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Parameters | 22M |
| Input | (query_text, job_title + " at " + company + ". " + description_snippet) |
| Output | Relevance score 0–1 |
| Speed | ~5ms per pair on CPU |
| 50 pairs | ~250ms total |
| Runs on | Modal (CPU, no GPU needed) |
| Library | `sentence-transformers` |

**Implementation:**

```python
# pipeline/src/search/reranker.py
from sentence_transformers import CrossEncoder

_model: CrossEncoder | None = None

def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
    return _model

def rerank(query: str, jobs: list[dict], top_k: int = 20) -> list[dict]:
    """Re-rank jobs using cross-encoder. Returns top_k sorted by relevance."""
    model = get_reranker()
    pairs = [
        (query, f"{j['title']} at {j['company_name']}. {(j.get('description_plain') or '')[:300]}")
        for j in jobs
    ]
    scores = model.predict(pairs, show_progress_bar=False)
    for job, score in zip(jobs, scores):
        job["rerank_score"] = float(score)
    return sorted(jobs, key=lambda j: j["rerank_score"], reverse=True)[:top_k]
```

**Where it runs:** Modal serverless function, called from the Next.js API route via HTTP. The model stays warm in Modal's container cache (~2s cold start, then instant).

**Fallback:** If Modal is down or latency exceeds 2s, return RRF results directly (graceful degradation, no re-ranking).

### 6.3 User Profile Embedding

**Profile template (mirrors job structured summary):**

```
Target Role: {target_role}
Skills: {skills, comma-separated}
Experience: {experience_text}
Location: {preferred_location}
Work Preference: {work_preference}
```

**Same model, same vector space:** Gemini embedding-001, 768 dimensions, stored as `halfvec(768)` in `user_profiles.profile_embedding`. Enables direct cosine similarity between user profile and job embeddings.

**Profile collection:** At this phase (Phase 2), profile data is inserted via `service_role` into the `user_profiles` table. Fields: target role (text), skills (text array from skills taxonomy), experience (text), preferred location (text), work preference (text: remote/hybrid/onsite/any), minimum salary (integer). The web form for user-facing profile creation is Phase 3.

**Re-embedding:** Whenever the user updates their profile, re-embed the structured template and store the new vector.

### 6.4 Search Quality Verification

**50+ test queries** covering:

| Category | Example queries | Count |
|---|---|---|
| Role-based | "Python developer", "nurse", "accountant", "chef" | 10 |
| Location-specific | "developer jobs in Manchester", "nurse London" | 10 |
| Skill-based | "AWS cloud engineer", "CIPD qualified HR" | 10 |
| Seniority | "senior data scientist", "junior marketing" | 5 |
| Salary range | "£50k+ developer", "high salary finance" | 5 |
| Remote/hybrid | "remote python", "hybrid accountant London" | 5 |
| Edge cases | Empty query, very long query, typos, non-English | 5+ |

**Metrics:** NDCG@20 comparing RRF-only vs RRF + cross-encoder. Target: ≥10% NDCG improvement with cross-encoder.

---

## 7. New Dependencies (Phase 2 Additions)

### 7.1 pipeline/pyproject.toml additions

| Package | Purpose | Phase 2 stage |
|---|---|---|
| `spacy>=3.7` | PhraseMatcher for skill extraction | Stage 1 |
| `sentence-transformers>=2.2` | Cross-encoder re-ranking | Stage 4 |
| `xgboost>=2.0` | Salary prediction | Stage 3 |
| `scikit-learn>=1.4` | Feature engineering, train/test split, metrics | Stage 3 |
| `datasketch>=1.6` | MinHash/LSH dedup | Stage 2 |
| `xxhash>=3.0` | Fast hashing for MinHash | Stage 2 |

**Modal image impact:** +500MB for SpaCy + en_core_web_sm + sentence-transformers. Cold start: ~5–8 seconds (up from ~2–3s). Acceptable for batch processing and warm serverless functions.

### 7.2 SpaCy Model Download

```python
# In Modal image definition
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "spacy>=3.7", "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz",
    # ... other deps
)
```

---

## 8. Cost Calculations

### 8.1 Phase 2 Monthly Budget Delta

| Item | Cost | Notes |
|---|---|---|
| SpaCy skill extraction | $0 | Rule-based, runs on Modal free tier |
| pg_trgm dedup | $0 | PostgreSQL built-in extension |
| MinHash/LSH | $0 | datasketch library, Modal compute |
| XGBoost training | $0 | ~5 min monthly on Modal |
| Companies House API | $0 | Free API |
| Cross-encoder inference | $0 | ms-marco-MiniLM on Modal CPU |
| Supabase storage delta | $0 | New tables + MVs within 8GB limit |
| **Phase 2 delta** | **~$0/mo** | |
| **Total (Phase 1 + 2)** | **~$31/mo** | |

### 8.2 One-Time Processing Costs

| Task | Cost | Time |
|---|---|---|
| ESCO CSV loading | $0 | ~5 min |
| Skills dictionary build | $0 | ~4 hours manual |
| Backfill job_skills (500K jobs) | $0 | ~20 min on Modal |
| Fuzzy dedup scan (500K jobs) | $0 | ~2 hours on Modal |
| MinHash/LSH build (400K jobs) | $0 | ~30 min on Modal |
| XGBoost training (100K+ jobs) | $0 | ~5 min on Modal |
| Companies House enrichment (50K companies) | $0 | ~7 hours at 2 req/sec |
| Cross-encoder model download | $0 | ~200MB, one-time |

---

## 9. Updated search_jobs_v2() vs Phase 1 search_jobs()

| Feature | search_jobs() (Phase 1) | search_jobs_v2() (Phase 2) |
|---|---|---|
| Return fields | 4 (id, title, company, rrf_score) | 18 (full job card data) |
| Default match_count | 20 | 50 (for cross-encoder input) |
| Duplicate filtering | None | `exclude_duplicates` parameter |
| Salary filter | `min_salary` only | `min_salary` + `max_salary`, uses predicted salary as fallback |
| Category filter | None | `category_filter` parameter |
| Skill filter | None | `skill_filters` array, checked via junction table |
| Re-ranking | None | Cross-encoder applied post-query |

**Phase 1 `search_jobs()` is preserved** — not dropped. `search_jobs_v2()` is additive. Phase 3 UI will use v2.

---

## 10. Acceptance Criteria

### Stage 1: Skills Extraction & Taxonomy (Week 5)

- [ ] `esco_skills` table loaded with ~13,939 rows from ESCO CSV
- [ ] `skills` table populated with ~10K–15K canonical skills
- [ ] SpaCy PhraseMatcher extracts skills from job descriptions
- [ ] "Python developer with AWS experience" extracts at least `['Python', 'AWS']`
- [ ] UK-specific: "CSCS card holder with SMSTS" extracts at least `['CSCS Card', 'SMSTS']`
- [ ] `job_skills` table populated for all `status='ready'` jobs
- [ ] Max 15 skills per job enforced
- [ ] `mv_skill_demand` returns rows with correct job counts
- [ ] `mv_skill_cooccurrence` returns skill pairs with count ≥ 10
- [ ] pg_cron refreshes both materialized views daily
- [ ] Processing rate: ≥5,000 jobs/minute on Modal

### Stage 2: Advanced Deduplication (Week 6)

- [ ] pg_trgm: "Senior Python Developer" and "Senior Python Dev" flagged as candidates (similarity ≥ 0.6)
- [ ] pg_trgm: "Goldman Sachs International" and "Goldman Sachs" match (similarity ≥ 0.5)
- [ ] Composite score correctly combines all 5 signals with defined weights
- [ ] `dup_score >= 0.65` marks the poorer version as `is_duplicate = TRUE`
- [ ] `canonical_id` correctly points to the richer version
- [ ] `search_jobs_v2()` with `exclude_duplicates=TRUE` skips marked duplicates
- [ ] MinHash signatures computed and stored in `description_hash`
- [ ] LSH index identifies near-duplicate candidates
- [ ] Combined pg_trgm + MinHash + composite score achieves ≥85% precision on 100 manually reviewed pairs
- [ ] Performance: dedup scan of 500K jobs completes in < 3 hours

### Stage 3: Salary Prediction & Company Enrichment (Week 7)

- [ ] XGBoost model trained on ≥50K labeled Adzuna jobs
- [ ] MAE < £8,000 on test set (target: < £5,000)
- [ ] Predictions stored with `salary_is_predicted = TRUE` and confidence score
- [ ] Sanity: no predictions < £10K or > £500K
- [ ] Companies House: search returns correct match for "Goldman Sachs"
- [ ] SIC code "62020" correctly maps to section "J" → "Technology"
- [ ] `companies` table enriched with SIC codes, status, date_of_creation
- [ ] Rate limit: sustained 2 req/sec, no 429 errors
- [ ] `salary_predicted_min`/`max` used as fallback in `search_jobs_v2()` salary filter

### Stage 4: Cross-Encoder Re-ranking (Week 8)

- [ ] Cross-encoder loaded and scores a (query, job) pair in < 10ms
- [ ] 50 pairs re-ranked in < 500ms total
- [ ] Re-ranked results measurably better than RRF-only (manual evaluation of 50 queries)
- [ ] `user_profiles` table accepts INSERT of all fields via `service_role`
- [ ] Profile embedding stored as halfvec(768) using Gemini
- [ ] Profile-based search returns relevant results
- [ ] RLS: users can only read/update own profile
- [ ] Graceful degradation: if Modal unavailable, return RRF results without re-ranking
- [ ] 50+ test queries pass with sensible results
