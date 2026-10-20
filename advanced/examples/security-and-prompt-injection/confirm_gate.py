#!/usr/bin/env python3
"""PreToolUse confirmation gate for Claude Code.

Forces a human prompt ("ask") for side-effecting connector/MCP calls and for
shell commands that can move data off the machine, and hard-denies a few
patterns that are never legitimate in an untrusted-content session.

Install: copy to .claude/hooks/confirm_gate.py and register it under
hooks.PreToolUse (see settings.untrusted-content.json in this folder).

Input  (stdin): Claude Code hook JSON with tool_name, tool_input, mcp_server.
Output (stdout): {"hookSpecificOutput": {"hookEventName": "PreToolUse", ...}}
No output + exit 0 = no opinion; normal permission rules apply.

Test without Claude Code:
  echo '{"tool_name":"mcp__gmail__send_email","tool_input":{"to":"x@example.com"}}' \
    | python3 confirm_gate.py
"""
import json
import re
import sys

# Verbs in an MCP tool name that mean "changes something someone else can see".
WRITE_VERBS = re.compile(
    r"(send|create|update|delete|remove|share|post|publish|invite|transfer|"
    r"write|upload|move|merge|approve|comment|reply|forward|trash)",
    re.IGNORECASE,
)

# Shell patterns that carry data out or fetch-and-run.
EGRESS = re.compile(
    r"(\bcurl\b|\bwget\b|\bnc\b|\bncat\b|\bscp\b|\brsync\b|\bssh\b|"
    r"\bgh\s+(gist|api|release)|\bgit\s+push\b|\bnpm\s+publish\b|"
    r"base64\s+.*\|)",
    re.IGNORECASE,
)

# Never legitimate here: piping a download into a shell, or touching key files.
HARD_DENY = re.compile(
    r"((curl|wget)[^|]*\|\s*(ba|z)?sh\b|\.ssh/id_|\.aws/credentials|"
    r"printenv|\benv\b\s*$|security\s+find-generic-password)",
    re.IGNORECASE,
)

# Domains you trust for WebFetch without a prompt. Everything else asks.
TRUSTED_FETCH = ("docs.python.org", "platform.claude.com", "code.claude.com")


def decide(event):
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    if tool == "Bash":
        cmd = tool_input.get("command", "")
        if HARD_DENY.search(cmd):
            return "deny", "Blocked by confirm_gate: credential access or pipe-to-shell."
        if EGRESS.search(cmd):
            return "ask", "confirm_gate: this command can send data off the machine."
        return None, None

    if tool == "WebFetch":
        url = tool_input.get("url", "")
        host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if any(host == d or host.endswith("." + d) for d in TRUSTED_FETCH):
            return None, None
        # Query strings on unknown hosts are the classic exfil channel.
        if "?" in url:
            return "ask", "confirm_gate: fetch to %s carries a query string." % host
        return None, None

    if tool.startswith("mcp__"):
        verb_part = tool.split("__")[-1]
        if WRITE_VERBS.search(verb_part):
            server = (event.get("mcp_server") or {}).get("name", tool.split("__")[1])
            return "ask", "confirm_gate: %s on %s changes external state." % (verb_part, server)
    return None, None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # malformed input: stay out of the way
    decision, reason = decide(event)
    if decision is None:
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
