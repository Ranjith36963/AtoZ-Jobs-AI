"""Tests for enrichment orchestrator (SPEC.md §5.2)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEnrichCompanies:
    """Company enrichment flow tests."""

    @pytest.mark.asyncio
    async def test_enriches_single_company(self) -> None:
        """Enriches a company with Companies House data."""
        from src.enrichment.orchestrator import enrich_companies

        mock_db = MagicMock()
        # Query returns one unenriched company
        mock_db.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "name": "Goldman Sachs International"}
        ]
        # Update call
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "src.enrichment.orchestrator.search_company", new_callable=AsyncMock
            ) as mock_search,
            patch(
                "src.enrichment.orchestrator.get_company_profile",
                new_callable=AsyncMock,
            ) as mock_profile,
        ):
            mock_search.return_value = {
                "company_number": "02263951",
                "title": "GOLDMAN SACHS INTERNATIONAL",
            }
            mock_profile.return_value = {
                "company_number": "02263951",
                "company_name": "GOLDMAN SACHS INTERNATIONAL",
                "sic_codes": ["64110"],
                "company_status": "active",
                "date_of_creation": "1988-06-09",
                "registered_office_address": {
                    "address_line_1": "Plumtree Court",
                    "locality": "London",
                    "postal_code": "EC4A 4HN",
                },
            }

            result = await enrich_companies(
                db_client=mock_db,
                api_key="test_key",
                batch_size=10,
            )

        assert result["enriched"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_handles_no_match(self) -> None:
        """Company not found on Companies House → skipped."""
        from src.enrichment.orchestrator import enrich_companies

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "name": "Totally Fake Company XYZ"}
        ]

        with patch(
            "src.enrichment.orchestrator.search_company", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = None

            result = await enrich_companies(
                db_client=mock_db,
                api_key="test_key",
                batch_size=10,
            )

        assert result["enriched"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_handles_empty_batch(self) -> None:
        """No unenriched companies → zero stats."""
        from src.enrichment.orchestrator import enrich_companies

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value.data = []

        result = await enrich_companies(
            db_client=mock_db,
            api_key="test_key",
            batch_size=10,
        )

        assert result["enriched"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_handles_api_error(self) -> None:
        """API error during search → counted as failed."""
        from src.enrichment.orchestrator import enrich_companies

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "name": "Error Corp"}
        ]

        with patch(
            "src.enrichment.orchestrator.search_company", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = Exception("API timeout")

            result = await enrich_companies(
                db_client=mock_db,
                api_key="test_key",
                batch_size=10,
            )

        assert result["failed"] == 1
        assert result["enriched"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self) -> None:
        """Verifies sleep is called between requests for rate limiting."""
        from src.enrichment.orchestrator import enrich_companies

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "name": "Company A"},
            {"id": 2, "name": "Company B"},
        ]
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "src.enrichment.orchestrator.search_company", new_callable=AsyncMock
            ) as mock_search,
            patch(
                "src.enrichment.orchestrator.get_company_profile",
                new_callable=AsyncMock,
            ) as mock_profile,
            patch(
                "src.enrichment.orchestrator.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
        ):
            mock_search.return_value = {"company_number": "00000001", "title": "TEST"}
            mock_profile.return_value = {
                "company_number": "00000001",
                "sic_codes": ["62020"],
                "company_status": "active",
            }

            await enrich_companies(
                db_client=mock_db,
                api_key="test_key",
                batch_size=10,
            )

        assert mock_sleep.call_count >= 1


class TestPredictMissingSalaries:
    """Salary prediction flow tests."""

    @pytest.mark.asyncio
    async def test_predicts_salaries(self) -> None:
        """Predicts salaries for jobs missing salary data."""
        from src.enrichment.orchestrator import predict_missing_salaries

        mock_db = MagicMock()
        # Jobs without salary
        mock_db.table.return_value.select.return_value.is_.return_value.is_.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": 1,
                "title": "Software Engineer",
                "location_region": "London",
                "category": "IT Jobs",
                "seniority": "Mid",
                "description_plain": "Python developer role",
            },
        ]
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_model = MagicMock()

        with (
            patch("src.enrichment.orchestrator.predict_salary") as mock_predict,
            patch("src.enrichment.orchestrator.build_features") as mock_features,
        ):
            import numpy as np

            mock_features.return_value = (np.array([[1.0, 2.0]]), np.array([45000.0]))
            mock_predict.return_value = [
                {
                    "predicted_min": 40000.0,
                    "predicted_max": 50000.0,
                    "confidence": 0.85,
                    "confidence_label": "HIGH",
                }
            ]

            result = await predict_missing_salaries(
                db_client=mock_db,
                model=mock_model,
                model_version="v1.0",
                batch_size=100,
            )

        assert result["predicted"] == 1

    @pytest.mark.asyncio
    async def test_no_jobs_to_predict(self) -> None:
        """No jobs without salary → zero predictions."""
        from src.enrichment.orchestrator import predict_missing_salaries

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.is_.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        mock_model = MagicMock()

        result = await predict_missing_salaries(
            db_client=mock_db,
            model=mock_model,
            model_version="v1.0",
        )

        assert result["predicted"] == 0

    @pytest.mark.asyncio
    async def test_prediction_error_handled(self) -> None:
        """Feature build failure → counted as failed."""
        from src.enrichment.orchestrator import predict_missing_salaries

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.is_.return_value.is_.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": 1,
                "title": "Engineer",
                "location_region": "London",
                "category": "IT Jobs",
                "seniority": "Mid",
                "description_plain": "Role",
            },
        ]

        mock_model = MagicMock()

        with patch("src.enrichment.orchestrator.build_features") as mock_features:
            mock_features.side_effect = ValueError("Not enough data")

            result = await predict_missing_salaries(
                db_client=mock_db,
                model=mock_model,
                model_version="v1.0",
            )

        assert result["failed"] >= 1
