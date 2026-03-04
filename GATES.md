# AtoZ Jobs AI — Phase 2 Quality Gates

**How to verify it works. Pass/fail criteria for every stage.**

Version: 1.0 · March 2026 · Companion to: SPEC.md (what) and PLAYBOOK.md (how).

---

## 1. Stage Gates — Pass/Fail Criteria

### 1.1 Gate 1: Skills Extraction & Taxonomy (Week 5)

Run these checks before completing Stage 1 on `search-match-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| S1 | Migration 007 | `supabase db reset` | Completes with zero errors. All Phase 1 + Phase 2 migrations applied. |
| S2 | Rollback 007 | Run `down.sql`, then `supabase db reset` | Clean rollback. Full chain re-applies. |
| S3 | esco_skills loaded | `SELECT count(*) FROM esco_skills` | ≥ 13,000 rows (ESCO v1.2.1 has ~13,939). |
| S4 | skills table populated | `SELECT count(*) FROM skills` | ≥ 10,000 canonical skills. |
| S5 | UK-specific entries | `SELECT count(*) FROM skills WHERE name IN ('CSCS Card', 'CIPD', 'NMC Registered', 'SIA Licence', 'ACCA')` | Returns 5 rows. |
| S6 | SpaCy: Python + AWS | `uv run pytest tests/test_spacy_matcher.py::test_python_aws` | "Python developer with AWS experience" extracts at least `['Python', 'AWS']`. |
| S7 | SpaCy: UK certs | `uv run pytest tests/test_spacy_matcher.py::test_uk_certs` | "CSCS card holder with SMSTS" extracts at least `['CSCS Card', 'SMSTS']`. |
| S8 | SpaCy: healthcare | `uv run pytest tests/test_spacy_matcher.py::test_healthcare` | "NMC registered nurse with enhanced DBS" extracts at least `['NMC Registered', 'DBS Check']`. |
| S9 | Max 15 skills | `uv run pytest tests/test_spacy_matcher.py::test_max_skills` | Job description with 20+ skill mentions → exactly 15 returned. |
| S10 | job_skills populated | `SELECT count(*) FROM job_skills` | > 0 after backfill. Average ~5–10 skills per job. |
| S11 | No orphans | `SELECT count(*) FROM job_skills js LEFT JOIN skills s ON s.id = js.skill_id WHERE s.id IS NULL` | Returns 0. |
| S12 | mv_skill_demand | `SELECT * FROM mv_skill_demand ORDER BY job_count DESC LIMIT 10` | Returns rows. Top skills are recognizable (Python, JavaScript, Project Management, etc). |
| S13 | mv_skill_cooccurrence | `SELECT * FROM mv_skill_cooccurrence ORDER BY cooccurrence_count DESC LIMIT 10` | Returns rows. Pairs make sense (Python + Django, AWS + Docker, etc). |
| S14 | Cron refresh | `SELECT * FROM cron.job WHERE jobname LIKE 'refresh-skill%'` | 2 cron jobs exist. |
| S15 | Processing rate | Time the backfill_job_skills Modal function on 5,000 jobs | ≥ 5,000 jobs/minute (≤ 60 seconds). |
| S16 | Coverage | `uv run pytest --cov=src/skills --cov-fail-under=85` | ≥ 85% line coverage on skills/. |

**FAIL gate:** S1–S11 are hard failures. S12–S16 are soft (should pass but non-blocking for merge).

### 1.2 Gate 2: Advanced Deduplication (Week 6)

Run these checks before completing Stage 2 on `search-match-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| D1 | Migration 008 | `supabase db reset` | Completes with zero errors. |
| D2 | Rollback 008 | Run `down.sql`, then `supabase db reset` | Clean rollback. |
| D3 | compute_duplicate_score | `SELECT compute_duplicate_score(0.7, true, 3.0, 0.8, 5)` | Returns 0.35*0.7 + 0.25*1 + 0.15*1 + 0.15*0.8 + 0.10*1 = 0.245 + 0.25 + 0.15 + 0.12 + 0.10 = 0.865. |
| D4 | pg_trgm title match | `SELECT similarity('Senior Python Developer', 'Senior Python Dev')` | ≥ 0.6. |
| D5 | pg_trgm company match | `SELECT similarity('Goldman Sachs International', 'Goldman Sachs')` | ≥ 0.5. |
| D6 | pg_trgm negative | `SELECT similarity('Python Developer', 'Chef')` | < 0.3. |
| D7 | Fuzzy candidates | `uv run pytest tests/test_fuzzy_matcher.py` | All tests pass. Known duplicate pairs flagged. Non-duplicates excluded. |
| D8 | MinHash similar | `uv run pytest tests/test_minhash.py::test_similar_texts` | Jaccard > 0.5 for reformatted same-content texts. |
| D9 | MinHash different | `uv run pytest tests/test_minhash.py::test_different_texts` | Jaccard < 0.3 for unrelated texts. |
| D10 | Canonical selection | `uv run pytest tests/test_fuzzy_matcher.py::test_pick_canonical` | Richest version kept. Poorer version gets `is_duplicate=TRUE`, `canonical_id` set. |
| D11 | Duplicate count | `SELECT count(*) FROM jobs WHERE is_duplicate = TRUE` after dedup run | > 0 (some duplicates found). |
| D12 | Canonical FK valid | `SELECT count(*) FROM jobs j WHERE j.canonical_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM jobs c WHERE c.id = j.canonical_id)` | Returns 0 (no broken references). |
| D13 | Precision estimate | Manually review 100 marked duplicates | ≥ 85% are true duplicates. |
| D14 | No false negatives | Manually check 20 known near-duplicate pairs (same job, different sources) | ≥ 80% detected by at least one dedup stage. |
| D15 | Performance | Time the full dedup scan on production data | Completes in < 3 hours for 500K jobs. |
| D16 | Coverage | `uv run pytest --cov=src/dedup --cov-fail-under=85` | ≥ 85% line coverage on dedup/. |

