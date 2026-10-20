#!/usr/bin/env bash
# PostToolUse hook (matcher "Edit|Write"): format + lint the file Claude just
# touched. Auto-fixes silently; if problems remain, returns decision:block so
# the lint output lands next to the tool result and Claude fixes it next turn.
# Tools are optional: anything not installed is skipped.
set -uo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path",""))' 2>/dev/null)"
[ -n "$file" ] && [ -f "$file" ] || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
have() { command -v "$1" >/dev/null 2>&1; }
report=""

case "$file" in
  *.py)
    if have ruff; then
      ruff format --quiet "$file" >/dev/null 2>&1
      report="$(ruff check --fix --quiet "$file" 2>&1)"
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    if [ -x node_modules/.bin/prettier ]; then
      node_modules/.bin/prettier --write --log-level warn "$file" >/dev/null 2>&1
    fi
    if [ -x node_modules/.bin/eslint ]; then
      report="$(node_modules/.bin/eslint --fix "$file" 2>&1)"
    fi
    ;;
  *.go)
    have gofmt && gofmt -w "$file"
    have go && report="$(go vet "./$(dirname "${file#"$PWD"/}")" 2>&1)"
    ;;
  *.sh)
    have shellcheck && report="$(shellcheck -f gcc "$file" 2>&1)"
    ;;
esac

[ -z "$report" ] && exit 0

# Keep the feedback short: Claude needs the first errors, not 400 lines.
printf '%s' "$report" | head -n 40 | python3 -c '
import json, sys
body = sys.stdin.read()
print(json.dumps({
    "decision": "block",
    "reason": "Lint still failing after auto-fix for " + sys.argv[1] + ":\n" + body + "\nFix these before moving on.",
}))
' "$file"
exit 0
