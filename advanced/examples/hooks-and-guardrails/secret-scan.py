#!/usr/bin/env python3
"""PreToolUse hook on Bash, filtered with "if": "Bash(git commit *)".

Scans the lines a commit would add (staged diff, plus tracked unstaged changes
when the command uses -a/--all) for credential patterns. On a hit it exits 2:
the commit never runs and stderr goes to Claude as the reason.
Findings are redacted so the secret itself is not echoed into the transcript.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import List, Tuple

PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-(proj-)?[A-Za-z0-9]{32,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Credential assignment", re.compile(
        r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")),
]
ALLOW_MARKER = "secret-scan: allow"  # put on a line to whitelist a known fake
SKIP_FILES = re.compile(r"(\.lock$|package-lock\.json$|\.min\.js$|\.svg$)")


def git(*args: str) -> str:
    res = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def added_lines(diff: str):
    current = None
    lineno = 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and current:
            yield current, lineno, line[1:]
            lineno += 1
        elif not line.startswith("-"):
            lineno += 1


def redact(s: str) -> str:
    s = s.strip()
    return s[:6] + "..." + s[-2:] if len(s) > 12 else "***"


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (event.get("tool_input") or {}).get("command", "")
    if "git" not in command or "commit" not in command:
        return 0  # belt and braces; the `if` filter is best-effort

    diff = git("diff", "--cached", "-U0", "--no-color")
    if re.search(r"\s(-a|--all|-[a-zA-Z]*a[a-zA-Z]*)\b", command):
        diff += "\n" + git("diff", "-U0", "--no-color")

    findings = []
    for path, lineno, text in added_lines(diff):
        if SKIP_FILES.search(path) or ALLOW_MARKER in text:
            continue
        for label, rx in PATTERNS:
            m = rx.search(text)
            if m:
                findings.append("  {}:{}  {}  ({})".format(path, lineno, label, redact(m.group(0))))
                break

    if not findings:
        return 0
    sys.stderr.write(
        "Commit blocked: possible secrets in the change.\n" + "\n".join(findings[:20]) +
        "\nMove the value to an env var or secret manager, unstage it (git restore --staged <file>), "
        "and commit again. If it is a test fixture, add the comment '" + ALLOW_MARKER + "' on that line "
        "and tell the user you did.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
