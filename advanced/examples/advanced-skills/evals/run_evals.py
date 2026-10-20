#!/usr/bin/env python3
"""Portable trigger + outcome eval harness for one skill in a Claude Code plugin.

Runs every case in cases.json through headless Claude Code (`claude -p`) in a fresh
temp workspace, with the plugin loaded (with-arm) and optionally without it
(baseline arm), then reports trigger recall, false-trigger rate and check pass rate.

    python3 run_evals.py cases.json --dry-run            # validate cases, print commands, no calls
    python3 run_evals.py cases.json --runs 3             # with-arm only
    python3 run_evals.py cases.json --runs 3 --baseline  # adds no-plugin arm and delta
    python3 run_evals.py cases.json --skill-md variants/desc-b.md   # A/B a description

Every non-dry run is a real model call billed to whatever account `claude` uses.
Gate CI with --min-recall / --max-false-trigger / --min-pass (exit 1 when missed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional, Tuple

CHECK_TYPES = {"regex"}
# 600 s covers a 25-turn agent run on a small fixture with headroom; raise for big repos.
DEFAULT_TIMEOUT_S = 600


def load_cases(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        suite = json.load(fh)
    base = os.path.dirname(os.path.abspath(path))
    suite["plugin_dir"] = os.path.abspath(os.path.join(base, suite["plugin_dir"]))
    return suite


def validate_suite(suite: dict) -> List[str]:
    errs = []
    if not os.path.isfile(os.path.join(suite["plugin_dir"], "skills", suite["skill"], "SKILL.md")):
        errs.append("skills/%s/SKILL.md not found under %s" % (suite["skill"], suite["plugin_dir"]))
    ids = set()
    for c in suite.get("cases", []):
        cid = c.get("id")
        if not cid or cid in ids:
            errs.append("case id missing or duplicated: %r" % cid)
        ids.add(cid)
        if not isinstance(c.get("should_trigger"), bool):
            errs.append("%s: should_trigger must be true/false" % cid)
        for chk in c.get("checks", []):
            if chk.get("type") not in CHECK_TYPES:
                errs.append("%s: unknown check type %r" % (cid, chk.get("type")))
            try:
                re.compile(chk.get("pattern", ""))
            except re.error as exc:
                errs.append("%s: bad regex %r: %s" % (cid, chk.get("pattern"), exc))
    pos = sum(1 for c in suite.get("cases", []) if c.get("should_trigger"))
    neg = len(suite.get("cases", [])) - pos
    if pos < 3 or neg < 3:
        errs.append("need >=3 should-trigger and >=3 should-not-trigger cases (have %d/%d)" % (pos, neg))
    return errs


def build_cmd(case: dict, suite: dict, plugin_dir: Optional[str]) -> List[str]:
    d = suite.get("defaults", {})
    cmd = ["claude", "-p", case["prompt"],
           "--output-format", "stream-json", "--verbose",
           "--max-turns", str(case.get("max_turns", d.get("max_turns", 10)))]
    tools = case.get("allowed_tools", d.get("allowed_tools"))
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    if case.get("model") or d.get("model"):
        cmd += ["--model", case.get("model") or d.get("model")]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    return cmd


def parse_stream(stdout: str, skill: str) -> Tuple[bool, str, Optional[float]]:
    """Return (skill_fired, final_text, cost_usd) from stream-json lines."""
    fired, final, cost, last_text = False, "", None, ""
    name_re = re.compile(r"^(?:[\w-]+:)?%s$" % re.escape(skill))
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []) or []:
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    if name_re.match(str((block.get("input") or {}).get("skill", ""))):
                        fired = True
                elif block.get("type") == "text":
                    last_text = block.get("text", "")
        elif ev.get("type") == "result":
            final = ev.get("result") or ""
            cost = ev.get("total_cost_usd")
    return fired, final or last_text, cost


def run_checks(case: dict, workdir: str, final_text: str) -> List[Tuple[dict, bool]]:
    out = []
    for chk in case.get("checks", []):
        target = chk.get("target", "result")
        if target == "result":
            text = final_text
        elif target.startswith("file:"):
            p = os.path.join(workdir, target[5:])
            text = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
        else:
            text = ""
        found = re.search(chk["pattern"], text) is not None
        out.append((chk, (not found) if chk.get("absent") else found))
    return out


def run_once(case: dict, suite: dict, plugin_dir: Optional[str], timeout: int) -> dict:
    work = tempfile.mkdtemp(prefix="skill-eval-")
    try:
        for rel, content in suite.get("fixture", {}).items():
            path = os.path.join(work, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        t0 = time.time()
        try:
            proc = subprocess.run(build_cmd(case, suite, plugin_dir), cwd=work,
                                  capture_output=True, text=True, timeout=timeout)
            stdout, err = proc.stdout, (proc.stderr.strip()[-300:] if proc.returncode else "")
        except subprocess.TimeoutExpired:
            stdout, err = "", "timeout after %ds" % timeout
        fired, final, cost = parse_stream(stdout, suite["skill"])
        checks = run_checks(case, work, final)
        return {"fired": fired, "checks_passed": sum(ok for _, ok in checks),
                "checks_total": len(checks), "cost_usd": cost,
                "seconds": round(time.time() - t0, 1), "error": err}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def plugin_variant(plugin_dir: str, skill: str, skill_md: Optional[str]) -> Tuple[str, Optional[str]]:
    if not skill_md:
        return plugin_dir, None
    tmp = tempfile.mkdtemp(prefix="skill-variant-")
    dest = os.path.join(tmp, os.path.basename(plugin_dir))
    shutil.copytree(plugin_dir, dest, ignore=shutil.ignore_patterns("evals"))
    shutil.copyfile(skill_md, os.path.join(dest, "skills", skill, "SKILL.md"))
    return dest, tmp


def summarize(rows: List[dict]) -> Dict[str, float]:
    pos = [r for r in rows if r["should_trigger"]]
    neg = [r for r in rows if not r["should_trigger"]]
    tot = sum(r["checks_total"] for r in rows)
    return {
        "recall": sum(r["fired"] for r in pos) / len(pos) if pos else 0.0,
        "false_trigger": sum(r["fired"] for r in neg) / len(neg) if neg else 0.0,
        "check_pass": sum(r["checks_passed"] for r in rows) / tot if tot else 1.0,
        "cost_usd": sum(r["cost_usd"] or 0 for r in rows),
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Skill trigger/outcome evals via claude -p")
    ap.add_argument("cases")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--case", help="regex filter on case id")
    ap.add_argument("--baseline", action="store_true", help="also run without the plugin")
    ap.add_argument("--skill-md", help="alternate SKILL.md to test (description A/B)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    ap.add_argument("--json", help="write full results to this path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-recall", type=float, default=0.0)
    ap.add_argument("--max-false-trigger", type=float, default=1.0)
    ap.add_argument("--min-pass", type=float, default=0.0)
    args = ap.parse_args(argv)

    suite = load_cases(args.cases)
    errs = validate_suite(suite)
    if errs:
        for e in errs:
            print("CASE ERROR: " + e)
        return 1
    cases = [c for c in suite["cases"] if not args.case or re.search(args.case, c["id"])]
    plugin_dir, tmp = plugin_variant(suite["plugin_dir"], suite["skill"], args.skill_md)

    if args.dry_run:
        print("%d case(s) valid. Commands for run 1:" % len(cases))
        for c in cases:
            print("  [%s] %s" % (c["id"], " ".join(json.dumps(x) if " " in x else x
                                                    for x in build_cmd(c, suite, plugin_dir))))
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        return 0
    if shutil.which("claude") is None:
        print("`claude` not on PATH")
        return 1

    arms = [("with", plugin_dir)] + ([("without", None)] if args.baseline else [])
    results: Dict[str, List[dict]] = {a: [] for a, _ in arms}
    try:
        for c in cases:
            for arm, pdir in arms:
                for i in range(args.runs):
                    r = run_once(c, suite, pdir, args.timeout)
                    r.update(id=c["id"], run=i + 1, should_trigger=c["should_trigger"])
                    results[arm].append(r)
                    mark = "fired" if r["fired"] else "-----"
                    print("%-8s %-28s run%d %s checks %d/%d %5.1fs %s" % (
                        arm, c["id"], i + 1, mark, r["checks_passed"], r["checks_total"],
                        r["seconds"], r["error"]))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    s = summarize(results["with"])
    print("\nWITH   recall %.2f  false-trigger %.2f  check-pass %.2f  cost $%.2f"
          % (s["recall"], s["false_trigger"], s["check_pass"], s["cost_usd"]))
    if args.baseline:
        b = summarize(results["without"])
        print("W/OUT  check-pass %.2f  cost $%.2f   delta check-pass %+.2f"
              % (b["check_pass"], b["cost_usd"], s["check_pass"] - b["check_pass"]))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"summary": s, "results": results}, fh, indent=2)
    ok = (s["recall"] >= args.min_recall and s["false_trigger"] <= args.max_false_trigger
          and s["check_pass"] >= args.min_pass)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
