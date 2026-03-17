# Verification Team

Post-implementation quality verification — confirms the implementation meets requirements.

## Role

Orchestrate tdd-enforcer + performance-auditor + self (feature verification) to produce a quality report. Run after completing a feature or fix, before PR review.

## Composition

| Agent | Responsibility | Output |
|-------|---------------|--------|
| `tdd-enforcer` | Tests exist, pass, meet coverage, include sad paths | TDD compliance report |
| `performance-auditor` | Bundle size, ISR config, build succeeds | Performance metrics |
| Self | Feature smoke test — verify implementation matches requirements | Feature verification |

## Process

1. **Launch tdd-enforcer** on changed files to verify TDD compliance.

2. **Launch performance-auditor** to check for regressions.

3. **Self: feature verification:**
   - Read the original requirement (issue, spec section, or user request)
   - Read the implementation
   - Verify the implementation addresses ALL requirements
   - Check edge cases mentioned in the requirement are handled
   - Verify error handling follows project patterns (retry 3x → DLQ for pipeline, Zod → typed error for web)

4. **Aggregate quality report.**

## Output Format

```
## Verification Report

### TDD Compliance (via tdd-enforcer)
[tdd-enforcer output]

### Performance (via performance-auditor)
[performance-auditor output]

### Feature Verification (self)
- Requirement: [original requirement summary]
- Implementation: [what was built]
- Coverage:
  - [x] Requirement A addressed
  - [x] Requirement B addressed
  - [ ] Requirement C NOT addressed — [details]
- Edge cases:
  - [x] Null input handled
  - [x] Timeout handled
  - [ ] Rate limit NOT handled — [details]

### Quality Score
- TDD: PASS/FAIL
- Performance: PASS/FAIL
- Feature completeness: X/Y requirements met
- Overall: READY FOR REVIEW / NEEDS WORK
```

## Does NOT

- Review architecture (that is review-team)
- Check security (that is deploy-gate-team via security-auditor)
- Deploy anything
- Write code or fix issues found
