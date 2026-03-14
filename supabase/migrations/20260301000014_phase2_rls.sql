-- Migration 014: Phase 2 RLS Policies
-- Adds Row-Level Security to esco_skills and sic_industry_map tables
-- Pattern: two-tier RLS (public read, service role write) per Migration 005

-- esco_skills: ESCO taxonomy reference table (read-only for public)
ALTER TABLE esco_skills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read esco_skills"
    ON esco_skills FOR SELECT USING (true);

CREATE POLICY "Service role writes esco_skills"
    ON esco_skills FOR ALL USING (auth.role() = 'service_role');

-- sic_industry_map: SIC code → industry section mapping (read-only for public)
ALTER TABLE sic_industry_map ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read sic_industry_map"
    ON sic_industry_map FOR SELECT USING (true);

CREATE POLICY "Service role writes sic_industry_map"
    ON sic_industry_map FOR ALL USING (auth.role() = 'service_role');
