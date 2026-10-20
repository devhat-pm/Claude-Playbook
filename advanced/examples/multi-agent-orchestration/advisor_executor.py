#!/usr/bin/env python3
"""Executor/advisor: a Haiku 5.5 executor that consults an Opus 5.5 (or Fable 5.1) advisor.

Uses the advisor tool (beta advisor-tool-2026-03-01). The executor does all the
tool calls and writes all the output at Haiku rates; the advisor reads the whole
transcript server-side at plan/stuck/done moments and returns short guidance.

Includes: the Haiku coding system prompt from the docs (abridged), a per-request
advisor cap (max_uses), a per-call output cap (max_tokens), advisor caching, a
conversation-level cap enforced client-side, pause_turn handling, and per-model
cost from usage.iterations.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 advisor_executor.py --workdir ./sandbox --task "Implement slugify() in slug.py with tests; run them"
    python3 advisor_executor.py --task x --dry-run

Requires: pip install anthropic. The run_cmd tool executes shell commands in --workdir:
point it at a disposable directory or container.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

EXECUTOR = "claude-haiku-5-5"
ADVISORS = {"opus": "claude-opus-5-5", "fable": "claude-fable-5-1"}
BETAS = ["advisor-tool-2026-03-01"]
PRICES = {  # USD/MTok (input, output); Haiku shown for prompts <= 100k tokens
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-fable-5-1": (10.0, 50.0),
}

SYSTEM = """You are a coding agent working in a sandbox directory.

You have access to an `advisor` tool backed by a stronger reviewer model. It takes NO parameters -- when you call advisor(), your entire conversation history is automatically forwarded.

Call advisor BEFORE substantive work -- before writing, before committing to an interpretation. Orientation first (list files, read them), then call advisor. Also call advisor when you believe the task is complete (write the files first), when stuck, and when considering a change of approach.

Give the advice serious weight. If a step fails empirically or a file contradicts a claim, adapt. If your evidence and the advice disagree, surface the conflict in one more advisor call instead of silently switching.

Hard rule: your first write_file or state-changing run_cmd on a task must be preceded by an advisor call. Read-only commands (ls, cat, grep) are not state-changing."""

CLIENT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read a file in the sandbox.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file in the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_cmd",
        "description": "Run a shell command in the sandbox root (60s timeout). Returns exit code and output.",
        "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]},
    },
]


def advisor_tool(model: str, per_request_cap: int) -> Dict[str, Any]:
    return {
        "type": "advisor_20260301",
        "name": "advisor",
        "model": model,
        "max_uses": per_request_cap,
        "max_tokens": 2048,  # caps advisor thinking+text per call (min 1024)
        "caching": {"type": "ephemeral", "ttl": "5m"},  # worth it at >= 3 calls per conversation
    }


def safe(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    p.relative_to(root)  # raises ValueError if outside
    return p


def run_client_tool(name: str, inp: Dict[str, Any], root: Path) -> str:
    if name == "read_file":
        return safe(root, inp["path"]).read_text(errors="replace")[:50000]
    if name == "write_file":
        p = safe(root, inp["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inp["content"])
        return "wrote %s (%d bytes)" % (inp["path"], len(inp["content"]))
    if name == "run_cmd":
        r = subprocess.run(inp["cmd"], shell=True, cwd=str(root), capture_output=True, text=True, timeout=60)
        return "exit=%d\n%s%s" % (r.returncode, r.stdout[-8000:], r.stderr[-4000:])
    raise ValueError("unknown tool " + name)


def field(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def iteration_costs(usage: Any, advisor_model: str) -> Dict[str, float]:
    out = {"executor": 0.0, "advisor": 0.0, "advisor_calls": 0}
    for it in field(usage, "iterations", None) or []:
        kind = field(it, "type")
        model = field(it, "model") or (advisor_model if kind == "advisor_message" else EXECUTOR)
        pin, pout = PRICES.get(model, PRICES[EXECUTOR])
        c = ((field(it, "input_tokens", 0) or 0) * pin + (field(it, "output_tokens", 0) or 0) * pout) / 1e6
        if kind == "advisor_message":
            out["advisor"] += c
            out["advisor_calls"] += 1
        else:
            out["executor"] += c
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--workdir", default="./sandbox")
    ap.add_argument("--advisor", choices=list(ADVISORS), default="opus")
    ap.add_argument("--advisor-cap", type=int, default=4, help="advisor calls per conversation")
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    advisor_model = ADVISORS[args.advisor]

    if args.dry_run:
        print(json.dumps({"model": EXECUTOR, "betas": BETAS,
                          "tools": [advisor_tool(advisor_model, 2)] + [t["name"] for t in CLIENT_TOOLS]}, indent=2))
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("set ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    import anthropic

    client = anthropic.Anthropic()
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Soft length cap addressed to the advisor directly, as the docs recommend.
    messages: List[Dict[str, Any]] = [{"role": "user", "content": args.task +
                                       "\n\n(Advisor: please keep your guidance under 80 words.)"}]
    totals = {"executor": 0.0, "advisor": 0.0, "advisor_calls": 0}
    advisor_enabled = True

    for step in range(args.max_steps):
        tools = list(CLIENT_TOOLS)
        if advisor_enabled:
            tools.insert(0, advisor_tool(advisor_model, per_request_cap=2))
        resp = client.beta.messages.create(
            model=EXECUTOR, max_tokens=8000, system=SYSTEM,
            messages=messages, tools=tools, betas=BETAS,
        )
        c = iteration_costs(resp.usage, advisor_model)
        for k in totals:
            totals[k] += c[k]
        # Round-trip all content verbatim, including advisor_tool_result blocks.
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "pause_turn":
            continue  # advisor call pending: resend with the advisor tool still present
        called = {b.id for b in resp.content if b.type == "server_tool_use"}
        answered = {b.tool_use_id for b in resp.content if b.type == "advisor_tool_result"}
        if totals["advisor_calls"] >= args.advisor_cap and not (called - answered):
            # conversation-level cap; old result blocks can stay. Never drop the tool while
            # a call is pending (that is a 400).
            advisor_enabled = False
        if resp.stop_reason != "tool_use":
            print("".join(b.text for b in resp.content if b.type == "text"))
            break
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            try:
                out = run_client_tool(b.name, b.input, root)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as e:
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": str(e), "is_error": True})
        messages.append({"role": "user", "content": results})

    print("\nadvisor calls=%d executor=$%.4f advisor=$%.4f total=$%.4f" % (
        totals["advisor_calls"], totals["executor"], totals["advisor"],
        totals["executor"] + totals["advisor"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
