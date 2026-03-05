-- Rollback Migration 007: RLS for uk_cities

DROP POLICY IF EXISTS "Service role writes uk_cities" ON uk_cities;
DROP POLICY IF EXISTS "Public can read uk_cities" ON uk_cities;
ALTER TABLE uk_cities DISABLE ROW LEVEL SECURITY;
