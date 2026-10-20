#!/usr/bin/env python3
"""Validate a bulk-edit plan (changes.json) before anything touches disk.

Usage:
    python3 validate_plan.py changes.json [--json]

Plan format:
    {
      "root": ".",                       # optional, defaults to the plan's directory
      "edits": [
        {"file": "src/api.py", "find": "getUser", "replace": "fetchUser",
         "expect_count": 3, "word": true}
      ]
    }

Exit codes: 0 = plan is safe to apply, 1 = errors (each printed with a fix hint),
2 = the plan file itself could not be read.
Errors are deliberately verbose so the model can fix the plan without guessing.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from typing import Dict, List, Tuple

# Files above this size are almost always generated or vendored; editing them in
# bulk is more likely a mistake than intent. 2 MB covers any hand-written source file.
MAX_FILE_BYTES = 2 * 1024 * 1024

# Hard cap on edits per plan. Past ~500 the diff is unreviewable by a human, which
# defeats the point of the plan step; split the plan instead.
MAX_EDITS = 500

ALLOWED_KEYS = {"file", "find", "replace", "expect_count", "word"}


def _pattern(find: str, word: bool) -> "re.Pattern[str]":
    escaped = re.escape(find)
    return re.compile(r"\b" + escaped + r"\b" if word else escaped)


def count_matches(text: str, find: str, word: bool) -> int:
    return len(_pattern(find, word).findall(text))


def near_matches(text: str, find: str, limit: int = 5) -> List[str]:
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text))
    return difflib.get_close_matches(find, sorted(tokens), n=limit, cutoff=0.6)


def load_plan(path: str) -> Tuple[dict, str]:
    with open(path, encoding="utf-8") as fh:
        plan = json.load(fh)
    default_root = os.path.dirname(os.path.abspath(path))
    root = os.path.abspath(os.path.join(default_root, plan.get("root", ".")))
    return plan, root


def validate(plan: dict, root: str) -> Tuple[List[str], List[str], Dict[str, int]]:
    errors: List[str] = []
    warnings: List[str] = []
    stats = {"edits": 0, "files": 0, "replacements": 0}

    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        return ['"edits" must be a non-empty list of edit objects.'], warnings, stats
    if len(edits) > MAX_EDITS:
        errors.append(
            "Plan has %d edits; the limit is %d. Split it into several plans."
            % (len(edits), MAX_EDITS)
        )

    seen_files = set()
    per_file: Dict[str, List[dict]] = {}
    for i, edit in enumerate(edits):
        where = "edits[%d]" % i
        if not isinstance(edit, dict):
            errors.append("%s: must be an object, got %s." % (where, type(edit).__name__))
            continue
        unknown = set(edit) - ALLOWED_KEYS
        if unknown:
            errors.append(
                "%s: unknown key(s) %s. Allowed: %s."
                % (where, sorted(unknown), sorted(ALLOWED_KEYS))
            )
        rel = edit.get("file")
        find = edit.get("find")
        replace = edit.get("replace")
        if not isinstance(rel, str) or not rel:
            errors.append('%s: "file" is required (path relative to root %s).' % (where, root))
            continue
        if not isinstance(find, str) or not find:
            errors.append('%s (%s): "find" must be a non-empty string.' % (where, rel))
            continue
        if not isinstance(replace, str):
            errors.append('%s (%s): "replace" must be a string (use "" to delete).' % (where, rel))
            continue
        if find == replace:
            warnings.append("%s (%s): find == replace; edit is a no-op." % (where, rel))

        abs_path = os.path.abspath(os.path.join(root, rel))
        if os.path.commonpath([abs_path, root]) != root:
            errors.append("%s: %s resolves outside root %s. Refusing." % (where, rel, root))
            continue
        if not os.path.isfile(abs_path):
            candidates = difflib.get_close_matches(
                os.path.basename(rel),
                [f for _, _, fs in os.walk(root) for f in fs],
                n=3,
            )
            hint = (" Similar files: %s." % ", ".join(candidates)) if candidates else ""
            errors.append("%s: file not found: %s.%s" % (where, rel, hint))
            continue
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            errors.append(
                "%s: %s is larger than %d bytes; likely generated. Remove it from the plan."
                % (where, rel, MAX_FILE_BYTES)
            )
            continue
        try:
            with open(abs_path, encoding="utf-8") as fh:
                text = fh.read()
        except UnicodeDecodeError:
            errors.append("%s: %s is not UTF-8 text; bulk edit only handles text." % (where, rel))
            continue

        word = bool(edit.get("word", False))
        n = count_matches(text, find, word)
        expected = edit.get("expect_count")
        if n == 0:
            close = near_matches(text, find)
            hint = (" Close matches in file: %s." % ", ".join(close)) if close else ""
            errors.append('%s: "%s" not found in %s.%s' % (where, find, rel, hint))
            continue
        if expected is not None and expected != n:
            errors.append(
                '%s: expected %s occurrence(s) of "%s" in %s, found %d. '
                "Fix expect_count or narrow the find string." % (where, expected, find, rel, n)
            )
        if expected is None:
            warnings.append(
                '%s: no expect_count for "%s" in %s (found %d). Add it to pin the plan.'
                % (where, find, rel, n)
            )
        per_file.setdefault(rel, []).append(edit)
        seen_files.add(rel)
        stats["replacements"] += n

    # Ordering hazards: an earlier replace that creates a later find in the same file.
    for rel, file_edits in per_file.items():
        for a_idx, a in enumerate(file_edits):
            for b in file_edits[a_idx + 1:]:
                if b["find"] in a["replace"]:
                    errors.append(
                        '%s: replace "%s" contains later find "%s"; the second edit would '
                        "rewrite the first edit's output. Reorder or merge them."
                        % (rel, a["replace"], b["find"])
                    )

    stats["edits"] = len(edits)
    stats["files"] = len(seen_files)
    return errors, warnings, stats


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    args = ap.parse_args(argv)
    try:
        plan, root = load_plan(args.plan)
    except (OSError, json.JSONDecodeError) as exc:
        print("Cannot read plan %s: %s" % (args.plan, exc), file=sys.stderr)
        return 2

    errors, warnings, stats = validate(plan, root)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                          "stats": stats}, indent=2))
    else:
        for w in warnings:
            print("WARN  " + w)
        for e in errors:
            print("ERROR " + e)
        verdict = "OK" if not errors else "FAILED (%d error(s))" % len(errors)
        print("%s: %d edit(s), %d file(s), %d replacement(s)"
              % (verdict, stats["edits"], stats["files"], stats["replacements"]))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
