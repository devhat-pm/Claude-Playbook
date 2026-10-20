#!/usr/bin/env python3
"""Apply Claude's structured triage to a GitHub issue, deterministically.

Reads `claude -p --output-format json --json-schema ...` output, validates every
label against the repo's real label list (drops anything invented), then applies
labels + a marker label in ONE gh call and posts one comment. Re-running is safe:
the marker label makes the workflow skip, and gh's --add-label is a no-op for
labels already present.

Usage: triage_apply.py result.json labels.txt ISSUE_NUMBER
Env:   GH_TOKEN (gh auth), optional DRY_RUN=1
"""
import json
import os
import subprocess
import sys
from typing import List

MARKER = "triaged-by-claude"


def run(cmd: List[str]) -> None:
    if os.environ.get("DRY_RUN") == "1":
        print("DRY_RUN:", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    result_path, labels_path, issue = argv
    with open(result_path, encoding="utf-8") as fh:
        result = json.load(fh)

    if result.get("is_error"):
        print("claude run reported an error: %s" % result.get("subtype"), file=sys.stderr)
        return 1
    out = result.get("structured_output")
    if not isinstance(out, dict):
        print("no structured_output in result", file=sys.stderr)
        return 1

    with open(labels_path, encoding="utf-8") as fh:
        allowed = {line.strip() for line in fh if line.strip()}

    wanted = [l for l in out.get("labels", []) if isinstance(l, str)]
    labels = [l for l in wanted if l in allowed]
    dropped = sorted(set(wanted) - set(labels))
    priority = out.get("priority")
    if isinstance(priority, str) and priority in allowed:
        labels.append(priority)
    labels.append(MARKER)

    cmd = ["gh", "issue", "edit", issue]
    for label in dict.fromkeys(labels):  # dedupe, keep order
        cmd += ["--add-label", label]
    run(cmd)

    lines = ["**Automated triage** (Claude, headless)", "", out.get("summary", "").strip()]
    dup = out.get("duplicate_of")
    if isinstance(dup, int) and dup > 0:
        lines.append("")
        lines.append("Possible duplicate of #%d. A human should confirm before closing." % dup)
    if dropped:
        lines.append("")
        lines.append("Ignored labels not in this repo: %s" % ", ".join(dropped))
    cost = result.get("total_cost_usd")
    if isinstance(cost, (int, float)):
        lines.append("")
        lines.append("<sub>est. cost $%.4f</sub>" % cost)
    run(["gh", "issue", "comment", issue, "--body", "\n".join(lines)])
    print(json.dumps({"issue": issue, "applied": labels, "dropped": dropped}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
