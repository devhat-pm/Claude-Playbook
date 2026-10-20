#!/usr/bin/env python3
"""Print a compact state brief for a long-running Claude Code task.

Reads tests.json, the tail of progress.txt and recent git history and prints
~30 lines to stdout. Wire it to a SessionStart hook with matcher "compact" so the
brief is re-injected after every compaction, or paste its output as the first
message of a fresh window.

Usage:
    python3 session_state.py [--dir PROJECT_DIR] [--progress-lines 15] [--commits 8]

Exit code is always 0 so a missing file never blocks the session.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def tests_summary(path: Path) -> str:
    if not path.is_file():
        return "tests.json: missing (first window should create it)"
    try:
        data = json.loads(path.read_text())
    except ValueError as e:
        return "tests.json: INVALID JSON (%s) -- fix before doing anything else" % e
    tests = data.get("tests", [])
    counts = {}
    for t in tests:
        counts[t.get("status", "unknown")] = counts.get(t.get("status", "unknown"), 0) + 1
    failing = [t for t in tests if t.get("status") == "failing"][:5]
    nxt = [t for t in tests if t.get("status") == "not_started"][:3]
    lines = ["tests.json: " + ", ".join("%s=%d" % kv for kv in sorted(counts.items()))]
    for t in failing:
        lines.append("  failing #%s %s" % (t.get("id"), t.get("name")))
    for t in nxt:
        lines.append("  next    #%s %s" % (t.get("id"), t.get("name")))
    return "\n".join(lines)


def progress_tail(path: Path, n: int) -> str:
    if not path.is_file():
        return "progress.txt: missing"
    lines = path.read_text(errors="replace").rstrip().splitlines()
    return "progress.txt (last %d lines):\n%s" % (min(n, len(lines)), "\n".join(lines[-n:]))


def git_log(cwd: Path, n: int) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", "-n", str(n)],
            cwd=str(cwd), capture_output=True, text=True, timeout=10,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "git: unavailable"
    n_dirty = len([l for l in dirty.stdout.splitlines() if l.strip()])
    return "git (last %d commits, %d uncommitted paths):\n%s" % (n, n_dirty, out.stdout.rstrip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--progress-lines", type=int, default=15)
    ap.add_argument("--commits", type=int, default=8)
    args = ap.parse_args()
    d = Path(args.dir).resolve()
    print("=== STATE BRIEF (re-read files before acting; do not trust memory of earlier turns) ===")
    print(tests_summary(d / "tests.json"))
    print(progress_tail(d / "progress.txt", args.progress_lines))
    print(git_log(d, args.commits))
    print("Rules: never edit or delete entries in tests.json except status; commit after each passing test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
