"""Tests for category mapper (SPEC.md §3.5, Gates P9–P12)."""

from src.processing.category import map_category


class TestReedMapping:
    """Reed sector → internal category (Gate P9)."""

    def test_it_telecoms(self) -> None:
        assert map_category("reed", "IT & Telecoms") == "Technology"

    def test_accountancy(self) -> None:
        assert map_category("reed", "Accountancy, Banking & Finance") == "Finance"

    def test_health(self) -> None:
        assert map_category("reed", "Health & Medicine") == "Healthcare"

    def test_engineering(self) -> None:
        assert map_category("reed", "Engineering") == "Engineering"

    def test_education(self) -> None:
        assert map_category("reed", "Education") == "Education"

    def test_sales(self) -> None:
        assert map_category("reed", "Sales") == "Sales & Marketing"

    def test_marketing(self) -> None:
        assert map_category("reed", "Marketing & PR") == "Sales & Marketing"

    def test_legal(self) -> None:
        assert map_category("reed", "Legal") == "Legal"

    def test_construction(self) -> None:
        assert map_category("reed", "Construction & Property") == "Construction"

    def test_creative(self) -> None:
        assert map_category("reed", "Creative & Design") == "Creative & Media"

    def test_hospitality(self) -> None:
        assert map_category("reed", "Catering & Hospitality") == "Hospitality"

    def test_unknown_reed_category(self) -> None:
        assert map_category("reed", "Unknown Sector") == "Other"


class TestAdzunaMapping:
    """Adzuna tag → internal category (Gate P10)."""

    def test_it_jobs(self) -> None:
        assert map_category("adzuna", "it-jobs") == "Technology"

    def test_accounting(self) -> None:
        assert map_category("adzuna", "accounting-finance-jobs") == "Finance"

    def test_healthcare(self) -> None:
        assert map_category("adzuna", "healthcare-nursing-jobs") == "Healthcare"

    def test_engineering(self) -> None:
        assert map_category("adzuna", "engineering-jobs") == "Engineering"

    def test_teaching(self) -> None:
        assert map_category("adzuna", "teaching-jobs") == "Education"

    def test_sales(self) -> None:
        assert map_category("adzuna", "sales-jobs") == "Sales & Marketing"

    def test_marketing(self) -> None:
        assert (
            map_category("adzuna", "pr-advertising-marketing-jobs")
            == "Sales & Marketing"
        )

    def test_legal(self) -> None:
        assert map_category("adzuna", "legal-jobs") == "Legal"

    def test_construction(self) -> None:
        assert map_category("adzuna", "construction-jobs") == "Construction"

    def test_creative(self) -> None:
        assert map_category("adzuna", "creative-design-jobs") == "Creative & Media"

    def test_hospitality(self) -> None:
        assert map_category("adzuna", "hospitality-catering-jobs") == "Hospitality"

    def test_unknown_adzuna_tag(self) -> None:
        assert map_category("adzuna", "unknown-jobs") == "Other"


class TestKeywordInference:
    """Title keyword inference for Jooble/Careerjet (Gate P11)."""

    def test_developer(self) -> None:
        assert map_category("jooble", title="Senior Python Developer") == "Technology"

    def test_software(self) -> None:
        assert map_category("jooble", title="Software Engineer") == "Technology"

    def test_devops(self) -> None:
        assert map_category("jooble", title="DevOps Engineer") == "Technology"

    def test_accountant(self) -> None:
        assert map_category("jooble", title="Senior Accountant") == "Finance"

    def test_nurse(self) -> None:
        assert map_category("careerjet", title="Registered Nurse") == "Healthcare"

    def test_teacher(self) -> None:
        assert map_category("jooble", title="Primary School Teacher") == "Education"

    def test_solicitor(self) -> None:
        assert map_category("jooble", title="Senior Solicitor") == "Legal"

    def test_chef(self) -> None:
        assert map_category("careerjet", title="Executive Chef") == "Hospitality"

    def test_plumber(self) -> None:
        assert map_category("jooble", title="Plumber") == "Construction"

    def test_designer(self) -> None:
        assert map_category("careerjet", title="Graphic Designer") == "Creative & Media"

    def test_sales_manager(self) -> None:
        assert map_category("jooble", title="Sales Manager") == "Sales & Marketing"

    def test_mechanical_engineer(self) -> None:
        assert map_category("careerjet", title="Mechanical Engineer") == "Engineering"


class TestCategoryFallback:
    """Fallback to 'Other' (Gate P12)."""

    def test_office_manager(self) -> None:
        assert map_category("jooble", title="Office Manager") == "Other"

    def test_office_assistant(self) -> None:
        assert map_category("careerjet", title="Office Assistant") == "Other"

    def test_no_category_no_title(self) -> None:
        assert map_category("jooble") == "Other"

    def test_empty_inputs(self) -> None:
        assert map_category("reed", "", "") == "Other"
