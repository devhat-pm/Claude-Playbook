#!/usr/bin/env bash
# PreToolUse hook for the reviewer subagent: allow read-only shell, block anything that writes.
# Install: copy to .claude/hooks/readonly-bash.sh and chmod +x.
# Reads the hook JSON on stdin; exit 2 blocks the call and feeds stderr back to Claude.
set -euo pipefail
cmd=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

# Block shell redirection into files and obvious mutators (redirects to /dev/null and 2>&1 are fine).
scan=$(printf '%s' "$cmd" | sed -E 's#[0-9]*>+ */dev/null##g; s#[0-9]*>&[0-9]##g')
if printf '%s' "$scan" | grep -Eq '(^|[^0-9&])>[^&]|>>|\btee\b|\brm\b|\bmv\b|\bcp\b|\bchmod\b|\bsed -i\b|\bnpm (install|i)\b|\bpip install\b'; then
  echo "reviewer is read-only: blocked: $cmd" >&2
  exit 2
fi
# git: allow only inspection subcommands.
if printf '%s' "$cmd" | grep -Eq '\bgit\b' && ! printf '%s' "$cmd" | grep -Eq '\bgit (diff|log|show|status|blame|rev-parse|merge-base|branch --list|ls-files)\b'; then
  echo "reviewer may only run read-only git subcommands: blocked: $cmd" >&2
  exit 2
fi
exit 0
