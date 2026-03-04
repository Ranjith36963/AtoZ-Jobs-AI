# PR Review Command

Review a pull request for code quality, security, and architectural consistency.

## Steps
1. Read all changed files in the PR
2. Check against CLAUDE.md conventions (root + subdirectory)
3. Run security audit (see .claude/agents/security-auditor.md)
4. Run architecture review (see .claude/agents/architecture-reviewer.md)
5. Verify tests exist for new/changed code
6. Check coverage meets minimums (80% pipeline, 60% web)
7. Verify conventional commit messages
8. Flag any SPEC.md deviations

## Output
- List of issues (blocking vs. non-blocking)
- Suggested fixes for each issue
- Overall assessment: approve / request changes
