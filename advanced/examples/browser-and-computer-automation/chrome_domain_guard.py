#!/usr/bin/env python3
"""Claude Code PreToolUse hook: allowlist for Claude in Chrome navigation.

Blocks mcp__claude-in-chrome__navigate (standalone or inside browser_batch) to any host not in
ALLOW (exact host or subdomain), and any non-http(s) scheme (javascript:, file:, data:, chrome:).
"back"/"forward" pass. Also blocks javascript_tool code that uses network/navigation primitives
(fetch, XMLHttpRequest, sendBeacon, WebSocket, location assignment, window.open) unless
CHROME_GUARD_ALLOW_JS_NET=1. Logs every decision to ~/.claude/chrome-nav.log.

Wire it up in .claude/settings.json (see browser-and-computer-automation.md, recipe 5).
Hook contract: JSON on stdin with tool_name + tool_input; exit 2 blocks, stderr is shown to Claude.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.parse import urlsplit

ALLOW = {
    "localhost", "127.0.0.1",
    "github.com", "docs.python.org", "developer.mozilla.org",
    # add your staging/admin hosts here
}
EXTRA = os.environ.get("CHROME_GUARD_ALLOW", "")  # comma-separated, for one-off sessions
ALLOW |= {h.strip().lower() for h in EXTRA.split(",") if h.strip()}
LOG = os.path.expanduser("~/.claude/chrome-nav.log")


def allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == a or host.endswith("." + a) for a in ALLOW)


def log(line: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), line))
    except OSError:
        pass


JS_NET = re.compile(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|"
                    r"location\s*(\.href)?\s*=|location\.(assign|replace)|window\.open|"
                    r"\.src\s*=|\.action\s*=")
P = "mcp__claude-in-chrome__"


def check_js(code: str) -> int:
    if os.environ.get("CHROME_GUARD_ALLOW_JS_NET") == "1" or not JS_NET.search(code):
        return 0
    log("BLOCK js-net %r" % code[:120])
    print("Blocked: page JavaScript may not make requests or navigate. Read the DOM only.",
          file=sys.stderr)
    return 2


def main() -> int:
    event = json.load(sys.stdin)
    name = event.get("tool_name", "")
    tin = event.get("tool_input", {}) or {}
    if name == P + "browser_batch":
        for item in tin.get("actions", []):
            n, i = item.get("name", ""), item.get("input", {}) or {}
            rc = check_url(str(i.get("url", ""))) if n == "navigate" else (
                check_js(str(i.get("text", ""))) if n == "javascript_tool" else 0)
            if rc:
                return rc
        return 0
    if name == P + "javascript_tool":
        return check_js(str(tin.get("text", "")))
    if name == P + "navigate":
        return check_url(str(tin.get("url", "")))
    return 0


def check_url(url: str) -> int:
    url = url.strip()
    if url in ("back", "forward"):
        return 0
    parts = urlsplit(url if "://" in url or url.split(":", 1)[0] in ("javascript", "data", "file", "chrome") else "https://" + url)
    if parts.scheme not in ("http", "https"):
        log("BLOCK scheme %s" % url)
        print("Blocked: only http(s) navigation is allowed.", file=sys.stderr)
        return 2
    if not allowed(parts.hostname or ""):
        log("BLOCK host %s" % url)
        print("Blocked: %s is not on the browsing allowlist. Ask the user to add it." % parts.hostname,
              file=sys.stderr)
        return 2
    log("ALLOW %s" % url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
