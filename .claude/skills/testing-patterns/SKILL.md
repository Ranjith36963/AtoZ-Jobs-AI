# Testing Patterns Skill

## TDD Workflow
1. Write tests first — they must FAIL initially
2. Implement the minimum code to pass
3. Refactor while keeping tests green

## Python Testing Stack
- pytest + pytest-asyncio + hypothesis
- httpx.MockTransport for HTTP mocking
- Contract tests with fixtures from tests/fixtures/

## Test Requirements
- Compare against pre-computed expectations, never function output
- Include sad paths: null, empty, timeout, rate limit, malformed data, auth expiry
- Use hypothesis @given() for property-based testing on parsers
- Coverage: 80% pipeline minimum, 85% collectors, 90% processing

## Patterns
- One test file per module: test_{module_name}.py
- Fixtures in pipeline/src/tests/fixtures/ (JSON API response samples)
- Use pytest.mark.parametrize for multiple input/output pairs
- async tests: use pytest-asyncio with asyncio_mode = "auto"
