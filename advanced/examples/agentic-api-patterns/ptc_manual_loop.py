"""Programmatic tool calling: Claude writes Python that calls your tool N times in the
code-execution container; only the aggregate comes back into context.

Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
Run:      python3 ptc_manual_loop.py

Grounded in https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling
"""
from __future__ import annotations

import json
import random
import time
from typing import Any, Dict, List, Optional

import anthropic

MODEL = "claude-opus-5-5"
CODE_EXEC = {"type": "code_execution_20260120", "name": "code_execution"}

TOOLS: List[Dict[str, Any]] = [
    CODE_EXEC,
    {
        "name": "get_expenses",
        "description": (
            "Return one employee's expense lines for a quarter. "
            "Output: JSON array of objects {date: str, category: str, amount_usd: number}. "
            "Can return several hundred rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "quarter": {"type": "string", "description": "e.g. 2026-Q3"},
            },
            "required": ["employee_id", "quarter"],
        },
        # Only callable from Claude's code, never directly (no strict: true here; PTC rejects it).
        "allowed_callers": ["code_execution_20260120"],
    },
]


def get_expenses(employee_id: str, quarter: str) -> str:
    rnd = random.Random(employee_id + quarter)
    rows = [
        {"date": "2026-07-%02d" % (i % 28 + 1), "category": rnd.choice(["travel", "meals", "software"]),
         "amount_usd": round(rnd.uniform(5, 900), 2)}
        for i in range(300)
    ]
    return json.dumps(rows)


def run(prompt: str) -> None:
    client = anthropic.Anthropic()
    messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
    container: Optional[str] = None

    for _ in range(40):
        kwargs: Dict[str, Any] = dict(model=MODEL, max_tokens=4096, tools=TOOLS, messages=messages)
        if container:
            kwargs["container"] = container  # mandatory while a programmatic call is pending
        resp = client.messages.create(**kwargs)
        if resp.container is not None:
            container = resp.container.id
        messages.append({"role": "assistant", "content": resp.content})  # append verbatim

        if resp.stop_reason == "pause_turn":
            continue  # server-tool loop hit its iteration cap; resend as-is
        if resp.stop_reason != "tool_use":
            for b in resp.content:
                if b.type == "text":
                    print(b.text)
            print("stop_reason:", resp.stop_reason, "| input tokens:", resp.usage.input_tokens)
            return

        results = []
        started = time.time()
        for b in resp.content:
            if b.type != "tool_use":
                continue
            caller = getattr(b, "caller", None)
            via = getattr(caller, "type", "direct")
            try:
                out = get_expenses(**b.input) if b.name == "get_expenses" else "unknown tool"
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            except Exception as exc:  # text-only error back into Claude's code
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": "Error: %s" % exc})
            print("served %s via %s" % (b.name, via))
        # Pending programmatic calls time out after ~4 min inside the container.
        if time.time() - started > 180:
            print("warning: tool latency is close to the programmatic-call timeout")
        # Reply must contain ONLY tool_result blocks when answering programmatic calls.
        messages.append({"role": "user", "content": results})

    print("gave up after 40 requests")


if __name__ == "__main__":
    run(
        "For employees E01..E20, pull 2026-Q3 expenses and list who exceeded $25,000 total "
        "or $5,000 in meals. Return a markdown table only."
    )
