-- Migration 006: UK cities reference table (geocoding fallback)
-- See SPEC.md §3.4: "Pre-populated table of ~100 UK cities with coordinates"

CREATE TABLE uk_cities (
    id          INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    population  INT,
    UNIQUE(name, region)
);

CREATE INDEX idx_uk_cities_name ON uk_cities USING gin(name gin_trgm_ops);
