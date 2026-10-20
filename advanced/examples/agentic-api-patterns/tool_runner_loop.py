"""Tool runner loop with an approval gate, error interception and a token-limit retry.

Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
Run:      python3 tool_runner_loop.py "Refund order 1042 and tell me the new balance"

Grounded in https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner
"""
from __future__ import annotations

import json
import sys
from typing import Dict

import anthropic
from anthropic import beta_tool

MODEL = "claude-sonnet-5-5"
FAKE_DB: Dict[str, float] = {"1042": 59.0, "1043": 12.5}
BALANCE = {"value": 1000.0}
DESTRUCTIVE = {"refund_order"}  # tools that need a human "y" before they run


@beta_tool
def get_order(order_id: str) -> str:
    """Look up an order's amount.

    Args:
        order_id: Numeric order id, e.g. "1042".
    """
    if order_id not in FAKE_DB:
        raise KeyError(f"order {order_id} not found")  # runner returns is_error=True
    return json.dumps({"order_id": order_id, "amount": FAKE_DB[order_id]})


@beta_tool
def refund_order(order_id: str) -> str:
    """Refund an order in full. Irreversible.

    Args:
        order_id: Numeric order id to refund.
    """
    amount = FAKE_DB.pop(order_id)
    BALANCE["value"] -= amount
    return json.dumps({"refunded": amount, "balance": BALANCE["value"]})


def run_once(client: anthropic.Anthropic, prompt: str, max_tokens: int) -> str:
    """Returns the final stop_reason so the caller can retry with a bigger budget."""
    last_stop = "end_turn"
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=max_tokens,
        max_iterations=8,  # hard ceiling on model round trips
        tools=[get_order, refund_order],
        messages=[{"role": "user", "content": prompt}],
    )

    for message in runner:
        last_stop = message.stop_reason or last_stop
        # 1) A truncated turn with no tool call ends the runner's loop; the caller retries.

        # 2) Refusal: stop; don't feed a refused turn back in.
        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            print("REFUSED:", getattr(details, "category", None))
            return "refusal"

        # 3) Human gate on destructive tools. Denying = take over history for this turn.
        calls = [b for b in message.content if b.type == "tool_use"]
        risky = [c for c in calls if c.name in DESTRUCTIVE]
        if risky:
            answer = input(f"Allow {[(c.name, c.input) for c in risky]}? [y/N] ")
            if answer.strip().lower() != "y":
                runner.append_messages(
                    message,
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": c.id,
                                "content": "Denied by operator. Do not retry.",
                                "is_error": True,
                            }
                            for c in calls
                        ],
                    },
                )
                continue

        # 4) Inspect tool results before they go back to Claude.
        tool_response = runner.generate_tool_call_response()
        if tool_response is not None:
            for block in tool_response["content"]:
                if block.get("is_error"):
                    print("tool error ->", json.dumps(block.get("content"))[:200])

        for block in message.content:
            if block.type == "text":
                print(block.text)
    return last_stop


def main(prompt: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    for budget in (1024, 4096):
        if run_once(client, prompt, budget) != "max_tokens":
            return
        print(f"[truncated at max_tokens={budget}; retrying with a larger budget]")


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or "What is order 1042 worth? Then refund it.")
