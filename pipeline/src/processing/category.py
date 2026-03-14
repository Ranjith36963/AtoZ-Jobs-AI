"""Category mapping — Reed/Adzuna exhaustive + keyword inference (SPEC.md §3.5).

Rule-based only. No LLM.
"""

import re

# Reed sector → Internal category (SPEC.md §3.5, authoritative)
REED_CATEGORY_MAP: dict[str, str] = {
    "IT & Telecoms": "Technology",
    "Accountancy": "Finance",
    "Accountancy, Banking & Finance": "Finance",
    "Banking": "Finance",
    "Banking & Finance": "Finance",
    "Health & Medicine": "Healthcare",
    "Healthcare & Medical": "Healthcare",
    "Engineering": "Engineering",
    "Education": "Education",
    "Education & Training": "Education",
    "Sales": "Sales & Marketing",
    "Marketing & PR": "Sales & Marketing",
    "Marketing": "Sales & Marketing",
    "PR": "Sales & Marketing",
    "Legal": "Legal",
    "Construction & Property": "Construction",
    "Construction": "Construction",
    "Property": "Construction",
    "Creative & Design": "Creative & Media",
    "Media": "Creative & Media",
    "Creative": "Creative & Media",
    "Design": "Creative & Media",
    "Catering & Hospitality": "Hospitality",
    "Hospitality": "Hospitality",
    "Catering": "Hospitality",
}

# Adzuna tag → Internal category
ADZUNA_CATEGORY_MAP: dict[str, str] = {
    "it-jobs": "Technology",
    "accounting-finance-jobs": "Finance",
    "healthcare-nursing-jobs": "Healthcare",
    "engineering-jobs": "Engineering",
    "teaching-jobs": "Education",
    "sales-jobs": "Sales & Marketing",
    "pr-advertising-marketing-jobs": "Sales & Marketing",
    "legal-jobs": "Legal",
    "construction-jobs": "Construction",
    "creative-design-jobs": "Creative & Media",
    "hospitality-catering-jobs": "Hospitality",
}

# Title keyword inference for Jooble/Careerjet (SPEC.md §3.5)
# Pre-compiled for performance
_KEYWORD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(?:software|developer|devops|data\s*scientist|sre|frontend|backend|"
            r"fullstack|full[\s-]?stack|cloud|cyber|sysadmin|QA|tester|IT\s*support|"
            r"programmer|web\s*developer|machine\s*learning|AI\s*engineer)\b",
            re.IGNORECASE,
        ),
        "Technology",
    ),
    (
        re.compile(
            r"\b(?:accountant|finance|auditor|tax|payroll|bookkeeper|actuary|"
            r"FCA|ACCA|CIMA|treasury|financial)\b",
            re.IGNORECASE,
        ),
        "Finance",
    ),
    (
        re.compile(
            r"\b(?:nurse|doctor|GP|pharmacist|midwife|carer|clinical|NHS|"
            r"paramedic|dentist|optometrist|healthcare|physiotherapist)\b",
            re.IGNORECASE,
        ),
        "Healthcare",
    ),
    (
        re.compile(
            r"\b(?:mechanical|electrical|civil|structural|chemical\s*engineer|"
            r"CAD|BIM|surveyor|quantity\s*surveyor)\b",
            re.IGNORECASE,
        ),
        "Engineering",
    ),
    (
        re.compile(
            r"\b(?:teacher|lecturer|tutor|teaching\s*assistant|SENCO|"
            r"headteacher|professor|trainer|education)\b",
            re.IGNORECASE,
        ),
        "Education",
    ),
    (
        re.compile(
            r"\b(?:sales|marketing|SEO|PPC|campaign|brand|account\s*manager|"
            r"business\s*development|BDM|copywriter)\b",
            re.IGNORECASE,
        ),
        "Sales & Marketing",
    ),
    (
        re.compile(
            r"\b(?:solicitor|barrister|paralegal|legal|conveyancer|regulatory)\b",
            re.IGNORECASE,
        ),
        "Legal",
    ),
    (
        re.compile(
            r"\b(?:construction|plumber|electrician|carpenter|bricklayer|"
            r"site\s*manager|foreman|CSCS|scaffolder)\b",
            re.IGNORECASE,
        ),
        "Construction",
    ),
    (
        re.compile(
            r"\b(?:designer|graphic|UX|UI|photographer|videographer|"
            r"animator|journalist|editor|producer)\b",
            re.IGNORECASE,
        ),
        "Creative & Media",
    ),
    (
        re.compile(
            r"\b(?:chef|cook|waiter|bartender|hotel|catering|kitchen|"
            r"front\s*of\s*house|restaurant)\b",
            re.IGNORECASE,
        ),
        "Hospitality",
    ),
]


def map_category(
    source_name: str,
    category_raw: str | None = None,
    title: str | None = None,
) -> str:
    """Map source category to internal category.

    Priority (SPEC.md §3.5):
    1. Reed/Adzuna: exhaustive source→internal mapping
    2. Jooble/Careerjet: source category match first, then keyword inference
    3. Default: 'Other'
    """
    # Try source-specific mapping first
    if category_raw:
        if source_name == "reed":
            result = REED_CATEGORY_MAP.get(category_raw)
            if result:
                return result
        elif source_name == "adzuna":
            result = ADZUNA_CATEGORY_MAP.get(category_raw)
            if result:
                return result
        else:
            # Jooble/Careerjet: try both maps
            result = REED_CATEGORY_MAP.get(category_raw)
            if result:
                return result
            result = ADZUNA_CATEGORY_MAP.get(category_raw)
            if result:
                return result

    # Keyword inference from title
    if title:
        for pattern, category in _KEYWORD_PATTERNS:
            if pattern.search(title):
                return category

    return "Other"
