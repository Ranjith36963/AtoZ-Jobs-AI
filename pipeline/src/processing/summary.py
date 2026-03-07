"""Structured summary builder — 6-field template (SPEC.md §3.7).

Generates text for embedding. Rule-based only. No LLM. $0/job.
"""


def build_summary(
    title: str,
    seniority_level: str = "Not specified",
    company_name: str = "",
    industry: str = "Unknown",
    skills: list[str] | None = None,
    employment_type: list[str] | None = None,
    location_type: str = "onsite",
    location_city: str | None = None,
    location_region: str | None = None,
) -> str:
    """Build 6-field structured summary for embedding.

    Template (SPEC.md §3.7):
        Title: {title}
        Seniority: {seniority_level}
        Company: {company_name} ({industry})
        Skills: {skills, max 15}
        Work Type: {employment_type} | {location_type}
        Location: {city}, {region}
    """
    # Field 1: Title (as-is, do NOT normalize)
    lines = [f"Title: {title}"]

    # Field 2: Seniority
    lines.append(f"Seniority: {seniority_level}")

    # Field 3: Company + industry
    if company_name:
        lines.append(f"Company: {company_name} ({industry})")
    else:
        lines.append(f"Company: Unknown ({industry})")

    # Field 4: Skills (max 15, ordered by frequency)
    if skills:
        skill_list = skills[:15]
        lines.append(f"Skills: {', '.join(skill_list)}")
    else:
        lines.append("Skills: Not extracted")

    # Field 5: Work Type
    emp_type_str = ", ".join(employment_type) if employment_type else "Not specified"
    loc_type_display = location_type.capitalize() if location_type else "Onsite"
    lines.append(f"Work Type: {emp_type_str} | {loc_type_display}")

    # Field 6: Location
    if location_type == "remote":
        lines.append("Location: Remote, UK-wide")
    elif location_type == "nationwide":
        lines.append("Location: Multiple locations, UK")
    elif location_city and location_region:
        lines.append(f"Location: {location_city}, {location_region}")
    elif location_city:
        lines.append(f"Location: {location_city}")
    else:
        lines.append("Location: Not specified")

    return "\n".join(lines)
