"""ESCO REST API client for downloading the full skills taxonomy.

Downloads ~14,500 skills from the official EU ESCO API when the CSV
file is not available locally. Used as a fallback in seed_esco.
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()

ESCO_API_BASE = "https://ec.europa.eu/esco/api"
SKILLS_SCHEME_URI = "http://data.europa.eu/esco/concept-scheme/skills"
ESCO_VERSION = "v1.2.0"
PAGE_SIZE = 100


async def fetch_all_esco_skills(
    version: str = ESCO_VERSION,
    page_size: int = PAGE_SIZE,
) -> dict[str, dict[str, str | list[str]]]:
    """Fetch all ESCO skills via the REST API with pagination.

    Args:
        version: ESCO dataset version (e.g. "v1.2.0").
        page_size: Number of skills per API page (max varies by API).

    Returns:
        Dict keyed by concept_uri, matching load_esco_csv() output format:
        {uri: {preferred_label, alt_labels, skill_type, description}}.
    """
    skills: dict[str, dict[str, str | list[str]]] = {}
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            url = (
                f"{ESCO_API_BASE}/resource/concept"
                f"?isInScheme={SKILLS_SCHEME_URI}"
                f"&language=en"
                f"&selectedVersion={version}"
                f"&limit={page_size}"
                f"&offset={offset}"
            )

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            total = data.get("total", 0)
            embedded = data.get("_embedded", {})

            if not embedded:
                break

            for uri, skill_data in embedded.items():
                preferred = _extract_label(skill_data)
                if not preferred:
                    continue

                alt_labels = _extract_alt_labels(skill_data)
                skill_type = skill_data.get("skillType", "")
                description = _extract_description(skill_data)

                skills[uri] = {
                    "preferred_label": preferred,
                    "alt_labels": alt_labels,
                    "skill_type": skill_type,
                    "description": description,
                }

            offset += page_size
            logger.info(
                "esco_api.progress",
                fetched=len(skills),
                total=total,
                offset=offset,
            )

            if offset >= total:
                break

    logger.info("esco_api.complete", total_skills=len(skills))
    return skills


def _extract_label(skill_data: dict[str, object]) -> str:
    """Extract English preferred label from API response."""
    pref = skill_data.get("preferredLabel", {})
    if isinstance(pref, dict):
        return str(pref.get("en", "")).strip()
    return ""


def _extract_alt_labels(skill_data: dict[str, object]) -> list[str]:
    """Extract English alternative labels, filtering short ones."""
    alt = skill_data.get("alternativeLabel", {})
    if isinstance(alt, dict):
        labels = alt.get("en", [])
        if isinstance(labels, list):
            return [
                str(a).strip()
                for a in labels
                if isinstance(a, str) and len(a.strip()) > 2
            ]
    return []


def _extract_description(skill_data: dict[str, object]) -> str:
    """Extract English description from API response."""
    desc = skill_data.get("description", {})
    if isinstance(desc, dict):
        en_desc = desc.get("en", {})
        if isinstance(en_desc, dict):
            return str(en_desc.get("literal", "")).strip()
        if isinstance(en_desc, str):
            return en_desc.strip()
    return ""
