#!/usr/bin/env python3
"""Daily usage/cost digest from the Usage and Cost Admin API, with two alerts.

  1. Spend: yesterday's cost vs --daily-budget-usd.
  2. Key anomaly: an API key whose tokens yesterday exceed --spike-x times its
     trailing mean (a cheap leaked-key detector), or a key you've never seen.

Also prints cache hit ratio per model, the number that most often explains a
cost jump after a prompt change.

Key: ANTHROPIC_ADMIN_KEY (sk-ant-admin01-...). Not available for individual
accounts or on Claude Platform on AWS. Stdlib only, Python 3.9+.

  python3 usage_cost_report.py --days 8 --daily-budget-usd 150
  python3 usage_cost_report.py --usage-fixture sample_usage.json --cost-fixture sample_cost.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.anthropic.com/v1/organizations"


def get_all(path: str, params: list, key: str) -> list:
    """Follow has_more/next_page and return every bucket."""
    buckets, page = [], None
    while True:
        q = list(params) + ([("page", page)] if page else [])
        req = urllib.request.Request(BASE + path + "?" + urllib.parse.urlencode(q), headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "user-agent": "claude-playbook-usage-report/1.0",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            doc = json.load(resp)
        buckets.extend(doc.get("data", []))
        if not doc.get("has_more"):
            return buckets
        page = doc.get("next_page")


def total_tokens(r: dict) -> int:
    cc = r.get("cache_creation") or {}
    return (r.get("uncached_input_tokens", 0) + r.get("cache_read_input_tokens", 0)
            + cc.get("ephemeral_5m_input_tokens", 0) + cc.get("ephemeral_1h_input_tokens", 0)
            + r.get("output_tokens", 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=8, help="window incl. yesterday (max 31)")
    ap.add_argument("--daily-budget-usd", type=float, default=None)
    ap.add_argument("--spike-x", type=float, default=3.0)
    ap.add_argument("--usage-fixture")
    ap.add_argument("--cost-fixture")
    args = ap.parse_args()

    if args.usage_fixture:
        with open(args.usage_fixture) as fh:
            usage = json.load(fh)["data"]
        with open(args.cost_fixture) as fh:
            cost = json.load(fh)["data"]
    else:
        key = os.environ.get("ANTHROPIC_ADMIN_KEY")
        if not key:
            print("set ANTHROPIC_ADMIN_KEY", file=sys.stderr)
            return 2
        today = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start = (today - dt.timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = today.strftime("%Y-%m-%dT%H:%M:%SZ")
        window = [("starting_at", start), ("ending_at", end), ("bucket_width", "1d"),
                  ("limit", "31")]
        usage = get_all("/usage_report/messages",
                        window + [("group_by[]", "model"), ("group_by[]", "api_key_id")], key)
        cost = get_all("/cost_report",
                       window + [("group_by[]", "workspace_id"), ("group_by[]", "description")],
                       key)

    if not usage:
        print("no usage buckets")
        return 0
    last_day = usage[-1]["starting_at"][:10]

    # Cache hit ratio per model over the window.
    per_model = {}
    for b in usage:
        for r in b["results"]:
            m = per_model.setdefault(r.get("model") or "?", [0, 0])
            m[0] += r.get("cache_read_input_tokens", 0)
            m[1] += total_tokens(r) - r.get("output_tokens", 0)
    print("cache hit ratio (cache_read / all input) by model:")
    for model, (hit, inp) in sorted(per_model.items()):
        print("  %-22s %5.1f%%  of %s input tokens" % (model, 100.0 * hit / max(inp, 1), inp))

    # Key anomaly: yesterday vs trailing mean.
    history = {}
    for b in usage:
        day = b["starting_at"][:10]
        for r in b["results"]:
            k = r.get("api_key_id") or "console/playground"
            history.setdefault(k, {}).setdefault(day, 0)
            history[k][day] += total_tokens(r)
    alerts = []
    for k, days in history.items():
        today_tokens = days.get(last_day, 0)
        prior = [v for d, v in days.items() if d != last_day]
        if not prior and today_tokens:
            alerts.append("NEW KEY %s used %d tokens on %s" % (k, today_tokens, last_day))
        elif prior:
            mean = sum(prior) / len(prior)
            if mean and today_tokens > args.spike_x * mean:
                alerts.append("SPIKE %s: %d tokens on %s vs %.0f trailing mean" % (
                    k, today_tokens, last_day, mean))

    # Spend: amounts are decimal strings in cents.
    spend = {}
    for b in cost:
        day = b["starting_at"][:10]
        for r in b["results"]:
            spend[day] = spend.get(day, 0.0) + float(r.get("amount", "0")) / 100.0
    if spend:
        print("daily spend (USD): " + ", ".join("%s %.2f" % (d, v) for d, v in sorted(spend.items())))
        y = spend.get(max(spend), 0.0)
        if args.daily_budget_usd is not None and y > args.daily_budget_usd:
            alerts.append("BUDGET %s spent $%.2f > $%.2f" % (max(spend), y, args.daily_budget_usd))

    for a in alerts:
        print("ALERT " + a)
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
