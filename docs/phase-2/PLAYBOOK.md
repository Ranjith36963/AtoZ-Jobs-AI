# AtoZ Jobs AI — Phase 2 Playbook

**How to build it. Stage-by-stage Claude Code instructions.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and GATES.md (verification).

---

## 0. Before You Start

### 0.1 Prerequisites

Everything from Phase 1 is already in place, plus:

- Phase 1 complete: all 102 verification items passed, `v0.1.0` tagged
- Production pipeline running: jobs being collected, processed, embedded
- `skills` and `job_skills` tables exist (empty, ready for Phase 2 population)
- `search_jobs()` function working with RRF
- ESCO CSV downloaded locally: `skills_en.csv` from `esco.ec.europa.eu/en/use-esco/download`
- Companies House API key registered at `developer.company-information.service.gov.uk`

### 0.2 New API Keys Needed

| Key | Provider | Phase 2 stage | Where to store |
|---|---|---|---|
| `COMPANIES_HOUSE_API_KEY` | Companies House | Stage 3 | Modal secrets, .env.local |

### 0.3 The Workflow (Same as Phase 1)

```
/clear                                          ← Clean context
ultrathink and plan [task]. Do NOT code yet.    ← Plan first
[review plan, challenge assumptions]            ← Human checks
Implement the plan.                             ← Code
uv run pytest / pnpm test                       ← Tests must pass
git add -A && git commit                        ← Conventional commit
```

### 0.4 When to /clear and /compact

| Trigger | Action |
|---|---|
| Starting a new stage (Skills → Dedup → Salary → Re-ranking) | `/clear` |
| Switching between pipeline Python and web TypeScript | `/clear` |
| Context getting long (>50 turns) | `/compact 'Focus on [current task]'` |
| After completing and committing a major file | `/compact` |

---

## 1. Stage 1: Skills Extraction & Taxonomy (Week 5)

**Branch:** `search-match-phase`

```bash
git checkout -b search-match-phase
```

### 1.1 Write Migration 007

**Prompt to Claude Code:**

```
Write supabase/migrations/007_skills_taxonomy/up.sql and down.sql.

Exact SQL from SPEC.md §2.1. Creates:
- esco_skills reference table
- Adds source + aliases columns to skills table
- mv_skill_demand materialized view
- mv_skill_cooccurrence materialized view
- pg_cron schedules for daily MV refresh at 3 AM

Run: supabase db reset
Verify: All tables and views exist. Cron jobs scheduled.
```

### 1.2 Build ESCO Loader

**Prompt to Claude Code:**

```
Build pipeline/src/skills/esco_loader.py

TDD: Write test first in tests/test_esco_loader.py.

Test cases:
1. load_esco_csv() parses skills_en.csv fixture (10-row sample) correctly
2. Each row extracts: concept_uri, preferred_label, alt_labels (newline-separated), skill_type
3. Alt labels with length <= 2 are filtered out
4. Returns dict keyed by concept_uri

Then implement: exact code pattern from SPEC.md §3.1.
The CSV file path will be provided as argument (downloaded separately).

Run tests: uv run pytest tests/test_esco_loader.py
```

### 1.3 Build Skill Dictionary

**Prompt to Claude Code:**

```
Build pipeline/src/skills/dictionary_builder.py

This builds the combined skill dictionary from 3 sources:
1. ESCO CSV (13,939 skills + aliases)
2. UK-specific entries (~300, hardcoded from SPEC.md §3.2 table)
3. SkillNER EMSI/Lightcast seed data (extract from skillNer package if available, else skip)

Output: dict[str, str] mapping lowercase pattern → canonical name.
Expected size: ~10K-15K canonical skills, ~40K-60K patterns.

Write build_dictionary() function that merges all sources, deduplicates by lowercase key.
Write tests: verify ESCO patterns present, UK-specific entries present, dedup works.

Run tests: uv run pytest tests/test_dictionary_builder.py
```

