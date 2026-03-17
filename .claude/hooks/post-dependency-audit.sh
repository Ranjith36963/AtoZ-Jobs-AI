#!/bin/bash
# PostToolUse hook: auto-audit after dependency changes
# Fires after any Bash command — checks if it was a dependency install/add

COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command' 2>/dev/null || echo "")

# pnpm add or pnpm install in web/
if echo "$COMMAND" | grep -qE "pnpm\s+(add|install)"; then
  echo "--- Dependency audit (pnpm) ---"
  cd web 2>/dev/null && pnpm audit --audit-level=high 2>&1 | tail -20
  exit 0
fi

# uv add in pipeline/
if echo "$COMMAND" | grep -qE "uv\s+add"; then
  echo "--- Dependency audit (uv) ---"
  cd pipeline 2>/dev/null && uv run pip-audit 2>&1 | tail -20
  exit 0
fi

# Not a dependency command — no-op
exit 0
