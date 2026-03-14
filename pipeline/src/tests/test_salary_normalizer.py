"""Tests for salary normalizer — all 12 patterns (SPEC.md §3.3, Gates P1–P4)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from src.processing.salary import (
    UK_MONTHS_PER_YEAR,
    UK_WORKING_DAYS_PER_YEAR,
    UK_WORKING_HOURS_PER_YEAR,
    normalize_salary,
    parse_salary_text,
)


class TestSalaryPatterns:
    """All 12 salary patterns from SPEC.md §3.3."""

    # Pattern 1: £25,000 – £30,000
    def test_annual_range(self) -> None:
        min_val, max_val = parse_salary_text("£25,000 – £30,000")
        assert min_val == 25_000
        assert max_val == 30_000

    def test_annual_range_dash(self) -> None:
        min_val, max_val = parse_salary_text("£25,000 - £30,000")
        assert min_val == 25_000
        assert max_val == 30_000

    # Pattern 2: £25k – £30k
    def test_k_range(self) -> None:
        min_val, max_val = parse_salary_text("£25k – £30k")
        assert min_val == 25_000
        assert max_val == 30_000

    def test_k_range_dash(self) -> None:
        min_val, max_val = parse_salary_text("£25k - £30k")
        assert min_val == 25_000
        assert max_val == 30_000

    # Pattern 3: £250–£350 per day
    def test_daily_rate(self) -> None:
        min_val, max_val = parse_salary_text("£250–£350 per day")
        assert min_val == 250 * UK_WORKING_DAYS_PER_YEAR
        assert max_val == 350 * UK_WORKING_DAYS_PER_YEAR

    def test_daily_rate_single(self) -> None:
        min_val, max_val = parse_salary_text("£300 per day")
        assert min_val == 300 * UK_WORKING_DAYS_PER_YEAR
        assert max_val == 300 * UK_WORKING_DAYS_PER_YEAR

    # Pattern 4: £15–£20 per hour
    def test_hourly_rate(self) -> None:
        min_val, max_val = parse_salary_text("£15–£20 per hour")
        assert min_val == 15 * UK_WORKING_HOURS_PER_YEAR
        assert max_val == 20 * UK_WORKING_HOURS_PER_YEAR

    def test_hourly_rate_ph(self) -> None:
        min_val, max_val = parse_salary_text("£18 p/h")
        assert min_val == 18 * UK_WORKING_HOURS_PER_YEAR
        assert max_val == 18 * UK_WORKING_HOURS_PER_YEAR

    # Pattern 5: £2,000–£3,000 per month
    def test_monthly_range(self) -> None:
        min_val, max_val = parse_salary_text("£2,000–£3,000 per month")
        assert min_val == 2_000 * UK_MONTHS_PER_YEAR
        assert max_val == 3_000 * UK_MONTHS_PER_YEAR

    def test_monthly_pcm(self) -> None:
        min_val, max_val = parse_salary_text("£3,500 pcm")
        assert min_val == 3_500 * UK_MONTHS_PER_YEAR
        assert max_val == 3_500 * UK_MONTHS_PER_YEAR

    # Pattern 6: £50,000 pro rata
    def test_pro_rata(self) -> None:
        min_val, max_val = parse_salary_text("£50,000 pro rata")
        assert min_val == 50_000
        assert max_val == 50_000

    # Pattern 7: £50,000 OTE
    def test_ote(self) -> None:
        min_val, max_val = parse_salary_text("£50,000 OTE")
        assert min_val == 50_000
        assert max_val == 50_000

    # Pattern 8: Competitive
    def test_competitive(self) -> None:
        min_val, max_val = parse_salary_text("Competitive")
        assert min_val is None
        assert max_val is None

    def test_attractive(self) -> None:
        min_val, max_val = parse_salary_text("Attractive salary package")
        assert min_val is None
        assert max_val is None

    # Pattern 9: DOE / Negotiable
    def test_doe(self) -> None:
        min_val, max_val = parse_salary_text("DOE")
        assert min_val is None
        assert max_val is None

    def test_negotiable(self) -> None:
        min_val, max_val = parse_salary_text("Negotiable")
        assert min_val is None
        assert max_val is None

    def test_depending(self) -> None:
        min_val, max_val = parse_salary_text("Depending on experience")
        assert min_val is None
        assert max_val is None

    # Pattern 10: Up to £40,000
    def test_up_to(self) -> None:
        min_val, max_val = parse_salary_text("Up to £40,000")
        assert min_val is None
        assert max_val == 40_000

    # Pattern 11: From £25,000
    def test_from(self) -> None:
        min_val, max_val = parse_salary_text("From £25,000")
        assert min_val == 25_000
        assert max_val is None

    # Pattern 12: £50,000 + benefits
    def test_plus_benefits(self) -> None:
        min_val, max_val = parse_salary_text("£50,000 + benefits")
        assert min_val == 50_000
        assert max_val == 50_000


class TestSalarySanity:
    """Sanity checks: reject < 10K or > 500K (Gate P2)."""

    def test_below_10k_rejected(self) -> None:
        min_val, max_val = parse_salary_text("£5,000")
        assert min_val is None
        assert max_val is None

    def test_above_500k_rejected(self) -> None:
        min_val, max_val = parse_salary_text("£600,000")
        assert min_val is None
        assert max_val is None

    def test_boundary_10k_accepted(self) -> None:
        min_val, max_val = parse_salary_text("£10,000")
        assert min_val == 10_000

    def test_boundary_500k_accepted(self) -> None:
        min_val, max_val = parse_salary_text("£500,000")
        assert min_val == 500_000


class TestSalaryPriority:
    """API fields take priority over salary_raw (Gate P3)."""

    def test_api_fields_priority(self) -> None:
        annual_min, annual_max = normalize_salary(
            salary_min=30000,
            salary_max=40000,
            salary_raw="£25k-£35k",
            salary_period=None,
        )
        assert annual_min == 30_000
        assert annual_max == 40_000

    def test_fallback_to_raw(self) -> None:
        annual_min, annual_max = normalize_salary(
            salary_min=None,
            salary_max=None,
            salary_raw="£25,000 - £35,000",
        )
        assert annual_min == 25_000
        assert annual_max == 35_000

    def test_daily_api_fields(self) -> None:
        annual_min, annual_max = normalize_salary(
            salary_min=300,
            salary_max=400,
            salary_period="daily",
        )
        assert annual_min == 300 * UK_WORKING_DAYS_PER_YEAR
        assert annual_max == 400 * UK_WORKING_DAYS_PER_YEAR

    def test_hourly_api_fields(self) -> None:
        annual_min, annual_max = normalize_salary(
            salary_min=15,
            salary_max=20,
            salary_period="hourly",
        )
        assert annual_min == 15 * UK_WORKING_HOURS_PER_YEAR
        assert annual_max == 20 * UK_WORKING_HOURS_PER_YEAR


class TestSalaryEdgeCases:
    """Sad paths: null, empty, malformed."""

    def test_none_input(self) -> None:
        assert normalize_salary() == (None, None)

    def test_empty_string(self) -> None:
        assert parse_salary_text("") == (None, None)

    def test_whitespace_only(self) -> None:
        assert parse_salary_text("   ") == (None, None)

    def test_no_numbers(self) -> None:
        assert parse_salary_text("Great opportunity") == (None, None)


class TestSalaryPropertyBased:
    """Property-based test: parser never raises on arbitrary input (Gate P4)."""

    @given(st.text(max_size=500))
    @settings(max_examples=200)
    def test_never_raises(self, text: str) -> None:
        result = parse_salary_text(text)
        assert isinstance(result, tuple)
        assert len(result) == 2