**FAIL gate:** D1–D12 are hard failures. D13–D16 are soft (require manual review).

### 1.3 Gate 3: Salary Prediction & Company Enrichment (Week 7)

Run these checks before completing Stage 3 on `search-match-phase`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| P1 | Migration 009 | `supabase db reset` | Completes with zero errors. |
| P2 | Rollback 009 | Run `down.sql`, then `supabase db reset` | Clean rollback. |
| P3 | SIC map seeded | `SELECT count(*) FROM sic_industry_map` | Returns 21 rows (sections A–U). |
| P4 | SIC mapping correct | `SELECT internal_category FROM sic_industry_map WHERE sic_section = 'J'` | Returns 'Technology'. |
| P5 | Feature engineering | `uv run pytest tests/test_salary_features.py` | All features extracted. Matrix shape correct. No NaN in features. |
| P6 | Model trains | `uv run pytest tests/test_salary_trainer.py::test_train` | Model trains without error on ≥ 50K samples. |
| P7 | MAE acceptable | `uv run pytest tests/test_salary_trainer.py::test_mae` | MAE < £8,000 on test set. |
| P8 | Prediction sanity | `uv run pytest tests/test_salary_trainer.py::test_sanity` | No predictions < £10,000 or > £500,000. |
| P9 | Salary stored | `SELECT count(*) FROM jobs WHERE salary_predicted_max IS NOT NULL AND salary_is_predicted = TRUE` after predict run | > 0. |
| P10 | Confidence scored | `SELECT DISTINCT salary_confidence FROM jobs WHERE salary_predicted_max IS NOT NULL` | Returns values in range [0, 1]. |
| P11 | CH: search works | `uv run pytest tests/test_companies_house.py::test_search` | Mock search returns parsed company data. |
| P12 | CH: SIC to section | `uv run pytest tests/test_companies_house.py::test_sic_mapping` | "62020" → "J". "86101" → "Q". "47110" → "G". |
| P13 | CH: rate limit | `uv run pytest tests/test_companies_house.py::test_rate_limit` | 429 response → backs off and retries. No crash. |
| P14 | Companies enriched | `SELECT count(*) FROM companies WHERE enriched_at IS NOT NULL` after enrichment run | > 0. |
| P15 | SIC codes stored | `SELECT count(*) FROM companies WHERE sic_codes IS NOT NULL AND array_length(sic_codes, 1) > 0` | > 0. |
| P16 | Model persistence | Save model → load model → predict on same data | Same predictions (within floating point tolerance). |
| P17 | Coverage: salary | `uv run pytest --cov=src/salary --cov-fail-under=85` | ≥ 85% line coverage. |
| P18 | Coverage: enrichment | `uv run pytest --cov=src/enrichment --cov-fail-under=85` | ≥ 85% line coverage. |

