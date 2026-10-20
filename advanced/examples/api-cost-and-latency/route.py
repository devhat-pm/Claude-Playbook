#!/usr/bin/env python3
"""Route a request to a model + effort by task type and measured prompt size.

    export ANTHROPIC_API_KEY=...            # count_tokens is free but needs a key
    python3 route.py --task extract --prompt-file ticket.txt
    python3 route.py --task agentic --prompt-file spec.md --latency-critical
    python3 route.py --task classify --prompt-file x.txt --offline   # chars/3.5 estimate, no call

The routing table is a starting policy, not a law: replace each row with the cheapest
(model, effort) that passes YOUR evals (see bench.py --expect).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import PRICES, cost_usd  # noqa: E402

# task -> (model, effort, expected output tokens). Model roles follow the models
# overview: Haiku for high-volume classification/extraction/routing, Sonnet for the
# speed/intelligence balance, Opus as the default for agentic/knowledge work,
# Fable for the hardest long-horizon reasoning.
ROUTES: Dict[str, Tuple[str, str, int]] = {
    "classify":  ("claude-haiku-5-5", "low", 50),
    "extract":   ("claude-haiku-5-5", "low", 400),
    "summarize": ("claude-sonnet-5-5", "low", 800),
    "chat":      ("claude-sonnet-5-5", "medium", 600),
    "code":      ("claude-opus-5-5", "medium", 3000),
    "agentic":   ("claude-opus-5-5", "high", 8000),
    "research":  ("claude-fable-5-1", "high", 12000),
}
# Rough chars-per-token for the offline estimate. The current tokenizer (Opus 4.7 and
# later) yields ~30% more tokens than older ones, so this errs high on purpose.
CHARS_PER_TOKEN = 3.5


def count(model: str, text: str, offline: bool) -> int:
    if offline or not os.environ.get("ANTHROPIC_API_KEY"):
        return int(len(text) / CHARS_PER_TOKEN) + 10
    import anthropic
    return anthropic.Anthropic().messages.count_tokens(
        model=model, messages=[{"role": "user", "content": text}]).input_tokens


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--task", required=True, choices=sorted(ROUTES))
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--latency-critical", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    text = open(a.prompt_file, encoding="utf-8").read()

    model, effort, out_tok = ROUTES[a.task]
    notes = []
    n = count(model, text, a.offline)
    if model == "claude-haiku-5-5" and n > 100_000:
        notes.append("Haiku 5.5 bills prompts >100k at $0.50/$2.50 (5x); still the cheapest.")
    speed = "standard"
    if a.latency_critical:
        if model == "claude-opus-5-5":
            speed = "fast"
            notes.append("Opus 5.5 fast mode: up to 2.5x output tok/s at 2x price; not in Batch.")
        elif effort != "low":
            effort = "low"
            notes.append("Lowered effort for latency; re-check quality on your evals.")
    est = cost_usd(model, {"input_tokens": n, "output_tokens": out_tok}, speed=speed) or 0
    print("route: %s effort=%s speed=%s" % (model, effort, speed))
    print("prompt tokens: %d (%s)" % (n, "estimate" if a.offline else "count_tokens"))
    print("est. cost/request: $%.5f   per 1M requests: $%.0f" % (est, est * 1e6))
    print("alternatives (same tokens, expected output %d):" % out_tok)
    for m in PRICES:
        c = cost_usd(m, {"input_tokens": n, "output_tokens": out_tok}) or 0
        print("  %-18s $%.5f" % (m, c))
    for line in notes:
        print("note: " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
