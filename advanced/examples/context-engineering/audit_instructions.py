#!/usr/bin/env python3
"""Audit what Claude Code will put in context from instruction files.

Walks a repo and reports, per file: line count, rough token estimate, whether it
loads at launch or on demand, and the @imports it pulls in (resolved recursively,
max 4 hops, as Claude Code does). Flags files over 200 lines and unscoped rules
that could be path-scoped.

Usage:
    python3 audit_instructions.py [REPO_ROOT] [--cwd SUBDIR] [--json]

No network, no API calls. Token estimate is chars/4 -- a rough proxy only;
run /context in a session for the real number.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", "worktrees"}
INSTRUCTION_NAMES = {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"}
MAX_IMPORT_DEPTH = 4
LINE_LIMIT = 200
# @path outside code spans/fences. Escaped spaces ("\ ") are part of the path.
IMPORT_RE = re.compile(r"(?<![\w`])@((?:[~./\w-]|\\ )+[\w/-])")


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def strip_code(text: str) -> str:
    """Remove fenced blocks and inline code spans: imports there are not expanded."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def strip_html_comments(text: str) -> str:
    """Block-level HTML comments are stripped before injection."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_paths_frontmatter(text: str) -> Optional[List[str]]:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    m = re.search(r"^paths:\s*(.*)$", fm, flags=re.M)
    if not m:
        return None
    inline = m.group(1).strip()
    if inline:
        return [p.strip().strip("\"'") for p in inline.strip("[]").split(",") if p.strip()]
    items = re.findall(r"^\s*-\s*(.+)$", fm[m.end():], flags=re.M)
    return [i.strip().strip("\"'") for i in items]


def resolve_imports(path: Path, depth: int, seen: Set[Path]) -> List[Dict]:
    if depth > MAX_IMPORT_DEPTH:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for raw in IMPORT_RE.findall(strip_code(text)):
        target = raw.replace("\\ ", " ")
        p = Path(os.path.expanduser(target))
        if not p.is_absolute():
            p = (path.parent / p).resolve()
        entry = {"import": raw, "resolved": str(p), "depth": depth, "exists": p.is_file()}
        if p.is_file() and p not in seen:
            seen.add(p)
            body = strip_html_comments(p.read_text(encoding="utf-8", errors="replace"))
            entry["lines"] = body.count("\n") + 1
            entry["tokens"] = est_tokens(body)
            entry["children"] = resolve_imports(p, depth + 1, seen)
        out.append(entry)
    return out


def sum_import_tokens(imports: List[Dict]) -> int:
    return sum(i.get("tokens", 0) + sum_import_tokens(i.get("children", [])) for i in imports)


def classify(path: Path, root: Path, cwd: Path) -> str:
    rel_parent = path.parent
    if path.parent.name == "rules" or "rules" in path.relative_to(root).parts:
        return "rule"
    if path.parent.name == ".claude":
        rel_parent = path.parent.parent
    try:
        cwd.relative_to(rel_parent)
        return "launch"  # cwd or an ancestor of cwd
    except ValueError:
        return "on-demand"  # subdirectory file: loads when Claude touches files there


def walk(root: Path) -> List[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            if f in INSTRUCTION_NAMES:
                found.append(p)
            elif f.endswith(".md") and ".claude/rules" in p.as_posix():
                found.append(p)
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--cwd", default=None, help="directory you launch claude from (default: root)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cwd = Path(args.cwd).resolve() if args.cwd else root
    report = []
    for p in walk(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        body = strip_html_comments(text)
        kind = classify(p, root, cwd)
        paths = parse_paths_frontmatter(text) if kind == "rule" else None
        loads = kind
        if kind == "rule":
            loads = "on-demand (paths)" if paths else "launch (unscoped rule)"
        imports = resolve_imports(p, 1, {p})
        lines = body.count("\n") + 1
        warnings = []
        if lines > LINE_LIMIT:
            warnings.append("over %d lines: split into path-scoped rules or skills" % LINE_LIMIT)
        if kind == "rule" and not paths and lines > 40:
            warnings.append("unscoped rule >40 lines: add paths: frontmatter if it only applies to part of the tree")
        if any(not i["exists"] for i in imports):
            warnings.append("broken @import")
        report.append({
            "file": str(p.relative_to(root)),
            "loads": loads,
            "lines": lines,
            "tokens": est_tokens(body),
            "import_tokens": sum_import_tokens(imports),
            "imports": imports,
            "warnings": warnings,
        })

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
        return 0

    always = sum(r["tokens"] + r["import_tokens"] for r in report if r["loads"].startswith("launch"))
    print("%-55s %-24s %6s %8s %8s" % ("file", "loads", "lines", "~tok", "~imp_tok"))
    for r in report:
        print("%-55s %-24s %6d %8d %8d" % (r["file"][:55], r["loads"], r["lines"], r["tokens"], r["import_tokens"]))
        for w in r["warnings"]:
            print("    ! " + w)
    print("\n~tokens loaded at launch from %s: %d (imports count in full)" % (cwd, always))
    return 0


if __name__ == "__main__":
    sys.exit(main())