**FAIL gate:** P1–P9, P11–P14 are hard failures. P10, P15–P18 are soft.

### 1.4 Gate 4: Cross-Encoder Re-ranking (Week 8)

Run these checks before squash-merging `search-match-phase` → `main`.

| # | Check | Command | Pass criteria |
|---|---|---|---|
| R1 | Migration 010 | `supabase db reset` | Completes with zero errors. All 10 migrations (001–010) applied. |
| R2 | Rollback 010 | Run `down.sql`, then `supabase db reset` | Clean rollback. |
| R3 | user_profiles table | `\d user_profiles` | All columns present. `profile_embedding HALFVEC(768)`. |
| R4 | RLS: own profile | Insert profile as user A, query as user B | User B sees 0 rows. User A sees 1 row. |
| R5 | search_jobs_v2 callable | `SELECT * FROM search_jobs_v2(query_text := 'developer')` | Returns results with 18 columns. No SQL error. |
| R6 | search_jobs_v2 filters | `SELECT * FROM search_jobs_v2(query_text := 'developer', category_filter := 'Technology', exclude_duplicates := true)` | Returns only Technology category, no duplicates. |
| R7 | search_jobs_v2 skills | `SELECT * FROM search_jobs_v2(skill_filters := ARRAY['Python', 'AWS'])` | Returns only jobs with Python AND/OR AWS in job_skills. |
| R8 | Cross-encoder loads | `uv run pytest tests/test_reranker.py::test_model_loads` | Model loads in < 5 seconds. |
| R9 | Cross-encoder relevance | `uv run pytest tests/test_reranker.py::test_relevance` | "Python developer" query: Python job scores higher than Chef job. |
| R10 | Cross-encoder speed | `uv run pytest tests/test_reranker.py::test_speed` | 50 pairs scored in < 2 seconds on CPU. |
| R11 | Re-ranking improves | Run 50 test queries from §2. Compare RRF-only vs RRF+re-rank. | ≥ 60% of queries: top-1 result is same or better with re-ranking (manual assessment). |
| R12 | Profile embedding | `uv run pytest tests/test_profile_handler.py::test_embedding` | Profile text → 768-dim vector. |
| R13 | Profile personalization | Create profile "Python developer in Manchester". Search "developer". | Manchester Python jobs rank higher than unrelated jobs. |
| R14 | Graceful degradation | Kill cross-encoder (mock unavailable). Run search. | Returns RRF results without re-ranking. No crash. No error to user. |
| R15 | E2E search latency | Time full search pipeline: embed query → search_jobs_v2 → rerank | < 3 seconds total. |
| R16 | search_jobs (Phase 1) | `SELECT * FROM search_jobs(query_text := 'developer')` | Still works. Phase 1 function not broken. |
| R17 | Coverage: total | `uv run pytest --cov=src --cov-fail-under=80` | ≥ 80% line coverage across entire pipeline. |
| R18 | Lint + types | `uv run ruff check . && uv run mypy src/` | Zero errors. |