### 1.4 Build SpaCy PhraseMatcher

**Prompt to Claude Code:**

```
Build pipeline/src/skills/spacy_matcher.py — exact code from SPEC.md §3.2.

This is the Phase 2 upgrade from Phase 1's regex SkillMatcher.
MUST implement the same interface: extract(text, max_skills=15) -> list[str]

Two-layer PhraseMatcher:
- Layer 1: attr="LOWER" for general skills (case-insensitive)
- Layer 2: attr="ORTH" for acronyms (AWS, SQL, ACCA, CIPD — uppercase, ≤6 chars)

TDD tests in tests/test_spacy_matcher.py:
1. "Python developer with AWS experience" → at least ['Python', 'AWS']
2. "CSCS card holder with SMSTS certification" → at least ['CSCS Card', 'SMSTS']
3. "NMC registered nurse with enhanced DBS" → at least ['NMC Registered', 'DBS Check']
4. "Project management using PRINCE2 methodology" → at least ['Project Management', 'PRINCE2']
5. Max 15 skills enforced
6. Empty string returns []
7. Deduplication: repeated mentions don't create duplicate entries

Run tests: uv run pytest tests/test_spacy_matcher.py
```

### 1.5 Build Job Skills Populator

**Prompt to Claude Code:**

```
Build pipeline/src/skills/populate.py

Backfills job_skills for all ready jobs missing skill extraction.

Logic:
1. Query jobs WHERE status='ready' AND NOT EXISTS (SELECT 1 FROM job_skills WHERE job_id = jobs.id)
2. Batch by 500
3. For each job: extract skills via SpaCySkillMatcher
4. For each skill: upsert into skills table (get or create by name)
5. Insert into job_skills with confidence=1.0, is_required=TRUE
6. Log progress via structlog

TDD tests in tests/test_populate.py:
1. Single job → skills extracted and inserted into job_skills
2. Skill already in skills table → reuses existing skill_id
3. Job already has job_skills entries → skipped
4. Batch processing: 10 jobs processed correctly

Run tests: uv run pytest tests/test_populate.py
```

### 1.6 Seed ESCO Data and Run Backfill

**Prompt to Claude Code:**

```
Build pipeline/src/skills/seed_esco.py

Script to:
1. Load ESCO CSV via esco_loader
2. Bulk insert into esco_skills table (13,939 rows)
3. Build combined dictionary via dictionary_builder
4. Seed skills table with canonical skills
5. Log counts via structlog

Write a Modal function to run this + the backfill:
  modal run src/modal_app.py::seed_esco
  modal run src/modal_app.py::backfill_job_skills
```

### 1.7 Update Modal Image

**Prompt to Claude Code:**

```
Update pipeline/src/modal_app.py Modal image definition.

Add to pip_install:
- spacy>=3.7
- en-core-web-sm model (install via URL: https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz)

Add new Modal functions:
- seed_esco: one-time ESCO data loading
- backfill_job_skills: batch skills extraction for existing jobs
- (keep all Phase 1 functions unchanged)

Expected image size increase: ~500MB. Cold start: ~5-8s (was ~2-3s).
```

### 1.8 Verify and Merge

```bash
uv run pytest --cov=src/skills --cov-fail-under=85
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(skills): SpaCy PhraseMatcher, ESCO taxonomy, job_skills backfill, materialized views"
git tag v0.2.0-skills
```

**`/clear` — Start fresh for Stage 2.**

---

## 2. Stage 2: Advanced Deduplication (Week 6)

**Branch:** `search-match-phase` (continue on same branch)

```bash
git checkout search-match-phase
```

### 2.1 Write Migration 008

**Prompt to Claude Code:**

```
Write supabase/migrations/008_advanced_dedup/up.sql and down.sql.

Exact SQL from SPEC.md §2.2. Creates:
- canonical_id, is_duplicate, duplicate_score, description_hash columns on jobs
- GIN trigram index on company_name
- B-tree index on canonical_id
- Partial index on ready + not duplicate
- compute_duplicate_score() SQL function

Run: supabase db reset
Verify: New columns exist. compute_duplicate_score(0.7, true, 3.0, 0.8, 5) returns expected value.
```

