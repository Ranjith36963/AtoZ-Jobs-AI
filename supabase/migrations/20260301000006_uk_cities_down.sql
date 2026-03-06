-- Rollback Migration 006: UK cities reference table

DROP INDEX IF EXISTS idx_uk_cities_name;
DROP TABLE IF EXISTS uk_cities;
