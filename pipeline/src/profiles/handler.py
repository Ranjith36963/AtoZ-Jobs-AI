"""User profile handler for search personalization (SPEC.md §6.3).

Builds profile text from user data, embeds via Gemini, and manages
profile storage in the user_profiles table.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger()

EmbedFn = Callable[[str], Awaitable[list[float]]]

PROFILE_TEMPLATE = """Target Role: {target_role}
Skills: {skills}
Experience: {experience_text}
Location: {preferred_location}
Work Preference: {work_preference}"""


def build_profile_text(profile_data: dict[str, Any]) -> str:
    """Build structured profile text for embedding.

    Args:
        profile_data: User profile fields.

    Returns:
        Formatted profile text string.
    """
    skills = profile_data.get("skills", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills or "")

    return PROFILE_TEMPLATE.format(
        target_role=profile_data.get("target_role", ""),
        skills=skills_str,
        experience_text=profile_data.get("experience_text", ""),
        preferred_location=profile_data.get("preferred_location", ""),
        work_preference=profile_data.get("work_preference", "any"),
    )


async def create_or_update_profile(
    user_id: str,
    profile_data: dict[str, Any],
    db_client: Client,
    embed_fn: EmbedFn | None = None,
) -> dict[str, Any]:
    """Create or update user profile with embedding.

    Args:
        user_id: UUID of authenticated user.
        profile_data: Profile fields dict.
        db_client: Supabase client.
        embed_fn: Async function to embed text -> list[float]. If None, uses Gemini.

    Returns:
        Profile dict with all fields.
    """
    profile_text = build_profile_text(profile_data)

    if embed_fn is None:
        from src.embeddings.embed import embed_all

        async def _embed_single(text: str) -> list[float]:
            results = await embed_all([text])
            return results[0] if results else []

        embed_fn = _embed_single

    embedding = await embed_fn(profile_text)

    profile: dict[str, Any] = {
        "id": user_id,
        "target_role": profile_data.get("target_role"),
        "skills": profile_data.get("skills", []),
        "experience_text": profile_data.get("experience_text"),
        "preferred_location": profile_data.get("preferred_location"),
        "preferred_lat": profile_data.get("preferred_lat"),
        "preferred_lng": profile_data.get("preferred_lng"),
        "work_preference": profile_data.get("work_preference", "any"),
        "min_salary": profile_data.get("min_salary"),
        "profile_embedding": embedding,
        "profile_text": profile_text,
    }

    db_client.table("user_profiles").upsert(profile).execute()

    logger.info(
        "profile.updated",
        user_id=user_id,
        has_embedding=embedding is not None,
    )
    return profile


async def get_profile_embedding(
    user_id: str,
    db_client: Client,
) -> list[float] | None:
    """Get profile embedding for search personalization.

    Args:
        user_id: UUID of authenticated user.
        db_client: Supabase client.

    Returns:
        768-dim embedding vector or None if no profile.
    """
    result = (
        db_client.table("user_profiles")
        .select("profile_embedding")
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        return None

    embedding: list[float] | None = result.data[0].get("profile_embedding")
    return embedding
