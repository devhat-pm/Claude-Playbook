#!/usr/bin/env bash
# Stop hook: if the working tree has source changes, run the test suite before
# Claude is allowed to end its turn. Failing tests -> decision:block with the
# tail of the output, so Claude keeps working.
#
# Test command: $CLAUDE_STOP_TEST_CMD, else auto-detected.
# A passing run is cached per tree state, so re-stopping without changes is free.
set -uo pipefail

input="$(cat)"
field() { printf '%s' "$input" | python3 -c "import json,sys; v=json.load(sys.stdin).get('$1'); print('' if v is None else str(v).lower())" 2>/dev/null; }

# Already continuing because of a stop hook: don't loop forever.
[ "$(field stop_hook_active)" = "true" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Only care about source changes (ignore docs-only turns).
changed="$(git status --porcelain | awk '{print $NF}' | grep -Ev '\.(md|txt|rst|png|jpg|svg)$' || true)"
[ -z "$changed" ] && exit 0

state="$( (git diff HEAD; git ls-files --others --exclude-standard) | shasum | cut -c1-16)"
cache_dir="${TMPDIR:-/tmp}/claude-stop-tests"
mkdir -p "$cache_dir"
[ -f "$cache_dir/$state" ] && exit 0

cmd="${CLAUDE_STOP_TEST_CMD:-}"
if [ -z "$cmd" ]; then
  if [ -f package.json ] && grep -q '"test"' package.json; then cmd="npm test --silent"
  elif [ -f pyproject.toml ] || [ -d tests ]; then cmd="python3 -m pytest -q -x"
  elif [ -f go.mod ]; then cmd="go test ./..."
  elif [ -f Cargo.toml ]; then cmd="cargo test --quiet"
  else exit 0
  fi
fi

out="$(bash -c "$cmd" 2>&1)"
status=$?
if [ $status -eq 0 ]; then
  touch "$cache_dir/$state"
  exit 0
fi

printf '%s' "$out" | tail -n 60 | python3 -c '
import json, sys
print(json.dumps({
    "decision": "block",
    "reason": "Tests fail (`" + sys.argv[1] + "`, exit " + sys.argv[2] + "). Fix the code, not the tests, then finish. Tail:\n" + sys.stdin.read(),
}))
' "$cmd" "$status"
exit 0
