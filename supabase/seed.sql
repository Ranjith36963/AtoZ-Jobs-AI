-- Tier 1: Reference data (committed to git)

-- Sources
INSERT INTO sources (name, api_base_url, is_active) VALUES
    ('reed',      'https://www.reed.co.uk/api/1.0',            true),
    ('adzuna',    'https://api.adzuna.com/v1/api/jobs/gb',      true),
    ('jooble',    'https://jooble.org/api',                     true),
    ('careerjet', 'https://search.api.careerjet.net/v4',        true);
