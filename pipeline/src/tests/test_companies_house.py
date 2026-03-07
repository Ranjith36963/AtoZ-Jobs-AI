"""Tests for Companies House API client (SPEC.md §5.2, Gates P11-P13)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.enrichment.companies_house import (
    get_company_profile,
    search_company,
    sic_to_section,
)


class TestSicToSection:
    """SIC code → section letter mapping tests."""

    def test_technology(self) -> None:
        """Gate P12: '62020' → 'J' (Information and Communication)."""
        assert sic_to_section("62020") == "J"

    def test_healthcare(self) -> None:
        """Gate P12: '86101' → 'Q' (Human Health)."""
        assert sic_to_section("86101") == "Q"

    def test_retail(self) -> None:
        """Gate P12: '47110' → 'G' (Wholesale and Retail Trade)."""
        assert sic_to_section("47110") == "G"

    def test_finance(self) -> None:
        assert sic_to_section("64110") == "K"

    def test_construction(self) -> None:
        assert sic_to_section("41100") == "F"

    def test_education(self) -> None:
        assert sic_to_section("85100") == "P"

    def test_agriculture(self) -> None:
        assert sic_to_section("01110") == "A"

    def test_manufacturing(self) -> None:
        assert sic_to_section("10110") == "C"

    def test_default_for_empty(self) -> None:
        assert sic_to_section("") == "S"

    def test_default_for_invalid(self) -> None:
        assert sic_to_section("abc") == "S"

    def test_default_for_none_input(self) -> None:
        assert sic_to_section("") == "S"


class TestSearchCompany:
    """Company search tests (mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_search_returns_match(self) -> None:
        """Gate P11: Mock search returns parsed company data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{
                "company_number": "00000001",
                "title": "GOLDMAN SACHS INTERNATIONAL",
                "company_status": "active",
            }]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await search_company("Goldman Sachs", "test_key", client=mock_client)
        assert result is not None
        assert result["company_number"] == "00000001"
        assert result["title"] == "GOLDMAN SACHS INTERNATIONAL"

    @pytest.mark.asyncio
    async def test_search_not_found(self) -> None:
        """Company not found → returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await search_company("NonexistentCompany12345", "test_key", client=mock_client)
        assert result is None

    @pytest.mark.asyncio
    async def test_404_returns_none(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await search_company("test", "test_key", client=mock_client)
        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limit_retries(self) -> None:
        """Gate P13: 429 → backs off and retries."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "items": [{"company_number": "00000001", "title": "TEST"}]
        }
        success_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[rate_limit_response, success_response])
        mock_client.aclose = AsyncMock()

        result = await search_company("test", "test_key", client=mock_client)
        assert result is not None
        assert mock_client.get.call_count == 2


class TestGetCompanyProfile:
    """Company profile retrieval tests."""

    @pytest.mark.asyncio
    async def test_get_profile(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "company_number": "00000001",
            "company_name": "TEST LTD",
            "sic_codes": ["62020"],
            "company_status": "active",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await get_company_profile("00000001", "test_key", client=mock_client)
        assert result["company_number"] == "00000001"
        assert result["sic_codes"] == ["62020"]
