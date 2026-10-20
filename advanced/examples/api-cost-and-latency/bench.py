#!/usr/bin/env python3
"""Cost / latency / quality benchmark across Claude models, effort levels and speed.

    export ANTHROPIC_API_KEY=...            # never hardcode it
    pip install anthropic
    python3 bench.py --prompt-file task.txt --models claude-haiku-5-5 claude-sonnet-5-5 \
        claude-opus-5-5 --efforts low medium high --runs 5 --expect '"label":\s*"(spam|ham)"'
    python3 bench.py --prompt-file task.txt --models claude-opus-5-5 --speeds standard fast
    python3 bench.py --task-file task.json --models claude-haiku-5-5 --efforts low --runs 5
    python3 bench.py ... --dry-run          # print the matrix and exit, no API calls

Measures per cell (model x effort x speed), streaming so time-to-first-token is real:
  ttft_s   first content delta (thinking or text) after request start
  total_s  request start -> final message
  otps     output tokens / (total_s - ttft_s)
  cost     from response usage via pricing.py (list prices)
  pass     fraction of runs whose final text matches --expect (if given), or with
           --task-file the mean fraction of items labelled exactly right
--task-file takes a JSON list of {"id", "text", "label"}; every run sends all items in one
request and scores the returned {"id": "label"} object item by item.
Writes bench_results.csv (or .json if --out ends in .json) and prints a table of medians.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import PRICES, cost_usd  # noqa: E402

try:  # optional: pick up ANTHROPIC_API_KEY from a git-ignored .env next to this script
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

EFFORTS = ("low", "medium", "high", "xhigh", "max")
FAST_MODELS = {"claude-opus-5-5"}  # fast mode without beta header (fast-mode docs)


def one_run(client, model: str, effort: str, speed: str, system: str, prompt: str,
            max_tokens: int) -> Dict[str, object]:
    kwargs = dict(model=model, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}],
                  output_config={"effort": effort})
    if system:
        kwargs["system"] = system
    if speed == "fast":
        kwargs["speed"] = "fast"
    t0 = time.perf_counter()
    ttft: Optional[float] = None
    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if ttft is None and getattr(event, "type", "") == "content_block_delta":
                ttft = time.perf_counter() - t0
        msg = stream.get_final_message()
    total = time.perf_counter() - t0
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    u = msg.usage
    used_speed = getattr(u, "speed", None) or speed
    gen = total - (ttft or 0.0)
    return {
        "model": model, "effort": effort, "speed": used_speed,
        "ttft_s": round(ttft or total, 3), "total_s": round(total, 3),
        "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
        "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "otps": round(u.output_tokens / gen, 1) if gen > 0 else 0.0,
        "cost_usd": cost_usd(model, u, speed=used_speed),
        "stop_reason": msg.stop_reason, "text": text,
    }


def task_prompt(items: List[Dict[str, str]]) -> str:
    labels = sorted({it["label"] for it in items})
    lines = ["Classify each message below as one of: %s." % ", ".join(labels),
             'Reply with only a JSON object mapping each id to its label, e.g. {"1": "%s"}.'
             % labels[0], ""]
    for it in items:
        lines.append("<message id=\"%s\">\n%s\n</message>" % (it["id"], it["text"]))
    return "\n".join(lines)


def score(text: str, items: List[Dict[str, str]]) -> float:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        got = {}
    return sum(str(got.get(it["id"], "")).strip() == it["label"] for it in items) / len(items)


def median(xs: List[float]) -> float:
    return statistics.median(xs) if xs else float("nan")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt-file")
    src.add_argument("--task-file", help="JSON list of {id, text, label}; scored per item")
    ap.add_argument("--system-file")
    ap.add_argument("--models", nargs="+", default=list(PRICES))
    ap.add_argument("--efforts", nargs="+", default=["medium"], choices=EFFORTS)
    ap.add_argument("--speeds", nargs="+", default=["standard"], choices=["standard", "fast"])
    ap.add_argument("--runs", type=int, default=3)
    # 16k leaves room for adaptive thinking at high effort; raise to 64k+ for xhigh/max.
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--expect", help="regex the final text must match to count as a pass")
    ap.add_argument("--out", default="bench_results.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    items: List[Dict[str, str]] = []
    if args.task_file:
        with open(args.task_file, encoding="utf-8") as fh:
            items = json.load(fh)
        prompt = task_prompt(items)
    else:
        prompt = open(args.prompt_file, encoding="utf-8").read()
    system = open(args.system_file, encoding="utf-8").read() if args.system_file else ""
    cells = [(m, e, s) for m in args.models for e in args.efforts for s in args.speeds
             if s == "standard" or m in FAST_MODELS]
    print("%d cell(s) x %d run(s) = %d request(s)" % (len(cells), args.runs,
                                                      len(cells) * args.runs))
    if args.dry_run:
        for c in cells:
            print("  %s effort=%s speed=%s" % c)
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first.", file=sys.stderr)
        return 1
    import anthropic  # imported late so --dry-run works without the SDK

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    expect = re.compile(args.expect) if args.expect else None
    rows: List[Dict[str, object]] = []
    for model, effort, speed in cells:
        for i in range(args.runs):
            try:
                r = one_run(client, model, effort, speed, system, prompt, args.max_tokens)
            except anthropic.APIStatusError as exc:   # e.g. 400 unsupported combo, 429
                print("  %s/%s/%s run %d: HTTP %s %s" % (model, effort, speed, i + 1,
                                                         exc.status_code, exc.message))
                continue
            r["run"] = i + 1
            if items:
                r["pass"] = score(r["text"], items)
            else:
                r["pass"] = bool(expect.search(r["text"])) if expect else None
            rows.append(r)
            print("  %-18s %-6s %-8s run%d %6.2fs ttft %5.2fs out %5d $%.5f" % (
                model, effort, r["speed"], i + 1, r["total_s"], r["ttft_s"],
                r["output_tokens"], r["cost_usd"] or 0))

    fields = ["model", "effort", "speed", "run", "ttft_s", "total_s", "otps", "input_tokens",
              "output_tokens", "cache_read", "cost_usd", "stop_reason", "pass"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        if args.out.endswith(".json"):
            json.dump(rows, fh, indent=1)
        else:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    print("\n| model | effort | speed | p50 total s | p50 TTFT s | p50 OTPS | p50 out tok "
          "| mean $/req | $/1k req | pass |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for model, effort, speed in cells:
        rs = [r for r in rows if r["model"] == model and r["effort"] == effort
              and r["speed"] == speed]
        if not rs:
            continue
        mean_cost = statistics.mean(float(r["cost_usd"] or 0) for r in rs)
        passes = [r["pass"] for r in rs if r["pass"] is not None]
        print("| %s | %s | %s | %.2f | %.2f | %.0f | %.0f | %.5f | %.2f | %s |" % (
            model, effort, speed,
            median([float(r["total_s"]) for r in rs]),
            median([float(r["ttft_s"]) for r in rs]),
            median([float(r["otps"]) for r in rs]),
            median([float(r["output_tokens"]) for r in rs]),
            mean_cost, mean_cost * 1000,
            "%.0f%%" % (100.0 * sum(passes) / len(passes)) if passes else "-"))
    print("\nRaw rows: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
