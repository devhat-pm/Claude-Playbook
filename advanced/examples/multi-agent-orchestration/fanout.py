#!/usr/bin/env python3
"""Orchestrator/worker fan-out on the Messages API.

1. PLAN   - orchestrator (Opus 5.5 or Fable 5.1) splits the job into <= N independent
            subtasks, each naming the files it needs (structured output).
2. FANOUT - Haiku 5.5 workers run the subtasks in parallel, each in its own small
            context, returning structured findings with verbatim evidence.
3. MERGE  - deterministic dedupe in Python, then the orchestrator reconciles
            conflicts and writes the final report from findings only (never raw files).

Usage:
    export ANTHROPIC_API_KEY=...
    python3 fanout.py --job "Find every place we build SQL by string concatenation" \
        --root ./src --glob "**/*.py" --max-workers 8
    python3 fanout.py --job "..." --root ./src --dry-run   # plan inputs + cost estimate, no API calls

Requires: pip install anthropic
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

MODELS = {"opus": "claude-opus-5-5", "fable": "claude-fable-5-1", "haiku": "claude-haiku-5-5"}
# USD per million tokens (input, output). Checked against the pricing page; re-check before relying on it.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),  # prompts <= 100k tokens; 0.50/2.50 above
}
HAIKU_TIER_LIMIT = 100_000
WORKER_CHAR_BUDGET = 300_000  # ~75k tokens: stays under Haiku 5.5's 100k price tier

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "instruction": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "instruction", "files"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["subtasks"],
    "additionalProperties": False,
}

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["file", "line", "claim", "evidence"],
                "additionalProperties": False,
            },
        },
        "unsure": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["findings", "unsure"],
    "additionalProperties": False,
}

WORKER_SYSTEM = (
    "You are one worker in a fan-out. Do only your subtask. Report only what you can quote: "
    "every finding needs the exact source line in `evidence`. Put anything you suspect but "
    "cannot quote in `unsure`. Never speculate about files you were not given."
)


def cost(model: str, usage: Any) -> float:
    pin, pout = PRICES[model]
    if model == "claude-haiku-5-5" and usage.input_tokens > HAIKU_TIER_LIMIT:
        pin, pout = 0.50, 2.50
    return (usage.input_tokens * pin + usage.output_tokens * pout) / 1e6


def text_of(resp: Any) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def plan(client: Any, model: str, job: str, files: List[str], n: int) -> Tuple[List[Dict], float]:
    prompt = (
        "Job: %s\n\nSplit this into at most %d independent subtasks for small, fast workers. "
        "Each subtask names the exact files it needs from the list below (no overlap unless "
        "required), and an instruction a worker can follow without seeing anything else. "
        "Prefer fewer, larger subtasks; if one worker can do it, return one.\n\nFiles:\n%s"
    ) % (job, n, "\n".join(files))
    resp = client.messages.create(
        model=model, max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
    )
    return json.loads(text_of(resp))["subtasks"][:n], cost(model, resp.usage)


def pack(root: Path, files: List[str]) -> str:
    parts, used = [], 0
    for f in files:
        p = (root / f).resolve()
        try:
            p.relative_to(root)
            body = p.read_text(errors="replace")
        except (ValueError, OSError):
            continue
        numbered = "\n".join("%d: %s" % (i + 1, l) for i, l in enumerate(body.splitlines()))
        if used + len(numbered) > WORKER_CHAR_BUDGET:
            parts.append("<truncated: remaining files omitted to stay under budget/>")
            break
        parts.append('<file path="%s">\n%s\n</file>' % (f, numbered))
        used += len(numbered)
    return "\n".join(parts)


async def worker(aclient: Any, sem: asyncio.Semaphore, root: Path, st: Dict) -> Tuple[Dict, float]:
    async with sem:
        model = MODELS["haiku"]
        content = "Subtask %s: %s\n\n%s" % (st["id"], st["instruction"], pack(root, st["files"]))
        try:
            resp = await aclient.messages.create(
                model=model, max_tokens=4000, system=WORKER_SYSTEM,
                messages=[{"role": "user", "content": content}],
                output_config={"format": {"type": "json_schema", "schema": FINDINGS_SCHEMA}},
            )
            out = json.loads(text_of(resp))
            out["subtask"] = st["id"]
            return out, cost(model, resp.usage)
        except Exception as e:  # one failed worker must not sink the run
            return {"subtask": st["id"], "findings": [], "unsure": [], "error": str(e)}, 0.0


def dedupe(results: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for r in results:
        for f in r["findings"]:
            key = (f["file"], f["line"], f["claim"].strip().lower()[:80])
            if key not in seen:
                seen.add(key)
                out.append(dict(f, subtask=r["subtask"]))
    return out


def merge(client: Any, model: str, job: str, findings: List[Dict], results: List[Dict]) -> Tuple[str, float]:
    unsure = [u for r in results for u in r.get("unsure", [])]
    errors = [r["subtask"] for r in results if r.get("error")]
    prompt = (
        "Job: %s\n\nWorker findings (deduplicated, each with quoted evidence):\n%s\n\n"
        "Unverified suspicions:\n%s\n\nFailed subtasks: %s\n\n"
        "Write the final report. Drop findings whose evidence does not support the claim. "
        "Group by severity. List failed subtasks as coverage gaps; do not guess their results."
    ) % (job, json.dumps(findings, indent=1), json.dumps(unsure), errors or "none")
    resp = client.messages.create(model=model, max_tokens=8000,
                                  messages=[{"role": "user", "content": prompt}])
    return text_of(resp), cost(model, resp.usage)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", default="**/*.py")
    ap.add_argument("--orchestrator", choices=["opus", "fable"], default="opus")
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    files = sorted(str(p.relative_to(root)) for p in root.glob(args.glob) if p.is_file())[:2000]
    orch = MODELS[args.orchestrator]

    if args.dry_run:
        chars = sum((root / f).stat().st_size for f in files)
        tok = chars // 4
        w_in, w_out = PRICES["claude-haiku-5-5"]
        o_in, o_out = PRICES[orch]
        est = (tok * w_in + args.max_workers * 2000 * w_out) / 1e6 + (30000 * o_in + 12000 * o_out) / 1e6
        print("%d files, ~%d tokens of source. orchestrator=%s workers<=%d" % (len(files), tok, orch, args.max_workers))
        print("rough cost estimate: $%.2f (all source read once by Haiku; plan+merge on %s)" % (est, orch))
        print("same job single-agent on %s reading all source: ~$%.2f input alone" % (orch, tok * o_in / 1e6))
        print("fan-out pays off when source tokens dwarf the ~42k-token plan+merge overhead; below that, use one agent")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("set ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    import anthropic

    client = anthropic.Anthropic()
    aclient = anthropic.AsyncAnthropic()
    subtasks, spent = plan(client, orch, args.job, files, args.max_workers)
    print("plan: %d subtasks ($%.3f)" % (len(subtasks), spent), file=sys.stderr)

    async def run_all() -> List[Tuple[Dict, float]]:
        sem = asyncio.Semaphore(args.concurrency)
        return await asyncio.gather(*(worker(aclient, sem, root, st) for st in subtasks))

    pairs = asyncio.run(run_all())
    results = [r for r, _ in pairs]
    spent += sum(c for _, c in pairs)
    findings = dedupe(results)
    print("workers: %d findings after dedupe ($%.3f so far)" % (len(findings), spent), file=sys.stderr)
    report, c = merge(client, orch, args.job, findings, results)
    spent += c
    print(report)
    print("\n[total cost ~$%.3f]" % spent, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
