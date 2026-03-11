"""Tests for job skills population (SPEC.md §3.3)."""

from unittest.mock import MagicMock, patch

import pytest

from src.skills.populate import (
    _call_with_retry,
    get_jobs_without_skills,
    insert_job_skills,
    populate_job_skills,
    upsert_skill,
)


def _mock_db_client(
    jobs: list[dict[str, object]] | None = None,
    existing_skill_id: int | None = None,
    existing_job_skill_ids: list[dict[str, object]] | None = None,
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

    # job_skills select chain (for exclusion query)
    js_select_chain = MagicMock()
    js_select_chain.select.return_value = js_select_chain
    js_select_chain.range.return_value = js_select_chain
    js_select_data = existing_job_skill_ids or []
    js_select_chain.execute.return_value = MagicMock(data=js_select_data)

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
    js_upsert_chain = MagicMock()
    js_upsert_chain.upsert.return_value = js_upsert_chain
    js_upsert_chain.execute.return_value = MagicMock(data=[])

    def table_router(name: str) -> MagicMock:
        if name == "jobs":
            return jobs_chain
        if name == "skills":
            if existing_skill_id:
                return skills_select_chain
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
            # Return select chain for get_jobs_without_skills, upsert chain for insert
            combined = MagicMock()
            combined.select.return_value = js_select_chain
            combined.upsert.return_value = js_upsert_chain
            return combined
        return MagicMock()

    client.table = table_router
    return client


class TestCallWithRetry:
    """Retry wrapper tests."""

    def test_succeeds_first_try(self) -> None:
        result = _call_with_retry("test_op", lambda: 42)
        assert result == 42

    @patch("src.skills.populate.time.sleep")
    def test_retries_on_failure(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("dropped")
            return 42

        result = _call_with_retry("test_op", flaky)
        assert result == 42
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("src.skills.populate.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep: MagicMock) -> None:
        def always_fails() -> None:
            raise ConnectionError("dropped")

        with pytest.raises(ConnectionError):
            _call_with_retry("test_op", always_fails)
        assert mock_sleep.call_count == 3  # 3 retries before final raise


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
        await insert_job_skills(db, job_id=1, skill_ids=[1, 2, 3])

    @pytest.mark.asyncio
    async def test_insert_empty_skills(self) -> None:
        db = _mock_db_client()
        await insert_job_skills(db, job_id=1, skill_ids=[])


class TestGetJobsWithoutSkills:
    """Tests for exclusion query pagination."""

    @pytest.mark.asyncio
    async def test_excludes_processed_ids(self) -> None:
        db = _mock_db_client(jobs=[{"id": 3, "title": "Dev", "description_plain": ""}])
        result = await get_jobs_without_skills(db, batch_size=10, processed_ids={1, 2})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_jobs_returns_empty(self) -> None:
        db = _mock_db_client(jobs=[])
        result = await get_jobs_without_skills(db, batch_size=10)
        assert result == []


class TestPopulateJobSkills:
    """End-to-end populate tests."""

    @pytest.mark.asyncio
    async def test_processes_single_job(self) -> None:
        mock_matcher = MagicMock()
        mock_matcher.extract.return_value = ["Python", "AWS"]

        jobs = [{"id": 1, "title": "Python Dev", "description_plain": "AWS experience"}]
        db = _mock_db_client(jobs=jobs)

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

    @pytest.mark.asyncio
    async def test_error_in_job_increments_error_count(self) -> None:
        mock_matcher = MagicMock()
        mock_matcher.extract.side_effect = RuntimeError("extraction failed")

        jobs = [{"id": 1, "title": "Test", "description_plain": "desc"}]
        db = _mock_db_client(jobs=jobs)

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
        assert stats["errors"] == 1
        assert stats["jobs_processed"] == 0