**FAIL gate:** R1–R10, R14, R16 are hard failures. R11–R13, R15, R17–R18 are soft.

---

## 2. Test Search Queries

These 15 queries verify the full Phase 2 search pipeline: search_jobs_v2() → cross-encoder re-ranking.

### Query Reference

| # | Description | Parameters | Expected behaviour |
|---|---|---|---|
| Q1 | Basic keyword + semantic | `query_text='Python developer'`, `query_embedding`, London coords | RRF returns candidates. Cross-encoder re-ranks. Top results are Python/software jobs in London. |
| Q2 | Skill filter | `skill_filters=['Python', 'AWS']` | Only jobs with Python or AWS in job_skills returned. |
| Q3 | Category filter | `query_text='analyst'`, `category_filter='Finance'` | Only finance analyst jobs. Not data analysts in tech. |
| Q4 | Exclude duplicates | `query_text='nurse'`, `exclude_duplicates=true` vs `false` | True: fewer results, no duplicates. False: includes duplicates. |
| Q5 | Predicted salary filter | `query_text='marketing manager'`, `min_salary=40000` | Jobs without real salary but with `salary_predicted_max >= 40000` included. |
| Q6 | Max salary filter | `query_text='graduate'`, `max_salary=30000` | Only entry-level/graduate jobs within salary range. |
| Q7 | Remote + skill | `query_text='DevOps'`, `include_remote=true`, `skill_filters=['Docker', 'Kubernetes']` | Remote DevOps jobs with container skills. |
| Q8 | Re-ranking verification | `query_text='senior data scientist machine learning'` | Cross-encoder should boost jobs mentioning ML/data science over generic "senior" roles. |
| Q9 | UK cert search | `query_text='CIPD qualified HR manager'` | Top results are HR manager jobs. Jobs with CIPD in job_skills rank higher. |
| Q10 | User profile search | Profile: "Python developer, Manchester, remote", `query_text='developer'` | Manchester + remote + Python jobs rank higher. |
| Q11 | Empty query + filters | No text, `category_filter='Healthcare'`, `min_salary=30000` | Returns healthcare jobs above £30K. No crash. |
| Q12 | Typo resilience | `query_text='softwar engeneer'` | FTS may fail but semantic catches intent. Some relevant results returned. |
| Q13 | UK-specific cert | `query_text='SIA door supervisor'` | Returns security jobs requiring SIA licence. |
| Q14 | All filters | `query_text='accountant'`, `query_embedding`, Edinburgh coords, `radius_miles=50`, `min_salary=50000`, `category_filter='Finance'`, `exclude_duplicates=true` | Finance accountant jobs near Edinburgh, ≥£50K, no duplicates. |
| Q15 | Graceful degradation | Same as Q1, but with cross-encoder mocked to fail | Returns RRF results directly. No re-ranking. No error. |

### Test Execution (Python)

```python
# tests/test_search_quality.py
import pytest
from pipeline.src.search.orchestrator import search

@pytest.mark.parametrize("query,filters,expected_min_results", [
    ("Python developer", {"search_lat": 51.5074, "search_lng": -0.1278}, 5),
    ("nurse", {"include_remote": True}, 3),
    ("SIA door supervisor", {}, 1),
    ("accountant", {"min_salary": 50000, "category_filter": "Finance"}, 1),
])
async def test_search_returns_results(query, filters, expected_min_results):
    result = await search(query=query, user_id=None, filters=filters)
    assert len(result["results"]) >= expected_min_results
    assert all("title" in r for r in result["results"])
    assert result["latency_ms"] < 3000
```

### Parameter Coverage Matrix

