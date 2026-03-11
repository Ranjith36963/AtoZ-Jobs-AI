-- Rollback Migration 014: Phase 2 RLS Policies

DROP POLICY IF EXISTS "Service role writes sic_industry_map" ON sic_industry_map;
DROP POLICY IF EXISTS "Public can read sic_industry_map" ON sic_industry_map;
ALTER TABLE sic_industry_map DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role writes esco_skills" ON esco_skills;
DROP POLICY IF EXISTS "Public can read esco_skills" ON esco_skills;
ALTER TABLE esco_skills DISABLE ROW LEVEL SECURITY;
