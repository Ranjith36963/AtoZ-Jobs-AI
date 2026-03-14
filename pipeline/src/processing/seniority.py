"""Seniority extraction from job titles (SPEC.md §3.6).

Regex patterns against job title. Rule-based only. No LLM.
"""

import re

# Pre-compiled patterns ordered by specificity (SPEC.md §3.6)
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(?:head|director|vp|vice\s*president|chief|cto|cfo|coo|ceo|cmo|cio)\b",
            re.IGNORECASE,
        ),
        "Executive",
    ),
    (re.compile(r"\b(?:lead|principal|staff)\b", re.IGNORECASE), "Lead"),
    (re.compile(r"\b(?:senior|sr\.?)\b", re.IGNORECASE), "Senior"),
    (re.compile(r"\b(?:mid|intermediate)\b", re.IGNORECASE), "Mid"),
    (
        re.compile(r"\b(?:junior|entry|graduate|intern|trainee)\b", re.IGNORECASE),
        "Junior",
    ),
]

# Experience years pattern
_EXPERIENCE_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)\b",
    re.IGNORECASE,
)


def extract_seniority(title: str) -> str:
    """Extract seniority level from job title.

    Returns one of: Junior, Mid, Senior, Lead, Executive, Not specified.
    """
    if not title or not title.strip():
        return "Not specified"

    for pattern, level in _PATTERNS:
        if pattern.search(title):
            return level

    return "Not specified"


def extract_experience_years(text: str) -> int | None:
    """Extract years of experience from text.

    Pattern: '5+ years of experience', '3 yrs exp', etc.
    Returns None if no match.
    """
    if not text:
        return None
    match = _EXPERIENCE_RE.search(text)
    if match:
        return int(match.group(1))
    return None
