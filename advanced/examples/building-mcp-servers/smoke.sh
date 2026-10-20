#!/usr/bin/env bash
# Smoke-test a Streamable HTTP MCP server without any client library.
# Usage: MCP_URL=http://127.0.0.1:3000/mcp MCP_TOKEN=devtok ./smoke.sh [tool_name '{"arg":"value"}']
set -euo pipefail
URL="${MCP_URL:-http://127.0.0.1:3000/mcp}"
TOKEN="${MCP_TOKEN:?set MCP_TOKEN}"
PV="2025-06-18"   # a 2025-era revision; both v2 SDKs still serve it
common=(-sS -X POST "$URL" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')

echo "== 1. no token -> expect 401 + WWW-Authenticate with resource_metadata"
curl "${common[@]}" -o /dev/null -D - -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | grep -iE '^HTTP/|^www-authenticate' || true

auth=(-H "Authorization: Bearer $TOKEN" -H "mcp-protocol-version: $PV")
echo "== 2. initialize"
hdrs="$(mktemp)"
curl "${common[@]}" "${auth[@]}" -D "$hdrs" -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"'"$PV"'","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' | grep '^data' | cut -c1-300
sid="$(grep -i '^mcp-session-id:' "$hdrs" | awk '{print $2}' | tr -d '\r' || true)"
[ -n "$sid" ] && auth+=(-H "mcp-session-id: $sid")
curl "${common[@]}" "${auth[@]}" -o /dev/null -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

echo "== 3. tools/list (names + annotations)"
curl "${common[@]}" "${auth[@]}" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | sed -n 's/^data: //p' |
  python3 -c 'import json,sys; [print(" ", t["name"], t.get("annotations", {})) for t in json.load(sys.stdin)["result"]["tools"]]'

if [ $# -ge 1 ]; then
  args="${2:-}"; [ -n "$args" ] || args='{}'
  echo "== 4. tools/call $1"
  curl "${common[@]}" "${auth[@]}" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"'"$1"'","arguments":'"$args"'}}' | sed -n 's/^data: //p'
fi
