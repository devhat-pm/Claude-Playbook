#!/usr/bin/env python3
"""Fresh-window relay: run a long task as a chain of short headless sessions.

Each leg is a new `claude -p` process (fresh context, no compaction). State lives
on disk: tests.json, progress.txt, git. The relay stops when every test in
tests.json is "passing", when the leg cap or the total budget is hit, or when a
leg makes no progress (no new commit and no status change) twice in a row.

Usage:
    python3 relay.py --dir path/to/project --legs 12 --leg-budget 3 --total-budget 25
    python3 relay.py --dir . --dry-run        # print the commands, call nothing

Requires the `claude` CLI on PATH. Spend is billed to whatever account the CLI
is logged into; --max-budget-usd is a client-side estimate, so leave headroom.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent

FIRST_PROMPT = """You are setting up a multi-session task. Do NOT implement features yet.
1. Read SPEC.md. Write tests.json: {"tests":[{"id":1,"name":"...","status":"not_started"}, ...]}
   covering every requirement. Write the real test files those entries point to.
2. Write init.sh that installs deps, starts any services and runs the test suite.
3. Create progress.txt with a "Session 1" entry: what exists, what is next.
4. git add -A && git commit -m "relay: scaffold".
It is unacceptable to remove or weaken tests later."""

NEXT_PROMPT = """Fresh context window. Your previous windows left state on disk.
Call pwd; you may only read and write inside this directory.
State brief from the harness:
---
{brief}
---
Do this, in order:
1. Read progress.txt, tests.json and `git log --oneline -15`. Run ./init.sh.
2. Run one end-to-end check of something already marked passing before new work.
3. Pick the lowest-id failing or not_started test. Make it pass with a general
   solution. Only change a test's "status" field; never edit or delete entries.
4. After each test goes green: update tests.json status, append to progress.txt,
   git commit. Stop starting new tests once you have used most of your turns;
   leave no uncommitted work."""


def run(cmd: List[str], cwd: Path, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def test_counts(d: Path) -> Dict[str, int]:
    try:
        tests = json.loads((d / "tests.json").read_text()).get("tests", [])
    except (OSError, ValueError):
        return {}
    out: Dict[str, int] = {}
    for t in tests:
        out[t.get("status", "unknown")] = out.get(t.get("status", "unknown"), 0) + 1
    return out


def head(d: Path) -> str:
    rc, out, _ = run(["git", "rev-parse", "HEAD"], d)
    return out.strip() if rc == 0 else ""


def checkpoint(d: Path, leg: int) -> None:
    rc, out, _ = run(["git", "status", "--porcelain"], d)
    if rc == 0 and out.strip():
        run(["git", "add", "-A"], d)
        run(["git", "commit", "-m", "relay: checkpoint after leg %d (uncommitted work)" % leg], d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--legs", type=int, default=10)
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--leg-budget", type=float, default=3.0, help="USD per leg (--max-budget-usd)")
    ap.add_argument("--total-budget", type=float, default=20.0)
    ap.add_argument("--permission-mode", default="acceptEdits")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = Path(args.dir).resolve()
    spent = 0.0
    stalls = 0
    for leg in range(1, args.legs + 1):
        first = not (d / "tests.json").exists()
        if first:
            prompt = FIRST_PROMPT
        else:
            _, brief, _ = run([sys.executable, str(HERE / "session_state.py"), "--dir", str(d)], d)
            prompt = NEXT_PROMPT.format(brief=brief.strip())
        cmd = [
            "claude", "-p", prompt,
            "--model", args.model,
            "--output-format", "json",
            "--max-turns", str(args.max_turns),
            "--max-budget-usd", str(args.leg_budget),
            "--permission-mode", args.permission_mode,
        ]
        if args.dry_run:
            print("%s leg: %s" % ("first" if first else "next", " ".join(shlex.quote(c) for c in cmd[:2] + ["<prompt>"] + cmd[3:])))
            print(prompt)
            return 0

        before_head, before_counts = head(d), test_counts(d)
        rc, out, err = run(cmd, d)
        try:
            result = json.loads(out)
        except ValueError:
            result = {}
        cost = float(result.get("total_cost_usd") or 0.0)
        spent += cost
        checkpoint(d, leg)
        counts = test_counts(d)
        print("leg %d rc=%d cost=$%.2f total=$%.2f tests=%s" % (leg, rc, cost, spent, counts))
        if rc != 0 and err:
            print("  stderr: " + err.strip()[:300])

        total = sum(counts.values())
        if total and counts.get("passing", 0) == total:
            print("all %d tests passing; done" % total)
            return 0
        if head(d) == before_head and counts == before_counts:
            stalls += 1
            if stalls >= 2:
                print("two legs with no commit and no status change; stopping for a human")
                return 2
        else:
            stalls = 0
        if spent >= args.total_budget:
            print("total budget reached")
            return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