### 2.2 Build pg_trgm Fuzzy Matcher

**Prompt to Claude Code:**

```
Build pipeline/src/dedup/fuzzy_matcher.py

Implements fuzzy duplicate detection using pg_trgm.

find_fuzzy_candidates(job_id: int, db_client) -> list[dict]:
  1. SET pg_trgm.similarity_threshold = 0.6
  2. Query candidates where title similarity >= 0.6
  3. For each candidate, compute full composite score via compute_duplicate_score()
  4. Return candidates with dup_score >= 0.65

mark_duplicate(duplicate_id: int, canonical_id: int, score: float, db_client):
  1. Set is_duplicate = TRUE, canonical_id, duplicate_score on the duplicate
  2. Keep canonical version unchanged

pick_canonical(job_a: dict, job_b: dict) -> tuple[int, int]:
  Exact logic from SPEC.md §4.3. Returns (canonical_id, duplicate_id).

TDD tests in tests/test_fuzzy_matcher.py:
1. Identical titles → flagged as candidate
2. "Senior Python Developer" vs "Senior Python Dev" → similarity > 0.6
3. Completely different jobs → not flagged
4. pick_canonical keeps job with more non-null fields
5. Composite score weights are correct (0.35 + 0.25 + 0.15 + 0.15 + 0.10 = 1.0)

Run tests: uv run pytest tests/test_fuzzy_matcher.py
```

### 2.3 Build MinHash/LSH Module

**Prompt to Claude Code:**

```
Build pipeline/src/dedup/minhash.py

Implements near-duplicate detection at scale using MinHash/LSH.

compute_minhash(text: str, num_perm: int = 128) -> MinHash
  Uses xxhash, 3-character grams. Exact code from SPEC.md §4.4.

build_lsh_index(jobs: list[dict], threshold: float = 0.5) -> MinHashLSH
  Builds index from job descriptions.

find_lsh_candidates(lsh: MinHashLSH, job_id: str, minhash: MinHash) -> list[str]
  Returns candidate job IDs from LSH query.

TDD tests in tests/test_minhash.py:
1. Identical texts → MinHash Jaccard ≈ 1.0
2. Similar texts (same content, different formatting) → Jaccard > 0.5
3. Completely different texts → Jaccard < 0.3
4. LSH index returns correct candidates for a near-duplicate
5. 3-character gram tokenization works on short and long texts

Run tests: uv run pytest tests/test_minhash.py
```

### 2.4 Build Dedup Orchestrator

**Prompt to Claude Code:**

```
Build pipeline/src/dedup/orchestrator.py

Combines all 3 dedup stages into a single pipeline:

run_advanced_dedup(batch_size: int = 1000):
  1. Query all ready, non-duplicate jobs
  2. Stage 1: Skip (already done in Phase 1 via content_hash)
  3. Stage 2: For each job, find pg_trgm fuzzy candidates
  4. Stage 3: Build MinHash/LSH index, find near-duplicate candidates
  5. For all candidates from stages 2+3: compute composite score
  6. Mark duplicates where score >= 0.65
  7. Log: total scanned, duplicates found, precision estimate

Add Modal function: backfill_dedup
Expected runtime: ~2-3 hours for 500K jobs.

Run tests: uv run pytest tests/test_dedup_orchestrator.py
```

### 2.5 Update search_jobs to Exclude Duplicates

**Prompt to Claude Code:**

```
The search_jobs_v2() function is in Migration 010.
For now, verify that the existing search_jobs() still works.
The duplicate exclusion will come with Migration 010 in Stage 4.

For Stage 2, just ensure:
1. is_duplicate column is populated correctly
2. canonical_id references are valid
3. Manual query: SELECT count(*) FROM jobs WHERE is_duplicate = TRUE returns > 0 after dedup run
```

