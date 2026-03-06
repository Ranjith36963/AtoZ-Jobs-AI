-- Migration 007: RLS for uk_cities reference table

ALTER TABLE uk_cities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read uk_cities" ON uk_cities FOR SELECT USING (true);
CREATE POLICY "Service role writes uk_cities" ON uk_cities FOR ALL USING (auth.role() = 'service_role');
