"""ESCO skills taxonomy downloader.

Downloads the ESCO skills_en.csv from a public GitHub mirror when the
CSV file is not available locally. Falls back to the ESCO REST API
(capped at ~200 results) as a last resort.

The CSV source is the official ESCO v1.1.1 dataset hosted at:
https://github.com/tabiya-tech/tabiya-esco-datasets-and-tools
"""

from __future__ import annotations

import csv
import io

import httpx
import structlog

logger = structlog.get_logger()

ESCO_CSV_URL = (
    "https://raw.githubusercontent.com/tabiya-tech/tabiya-esco-datasets-and-tools"
    "/main/datasets/esco/v1.1.1/classification/en/csv/skills_en.csv"
)

ESCO_API_BASE = "https://ec.europa.eu/esco/api"
SKILLS_SCHEME_URI = "http://data.europa.eu/esco/concept-scheme/skills"


async def fetch_all_esco_skills() -> dict[str, dict[str, str | list[str]]]:
    """Download full ESCO skills taxonomy (~13,900 skills).

    Strategy:
    1. Download skills_en.csv from GitHub mirror (fast, complete)
    2. Fall back to ESCO REST API if GitHub is unreachable (may be partial)

    Returns:
        Dict keyed by concept_uri, matching load_esco_csv() output format:
        {uri: {preferred_label, alt_labels, skill_type, description}}.
    """
    # Try CSV download first (reliable, complete)
    try:
        return await _download_csv()
    except Exception as e:
        logger.warning("esco_download.csv_failed", error=str(e))

    # Fallback: REST API (capped at ~200 by server)
    logger.info("esco_download.trying_api_fallback")
    return await _fetch_from_api()


async def _download_csv(
    url: str = ESCO_CSV_URL,
) -> dict[str, dict[str, str | list[str]]]:
    """Download and parse ESCO skills_en.csv from GitHub.

    Args:
        url: URL to the raw CSV file.

    Returns:
        Parsed skills dict.
    """
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    skills: dict[str, dict[str, str | list[str]]] = {}
    reader = csv.DictReader(io.StringIO(response.text))

    for row in reader:
        uri = row.get("conceptUri", "").strip()
        preferred = row.get("preferredLabel", "").strip()
        if not uri or not preferred:
            continue

        alt_raw = row.get("altLabels", "") or ""
        alt_labels = [
            a.strip() for a in alt_raw.split("\n") if a.strip() and len(a.strip()) > 2
        ]

        skills[uri] = {
            "preferred_label": preferred,
            "alt_labels": alt_labels,
            "skill_type": row.get("skillType", "").strip(),
            "description": (row.get("description", "") or "").strip(),
        }

    logger.info("esco_download.csv_complete", total_skills=len(skills), url=url)
    return skills


async def _fetch_from_api() -> dict[str, dict[str, str | list[str]]]:
    """Fetch ESCO skills via REST API (limited to ~200 by server pagination cap).

    Returns:
        Partial skills dict (may not contain full taxonomy).
    """
    skills: dict[str, dict[str, str | list[str]]] = {}
    offset = 0
    page_size = 100

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            url = (
                f"{ESCO_API_BASE}/resource/concept"
                f"?isInScheme={SKILLS_SCHEME_URI}"
                f"&language=en"
                f"&selectedVersion=v1.2.0"
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

                skills[uri] = {
                    "preferred_label": preferred,
                    "alt_labels": _extract_alt_labels(skill_data),
                    "skill_type": str(skill_data.get("skillType", "")),
                    "description": _extract_description(skill_data),
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