### 2.6 Verify and Merge

```bash
uv run pytest --cov=src/dedup --cov-fail-under=85
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(dedup): pg_trgm fuzzy matching, MinHash/LSH, composite scoring, dedup orchestrator"
git tag v0.2.0-dedup
```

**`/clear` — Start fresh for Stage 3.**

---

## 3. Stage 3: Salary Prediction & Company Enrichment (Week 7)

**Branch:** `search-match-phase` (continue on same branch)

```bash
git checkout search-match-phase
```

### 3.1 Write Migration 009

**Prompt to Claude Code:**

```
Write supabase/migrations/009_salary_company/up.sql and down.sql.

Exact SQL from SPEC.md §2.3. Creates:
- salary_predicted_min/max, salary_confidence, salary_model_version on jobs
- companies_house_number, sic_codes, company_status, date_of_creation, registered_address, enriched_at on companies
- sic_industry_map reference table with all 21 SIC sections seeded

Run: supabase db reset
Verify: New columns exist. sic_industry_map has 21 rows.
```

### 3.2 Build Feature Engineering Pipeline

**Prompt to Claude Code:**

```
Build pipeline/src/salary/features.py

Extract features from jobs for salary prediction.

build_features(jobs: list[dict]) -> tuple[np.ndarray, np.ndarray]:
  Returns (feature_matrix, salary_labels).

  Features (from SPEC.md §5.1):
  - TF-IDF of job title (max 500 features)
  - One-hot location region (12 UK regions)
  - One-hot category (~15 categories)
  - Multi-hot employment type
  - Ordinal seniority (Junior=1, Mid=2, Senior=3, Lead=4, Executive=5)
  - Skill count (integer)
  - Top 50 skills binary presence

  Labels: salary_annual_max (only jobs where salary_is_predicted = FALSE)

TDD tests in tests/test_salary_features.py:
1. TF-IDF produces correct feature count
2. One-hot encoding handles all 12 regions
3. Missing seniority → encoded as 0
4. Jobs without salary excluded from labels
5. Feature matrix shape matches expected dimensions

Run tests: uv run pytest tests/test_salary_features.py
```

### 3.3 Build Salary Trainer

**Prompt to Claude Code:**

```
Build pipeline/src/salary/trainer.py — exact code pattern from SPEC.md §5.1.

train_salary_model(features, labels) -> xgb.Booster
  80/20 train/test split, random_state=42.
  XGBoost with max_depth=6, learning_rate=0.1, 200 rounds, early stopping 20.
  Log MAE and median AE.
  Validation: MAE < £8,000 target, < £5,000 stretch goal.

predict_salary(model, features) -> list[dict]:
  Returns [{predicted_min, predicted_max, confidence}] for each job.
  predicted_min = prediction * 0.9 (10% lower bound)
  predicted_max = prediction * 1.1 (10% upper bound)
  confidence: HIGH/MEDIUM/LOW based on model uncertainty

save_model(model, path) and load_model(path) for persistence.

TDD tests in tests/test_salary_trainer.py:
1. Model trains without error on synthetic data
2. Predictions are within sane range (£10K–£500K)
3. MAE computed correctly
4. Model save/load round-trips correctly

Run tests: uv run pytest tests/test_salary_trainer.py
```

### 3.4 Build Companies House Client

**Prompt to Claude Code:**

```
Build pipeline/src/enrichment/companies_house.py — exact code from SPEC.md §5.2.

search_company(name, api_key) -> dict | None
  GET /search/companies?q={name}&items_per_page=5
  Basic Auth: api_key as username, empty password
  Returns best match or None

get_company_profile(company_number, api_key) -> dict
  GET /company/{company_number}
  Returns full profile

sic_to_section(sic_code: str) -> str
  Maps 5-digit SIC code to section letter (A-U). Exact mapping from SPEC.md §5.2.

Rate limiting: max 2 req/sec (600 per 5 min).
Error handling: 429 → exponential backoff. 404 → return None. 5xx → retry 3x.

TDD tests in tests/test_companies_house.py:
1. search_company with mock response → parses correctly
2. sic_to_section("62020") → "J" (Information and Communication)
3. sic_to_section("86101") → "Q" (Human Health)
4. Rate limit: 429 response → retries after delay
5. Company not found → returns None gracefully

Run tests: uv run pytest tests/test_companies_house.py
```

