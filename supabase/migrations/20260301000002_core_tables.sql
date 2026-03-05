-- Migration 002: Core tables

CREATE TABLE sources (
    id          SMALLINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL UNIQUE,
    api_base_url TEXT,
    is_active   BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    config      JSONB DEFAULT '{}'
);

CREATE TABLE companies (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    website         TEXT,
    industry        TEXT,
    company_size    TEXT,
    sic_code        TEXT,
    metadata        JSONB DEFAULT '{}'
);

CREATE TABLE jobs (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source_id       SMALLINT NOT NULL REFERENCES sources(id),
    external_id     TEXT NOT NULL,
    source_url      TEXT NOT NULL,

    -- Core fields (schema.org/JobPosting aligned)
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    description_plain TEXT,
    company_id      BIGINT REFERENCES companies(id),
    company_name    TEXT NOT NULL,

    -- Location
    location_raw    TEXT,
    location_city   TEXT,
    location_region TEXT,
    location_postcode TEXT,
    location_type   TEXT DEFAULT 'onsite',  -- 'onsite','remote','hybrid','nationwide'
    location        GEOGRAPHY(POINT, 4326),

    -- Employment
    employment_type TEXT[],                 -- '{full_time,permanent}'
    seniority_level TEXT,
    visa_sponsorship TEXT,                  -- 'yes','no','unknown'

    -- Salary (normalized to annual GBP)
    salary_min          NUMERIC(12,2),
    salary_max          NUMERIC(12,2),
    salary_currency     CHAR(3) DEFAULT 'GBP',
    salary_period       TEXT DEFAULT 'annual',
    salary_raw          TEXT,
    salary_annual_min   NUMERIC(12,2),
    salary_annual_max   NUMERIC(12,2),
    salary_is_predicted BOOLEAN DEFAULT FALSE,

    -- Classification
    category            TEXT,
    soc_code            TEXT,
    esco_occupation_uri TEXT,

    -- Dates
    date_posted     TIMESTAMPTZ NOT NULL,
    date_expires    TIMESTAMPTZ,
    date_crawled    TIMESTAMPTZ DEFAULT now(),

    -- Processing state
    status          TEXT DEFAULT 'raw',
    -- Valid values: raw, parsed, normalized, geocoded, embedded, ready, expired, archived
    retry_count     INT DEFAULT 0,
    last_error      TEXT,

    -- Search infrastructure
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title,'')), 'A') ||
        setweight(to_tsvector('english', coalesce(company_name,'')), 'B') ||
        setweight(to_tsvector('english', coalesce(description_plain,'')), 'C')
    ) STORED,
    embedding       HALFVEC(768),

    -- Deduplication
    content_hash    TEXT,

    -- Raw preservation
    raw_data        JSONB,

    UNIQUE(source_id, external_id)
);

CREATE TABLE skills (
    id          INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        TEXT NOT NULL UNIQUE,
    esco_uri    TEXT,
    lightcast_id TEXT,
    skill_type  TEXT,        -- 'hard','soft','knowledge'
    category    TEXT
);

CREATE TABLE job_skills (
    job_id      BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id    INT REFERENCES skills(id),
    confidence  FLOAT,
    is_required BOOLEAN DEFAULT true,
    PRIMARY KEY (job_id, skill_id)
);
