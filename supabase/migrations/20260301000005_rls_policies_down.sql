-- Rollback Migration 005: Row-Level Security

DROP POLICY IF EXISTS "Service role writes job_skills" ON job_skills;
DROP POLICY IF EXISTS "Service role writes skills"     ON skills;
DROP POLICY IF EXISTS "Service role writes companies"  ON companies;
DROP POLICY IF EXISTS "Service role writes sources"    ON sources;

DROP POLICY IF EXISTS "Public can read job_skills" ON job_skills;
DROP POLICY IF EXISTS "Public can read skills"     ON skills;
DROP POLICY IF EXISTS "Public can read companies"  ON companies;
DROP POLICY IF EXISTS "Public can read sources"    ON sources;

DROP POLICY IF EXISTS "Service role full access to jobs" ON jobs;
DROP POLICY IF EXISTS "Public can read ready jobs"       ON jobs;

ALTER TABLE job_skills DISABLE ROW LEVEL SECURITY;
ALTER TABLE skills     DISABLE ROW LEVEL SECURITY;
ALTER TABLE companies  DISABLE ROW LEVEL SECURITY;
ALTER TABLE sources    DISABLE ROW LEVEL SECURITY;
ALTER TABLE jobs       DISABLE ROW LEVEL SECURITY;