### 3.5 Build Enrichment Orchestrator

**Prompt to Claude Code:**

```
Build pipeline/src/enrichment/orchestrator.py

enrich_companies(batch_size: int = 100):
  1. Query companies WHERE enriched_at IS NULL
  2. For each company: search Companies House
  3. If match found: get full profile, extract SIC codes, status, creation date
  4. Update companies table
  5. Rate limit: asyncio.sleep(0.5) between requests
  6. Log progress

predict_missing_salaries():
  1. Load trained XGBoost model
  2. Query jobs WHERE salary_annual_max IS NULL AND salary_predicted_max IS NULL
  3. Build features for batch
  4. Predict and store in salary_predicted_min/max with confidence
  5. Set salary_model_version

Add Modal functions:
  train_salary_model (monthly cron)
  enrich_companies (nightly cron)
  predict_salaries (nightly cron, after training)
```

### 3.6 Verify and Merge

```bash
uv run pytest --cov=src/salary --cov-fail-under=85
uv run pytest --cov=src/enrichment --cov-fail-under=85
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(salary): XGBoost prediction, Companies House enrichment, SIC mapping"
git tag v0.2.0-salary
```

**`/clear` — Start fresh for Stage 4.**

---

## 4. Stage 4: Cross-Encoder Re-ranking (Week 8)

**Branch:** `search-match-phase` (continue on same branch)

```bash
git checkout search-match-phase
```

### 4.1 Write Migration 010

**Prompt to Claude Code:**

```
Write supabase/migrations/010_user_profiles_search_v2/up.sql and down.sql.

Exact SQL from SPEC.md §2.4. Creates:
- user_profiles table with embedding, RLS policies
- search_jobs_v2() function with expanded filters and return fields

Run: supabase db reset
Verify: user_profiles table exists with RLS. search_jobs_v2() callable.
```

### 4.2 Build Cross-Encoder Re-ranker

**Prompt to Claude Code:**

```
Build pipeline/src/search/reranker.py — exact code from SPEC.md §6.2.

get_reranker() -> CrossEncoder
  Lazy-loads ms-marco-MiniLM-L-6-v2, max_length=512.

rerank(query: str, jobs: list[dict], top_k: int = 20) -> list[dict]:
  Creates (query, job_text) pairs
  job_text = "{title} at {company}. {description[:300]}"
  Scores all pairs, sorts by score, returns top_k
  Adds rerank_score to each job dict

TDD tests in tests/test_reranker.py:
1. Relevant job scores higher than irrelevant job
   e.g., query="Python developer", job_a="Senior Python Developer at TechCo", job_b="Chef at Restaurant"
2. 50 pairs scored in < 2 seconds (CPU)
3. top_k=5 returns exactly 5 results
4. Empty job list returns empty list
5. rerank_score added to each job dict

Run tests: uv run pytest tests/test_reranker.py
```

### 4.3 Build User Profile Handler

**Prompt to Claude Code:**

```
Build pipeline/src/profiles/handler.py

create_or_update_profile(user_id: str, profile_data: dict) -> dict:
  1. Build profile text template from SPEC.md §6.4
  2. Embed via Gemini embedding-001 (same model as jobs)
  3. Upsert into user_profiles table
  4. Return profile with embedding

get_profile_embedding(user_id: str) -> list[float] | None:
  Returns profile embedding for search personalization.

Profile text template:
  Target Role: {target_role}
  Skills: {skills, comma-separated}
  Experience: {experience_text}
  Location: {preferred_location}
  Work Preference: {work_preference}

TDD tests in tests/test_profile_handler.py:
1. Profile text template correctly formatted
2. Embedding is 768 dimensions
3. Re-embedding on update produces new vector
4. Missing optional fields handled (empty string, not error)
5. RLS: only user's own profile returned

Run tests: uv run pytest tests/test_profile_handler.py
```

