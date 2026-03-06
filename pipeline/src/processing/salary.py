"""Salary normalization — 12 regex patterns (SPEC.md §3.3).

Converts raw salary text and structured API fields to annual GBP min/max.
Rule-based only. No LLM.
"""

import re

import structlog

logger = structlog.get_logger()

# UK financial constants (Doc 9 — resolved)
UK_WORKING_DAYS_PER_YEAR = 252  # 260 weekdays - 8 UK bank holidays
UK_WORKING_HOURS_PER_YEAR = 1950  # 37.5 hours/week × 52 weeks
UK_MONTHS_PER_YEAR = 12

# Sanity bounds
SALARY_MIN_BOUND = 10_000
SALARY_MAX_BOUND = 500_000

# Pre-compiled patterns (ordered by specificity)
_CURRENCY = r"£"
_NUMBER = r"[\d,]+(?:\.\d{1,2})?"

# Period detection
_DAILY = re.compile(r"per\s*day|daily|day\s*rate", re.IGNORECASE)
_HOURLY = re.compile(r"per\s*hour|hourly|p/?h\b", re.IGNORECASE)
_MONTHLY = re.compile(r"per\s*month|monthly|pcm", re.IGNORECASE)

# Qualifier detection
_PRO_RATA = re.compile(r"pro\s*rata", re.IGNORECASE)
_OTE = re.compile(r"\bote\b|on\s*target", re.IGNORECASE)
_COMPETITIVE = re.compile(r"\bcompetitive\b|\battractive\b", re.IGNORECASE)
_DOE = re.compile(r"\bdoe\b|\bnegotiable\b|\bdepending\b", re.IGNORECASE)
_UP_TO = re.compile(
    r"up\s*to\s*" + _CURRENCY + r"?\s*(" + _NUMBER + r")", re.IGNORECASE
)
_FROM = re.compile(r"from\s*" + _CURRENCY + r"?\s*(" + _NUMBER + r")", re.IGNORECASE)

# Range patterns
_RANGE_K = re.compile(
    _CURRENCY + r"\s*(\d+)\s*k\s*[-–—to]+\s*" + _CURRENCY + r"?\s*(\d+)\s*k",
    re.IGNORECASE,
)
_RANGE_FULL = re.compile(
    _CURRENCY
    + r"\s*("
    + _NUMBER
    + r")\s*[-–—to]+\s*"
    + _CURRENCY
    + r"?\s*("
    + _NUMBER
    + r")",
    re.IGNORECASE,
)
_SINGLE_K = re.compile(_CURRENCY + r"\s*(\d+)\s*k\b", re.IGNORECASE)
_SINGLE_FULL = re.compile(_CURRENCY + r"\s*(" + _NUMBER + r")", re.IGNORECASE)


def _parse_number(s: str) -> float:
    """Parse a number string like '25,000' or '25000.50'."""
    return float(s.replace(",", ""))


def _annualize(value: float, period: str | None) -> float:
    """Convert a salary value to annual based on period."""
    if period == "daily":
        return value * UK_WORKING_DAYS_PER_YEAR
    if period == "hourly":
        return value * UK_WORKING_HOURS_PER_YEAR
    if period == "monthly":
        return value * UK_MONTHS_PER_YEAR
    return value  # already annual or unknown


def _sanity_check(value: float | None) -> float | None:
    """Reject values outside 10K–500K range."""
    if value is None:
        return None
    if value < SALARY_MIN_BOUND or value > SALARY_MAX_BOUND:
        return None
    return value


def _detect_period(text: str) -> str | None:
    """Detect salary period from text."""
    if _DAILY.search(text):
        return "daily"
    if _HOURLY.search(text):
        return "hourly"
    if _MONTHLY.search(text):
        return "monthly"
    return None


def parse_salary_text(text: str) -> tuple[float | None, float | None]:
    """Parse salary text into (annual_min, annual_max).

    Implements all 12 patterns from SPEC.md §3.3.
    Returns (None, None) for unparseable or non-numeric salary text.
    """
    if not text or not text.strip():
        return None, None

    text = text.strip()

    # Pattern 8: Competitive / Attractive → NULL
    if _COMPETITIVE.search(text):
        return None, None

    # Pattern 9: DOE / Negotiable → NULL
    if _DOE.search(text):
        return None, None

    # Detect period
    period = _detect_period(text)

    # Pattern 10: "Up to £40,000"
    up_to_match = _UP_TO.search(text)
    if up_to_match and not _RANGE_FULL.search(text):
        max_val = _annualize(_parse_number(up_to_match.group(1)), period)
        return _sanity_check(None), _sanity_check(max_val)

    # Pattern 11: "From £25,000"
    from_match = _FROM.search(text)
    if from_match and not _RANGE_FULL.search(text):
        min_val = _annualize(_parse_number(from_match.group(1)), period)
        return _sanity_check(min_val), _sanity_check(None)

    # Pattern 2: "£25k – £30k" (check before full range)
    range_k = _RANGE_K.search(text)
    if range_k:
        min_val = _annualize(float(range_k.group(1)) * 1000, period)
        max_val = _annualize(float(range_k.group(2)) * 1000, period)
        return _sanity_check(min_val), _sanity_check(max_val)

    # Pattern 1/3/4/5: "£25,000 – £30,000" or "£250–£350 per day" etc.
    range_full = _RANGE_FULL.search(text)
    if range_full:
        min_val = _annualize(_parse_number(range_full.group(1)), period)
        max_val = _annualize(_parse_number(range_full.group(2)), period)

        # Pattern 6: Pro rata — store as-is
        # Pattern 7: OTE — stored, but keep the parsed values
        return _sanity_check(min_val), _sanity_check(max_val)

    # Pattern 2 single: "£25k"
    single_k = _SINGLE_K.search(text)
    if single_k:
        val = _annualize(float(single_k.group(1)) * 1000, period)
        return _sanity_check(val), _sanity_check(val)

    # Pattern 12: "£50,000 + benefits" or single number
    single_full = _SINGLE_FULL.search(text)
    if single_full:
        val = _annualize(_parse_number(single_full.group(1)), period)
        return _sanity_check(val), _sanity_check(val)

    return None, None


def normalize_salary(
    salary_min: float | None = None,
    salary_max: float | None = None,
    salary_raw: str | None = None,
    salary_period: str | None = None,
    salary_is_predicted: bool = False,
) -> tuple[float | None, float | None]:
    """Normalize salary to annual GBP (SPEC.md §3.3).

    Priority:
    1. Use structured API fields first (salary_min/salary_max)
    2. If null, parse salary_raw text
    3. Sanity check: reject < 10K or > 500K
    """
    annual_min: float | None = None
    annual_max: float | None = None

    # Priority 1: structured API fields
    if salary_min is not None or salary_max is not None:
        if salary_min is not None:
            annual_min = _annualize(salary_min, salary_period)
        if salary_max is not None:
            annual_max = _annualize(salary_max, salary_period)
        annual_min = _sanity_check(annual_min)
        annual_max = _sanity_check(annual_max)
        return annual_min, annual_max

    # Priority 2: parse salary_raw text
    if salary_raw:
        return parse_salary_text(salary_raw)

    return None, None
