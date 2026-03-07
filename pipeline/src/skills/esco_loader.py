"""ESCO CSV loader (SPEC.md §3.1).

Loads ESCO skills CSV into structured dict for skill dictionary building.
"""

import csv


def load_esco_csv(filepath: str) -> dict[str, dict[str, object]]:
    """Load ESCO skills CSV into structured dict.

    Args:
        filepath: Path to skills_en.csv from ESCO download.

    Returns:
        Dict keyed by concept_uri with preferred_label, alt_labels,
        skill_type, and description.
    """
    skills: dict[str, dict[str, object]] = {}
    with open(filepath) as f:
        for row in csv.DictReader(f):
            uri = row["conceptUri"].strip()
            preferred = row["preferredLabel"].strip()
            alt_labels = [
                a.strip()
                for a in row.get("altLabels", "").split("\n")
                if a.strip() and len(a.strip()) > 2
            ]
            skills[uri] = {
                "preferred_label": preferred,
                "alt_labels": alt_labels,
                "skill_type": row.get("skillType", "").strip(),
                "description": row.get("description", "").strip(),
            }
    return skills