### 4.4 Build Search Orchestrator (API endpoint)

**Prompt to Claude Code:**

```
Build pipeline/src/search/orchestrator.py

This is the main search endpoint that combines everything:

search(query: str, user_id: str | None, filters: dict) -> dict:
  1. Embed query via Gemini
  2. Call search_jobs_v2() with query_text + query_embedding + filters → top 50
  3. Cross-encoder rerank → top 20
  4. If user_id: factor in profile embedding for personalization
  5. Return results with rrf_score, rerank_score

This will be called from a Modal HTTP endpoint or Next.js API route.

Create a Modal @web_endpoint for this:
  POST /search
  Body: { query, user_id?, filters? }
  Response: { results: [...], total, latency_ms }

Test with: curl -X POST https://<modal-url>/search -d '{"query": "Python developer in London"}'
```

### 4.5 Update Modal Image and Functions

**Prompt to Claude Code:**

```
Update pipeline/src/modal_app.py for all Phase 2 additions.

New dependencies in image:
- sentence-transformers>=2.2
- xgboost>=2.0
- scikit-learn>=1.4
- datasketch>=1.6
- xxhash>=3.0

New secrets:
- COMPANIES_HOUSE_API_KEY

New Modal functions:
- seed_esco (one-time)
- backfill_job_skills (one-time, then daily for new jobs)
- backfill_dedup (one-time, then daily for new jobs)
- train_salary_model (monthly cron)
- enrich_companies (nightly cron)
- predict_salaries (nightly cron)
- search (web endpoint, always warm)

New cron schedules:
- Daily: backfill_job_skills for new ready jobs
- Daily: run dedup for new ready jobs
- Daily: predict salaries for jobs missing salary
- Nightly: enrich new companies
- Monthly: retrain salary model
```

### 4.6 Search Quality Verification

**Prompt to Claude Code:**

```
Build tests/test_search_quality.py

50+ test queries from SPEC.md §6.5 covering:
- Role-based (10 queries)
- Location-specific (10 queries)
- Skill-based (10 queries)
- Seniority (5 queries)
- Salary range (5 queries)
- Remote/hybrid (5 queries)
- Edge cases (5+ queries)

For each query, verify:
1. Results returned (non-empty for valid queries)
2. Top result is relevant (title or skills match)
3. Cross-encoder score > RRF score correlation (reranking helps)
4. No SQL errors
5. Response time < 2 seconds (including re-ranking)

Run: uv run pytest tests/test_search_quality.py -v
```

### 4.7 Verify and Merge

```bash
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check . && uv run mypy src/
git add -A
git commit -m "feat(search): cross-encoder re-ranking, user profiles, search_jobs_v2"
# Squash merge search-match-phase to main
git checkout main
git merge --squash search-match-phase
git commit -m "feat(pipeline): Phase 2 complete — skills, dedup, salary, re-ranking, search_jobs_v2"
git tag v0.2.0
```

---

## 5. Production Deployment

### 5.1 Deploy Database Migrations

```bash
# Push all Phase 2 migrations (007-010)
supabase db push

# Verify
supabase db remote commit
# Tables: esco_skills, sic_industry_map, user_profiles exist
# Functions: search_jobs_v2, compute_duplicate_score exist
# Views: mv_skill_demand, mv_skill_cooccurrence exist
```

### 5.2 Deploy Pipeline

