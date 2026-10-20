#!/usr/bin/env python3
"""PreToolUse hook: refuse Edit/Write/NotebookEdit on protected paths, and tell
Claude what to do instead.

Wire it with matcher "Edit|Write|NotebookEdit". Rules live in
.claude/protected-paths.txt (one per line: `<glob>  <what to do instead>`),
falling back to DEFAULT_RULES. Globs are matched against the path relative to
the project root, with fnmatch semantics (`*` crosses `/`).
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from typing import List, Optional, Tuple

DEFAULT_RULES: List[Tuple[str, str]] = [
    ("db/migrations/*", "Never edit an applied migration. Create a new migration file instead."),
    (".github/workflows/*", "CI config is owned by platform. Describe the change for a human."),
    ("*.lock", "Lockfiles change only via the package manager (npm install / uv lock)."),
    ("package-lock.json", "Lockfiles change only via the package manager."),
    (".env*", "Secrets files are off-limits. Ask the user to set the value."),
    ("vendor/*", "Vendored code is pinned. Patch upstream or add an override."),
]


def load_rules(project_dir: str) -> List[Tuple[str, str]]:
    path = os.path.join(project_dir, ".claude", "protected-paths.txt")
    if not os.path.isfile(path):
        return DEFAULT_RULES
    rules: List[Tuple[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            rules.append((parts[0], parts[1] if len(parts) > 1 else "This path is protected."))
    return rules


def match(rel: str, rules: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    base = os.path.basename(rel)
    for pattern, advice in rules:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(base, pattern):
            return pattern, advice
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # not our problem; let the normal permission flow decide
    tool_input = event.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    # Paths arrive absolute; normalise Windows separators before comparing.
    target = target.replace("\\", "/")
    root = project_dir.replace("\\", "/").rstrip("/") + "/"
    rel = target[len(root):] if target.startswith(root) else target

    hit = match(rel, load_rules(project_dir))
    if hit is None:
        return 0

    pattern, advice = hit
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "{} is protected (rule: {}). {}".format(rel, pattern, advice),
        }
    }
    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
