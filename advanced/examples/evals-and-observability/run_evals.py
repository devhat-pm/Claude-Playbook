#!/usr/bin/env python3
"""Prompt regression harness: code graders first, LLM judge second, baseline diff last.

Eval set: JSONL, one case per line:
  {"id": "...", "category": "...", "critical": true,
   "input": "...",                      # user message
   "must_include": ["regex", ...],      # code grader, all must match (case-insensitive)
   "must_not_include": ["regex", ...],  # code grader, none may match
   "max_words": 120,                    # code grader
   "rubric": "PASS if ... FAIL if ..."} # LLM judge (optional)

Modes:
  --replay outputs.jsonl   grade saved outputs ({"id","output"} per line); no generation call
  --no-judge               skip LLM judge (free; code graders only)
  (default)                generate with --model, judge with --judge-model; needs ANTHROPIC_API_KEY

  python3 run_evals.py --system system_prompt.md --cases evalset.example.jsonl \
      --replay sample_outputs.jsonl --no-judge --baseline baseline.json --out results.json

Exit: 0 ok, 1 regression or critical failure, 2 setup error.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time

JUDGE_SCHEMA = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "evidence": {"type": "string"},
                "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            },
            "required": ["evidence", "verdict"],
            "additionalProperties": False,
        },
    }
}

JUDGE_PROMPT = """You are grading one response from an AI assistant against a rubric.

<user_input>
{input}
</user_input>

<response>
{output}
</response>

<rubric>
{rubric}
</rubric>

Quote the part of the response that decides the verdict in "evidence", then give the verdict. \
Judge only what the rubric asks. Formatting differences do not matter unless the rubric says so. \
If the rubric's PASS condition is not clearly met, the verdict is FAIL."""


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def client():
    import anthropic  # lazy: --replay --no-judge needs no deps

    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def call_with_retry(fn, tries=4):
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - SDK raises several types
            if i == tries - 1:
                raise
            print("retry after %s" % type(exc).__name__, file=sys.stderr)
            time.sleep(2 ** i)


def generate(c, model, system, case, effort):
    def go():
        kwargs = dict(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": case["input"]}],
        )
        if effort:
            kwargs["output_config"] = {"effort": effort}
        resp = c.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, resp.usage.input_tokens, resp.usage.output_tokens

    return call_with_retry(go)


def judge_once(c, judge_model, case, output):
    def go():
        resp = c.messages.create(
            model=judge_model,
            max_tokens=4096,
            output_config=JUDGE_SCHEMA,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                input=case["input"], output=output, rubric=case["rubric"])}],
        )
        if resp.stop_reason == "refusal":
            return {"verdict": "FAIL", "evidence": "judge refused"}
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        return json.loads(text)

    return call_with_retry(go)


def code_grade(case, output):
    fails = []
    for pat in case.get("must_include", []):
        if not re.search(pat, output, re.IGNORECASE | re.DOTALL):
            fails.append("missing /%s/" % pat)
    for pat in case.get("must_not_include", []):
        if re.search(pat, output, re.IGNORECASE | re.DOTALL):
            fails.append("forbidden /%s/" % pat)
    limit = case.get("max_words")
    if limit and len(output.split()) > limit:
        fails.append("%d words > %d" % (len(output.split()), limit))
    return fails


def run_case(case, args, system, replay):
    rec = {"id": case["id"], "category": case.get("category", "general"),
           "critical": bool(case.get("critical"))}
    if replay is not None:
        output = replay.get(case["id"])
        if output is None:
            rec.update(passed=False, reasons=["no replayed output"], output="")
            return rec
    else:
        output, tin, tout = generate(client(), args.model, system, case, args.effort)
        rec["tokens"] = {"input": tin, "output": tout}
    rec["output"] = output

    reasons = code_grade(case, output)
    rec["code_pass"] = not reasons
    # Don't pay for a judge when a cheap grader already failed.
    if case.get("rubric") and not args.no_judge and not reasons:
        c = client()
        votes = [judge_once(c, args.judge_model, case, output) for _ in range(args.votes)]
        passes = sum(1 for v in votes if v.get("verdict") == "PASS")
        rec["judge"] = {"passes": passes, "votes": len(votes),
                        "evidence": [v.get("evidence", "")[:300] for v in votes]}
        if passes * 2 <= len(votes):
            reasons.append("judge %d/%d PASS" % (passes, len(votes)))
    rec["passed"] = not reasons
    rec["reasons"] = reasons
    return rec


def summarise(results):
    by_cat = {}
    for r in results:
        b = by_cat.setdefault(r["category"], [0, 0])
        b[0] += int(r["passed"])
        b[1] += 1
    total = sum(int(r["passed"]) for r in results)
    return {
        "pass_rate": round(total / max(len(results), 1), 4),
        "passed": total,
        "total": len(results),
        "by_category": {k: round(v[0] / v[1], 4) for k, v in sorted(by_cat.items())},
        "critical_failures": [r["id"] for r in results if r["critical"] and not r["passed"]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, help="system prompt file under test")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--judge-model", default="claude-opus-5-5")
    ap.add_argument("--effort", default=None, help="low|medium|high|xhigh|max")
    ap.add_argument("--votes", type=int, default=3)
    ap.add_argument("--replay", help="JSONL of saved outputs; skips generation")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--baseline", help="previous results.json to diff against")
    ap.add_argument("--tolerance", type=float, default=0.02, help="allowed pass-rate drop")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--out", default="results.json")
    args = ap.parse_args()

    needs_api = not args.replay or not args.no_judge
    if needs_api and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set (use --replay ... --no-judge for an offline run)",
              file=sys.stderr)
        return 2

    with open(args.system, encoding="utf-8") as fh:
        system = fh.read()
    cases = load_jsonl(args.cases)
    replay = None
    if args.replay:
        replay = {r["id"]: r["output"] for r in load_jsonl(args.replay)}

    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda c: run_case(c, args, system, replay), cases))

    summary = summarise(results)
    doc = {"model": args.model, "judge_model": None if args.no_judge else args.judge_model,
           "system_prompt": args.system, "summary": summary, "results": results}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)

    for r in results:
        print("%-4s %-28s %s" % ("ok" if r["passed"] else "FAIL", r["id"], "; ".join(r["reasons"])))
    print("pass rate %.1f%% (%d/%d)  by category %s" % (
        100 * summary["pass_rate"], summary["passed"], summary["total"], summary["by_category"]))

    status = 0
    if summary["critical_failures"]:
        print("CRITICAL: %s" % ", ".join(summary["critical_failures"]))
        status = 1
    if args.baseline and os.path.exists(args.baseline):
        with open(args.baseline, encoding="utf-8") as fh:
            base = json.load(fh)
        drop = base["summary"]["pass_rate"] - summary["pass_rate"]
        base_pass = {r["id"] for r in base["results"] if r["passed"]}
        newly_failing = [r["id"] for r in results if r["id"] in base_pass and not r["passed"]]
        print("baseline %.1f%% -> %.1f%%; newly failing: %s" % (
            100 * base["summary"]["pass_rate"], 100 * summary["pass_rate"],
            ", ".join(newly_failing) or "none"))
        if drop > args.tolerance:
            print("REGRESSION: pass rate dropped %.1f pts (tolerance %.1f)" % (
                100 * drop, 100 * args.tolerance))
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
