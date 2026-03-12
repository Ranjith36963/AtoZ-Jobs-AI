"""Tests for ESCO REST API client (skills/esco_api.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.skills.esco_api import (
    _extract_alt_labels,
    _extract_description,
    _extract_label,
    fetch_all_esco_skills,
)


# ===========================================================================
# Helper extraction functions
# ===========================================================================


class TestExtractLabel:
    """Tests for _extract_label."""

    def test_extracts_english_label(self) -> None:
        skill = {"preferredLabel": {"en": "Python", "de": "Python-Sprache"}}
        assert _extract_label(skill) == "Python"

    def test_empty_when_no_en(self) -> None:
        skill = {"preferredLabel": {"de": "Python-Sprache"}}
        assert _extract_label(skill) == ""

    def test_empty_when_no_preferred_label(self) -> None:
        assert _extract_label({}) == ""

    def test_strips_whitespace(self) -> None:
        skill = {"preferredLabel": {"en": "  Python  "}}
        assert _extract_label(skill) == "Python"

    def test_non_dict_preferred_label(self) -> None:
        skill = {"preferredLabel": "not a dict"}
        assert _extract_label(skill) == ""


class TestExtractAltLabels:
    """Tests for _extract_alt_labels."""

    def test_extracts_english_alts(self) -> None:
        skill = {"alternativeLabel": {"en": ["Python 3", "Python programming"]}}
        result = _extract_alt_labels(skill)
        assert "Python 3" in result
        assert "Python programming" in result

    def test_filters_short_labels(self) -> None:
        skill = {"alternativeLabel": {"en": ["AI", "ML", "Python programming"]}}
        result = _extract_alt_labels(skill)
        assert result == ["Python programming"]

    def test_empty_when_no_en(self) -> None:
        skill = {"alternativeLabel": {"de": ["Python-Sprache"]}}
        assert _extract_alt_labels(skill) == []

    def test_empty_when_no_alt_labels(self) -> None:
        assert _extract_alt_labels({}) == []

    def test_non_dict_alt_label(self) -> None:
        skill = {"alternativeLabel": "not a dict"}
        assert _extract_alt_labels(skill) == []

    def test_non_list_en_labels(self) -> None:
        skill = {"alternativeLabel": {"en": "single string"}}
        assert _extract_alt_labels(skill) == []


class TestExtractDescription:
    """Tests for _extract_description."""

    def test_extracts_literal(self) -> None:
        skill = {"description": {"en": {"literal": "Use Python for development."}}}
        assert _extract_description(skill) == "Use Python for development."

    def test_string_description(self) -> None:
        skill = {"description": {"en": "Simple string description"}}
        assert _extract_description(skill) == "Simple string description"

    def test_empty_when_no_description(self) -> None:
        assert _extract_description({}) == ""

    def test_empty_when_no_en(self) -> None:
        skill = {"description": {"de": {"literal": "German text"}}}
        assert _extract_description(skill) == ""


# ===========================================================================
# fetch_all_esco_skills — paginated API
# ===========================================================================


class TestFetchAllEscoSkills:
    """Tests for fetch_all_esco_skills with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_fetches_single_page(self) -> None:
        """Single page with 2 skills returns both."""
        api_response = {
            "total": 2,
            "count": 2,
            "offset": 0,
            "_embedded": {
                "http://data.europa.eu/esco/skill/001": {
                    "preferredLabel": {"en": "Python"},
                    "alternativeLabel": {"en": ["Python 3", "Python programming"]},
                    "skillType": "skill/competence",
                    "description": {"en": {"literal": "Use Python"}},
                },
                "http://data.europa.eu/esco/skill/002": {
                    "preferredLabel": {"en": "Django"},
                    "alternativeLabel": {"en": ["Django framework"]},
                    "skillType": "knowledge",
                    "description": {"en": {"literal": "Django web framework"}},
                },
            },
            "_links": {},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await fetch_all_esco_skills(page_size=100)

        assert len(result) == 2
        assert (
            result["http://data.europa.eu/esco/skill/001"]["preferred_label"]
            == "Python"
        )
        assert (
            result["http://data.europa.eu/esco/skill/002"]["preferred_label"]
            == "Django"
        )
        assert (
            "Python 3" in result["http://data.europa.eu/esco/skill/001"]["alt_labels"]
        )

    @pytest.mark.asyncio
    async def test_paginates_correctly(self) -> None:
        """Two pages of results are combined."""
        page1 = {
            "total": 3,
            "count": 2,
            "offset": 0,
            "_embedded": {
                "http://data.europa.eu/esco/skill/001": {
                    "preferredLabel": {"en": "Python"},
                    "alternativeLabel": {"en": []},
                    "skillType": "",
                    "description": {},
                },
                "http://data.europa.eu/esco/skill/002": {
                    "preferredLabel": {"en": "Java"},
                    "alternativeLabel": {"en": []},
                    "skillType": "",
                    "description": {},
                },
            },
            "_links": {},
        }
        page2 = {
            "total": 3,
            "count": 1,
            "offset": 2,
            "_embedded": {
                "http://data.europa.eu/esco/skill/003": {
                    "preferredLabel": {"en": "SQL"},
                    "alternativeLabel": {"en": []},
                    "skillType": "",
                    "description": {},
                },
            },
            "_links": {},
        }

        responses = [MagicMock(), MagicMock()]
        responses[0].json.return_value = page1
        responses[0].raise_for_status = MagicMock()
        responses[1].json.return_value = page2
        responses[1].raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = responses
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await fetch_all_esco_skills(page_size=2)

        assert len(result) == 3
        assert "http://data.europa.eu/esco/skill/003" in result

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        """Empty API response returns empty dict."""
        api_response = {
            "total": 0,
            "count": 0,
            "offset": 0,
            "_embedded": {},
            "_links": {},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await fetch_all_esco_skills()

        assert result == {}

    @pytest.mark.asyncio
    async def test_skips_skills_without_label(self) -> None:
        """Skills with empty preferred label are skipped."""
        api_response = {
            "total": 2,
            "count": 2,
            "offset": 0,
            "_embedded": {
                "http://data.europa.eu/esco/skill/001": {
                    "preferredLabel": {"en": "Python"},
                    "alternativeLabel": {"en": []},
                    "skillType": "",
                    "description": {},
                },
                "http://data.europa.eu/esco/skill/002": {
                    "preferredLabel": {"de": "Nur Deutsch"},  # no English label
                    "alternativeLabel": {"en": []},
                    "skillType": "",
                    "description": {},
                },
            },
            "_links": {},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await fetch_all_esco_skills()

        assert len(result) == 1
        assert "http://data.europa.eu/esco/skill/001" in result

    @pytest.mark.asyncio
    async def test_http_error_propagates(self) -> None:
        """HTTP errors are raised (caller handles retry)."""
        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await fetch_all_esco_skills()


# ===========================================================================
# seed_esco_from_api (integration with seeder)
# ===========================================================================


class TestSeedEscoFromApi:
    """Tests for seed_esco_from_api."""

    @pytest.mark.asyncio
    async def test_downloads_and_seeds(self) -> None:
        """API data is fetched and upserted into esco_skills."""
        from src.skills.seed_esco import seed_esco_from_api

        mock_esco_data = {
            "http://data.europa.eu/esco/skill/001": {
                "preferred_label": "Python",
                "alt_labels": ["Python 3"],
                "skill_type": "skill/competence",
                "description": "Use Python",
            },
        }

        db = MagicMock()
        chain = MagicMock()
        db.table.return_value = chain
        chain.upsert.return_value = chain

        with patch(
            "src.skills.esco_api.fetch_all_esco_skills",
            new_callable=AsyncMock,
            return_value=mock_esco_data,
        ):
            count = await seed_esco_from_api(db)

        assert count == 1
        db.table.assert_called_with("esco_skills")
        chain.upsert.assert_called_once()
