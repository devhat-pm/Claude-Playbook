#!/usr/bin/env python3
"""Message Batches pipeline: JSONL in -> batch(es) -> JSONL out, with retry file and cost.

    export ANTHROPIC_API_KEY=...
    python3 batch_pipeline.py submit  items.jsonl --model claude-haiku-5-5 --system-file rubric.md
    python3 batch_pipeline.py status
    python3 batch_pipeline.py collect --out results.jsonl     # waits until every batch has ended
    python3 batch_pipeline.py submit  retry.jsonl ...         # resubmit retryable failures
    python3 batch_pipeline.py submit  items.jsonl ... --dry-run   # build + size-check, no calls

items.jsonl: one {"id": "...", "text": "..."} per line. ids are sanitised to the
custom_id rule ^[a-zA-Z0-9_-]{1,64}$ and must be unique.
State (batch ids, id map) lives in .batch_state.json in the current directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import cost_usd  # noqa: E402

STATE = ".batch_state.json"
# Documented limits: 100,000 requests or 256 MB per batch. Stay under both with margin.
MAX_REQ_PER_BATCH = 100_000
MAX_BYTES_PER_BATCH = 200 * 1024 * 1024
POLL_S = 60  # most batches finish within an hour; polling faster just burns rate limit


def safe_id(raw: str, used: set) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]", "_", str(raw))[:56] or "item"
    cid, n = base, 1
    while cid in used:
        cid, n = "%s-%d" % (base, n), n + 1
    used.add(cid)
    return cid


def build_requests(items: List[dict], model: str, system: str, max_tokens: int,
                   effort: str) -> List[dict]:
    used: set = set()
    reqs = []
    for it in items:
        params = {
            "model": model, "max_tokens": max_tokens,
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": it["text"]}],
        }
        if system:
            # Identical cached prefix in every request = best-effort cache hits inside the batch.
            params["system"] = [{"type": "text", "text": system,
                                 "cache_control": {"type": "ephemeral"}}]
        reqs.append({"custom_id": safe_id(it["id"], used), "params": params,
                     "_orig_id": it["id"]})
    return reqs


def chunk(reqs: List[dict]) -> List[List[dict]]:
    out, cur, size = [], [], 0
    for r in reqs:
        b = len(json.dumps(r))
        if cur and (len(cur) >= MAX_REQ_PER_BATCH or size + b > MAX_BYTES_PER_BATCH):
            out.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += b
    if cur:
        out.append(cur)
    return out


def load_state() -> Dict:
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"batches": [], "id_map": {}, "model": None}


def save_state(st: Dict) -> None:
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)


def cmd_submit(a, client) -> int:
    with open(a.items, encoding="utf-8") as fh:
        items = [json.loads(line) for line in fh if line.strip()]
    system = open(a.system_file, encoding="utf-8").read() if a.system_file else ""
    reqs = build_requests(items, a.model, system, a.max_tokens, a.effort)
    groups = chunk(reqs)
    print("%d request(s) -> %d batch(es)" % (len(reqs), len(groups)))
    if a.dry_run:
        print(json.dumps({k: v for k, v in reqs[0].items() if k != "_orig_id"}, indent=2)[:1500])
        return 0
    st = load_state()
    st["model"] = a.model
    for g in groups:
        batch = client.messages.batches.create(
            requests=[{"custom_id": r["custom_id"], "params": r["params"]} for r in g])
        st["batches"].append(batch.id)
        for r in g:
            st["id_map"][r["custom_id"]] = r["_orig_id"]
        print("created %s (%d requests)" % (batch.id, len(g)))
    save_state(st)
    return 0


def cmd_status(_a, client) -> int:
    for bid in load_state()["batches"]:
        b = client.messages.batches.retrieve(bid)
        print(bid, b.processing_status, b.request_counts)
    return 0


def cmd_collect(a, client) -> int:
    st = load_state()
    while True:
        pending = [b for b in st["batches"]
                   if client.messages.batches.retrieve(b).processing_status != "ended"]
        if not pending:
            break
        print("%d batch(es) still processing; sleeping %ds" % (len(pending), POLL_S))
        time.sleep(POLL_S)

    counts = {"succeeded": 0, "errored": 0, "canceled": 0, "expired": 0}
    usd, retry = 0.0, []
    with open(a.out, "w", encoding="utf-8") as out:
        for bid in st["batches"]:
            for res in client.messages.batches.results(bid):   # order is NOT guaranteed
                kind = res.result.type
                counts[kind] = counts.get(kind, 0) + 1
                orig = st["id_map"].get(res.custom_id, res.custom_id)
                row = {"id": orig, "status": kind}
                if kind == "succeeded":
                    m = res.result.message
                    row["text"] = "".join(b.text for b in m.content
                                          if getattr(b, "type", "") == "text")
                    row["usage"] = m.usage.model_dump() if hasattr(m.usage, "model_dump") else None
                    usd += cost_usd(m.model, m.usage, batch=True) or 0.0
                elif kind == "errored":
                    etype = res.result.error.error.type
                    row["error"] = etype
                    if etype != "invalid_request_error":   # invalid ones need a fixed body
                        retry.append(orig)
                elif kind == "expired":
                    retry.append(orig)
                out.write(json.dumps(row) + "\n")
    print("results:", counts, "-> %s" % a.out)
    print("batch cost (list price, 50%% off, incl. cache): $%.4f" % usd)
    if retry and a.items_for_retry:
        with open(a.items_for_retry, encoding="utf-8") as fh:
            src = {str(json.loads(l)["id"]): l for l in fh if l.strip()}
        with open("retry.jsonl", "w", encoding="utf-8") as fh:
            for rid in retry:
                if str(rid) in src:
                    fh.write(src[str(rid)])
        print("%d retryable item(s) -> retry.jsonl" % len(retry))
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("items")
    s.add_argument("--model", default="claude-haiku-5-5")
    s.add_argument("--system-file")
    s.add_argument("--max-tokens", type=int, default=1024)
    s.add_argument("--effort", default="low")
    s.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    c = sub.add_parser("collect")
    c.add_argument("--out", default="results.jsonl")
    c.add_argument("--items-for-retry", help="original items.jsonl, to write retry.jsonl")
    a = ap.parse_args(argv)

    client = None
    if not (a.cmd == "submit" and a.dry_run):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Set ANTHROPIC_API_KEY first.", file=sys.stderr)
            return 1
        import anthropic
        client = anthropic.Anthropic()
    return {"submit": cmd_submit, "status": cmd_status, "collect": cmd_collect}[a.cmd](a, client)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
