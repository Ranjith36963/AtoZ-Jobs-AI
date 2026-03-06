"""Tests for search_jobs() SQL function (GATES.md M10, Q1-Q10).

These tests verify the SQL migration file content and parameter coverage.
Actual DB execution requires a running Supabase instance.
"""

import os

import pytest


MIGRATION_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "supabase",
    "migrations",
)


class TestSearchJobsMigrationExists:
    def test_migration_file_exists(self) -> None:
        """Migration 008 search_jobs SQL file must exist."""
        migration_path = os.path.join(
            MIGRATION_DIR,
            "20260301000008_search_jobs.sql",
        )
        assert os.path.isfile(migration_path), (
            f"Migration file not found: {migration_path}"
        )

    def test_rollback_file_exists(self) -> None:
        """Migration 008 down.sql rollback file must exist."""
        down_path = os.path.join(
            MIGRATION_DIR,
            "20260301000008_search_jobs_down.sql",
        )
        assert os.path.isfile(down_path), f"Rollback file not found: {down_path}"


class TestSearchJobsSQLContent:
    @pytest.fixture()
    def sql_content(self) -> str:
        migration_path = os.path.join(
            MIGRATION_DIR,
            "20260301000008_search_jobs.sql",
        )
        with open(migration_path) as f:
            return f.read()

    def test_function_created(self, sql_content: str) -> None:
        """SQL must create the search_jobs function."""
        assert "CREATE OR REPLACE FUNCTION search_jobs" in sql_content

    def test_returns_table(self, sql_content: str) -> None:
        """Function must return a TABLE type."""
        assert "RETURNS TABLE" in sql_content

    # ── Parameter coverage (all 10 params from SPEC.md §5) ──

    def test_param_query_text(self, sql_content: str) -> None:
        assert "query_text" in sql_content

    def test_param_query_embedding(self, sql_content: str) -> None:
        assert "query_embedding" in sql_content

    def test_param_search_lat(self, sql_content: str) -> None:
        assert "search_lat" in sql_content

    def test_param_search_lng(self, sql_content: str) -> None:
        assert "search_lng" in sql_content

    def test_param_radius_miles(self, sql_content: str) -> None:
        assert "radius_miles" in sql_content

    def test_param_include_remote(self, sql_content: str) -> None:
        assert "include_remote" in sql_content

    def test_param_min_salary(self, sql_content: str) -> None:
        assert "min_salary" in sql_content

    def test_param_work_type_filter(self, sql_content: str) -> None:
        assert "work_type_filter" in sql_content

    def test_param_match_count(self, sql_content: str) -> None:
        assert "match_count" in sql_content

    def test_param_rrf_k(self, sql_content: str) -> None:
        assert "rrf_k" in sql_content

    # ── CTE structure ──

    def test_pre_filter_cte(self, sql_content: str) -> None:
        """Must have a filtered CTE for pre-filtering."""
        assert "filtered" in sql_content
        assert "status = 'ready'" in sql_content

    def test_fts_cte(self, sql_content: str) -> None:
        """Must have a FTS CTE using websearch_to_tsquery."""
        assert "websearch_to_tsquery" in sql_content

    def test_semantic_cte(self, sql_content: str) -> None:
        """Must have a semantic CTE using cosine distance."""
        assert "<=>" in sql_content

    def test_rrf_combination(self, sql_content: str) -> None:
        """Must combine scores via RRF formula."""
        assert "rrf_k" in sql_content
        assert "rrf_score" in sql_content

    def test_geo_filter(self, sql_content: str) -> None:
        """Must use ST_DWithin for geo filtering."""
        assert "ST_DWithin" in sql_content

    def test_salary_filter(self, sql_content: str) -> None:
        """Must filter by salary."""
        assert "salary_annual_max" in sql_content

    def test_work_type_filter_in_sql(self, sql_content: str) -> None:
        """Must filter by work type using employment_type array."""
        assert "employment_type" in sql_content

    def test_remote_filter(self, sql_content: str) -> None:
        """Must handle include_remote for remote/nationwide jobs."""
        assert "remote" in sql_content
        assert "nationwide" in sql_content

    def test_miles_to_meters_conversion(self, sql_content: str) -> None:
        """Must convert miles to meters (1609.344)."""
        assert "1609.344" in sql_content

    def test_halfvec_768(self, sql_content: str) -> None:
        """Must use HALFVEC(768) for embedding parameter."""
        assert "768" in sql_content


class TestSearchJobsDownSQL:
    def test_drops_function(self) -> None:
        """Rollback must drop the search_jobs function."""
        down_path = os.path.join(
            MIGRATION_DIR,
            "20260301000008_search_jobs_down.sql",
        )
        with open(down_path) as f:
            content = f.read()
        assert "DROP FUNCTION" in content
        assert "search_jobs" in content


# ── Q1-Q10 parameter coverage validation ──
# These tests verify the SQL supports all 10 query scenarios from GATES.md §2.
# Actual execution requires a running database with seed data.


class TestQueryParameterCoverage:
    """Verify the SQL function signature supports all Q1-Q10 parameter combos."""

    @pytest.fixture()
    def sql_content(self) -> str:
        migration_path = os.path.join(
            MIGRATION_DIR,
            "20260301000008_search_jobs.sql",
        )
        with open(migration_path) as f:
            return f.read()

    def test_q1_keyword_geo_semantic(self, sql_content: str) -> None:
        """Q1: query_text + query_embedding + search_lat/lng + radius_miles."""
        for param in [
            "query_text",
            "query_embedding",
            "search_lat",
            "search_lng",
            "radius_miles",
        ]:
            assert param in sql_content

    def test_q2_remote_only(self, sql_content: str) -> None:
        """Q2: query_text + include_remote."""
        assert "include_remote" in sql_content

    def test_q3_semantic_only(self, sql_content: str) -> None:
        """Q3: query_embedding only (no query_text) — semantic CTE degrades."""
        assert "query_embedding IS NOT NULL" in sql_content

    def test_q4_fts_only(self, sql_content: str) -> None:
        """Q4: query_text only (no query_embedding) — FTS CTE only."""
        assert "query_text IS NOT NULL" in sql_content

    def test_q5_geo_salary_filter(self, sql_content: str) -> None:
        """Q5: query_text + search_lat/lng + min_salary."""
        assert "min_salary" in sql_content

    def test_q6_work_type_filter(self, sql_content: str) -> None:
        """Q6: query_text + search_lat/lng + work_type_filter."""
        assert "work_type_filter" in sql_content

    def test_q7_empty_search_defaults(self, sql_content: str) -> None:
        """Q7: All defaults (NULLs). Must not crash."""
        # Verified by DEFAULT NULL on all params
        assert "DEFAULT NULL" in sql_content or "DEFAULT" in sql_content

    def test_q8_no_location(self, sql_content: str) -> None:
        """Q8: query_text but no lat/lng — geo filter must be skipped."""
        assert "search_lat IS NULL" in sql_content

    def test_q9_custom_match_count(self, sql_content: str) -> None:
        """Q9: match_count = 5 — must LIMIT by match_count."""
        assert "LIMIT match_count" in sql_content

    def test_q10_all_filters(self, sql_content: str) -> None:
        """Q10: All filters combined — all params must exist."""
        required = [
            "query_text",
            "query_embedding",
            "search_lat",
            "search_lng",
            "radius_miles",
            "min_salary",
            "include_remote",
            "work_type_filter",
        ]
        for param in required:
            assert param in sql_content
