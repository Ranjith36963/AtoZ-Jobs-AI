#!/bin/bash
# PreToolUse hook: remind about migration safety when editing SQL files
# Fires before Edit tool — checks if target is a migration file

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path' 2>/dev/null || echo "")

if echo "$FILE_PATH" | grep -qE "supabase/migrations/.*\.(sql)$"; then
  echo "⚠️  Migration file edit detected."
  echo "Remember: every up.sql needs a down.sql."
  echo "After editing, run: just reset && just seed"
  echo "See: .claude/skills/migration-safety/SKILL.md"
fi

# Always allow — this is informational only
exit 0
