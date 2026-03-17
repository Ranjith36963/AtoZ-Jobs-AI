#!/bin/bash
# PreToolUse hook: block automated secret rotation commands
# These operations are irreversible and must be done manually with explicit confirmation

COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command' 2>/dev/null || echo "")

if echo "$COMMAND" | grep -qiE "supabase\s+secrets\s+set|doppler\s+secrets?\s+set|modal\s+secret\s+create"; then
  echo "BLOCKED: Secret rotation detected."
  echo "Secret rotation is irreversible and must be done manually."
  echo "Do not automate this — rotate secrets with explicit human confirmation at each step."
  exit 2
fi

# Not a secret rotation command — allow
exit 0
