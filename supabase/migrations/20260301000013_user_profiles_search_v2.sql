-- Migration 013: User profiles and search_jobs_v2 (SPEC.md §2.4, §6)
-- Adds user_profiles table with RLS and search_jobs_v2() with expanded filters.

-- User profiles table for search personalization
CREATE TABLE IF NOT EXISTS user_profiles (
    id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    target_role         TEXT,
    skills              TEXT[],
    experience_text     TEXT,
    preferred_location  TEXT,
    preferred_lat       FLOAT,
    preferred_lng       FLOAT,
    work_preference     TEXT CHECK (work_preference IN ('remote', 'hybrid', 'onsite', 'any')),
    min_salary          INT,
    profile_embedding   HALFVEC(768),
    profile_text        TEXT,
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- RLS policies
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

-- Index for profile embedding similarity search
CREATE INDEX IF NOT EXISTS idx_user_profiles_embedding
    ON user_profiles USING hnsw (profile_embedding halfvec_cosine_ops);

-- search_jobs_v2: expanded filters, duplicate exclusion, skill filters, predicted salary
CREATE OR REPLACE FUNCTION search_jobs_v2(
    query_text          TEXT DEFAULT NULL,
    query_embedding     HALFVEC(768) DEFAULT NULL,
    search_lat          FLOAT DEFAULT NULL,
    search_lng          FLOAT DEFAULT NULL,
    radius_miles        FLOAT DEFAULT 25,
    include_remote      BOOLEAN DEFAULT TRUE,
    min_salary          INT DEFAULT NULL,
    max_salary          INT DEFAULT NULL,
    work_type_filter    TEXT DEFAULT NULL,
    category_filter     TEXT DEFAULT NULL,
    skill_filters       TEXT[] DEFAULT NULL,
    exclude_duplicates  BOOLEAN DEFAULT TRUE,
    match_count         INT DEFAULT 50,
    rrf_k               INT DEFAULT 50
)
RETURNS TABLE (
    id                  BIGINT,
    title               TEXT,
    company_name        TEXT,
    description_plain   TEXT,
    location_city       TEXT,
    location_region     TEXT,
    location_type       TEXT,
    salary_annual_min   NUMERIC,
    salary_annual_max   NUMERIC,
    salary_predicted_min NUMERIC,
    salary_predicted_max NUMERIC,
    salary_is_predicted BOOLEAN,
    employment_type     TEXT[],
    seniority_level     TEXT,
    category            TEXT,
    date_posted         TIMESTAMPTZ,
    source_url          TEXT,
    rrf_score           FLOAT
)
LANGUAGE sql STABLE AS $$
WITH filtered AS (
    SELECT j.id FROM jobs j
    WHERE j.status = 'ready'
      AND (NOT exclude_duplicates OR j.is_duplicate IS NOT TRUE)
      AND (
          (include_remote AND j.location_type IN ('remote', 'nationwide'))
          OR j.location_type IN ('onsite', 'hybrid')
             AND (search_lat IS NULL OR ST_DWithin(
                j.location,
                ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
                radius_miles * 1609.344
             ))
          OR search_lat IS NULL
      )
      AND (min_salary IS NULL
           OR COALESCE(j.salary_annual_max, j.salary_predicted_max) >= min_salary)
      AND (max_salary IS NULL
           OR COALESCE(j.salary_annual_min, j.salary_predicted_min) <= max_salary)
      AND (work_type_filter IS NULL OR work_type_filter = ANY(j.employment_type))
      AND (category_filter IS NULL OR j.category = category_filter)
      AND (skill_filters IS NULL OR EXISTS (
          SELECT 1 FROM job_skills js
          JOIN skills s ON s.id = js.skill_id
          WHERE js.job_id = j.id AND s.name = ANY(skill_filters)
      ))
),
fts AS (
    SELECT f.id,
           ROW_NUMBER() OVER (
               ORDER BY ts_rank_cd(j.search_vector, websearch_to_tsquery(query_text)) DESC
           ) AS rank
    FROM filtered f
    JOIN jobs j ON j.id = f.id
    WHERE query_text IS NOT NULL
      AND j.search_vector @@ websearch_to_tsquery(query_text)
    LIMIT match_count * 2
),
semantic AS (
    SELECT f.id,
           ROW_NUMBER() OVER (
               ORDER BY j.embedding <=> query_embedding
           ) AS rank
    FROM filtered f
    JOIN jobs j ON j.id = f.id
    WHERE query_embedding IS NOT NULL
      AND j.embedding IS NOT NULL
    LIMIT match_count * 2
)
SELECT
    j.id,
    j.title,
    j.company_name,
    j.description_plain,
    j.location_city,
    j.location_region,
    j.location_type,
    j.salary_annual_min,
    j.salary_annual_max,
    j.salary_predicted_min,
    j.salary_predicted_max,
    (j.salary_predicted_max IS NOT NULL AND j.salary_annual_max IS NULL) AS salary_is_predicted,
    j.employment_type,
    j.seniority_level,
    j.category,
    j.date_posted,
    j.source_url,
    COALESCE(1.0 / (rrf_k + fts.rank), 0)
      + COALESCE(1.0 / (rrf_k + semantic.rank), 0) AS rrf_score
FROM fts
FULL OUTER JOIN semantic ON fts.id = semantic.id
JOIN jobs j ON j.id = COALESCE(fts.id, semantic.id)
ORDER BY rrf_score DESC
LIMIT match_count;
$$;