| Parameter | Exercised in queries |
|---|---|
| `query_text` | Q1–Q10, Q12–Q14 |
| `query_embedding` | Q1, Q8, Q10, Q14 |
| `search_lat` / `search_lng` | Q1, Q14 |
| `skill_filters` | Q2, Q7 |
| `category_filter` | Q3, Q11, Q14 |
| `exclude_duplicates` | Q4, Q14 |
| `min_salary` / `max_salary` | Q5, Q6, Q11, Q14 |
| `include_remote` | Q7 |
| User profile | Q10 |
| Graceful degradation | Q15 |
| Null parameters | Q11 (no text) |

---

## 3. Go/No-Go Production Checklist

Every item must pass before deploying Phase 2 to production. Execute in order.

### 3.1 Pre-Deployment (Local Verification)

| # | Check | Command / SQL | Pass criteria |
|---|---|---|---|
| G1 | Full migration chain (001–010) | `supabase db reset` | Zero errors. All 10 migrations applied. |
| G2 | All rollbacks work (010–007) | Run each `down.sql` in reverse, then `supabase db reset` | Each down.sql succeeds. Full chain re-applies cleanly. |
| G3 | Phase 1 search preserved | `SELECT * FROM search_jobs(query_text := 'developer')` | Still returns results. Phase 1 function not broken. |
| G4 | Phase 2 search works | `SELECT * FROM search_jobs_v2(query_text := 'developer', exclude_duplicates := true)` | Returns results with 18 columns. |
| G5 | Pipeline test coverage | `uv run pytest --cov=src --cov-fail-under=80` | ≥ 80% line coverage. 0 test failures. |
| G6 | Linting + type checks | `uv run ruff check . && uv run mypy src/` | Zero errors on both. |
| G7 | Skills populated | `SELECT count(*) FROM job_skills` | > 0. |
| G8 | Dedup run | `SELECT count(*) FROM jobs WHERE is_duplicate = TRUE` | > 0. |
| G9 | Salary model trained | Salary model file exists on Modal volume | Model loads and predicts without error. |
| G10 | Companies enriched | `SELECT count(*) FROM companies WHERE enriched_at IS NOT NULL` | > 0. |
| G11 | Cross-encoder functional | Test rerank on 10 queries locally | Returns re-ranked results in < 2 seconds. |
| G12 | RLS: user_profiles | Query as anon: `SELECT * FROM user_profiles` | Returns 0 rows. |
| G13 | Performance baseline | `EXPLAIN ANALYZE SELECT * FROM search_jobs_v2(query_text := 'developer')` | P95 < 80ms for DB query. Total pipeline < 3s. |

### 3.2 Production Deployment

| # | Step | Command | Verification |
|---|---|---|---|
| G14 | Push migrations | `supabase db push` | No errors. New tables/functions exist. |
| G15 | Deploy Modal | `modal deploy pipeline/src/modal_app.py` | All cron functions + search endpoint visible. |
| G16 | Update secrets | `modal secret update atoz-env` with new keys | `COMPANIES_HOUSE_API_KEY` present. |
| G17 | Seed ESCO | `modal run src/modal_app.py::seed_esco` | `esco_skills` table has ≥ 13,000 rows. |
| G18 | Backfill skills | `modal run src/modal_app.py::backfill_job_skills` | `job_skills` rows created for existing ready jobs. |
| G19 | Run dedup | `modal run src/modal_app.py::backfill_dedup` | Duplicates flagged. `is_duplicate = TRUE` count > 0. |
| G20 | Train salary model | `modal run src/modal_app.py::train_salary_model` | Model trained. MAE logged. |
| G21 | Enrich companies | `modal run src/modal_app.py::enrich_companies` | Companies enriched with SIC codes. |
| G22 | Predict salaries | `modal run src/modal_app.py::predict_salaries` | Missing salaries filled. `salary_predicted_max` count > 0. |
| G23 | Search endpoint live | `curl -X POST https://<modal-url>/search -d '{"query":"developer"}'` | Returns JSON results with latency < 3s. |

### 3.3 Post-Deployment Monitoring (First 24 Hours)

