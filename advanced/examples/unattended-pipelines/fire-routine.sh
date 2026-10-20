#!/usr/bin/env bash
# Fire a Claude Code cloud scheduled task (routine) via its API trigger.
# The endpoint has NO idempotency key: every successful POST starts a new session.
# This wrapper adds: dedupe by key (no double-fire for the same alert/deploy), bounded
# retries on 429/5xx honoring Retry-After, and distinct exit codes the caller can alert on.
#
# Required env:
#   ROUTINE_FIRE_URL   the task's Fire URL (https://api.anthropic.com/v1/claude_code/routines/trig_.../fire)
#   ROUTINE_TOKEN      the task's bearer token (shown once when generated; keep in a secret store)
# Optional env:
#   DEDUPE_DIR         where fired keys are recorded (default: ${XDG_STATE_HOME:-$HOME/.local/state}/routine-fires)
#   MAX_ATTEMPTS       default 4
#
# Usage: fire-routine.sh <dedupe-key> <text-file-or-->
#   echo "Deploy 4f2c1 to prod finished" | fire-routine.sh deploy-4f2c1 -
#
# Docs: https://code.claude.com/docs/en/routines#trigger-a-scheduled-task
set -euo pipefail

key="${1:?dedupe key required}"
src="${2:--}"
: "${ROUTINE_FIRE_URL:?set ROUTINE_FIRE_URL}"
: "${ROUTINE_TOKEN:?set ROUTINE_TOKEN}"
max_attempts="${MAX_ATTEMPTS:-4}"
dedupe_dir="${DEDUPE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/routine-fires}"
mkdir -p "$dedupe_dir"

safe_key=$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '_')
marker="$dedupe_dir/$safe_key"
if [ -e "$marker" ]; then
  echo "already fired for key '$key': $(cat "$marker")"
  exit 0
fi

if [ "$src" = "-" ]; then text=$(cat); else text=$(cat "$src"); fi
# Endpoint rejects text over 65,536 characters with 400; keep headroom for the key line.
text=${text:0:65000}
# The task receives this inside a <routine-fire-payload> block marked untrusted.
# Prefix the key so the run can log it and you can grep sessions by it.
body=$(jq -n --arg t "dedupe_key: $key
$text" '{text: $t}')

attempt=1
delay=5
while :; do
  resp_file=$(mktemp)
  hdr_file=$(mktemp)
  code=$(curl -sS -o "$resp_file" -D "$hdr_file" -w '%{http_code}' -X POST "$ROUTINE_FIRE_URL" \
    -H "Authorization: Bearer $ROUTINE_TOKEN" \
    -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    -d "$body") || code="000"

  if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
    url=$(jq -r '.claude_code_session_url // empty' "$resp_file")
    printf '%s %s\n' "$(date -u +%FT%TZ)" "${url:-no-url}" > "$marker"
    echo "fired: ${url:-<no session url in response>}"
    rm -f "$resp_file" "$hdr_file"
    exit 0
  fi

  echo "attempt $attempt: HTTP $code: $(head -c 300 "$resp_file")" >&2
  retry_after=$(awk 'tolower($1)=="retry-after:"{gsub("\r","",$2); print $2}' "$hdr_file")
  rm -f "$resp_file" "$hdr_file"
  case "$code" in
    401) echo "token missing or not for this routine (regenerated?)" >&2; exit 3 ;;
    403) echo "account/org has no access to the fire endpoint" >&2; exit 3 ;;
    400) echo "rejected: routine paused, bad version header, or text too long" >&2; exit 4 ;;
    404) echo "routine not found" >&2; exit 4 ;;
  esac
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "giving up after $attempt attempts" >&2
    exit 5
  fi
  case "$retry_after" in
    ''|*[!0-9]*) sleep "$delay" ;;
    *)
      # 429 Retry-After points at the hourly window reset; don't block a pipeline for an hour.
      if [ "$retry_after" -gt 300 ]; then
        echo "hourly fire cap reached; window resets in ${retry_after}s" >&2
        exit 5
      fi
      sleep "$retry_after" ;;
  esac
  attempt=$((attempt + 1))
  delay=$((delay * 3))
done
