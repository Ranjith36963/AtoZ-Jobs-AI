# Test Standards Rules

1. **TDD required.** Write tests first, confirm they fail, then implement.
2. **Pre-computed expectations.** Compare against known expected values, never against function output.
3. **Sad paths required.** Every test file must include: null, empty, timeout, rate limit, malformed data, auth expiry.
4. **Property-based testing.** Use hypothesis @given() for parsers (salary, location, seniority). Parser must never raise unhandled exception on arbitrary input.
5. **Coverage minimums.** Pipeline: 80%. Collectors: 85%. Processing: 90%. Web: 60%.
6. **Contract tests.** Save real API response samples to tests/fixtures/. Test adapters against these fixtures.
7. **One test file per module.** Named test_{module_name}.py.
8. **Async tests.** Use pytest-asyncio with asyncio_mode = "auto".
