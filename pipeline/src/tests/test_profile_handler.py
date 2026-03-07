"""Tests for user profile handler (SPEC.md §6.3, Gates R12-R13)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.profiles.handler import (
    build_profile_text,
    create_or_update_profile,
    get_profile_embedding,
)


class TestBuildProfileText:
    """Profile text template tests."""

    def test_full_profile(self) -> None:
        """All fields present → correctly formatted."""
        text = build_profile_text({
            "target_role": "Software Engineer",
            "skills": ["Python", "AWS", "Docker"],
            "experience_text": "5 years in backend development",
            "preferred_location": "London",
            "work_preference": "hybrid",
        })

        assert "Target Role: Software Engineer" in text
        assert "Skills: Python, AWS, Docker" in text
        assert "Experience: 5 years in backend development" in text
        assert "Location: London" in text
        assert "Work Preference: hybrid" in text

    def test_missing_fields(self) -> None:
        """Missing fields → empty strings, no errors."""
        text = build_profile_text({})

        assert "Target Role: " in text
        assert "Skills: " in text
        assert "Work Preference: any" in text

    def test_empty_skills(self) -> None:
        """Empty skills list → empty skills string."""
        text = build_profile_text({"skills": []})
        assert "Skills: \n" in text or "Skills: " in text

    def test_single_skill(self) -> None:
        """Single skill → no trailing comma."""
        text = build_profile_text({"skills": ["Python"]})
        assert "Skills: Python" in text
        assert "Skills: Python," not in text


class TestCreateOrUpdateProfile:
    """Profile creation/update tests."""

    @pytest.mark.asyncio
    async def test_creates_profile(self) -> None:
        """Creates profile with embedding."""
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        mock_embed = AsyncMock(return_value=[0.1] * 768)

        profile_data = {
            "target_role": "Data Scientist",
            "skills": ["Python", "ML"],
            "experience_text": "3 years",
            "preferred_location": "Manchester",
            "work_preference": "remote",
            "min_salary": 50000,
        }

        result = await create_or_update_profile(
            user_id="user-123",
            profile_data=profile_data,
            db_client=mock_db,
            embed_fn=mock_embed,
        )

        assert result["id"] == "user-123"
        assert result["target_role"] == "Data Scientist"
        assert result["skills"] == ["Python", "ML"]
        assert result["profile_embedding"] == [0.1] * 768
        assert "Target Role: Data Scientist" in result["profile_text"]

        mock_db.table.assert_called_with("user_profiles")

    @pytest.mark.asyncio
    async def test_embedding_dimension(self) -> None:
        """Gate R12: Profile embedding is 768 dimensions."""
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        embedding_768 = [0.01 * i for i in range(768)]
        mock_embed = AsyncMock(return_value=embedding_768)

        result = await create_or_update_profile(
            user_id="user-456",
            profile_data={"target_role": "Engineer"},
            db_client=mock_db,
            embed_fn=mock_embed,
        )

        assert len(result["profile_embedding"]) == 768

    @pytest.mark.asyncio
    async def test_update_produces_new_embedding(self) -> None:
        """Re-embedding on update produces new vector."""
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        call_count = 0

        async def varying_embed(text: str) -> list[float]:
            nonlocal call_count
            call_count += 1
            return [0.1 * call_count] * 768

        result1 = await create_or_update_profile(
            user_id="user-789",
            profile_data={"target_role": "Engineer"},
            db_client=mock_db,
            embed_fn=varying_embed,
        )

        result2 = await create_or_update_profile(
            user_id="user-789",
            profile_data={"target_role": "Senior Engineer"},
            db_client=mock_db,
            embed_fn=varying_embed,
        )

        assert result1["profile_embedding"] != result2["profile_embedding"]

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self) -> None:
        """Missing optional fields handled without error."""
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_embed = AsyncMock(return_value=[0.0] * 768)

        result = await create_or_update_profile(
            user_id="user-empty",
            profile_data={},
            db_client=mock_db,
            embed_fn=mock_embed,
        )

        assert result["target_role"] is None
        assert result["skills"] == []
        assert result["work_preference"] == "any"


class TestGetProfileEmbedding:
    """Profile embedding retrieval tests."""

    @pytest.mark.asyncio
    async def test_returns_embedding(self) -> None:
        """Returns embedding for existing profile."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"profile_embedding": [0.5] * 768}
        ]

        result = await get_profile_embedding("user-123", mock_db)
        assert result == [0.5] * 768

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self) -> None:
        """No profile → returns None."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = await get_profile_embedding("nonexistent", mock_db)
        assert result is None