```bash
# Update Modal secrets
modal secret update atoz-env \
    COMPANIES_HOUSE_API_KEY=<value>

# Deploy
cd pipeline && modal deploy src/modal_app.py

# One-time: seed ESCO data
modal run src/modal_app.py::seed_esco

# One-time: backfill job_skills
modal run src/modal_app.py::backfill_job_skills

# One-time: run advanced dedup
modal run src/modal_app.py::backfill_dedup

# One-time: train salary model
modal run src/modal_app.py::train_salary_model

# One-time: initial company enrichment
modal run src/modal_app.py::enrich_companies

# One-time: predict missing salaries
modal run src/modal_app.py::predict_salaries
```

### 5.3 Run GATES.md Go/No-Go Checklist

Execute every item in GATES.md. All items must pass before declaring Phase 2 complete.

### 5.4 Monitor First 24 Hours

Watch for: cross-encoder latency (>2s), missing skill extractions, dedup false positives, salary prediction outliers.

---

## Appendix A: File Creation Order (Quick Reference)

| Order | File | Stage |
|---|---|---|
| 1 | Migration 007 (up.sql + down.sql) | Skills |
| 2 | pipeline/src/skills/esco_loader.py | Skills |
| 3 | pipeline/src/skills/dictionary_builder.py | Skills |
| 4 | pipeline/src/skills/spacy_matcher.py | Skills |
| 5 | pipeline/src/skills/populate.py | Skills |
| 6 | pipeline/src/skills/seed_esco.py | Skills |
| 7 | Migration 008 (up.sql + down.sql) | Dedup |
| 8 | pipeline/src/dedup/fuzzy_matcher.py | Dedup |
| 9 | pipeline/src/dedup/minhash.py | Dedup |
| 10 | pipeline/src/dedup/orchestrator.py | Dedup |
| 11 | Migration 009 (up.sql + down.sql) | Salary |
| 12 | pipeline/src/salary/features.py | Salary |
| 13 | pipeline/src/salary/trainer.py | Salary |
| 14 | pipeline/src/enrichment/companies_house.py | Salary |
| 15 | pipeline/src/enrichment/orchestrator.py | Salary |
| 16 | Migration 010 (up.sql + down.sql) | Re-ranking |
| 17 | pipeline/src/search/reranker.py | Re-ranking |
| 18 | pipeline/src/profiles/handler.py | Re-ranking |
| 19 | pipeline/src/search/orchestrator.py | Re-ranking |
| 20 | Update pipeline/src/modal_app.py | Re-ranking |
| 21 | tests/test_search_quality.py | Re-ranking |

## Appendix B: Conventional Commit Messages

```
feat(skills): ESCO loader and taxonomy seeding
feat(skills): SpaCy PhraseMatcher with two-layer matching
feat(skills): job_skills backfill and materialized views
feat(dedup): pg_trgm fuzzy matching with composite scoring
feat(dedup): MinHash/LSH near-duplicate detection
feat(dedup): dedup orchestrator combining all 3 stages
feat(salary): XGBoost salary prediction with feature engineering
feat(enrichment): Companies House API integration with SIC mapping
feat(search): cross-encoder ms-marco-MiniLM re-ranking
feat(search): user profile embedding and search personalization
feat(search): search_jobs_v2 with expanded filters
feat(search): search quality verification (50+ test queries)
feat(pipeline): Phase 2 complete, E2E verified, production ready
```

## Appendix C: CLAUDE.md Updates for Phase 2

Add these lines to the root CLAUDE.md after Phase 2 deployment:

```
## Phase 2 Additions
- SpaCy PhraseMatcher for skill extraction (Phase 2 upgrade from Phase 1 regex)
- Cross-encoder: ms-marco-MiniLM-L-6-v2 for re-ranking (CPU, no GPU)
- XGBoost salary prediction (trained monthly on Adzuna labeled data)
- Companies House API for company enrichment (free, 600 req/5min)
- search_jobs_v2() replaces search_jobs() for Phase 3 UI
- Materialized views: mv_skill_demand, mv_skill_cooccurrence (refreshed daily)
```
