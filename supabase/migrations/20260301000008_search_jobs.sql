-- Migration 008: search_jobs() hybrid search function (SPEC.md §5)
-- Combines FTS + semantic search via RRF (Reciprocal Rank Fusion, k=50).
-- Pre-filter CTE eliminates geographically distant jobs before expensive vector search.

CREATE OR REPLACE FUNCTION search_jobs(
    query_text       TEXT DEFAULT NULL,
    query_embedding  HALFVEC(768) DEFAULT NULL,
    search_lat       FLOAT DEFAULT NULL,
    search_lng       FLOAT DEFAULT NULL,
    radius_miles     FLOAT DEFAULT 25,
    include_remote   BOOLEAN DEFAULT TRUE,
    min_salary       INT DEFAULT NULL,
    work_type_filter TEXT DEFAULT NULL,
    match_count      INT DEFAULT 20,
    rrf_k            INT DEFAULT 50
)
RETURNS TABLE (id BIGINT, title TEXT, company TEXT, rrf_score FLOAT)
LANGUAGE sql AS $$
-- NOTE: Using <=> (cosine distance) with halfvec_cosine_ops index.
-- Mathematically equivalent to <#> (inner product) for normalized vectors.
-- All embeddings are re-normalized after Matryoshka dimension reduction.
WITH filtered AS (
    SELECT j.id FROM jobs j
    WHERE j.status = 'ready'
      AND (include_remote AND j.location_type IN ('remote','nationwide')
        OR j.location_type IN ('onsite','hybrid')
          AND (search_lat IS NULL OR ST_DWithin(j.location,
            ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
            radius_miles * 1609.344)))
      AND (min_salary IS NULL OR j.salary_annual_max >= min_salary)
      AND (work_type_filter IS NULL OR work_type_filter = ANY(j.employment_type))
),
fts AS (
    SELECT f.id, ROW_NUMBER() OVER(
        ORDER BY ts_rank_cd(j.search_vector, websearch_to_tsquery(query_text)) DESC
    ) AS rank FROM filtered f JOIN jobs j ON j.id = f.id
    WHERE query_text IS NOT NULL
      AND j.search_vector @@ websearch_to_tsquery(query_text)
    LIMIT match_count * 2
),
semantic AS (
    SELECT f.id, ROW_NUMBER() OVER(
        ORDER BY j.embedding <=> query_embedding
    ) AS rank FROM filtered f JOIN jobs j ON j.id = f.id
    WHERE query_embedding IS NOT NULL AND j.embedding IS NOT NULL
    LIMIT match_count * 2
)
SELECT j.id, j.title, j.company_name,
    COALESCE(1.0/(rrf_k + fts.rank), 0)
  + COALESCE(1.0/(rrf_k + semantic.rank), 0) AS rrf_score
FROM fts FULL OUTER JOIN semantic ON fts.id = semantic.id
JOIN jobs j ON j.id = COALESCE(fts.id, semantic.id)
ORDER BY rrf_score DESC LIMIT match_count;
$$;