| # | Alert condition | Threshold | Action |
|---|---|---|---|
| G24 | Cross-encoder latency | P95 > 2 seconds per search | Check Modal container warmth. Check model loading time. Consider pre-warming. |
| G25 | Dedup false positives | User reports (or manual check) shows non-duplicates flagged | Raise composite threshold from 0.65 to 0.70. Review title similarity threshold. |
| G26 | Salary prediction outliers | Predicted salary < £15K or > £300K | Check feature engineering. Check model version. Retrain if needed. |
| G27 | Companies House 429s | > 10 rate limit errors in 1 hour | Reduce request rate. Check if concurrent jobs running. |
| G28 | Skills extraction failures | > 5% of new jobs fail skill extraction | Check SpaCy model availability. Check Modal image. |
| G29 | MV refresh failures | `SELECT * FROM cron.job WHERE jobname LIKE 'refresh%'` shows failed | Check pg_cron logs. Run manual `REFRESH MATERIALIZED VIEW CONCURRENTLY`. |
| G30 | Phase 1 pipeline health | `SELECT * FROM pipeline_health` | All Phase 1 metrics still healthy. No regression. |

**Decision point:** If G24–G30 are all clear after 24 hours, Phase 2 is **production-stable**. Tag `v0.2.0` and begin Phase 3 planning.

---

## 4. Rollback Procedures

### 4.1 Migration Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| Bad migration (pre-production) | Run `down.sql` for failed migration. Fix. Re-apply. `supabase db reset` must pass. | < 15 min |
| Bad migration (production) | `supabase db push` the corrected migration. If irreversible, PITR restore. | < 30 min |
| Phase 2 migration breaks Phase 1 | Roll back all Phase 2 migrations (010, 009, 008, 007 down.sql in order). Phase 1 functions still work. | < 30 min |

### 4.2 Component Rollback

| Scenario | Recovery | Estimated RTO |
|---|---|---|
| SpaCy model corrupt/missing | Re-download `en_core_web_sm` in Modal image. Fall back to Phase 1 regex matcher. | < 30 min |
| XGBoost model corrupt | Retrain from scratch (`modal run train_salary_model`). Set `salary_predicted_*` to NULL for affected jobs. | < 1 hour |
| Cross-encoder unavailable | Graceful degradation built in: search returns RRF results without re-ranking. | 0 (automatic) |
| Companies House API down | Enrichment paused. No impact on search. Resume when API recovers. | 0 (wait) |
| Dedup false positives (bad batch) | `UPDATE jobs SET is_duplicate = FALSE, canonical_id = NULL WHERE duplicate_score < 0.70` | < 15 min |

### 4.3 Full Phase 2 Rollback

If Phase 2 causes unrecoverable issues:

```bash
# 1. Disable Phase 2 cron jobs
SELECT cron.unschedule('refresh-skill-demand');
SELECT cron.unschedule('refresh-skill-cooccurrence');

# 2. Switch search back to Phase 1 function
# (search_jobs() still exists, unchanged)

# 3. Roll back migrations in reverse order
psql $DATABASE_URL < supabase/migrations/010_user_profiles_search_v2/down.sql
psql $DATABASE_URL < supabase/migrations/009_salary_company/down.sql
psql $DATABASE_URL < supabase/migrations/008_advanced_dedup/down.sql
psql $DATABASE_URL < supabase/migrations/007_skills_taxonomy/down.sql

# 4. Re-deploy Phase 1 Modal image
git checkout v0.1.0 -- pipeline/src/modal_app.py
cd pipeline && modal deploy src/modal_app.py

# 5. Verify Phase 1 still works
SELECT * FROM search_jobs(query_text := 'developer');
SELECT * FROM pipeline_health;
```

**RTO for full rollback: < 1 hour.** Zero data loss — Phase 1 data and functions are untouched.

---

## 5. Performance SLAs

These targets apply from the moment Phase 2 reaches production.

