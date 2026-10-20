#!/usr/bin/env python3
"""Measure prompt-cache hit rate, savings and TTFT for a fixed prefix + varying questions.

    export ANTHROPIC_API_KEY=...
    python3 cache_probe.py --doc handbook.md --questions qs.txt --model claude-sonnet-5-5
    python3 cache_probe.py ... --warm            # pre-warm with max_tokens=0 first
    python3 cache_probe.py ... --ttl 1h --gap 400   # check the 1h TTL survives a >5 min gap
    python3 cache_probe.py ... --dry-run         # show request layout, no calls

Layout (static -> dynamic; breakpoint on the LAST block that is identical every time):
    tools   (none here)
    system  [0] instructions   (static)
            [1] reference doc  (static)  <- cache_control breakpoint
    messages[0] user question  (varies; never put the breakpoint here)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import cost_usd, uncached_cost_usd  # noqa: E402

try:  # optional: pick up ANTHROPIC_API_KEY from a git-ignored .env next to this script
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

INSTRUCTIONS = ("You answer questions strictly from the reference document. "
                "Quote the section heading you used. Say 'not in document' otherwise.")


def build(model: str, doc: str, question: str, ttl: str, effort: str, max_tokens: int) -> dict:
    cc = {"type": "ephemeral"} if ttl == "5m" else {"type": "ephemeral", "ttl": "1h"}
    return dict(
        model=model, max_tokens=max_tokens,
        output_config={"effort": effort},          # keep identical across calls: it's in the cache key
        system=[{"type": "text", "text": INSTRUCTIONS},
                {"type": "text", "text": doc, "cache_control": cc}],
        messages=[{"role": "user", "content": question}],
    )


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", required=True)
    ap.add_argument("--questions", required=True, help="one question per line")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--ttl", choices=["5m", "1h"], default="5m")
    ap.add_argument("--gap", type=float, default=0.0, help="seconds between requests")
    ap.add_argument("--warm", action="store_true", help="send a max_tokens=0 warm-up first")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    doc = open(args.doc, encoding="utf-8").read()
    qs = [q.strip() for q in open(args.questions, encoding="utf-8") if q.strip()]
    if args.dry_run:
        req = build(args.model, doc[:80] + "...", qs[0] if qs else "?", args.ttl, args.effort,
                    args.max_tokens)
        import json
        print(json.dumps(req, indent=2))
        print("%d question(s); warm=%s; gap=%ss" % (len(qs), args.warm, args.gap))
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first.", file=sys.stderr)
        return 1
    import anthropic

    client = anthropic.Anthropic()
    # Free and exact enough to check the prefix clears the model's minimum cacheable length.
    n = client.messages.count_tokens(model=args.model, system=build(
        args.model, doc, "x", args.ttl, args.effort, 1)["system"],
        messages=[{"role": "user", "content": "x"}]).input_tokens
    print("prefix ~%d tokens (count_tokens estimate)" % n)

    if args.warm:
        w = client.messages.create(**build(args.model, doc, "warmup", args.ttl, args.effort, 0))
        print("warm-up: wrote %s cache tokens, stop_reason=%s"
              % (w.usage.cache_creation_input_tokens, w.stop_reason))

    tot, tot_uncached, read, prompt_total = 0.0, 0.0, 0, 0
    print("%-3s %8s %8s %8s %7s %7s %9s" % ("#", "write", "read", "uncach", "ttft_s", "hit%", "cost$"))
    for i, q in enumerate(qs):
        if i and args.gap:
            time.sleep(args.gap)
        t0, ttft = time.perf_counter(), None
        with client.messages.stream(**build(args.model, doc, q, args.ttl, args.effort,
                                            args.max_tokens)) as s:
            for ev in s:
                if ttft is None and getattr(ev, "type", "") == "content_block_delta":
                    ttft = time.perf_counter() - t0
            msg = s.get_final_message()
        u = msg.usage
        w_, r_, i_ = (u.cache_creation_input_tokens or 0, u.cache_read_input_tokens or 0,
                      u.input_tokens)
        c, c0 = cost_usd(args.model, u) or 0.0, uncached_cost_usd(args.model, u) or 0.0
        tot, tot_uncached = tot + c, tot_uncached + c0
        read, prompt_total = read + r_, prompt_total + w_ + r_ + i_
        print("%-3d %8d %8d %8d %7.2f %6.0f%% %9.5f" % (
            i + 1, w_, r_, i_, ttft or 0, 100.0 * r_ / max(1, w_ + r_ + i_), c))
        if w_ == 0 and r_ == 0:
            print("    ^ nothing cached: prefix below the model minimum, or breakpoint misplaced")

    print("\nhit ratio (read / all prompt tokens): %.1f%%" % (100.0 * read / max(1, prompt_total)))
    print("cost with cache $%.4f vs without $%.4f  (saved %.0f%%)" % (
        tot, tot_uncached, 100.0 * (1 - tot / tot_uncached) if tot_uncached else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
