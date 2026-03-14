-- Rollback Migration 013: User profiles and search_jobs_v2

DROP FUNCTION IF EXISTS search_jobs_v2;

DROP INDEX IF EXISTS idx_user_profiles_embedding;

DROP POLICY IF EXISTS "Service role full access to profiles" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can read own profile" ON user_profiles;

DROP TABLE IF EXISTS user_profiles;
