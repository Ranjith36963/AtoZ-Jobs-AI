-- Rollback Migration 012: Salary Prediction & Company Enrichment

DROP TABLE IF EXISTS sic_industry_map;
DROP INDEX IF EXISTS idx_companies_house_number;
ALTER TABLE companies DROP COLUMN IF EXISTS enriched_at;
ALTER TABLE companies DROP COLUMN IF EXISTS registered_address;
ALTER TABLE companies DROP COLUMN IF EXISTS date_of_creation;
ALTER TABLE companies DROP COLUMN IF EXISTS company_status;
ALTER TABLE companies DROP COLUMN IF EXISTS sic_codes;
ALTER TABLE companies DROP COLUMN IF EXISTS companies_house_number;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_model_version;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_confidence;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_predicted_max;
ALTER TABLE jobs DROP COLUMN IF EXISTS salary_predicted_min;