| # | Metric | Target | Alert threshold | How to measure | When to act |
|---|---|---|---|---|---|
| S1 | `search_jobs_v2()` P95 | < 80ms | > 150ms | `EXPLAIN ANALYZE` + `pg_stat_statements` | Check indexes. Check duplicate exclusion performance. Run `VACUUM ANALYZE`. |
| S2 | Cross-encoder re-rank (50 pairs) | < 500ms | > 1000ms | structlog timing in Modal | Check model loading. Check CPU allocation. Consider reducing to top 30. |
| S3 | Full search pipeline (query → results) | < 3s | > 5s | End-to-end timing in search orchestrator | Check each stage independently. Check cross-encoder latency. |
| S4 | Skill extraction throughput | ≥ 5,000 jobs/min | < 2,000 jobs/min | structlog timing in Modal | Check SpaCy model. Check Modal cold starts. |
| S5 | Dedup scan (new jobs daily) | < 30 min for 5K jobs | > 1 hour | Modal function duration | Check pg_trgm index health. Reduce candidate window. |
| S6 | Companies House enrichment | ≤ 2 req/sec sustained | > 5 429 errors/hour | structlog timing | Reduce request rate. Add jitter. |
| S7 | Salary model training | < 10 min on 100K jobs | > 30 min | Modal function duration | Check feature count. Reduce XGBoost rounds. |
| S8 | MV refresh (daily) | < 5 min each | > 15 min | pg_cron job duration | Check table sizes. Add more indexes on job_skills. |
| S9 | User profile embedding | < 2s per profile update | > 5s | API response timing | Check Gemini API status. Pre-compute templates. |

---

## 6. Error Taxonomy (Phase 2 Additions)

| Error type | Retry? | Max retries | Backoff | Gate impact |
|---|---|---|---|---|
| `SkillExtractionError` | Yes | 2 | 1s fixed | SpaCy model issue. Retry, then fall back to Phase 1 regex matcher. |
| `FuzzyDedupError` | Yes | 2 | 2^n seconds | pg_trgm query issue. Retry. Skip job if persistent. |
| `MinHashError` | No | 0 | N/A | Data issue. Skip MinHash for this job. Log for investigation. |
| `SalaryPredictionError` | No | 0 | N/A | Model issue. Leave salary unpredicted. Retrain model. |
| `CompaniesHouseRateLimitError` | Yes | 3 | `Retry-After` or 60s | Back off. Resume in next batch. |
| `CompaniesHouseNotFoundError` | No | 0 | N/A | Company not in CH. Set `enriched_at` to prevent re-querying. |
| `CrossEncoderError` | No | 0 | N/A | Return RRF results without re-ranking. Graceful degradation. |
| `ProfileEmbeddingError` | Yes | 2 | 2^n seconds | Gemini API issue. Retry, then return search without profile personalization. |

---

## 7. Phase 2 Completion Criteria

Phase 2 is **complete** when ALL of the following are true:

- [ ] All 16 Gate 1 (Skills) checks pass
- [ ] All 16 Gate 2 (Dedup) checks pass
- [ ] All 18 Gate 3 (Salary & Enrichment) checks pass
- [ ] All 18 Gate 4 (Re-ranking) checks pass
- [ ] All 15 test search queries execute without error
- [ ] All 23 go/no-go items (G1–G23) pass
- [ ] 24-hour monitoring (G24–G30) shows no critical alerts
- [ ] All 9 performance SLAs meet target thresholds
- [ ] Git tag `v0.2.0` applied to `main` branch
- [ ] `STATUS.md` updated with Phase 2 completion date and metrics
- [ ] CLAUDE.md updated with Phase 2 additions

**Total verification items: 68 gate checks + 15 queries + 30 go/no-go items + 9 SLAs = 122 verifiable items.**

When all 122 items pass: **Phase 2 is production-stable. Begin Phase 3 (Display) planning.**
