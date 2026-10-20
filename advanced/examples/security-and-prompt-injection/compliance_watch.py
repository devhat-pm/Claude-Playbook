#!/usr/bin/env python3
"""Poll the Compliance API Activity Feed for security-relevant events.

Watches for new connector/MCP grants, tool-policy changes and new API keys,
prints one JSON line per hit (pipe to your SIEM or Slack webhook), and stores a
cursor so each run only sees new activity.

Key: ANTHROPIC_COMPLIANCE_ACCESS_KEY (Compliance Access Key or an Admin API key;
both can read the Activity Feed with the read:compliance_activities scope).

  python3 compliance_watch.py --since 2026-10-01T00:00:00Z     # first run
  python3 compliance_watch.py                                  # incremental (cron)
  python3 compliance_watch.py --fixture sample_activities.json # offline test

Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.anthropic.com/v1/compliance/activities"

# Activity types from the Compliance API reference. Extend as needed; the feed
# has hundreds of types, see /docs/en/api/compliance/activities/list.
WATCH = [
    "integration_user_connected",
    "mcp_server_created",
    "mcp_server_updated",
    "mcp_tool_policy_updated",
    "mcp_tools_enabled",
    "platform_api_key_created",
    "admin_api_key_created",
    "role_assignment_granted",
]


def fetch_page(key: str, params: list) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "user-agent": "claude-playbook-compliance-watch/1.0",
    })
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code == 429 or err.code >= 500:
                time.sleep(2 ** attempt)  # same cursor is safe to retry
                continue
            raise
    raise RuntimeError("gave up after retries")


def walk(key: str, since: str | None, newest_seen: str | None):
    """Yield activities newer than the stored marker, newest first."""
    base = [("limit", "500")] + [("activity_types[]", t) for t in WATCH]
    if since:
        base.append(("created_at.gte", since))
    after = None
    while True:
        params = list(base) + ([("after_id", after)] if after else [])
        page = fetch_page(key, params)
        for act in page.get("data", []):
            if newest_seen and act["id"] == newest_seen:
                return
            yield act
        if not page.get("has_more"):
            return
        after = page.get("last_id")


def summarise(act: dict) -> dict:
    actor = act.get("actor") or {}
    who = actor.get("email_address") or actor.get("api_key_id") or actor.get("admin_api_key_id")
    extra = {k: v for k, v in act.items()
             if k not in ("id", "created_at", "actor", "type", "organization_uuid")}
    return {
        "at": act.get("created_at"),
        "type": act.get("type"),
        "actor_type": actor.get("type"),
        "actor": who,
        "ip": actor.get("ip_address"),
        "details": extra,
        "activity_id": act.get("id"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="RFC 3339 lower bound for the first run")
    ap.add_argument("--state", default=".compliance_watch_state.json")
    ap.add_argument("--fixture", help="read activities from a local JSON file instead")
    args = ap.parse_args()

    state = {}
    if os.path.exists(args.state):
        with open(args.state) as fh:
            state = json.load(fh)

    if args.fixture:
        with open(args.fixture) as fh:
            acts = [a for a in json.load(fh)["data"] if a.get("type") in WATCH]
    else:
        key = os.environ.get("ANTHROPIC_COMPLIANCE_ACCESS_KEY")
        if not key:
            print("set ANTHROPIC_COMPLIANCE_ACCESS_KEY", file=sys.stderr)
            return 2
        acts = list(walk(key, args.since, state.get("newest_id")))

    for act in acts:
        print(json.dumps(summarise(act)))

    if acts and not args.fixture:
        # Persist only after everything above was emitted.
        state["newest_id"] = acts[0]["id"]
        with open(args.state, "w") as fh:
            json.dump(state, fh)
    print("%d matching activities" % len(acts), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
