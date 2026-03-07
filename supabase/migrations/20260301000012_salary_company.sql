-- Migration 012: Salary Prediction & Company Enrichment (Phase 2, Stage 3)

-- Salary prediction columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_predicted_min NUMERIC(12,2);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_predicted_max NUMERIC(12,2);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_confidence FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_model_version TEXT;

-- Company enrichment columns
ALTER TABLE companies ADD COLUMN IF NOT EXISTS companies_house_number TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS sic_codes TEXT[];
ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_status TEXT;     -- 'active','dissolved', etc.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS date_of_creation DATE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS registered_address JSONB;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

CREATE INDEX idx_companies_house_number ON companies(companies_house_number)
    WHERE companies_house_number IS NOT NULL;

-- SIC code to industry category mapping table
CREATE TABLE sic_industry_map (
    sic_section  CHAR(1) PRIMARY KEY,  -- A-U
    sic_label    TEXT NOT NULL,
    internal_category TEXT NOT NULL     -- maps to our category taxonomy
);

-- Seed SIC sections → internal categories
INSERT INTO sic_industry_map (sic_section, sic_label, internal_category) VALUES
    ('A', 'Agriculture, Forestry and Fishing', 'Agriculture'),
    ('B', 'Mining and Quarrying', 'Energy & Utilities'),
    ('C', 'Manufacturing', 'Manufacturing'),
    ('D', 'Electricity, Gas, Steam', 'Energy & Utilities'),
    ('E', 'Water Supply, Sewerage', 'Energy & Utilities'),
    ('F', 'Construction', 'Construction'),
    ('G', 'Wholesale and Retail Trade', 'Retail'),
    ('H', 'Transportation and Storage', 'Logistics & Transport'),
    ('I', 'Accommodation and Food Service', 'Hospitality'),
    ('J', 'Information and Communication', 'Technology'),
    ('K', 'Financial and Insurance', 'Finance'),
    ('L', 'Real Estate Activities', 'Property'),
    ('M', 'Professional, Scientific and Technical', 'Professional Services'),
    ('N', 'Administrative and Support Service', 'Administration'),
    ('O', 'Public Administration and Defence', 'Public Sector'),
    ('P', 'Education', 'Education'),
    ('Q', 'Human Health and Social Work', 'Healthcare'),
    ('R', 'Arts, Entertainment and Recreation', 'Creative & Media'),
    ('S', 'Other Service Activities', 'Other'),
    ('T', 'Households as Employers', 'Other'),
    ('U', 'Extraterritorial Organisations', 'Other');
