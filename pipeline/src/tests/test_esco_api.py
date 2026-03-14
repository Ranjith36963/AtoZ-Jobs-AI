"""Tests for ESCO skills taxonomy downloader (skills/esco_api.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.skills.esco_api import (
    _download_csv,
    _extract_alt_labels,
    _extract_description,
    _extract_label,
    _fetch_from_api,
    fetch_all_esco_skills,
)


# ===========================================================================
# Helper extraction functions (used by API fallback)
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
# _download_csv — CSV download from GitHub
# ===========================================================================


SAMPLE_CSV = (
    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,"
    "altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,"
    "inScheme,description\n"
    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/001,"
    "skill/competence,sector-specific,Python programming,"
    '"Python 3\nPython dev",,released,2024-01-01,,,,'
    "Use Python for software development\n"
    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/002,"
    "knowledge,cross-sector,Django framework,"
    '"Django web\nDj",,released,2024-01-01,,,,'
    "Django web framework for Python\n"
    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/003,"
    "skill/competence,sector-specific,,,,,2024-01-01,,,,"
    "No preferred label skill\n"
)


class TestDownloadCsv:
    """Tests for _download_csv."""

    @pytest.mark.asyncio
    async def test_parses_csv_correctly(self) -> None:
        """CSV is downloaded and parsed into expected format."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_CSV
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await _download_csv()

        # Should have 2 skills (3rd has empty preferredLabel → skipped)
        assert len(result) == 2
        assert (
            result["http://data.europa.eu/esco/skill/001"]["preferred_label"]
            == "Python programming"
        )
        assert (
            result["http://data.europa.eu/esco/skill/001"]["skill_type"]
            == "skill/competence"
        )
        assert (
            "Python 3" in result["http://data.europa.eu/esco/skill/001"]["alt_labels"]
        )
        # "Dj" is only 2 chars → filtered out
        assert "Dj" not in result["http://data.europa.eu/esco/skill/002"]["alt_labels"]
        assert (
            "Django web" in result["http://data.europa.eu/esco/skill/002"]["alt_labels"]
        )

    @pytest.mark.asyncio
    async def test_handles_empty_csv(self) -> None:
        """Empty CSV (header only) returns empty dict."""
        csv_text = (
            "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,"
            "altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,"
            "inScheme,description\n"
        )
        mock_response = MagicMock()
        mock_response.text = csv_text
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await _download_csv()

        assert result == {}

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        """HTTP error during download is raised."""
        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await _download_csv()

    @pytest.mark.asyncio
    async def test_null_description_handled(self) -> None:
        """Null/missing description doesn't crash."""
        csv_text = (
            "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,"
            "altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,"
            "inScheme,description\n"
            "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/001,"
            "skill/competence,sector-specific,Python,,,released,2024-01-01,,,,\n"
        )
        mock_response = MagicMock()
        mock_response.text = csv_text
        mock_response.raise_for_status = MagicMock()

        with patch("src.skills.esco_api.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await _download_csv()

        assert len(result) == 1
        assert result["http://data.europa.eu/esco/skill/001"]["description"] == ""


# ===========================================================================
# _fetch_from_api — REST API fallback
# ===========================================================================


class TestFetchFromApi:
    """Tests for _fetch_from_api (REST API fallback)."""

    @pytest.mark.asyncio
    async def test_fetches_skills_from_api(self) -> None:
        """API response is parsed correctly."""
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

            result = await _fetch_from_api()

        assert len(result) == 2
        assert (
            result["http://data.europa.eu/esco/skill/001"]["preferred_label"]
            == "Python"
        )

    @pytest.mark.asyncio
    async def test_empty_api_response(self) -> None:
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

            result = await _fetch_from_api()

        assert result == {}


# ===========================================================================
# fetch_all_esco_skills — top-level orchestrator
# ===========================================================================


class TestFetchAllEscoSkills:
    """Tests for fetch_all_esco_skills (CSV > API fallback)."""

    @pytest.mark.asyncio
    async def test_uses_csv_when_available(self) -> None:
        """CSV download is used as primary source."""
        mock_skills = {
            "http://data.europa.eu/esco/skill/001": {
                "preferred_label": "Python",
                "alt_labels": [],
                "skill_type": "",
                "description": "",
            },
        }

        with patch(
            "src.skills.esco_api._download_csv",
            new_callable=AsyncMock,
            return_value=mock_skills,
        ) as mock_csv:
            result = await fetch_all_esco_skills()

        assert len(result) == 1
        mock_csv.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_api_when_csv_fails(self) -> None:
        """API fallback is used when CSV download fails."""
        api_skills = {
            "http://data.europa.eu/esco/skill/001": {
                "preferred_label": "Python",
                "alt_labels": [],
                "skill_type": "",
                "description": "",
            },
        }

        with (
            patch(
                "src.skills.esco_api._download_csv",
                new_callable=AsyncMock,
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                ),
            ),
            patch(
                "src.skills.esco_api._fetch_from_api",
                new_callable=AsyncMock,
                return_value=api_skills,
            ) as mock_api,
        ):
            result = await fetch_all_esco_skills()

        assert len(result) == 1
        mock_api.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_csv_network_error_triggers_fallback(self) -> None:
        """Network error on CSV triggers API fallback."""
        with (
            patch(
                "src.skills.esco_api._download_csv",
                new_callable=AsyncMock,
                side_effect=httpx.ConnectError("Connection refused"),
            ),
            patch(
                "src.skills.esco_api._fetch_from_api",
                new_callable=AsyncMock,
                return_value={},
            ) as mock_api,
        ):
            result = await fetch_all_esco_skills()

        assert result == {}
        mock_api.assert_awaited_once()


# ===========================================================================
# seed_esco_from_api (integration with seeder)
# ===========================================================================


class TestSeedEscoFromApi:
    """Tests for seed_esco_from_api."""

    @pytest.mark.asyncio
    async def test_downloads_and_seeds(self) -> None:
        """Fetched data is upserted into esco_skills table."""
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
