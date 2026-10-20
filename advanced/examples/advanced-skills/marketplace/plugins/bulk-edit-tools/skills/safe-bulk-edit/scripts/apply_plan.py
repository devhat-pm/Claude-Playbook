#!/usr/bin/env python3
"""Apply a validated bulk-edit plan, with backups and a post-apply verification.

Usage:
    python3 apply_plan.py changes.json --dry-run   # print unified diff, write nothing
    python3 apply_plan.py changes.json             # back up, apply, verify

Always re-validates first; refuses to write if validation fails.
Backups go to <root>/.bulk-edit-backup/<UTC timestamp>/ mirroring relative paths.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import os
import shutil
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_plan import _pattern, count_matches, load_plan, validate  # noqa: E402


def plan_by_file(plan: dict) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for edit in plan["edits"]:
        grouped.setdefault(edit["file"], []).append(edit)
    return grouped


def rewrite(text: str, edits: List[dict]) -> str:
    for edit in edits:
        pat = _pattern(edit["find"], bool(edit.get("word", False)))
        text = pat.sub(lambda _m, r=edit["replace"]: r, text)
    return text


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    plan, root = load_plan(args.plan)
    errors, _warnings, _stats = validate(plan, root)
    if errors:
        print("Plan failed validation; run validate_plan.py and fix these first:")
        for e in errors:
            print("ERROR " + e)
        return 1

    stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_root = os.path.join(root, ".bulk-edit-backup", stamp)
    changed = 0
    for rel, edits in plan_by_file(plan).items():
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8") as fh:
            before = fh.read()
        after = rewrite(before, edits)
        if before == after:
            continue
        changed += 1
        if args.dry_run:
            sys.stdout.writelines(difflib.unified_diff(
                before.splitlines(True), after.splitlines(True),
                fromfile="a/" + rel, tofile="b/" + rel))
            continue
        dest = os.path.join(backup_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(after)

    if args.dry_run:
        print("\nDRY RUN: %d file(s) would change. Nothing written." % changed)
        return 0

    # Verify: every find string is gone unless the replacement reintroduces it.
    leftovers = []
    for rel, edits in plan_by_file(plan).items():
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            text = fh.read()
        for edit in edits:
            word = bool(edit.get("word", False))
            if edit["find"] in edit["replace"]:
                continue
            n = count_matches(text, edit["find"], word)
            if n:
                leftovers.append('%s: %d "%s" remain' % (rel, n, edit["find"]))
    print("Applied: %d file(s) changed. Backup: %s" % (changed, backup_root))
    if leftovers:
        print("VERIFY FAILED:")
        for line in leftovers:
            print("  " + line)
        return 1
    print("VERIFY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
