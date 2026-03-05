-- Migration 005: Row-Level Security

ALTER TABLE jobs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources    ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies  ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills     ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skills ENABLE ROW LEVEL SECURITY;

-- Public read: anyone can read ready jobs (anon key)
CREATE POLICY "Public can read ready jobs"
    ON jobs FOR SELECT USING (status = 'ready');

-- Service role: pipeline can read/write everything (service_role key)
CREATE POLICY "Service role full access to jobs"
    ON jobs FOR ALL USING (auth.role() = 'service_role');

-- Public read: reference tables
CREATE POLICY "Public can read sources"    ON sources    FOR SELECT USING (true);
CREATE POLICY "Public can read companies"  ON companies  FOR SELECT USING (true);
CREATE POLICY "Public can read skills"     ON skills     FOR SELECT USING (true);
CREATE POLICY "Public can read job_skills" ON job_skills FOR SELECT USING (true);

-- Service role write: reference tables
CREATE POLICY "Service role writes sources"    ON sources    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes companies"  ON companies  FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes skills"     ON skills     FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role writes job_skills" ON job_skills FOR ALL USING (auth.role() = 'service_role');
