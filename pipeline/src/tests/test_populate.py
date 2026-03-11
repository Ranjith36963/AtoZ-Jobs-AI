"""Tests for job skills population (SPEC.md §3.3)."""

from unittest.mock import MagicMock

import pytest

from src.skills.populate import (
    insert_job_skills,
    populate_job_skills,
    upsert_skill,
)


def _mock_db_client(
    jobs: list[dict[str, object]] | None = None,
    existing_skill_id: int | None = None,
) -> MagicMock:
    """Build a mock Supabase client."""
    client = MagicMock()

    # jobs query chain
    jobs_chain = MagicMock()
    jobs_chain.select.return_value = jobs_chain
    jobs_chain.eq.return_value = jobs_chain
    jobs_chain.not_.in_.return_value = jobs_chain
    jobs_chain.limit.return_value = jobs_chain
    jobs_chain.execute.return_value = MagicMock(data=jobs or [])

    # skills query chain
    skills_select_chain = MagicMock()
    skills_select_chain.select.return_value = skills_select_chain
    skills_select_chain.eq.return_value = skills_select_chain
    skills_select_chain.limit.return_value = skills_select_chain
    if existing_skill_id:
        skills_select_chain.execute.return_value = MagicMock(
            data=[{"id": existing_skill_id}]
        )
    else:
        skills_select_chain.execute.return_value = MagicMock(data=[])

    # skills insert chain
    skills_insert_chain = MagicMock()
    skills_insert_chain.insert.return_value = skills_insert_chain
    skills_insert_chain.execute.return_value = MagicMock(data=[{"id": 99}])

    # job_skills upsert chain
    js_chain = MagicMock()
    js_chain.upsert.return_value = js_chain
    js_chain.execute.return_value = MagicMock(data=[])

    def table_router(name: str) -> MagicMock:
        if name == "jobs":
            return jobs_chain
        if name == "skills":
            if existing_skill_id:
                return skills_select_chain
            # First call returns no results (for select), second is insert
            mock = MagicMock()
            mock.select.return_value = mock
            mock.eq.return_value = mock
            mock.limit.return_value = mock
            mock.execute.return_value = MagicMock(data=[])
            mock.insert.return_value = MagicMock(
                execute=MagicMock(return_value=MagicMock(data=[{"id": 99}]))
            )
            return mock
        if name == "job_skills":
            return js_chain
        return MagicMock()

    client.table = table_router
    return client


class TestUpsertSkill:
    """Skill upsert tests."""

    @pytest.mark.asyncio
    async def test_existing_skill_returns_id(self) -> None:
        db = _mock_db_client(existing_skill_id=42)
        result = await upsert_skill(db, "Python")
        assert result == 42

    @pytest.mark.asyncio
    async def test_new_skill_creates_and_returns_id(self) -> None:
        db = _mock_db_client()
        result = await upsert_skill(db, "NewSkill")
        assert isinstance(result, int)


class TestInsertJobSkills:
    """Job skills insertion tests."""

    @pytest.mark.asyncio
    async def test_insert_multiple_skills(self) -> None:
        db = _mock_db_client()
        # Should not raise
        await insert_job_skills(db, job_id=1, skill_ids=[1, 2, 3])

    @pytest.mark.asyncio
    async def test_insert_empty_skills(self) -> None:
        db = _mock_db_client()
        # Should not raise with empty list
        await insert_job_skills(db, job_id=1, skill_ids=[])


class TestPopulateJobSkills:
    """End-to-end populate tests."""

    @pytest.mark.asyncio
    async def test_processes_single_job(self) -> None:
        mock_matcher = MagicMock()
        mock_matcher.extract.return_value = ["Python", "AWS"]

        jobs = [{"id": 1, "title": "Python Dev", "description_plain": "AWS experience"}]
        db = _mock_db_client(jobs=jobs)

        # After first batch returns jobs, second batch returns empty to stop loop
        call_count = 0
        original_table = db.table

        def table_with_empty_second_call(name: str) -> MagicMock:
            nonlocal call_count
            if name == "jobs":
                call_count += 1
                if call_count > 1:
                    mock = MagicMock()
                    mock.select.return_value = mock
                    mock.eq.return_value = mock
                    mock.not_.in_.return_value = mock
                    mock.limit.return_value = mock
                    mock.execute.return_value = MagicMock(data=[])
                    return mock
            return original_table(name)  # type: ignore[no-any-return]

        db.table = table_with_empty_second_call

        stats = await populate_job_skills(db, mock_matcher, batch_size=10)
        assert stats["jobs_processed"] == 1
        assert stats["skills_extracted"] == 2
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_no_jobs_returns_zero_stats(self) -> None:
        mock_matcher = MagicMock()
        db = _mock_db_client(jobs=[])
        stats = await populate_job_skills(db, mock_matcher)
        assert stats["jobs_processed"] == 0
