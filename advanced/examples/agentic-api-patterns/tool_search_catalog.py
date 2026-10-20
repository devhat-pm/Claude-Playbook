"""Tool search over a 150-tool catalog: defer everything except a few hot tools,
log what Claude discovers, and lint descriptions so regex/BM25 can find them.

Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
Run:      python3 tool_search_catalog.py --lint            # offline checks only
          python3 tool_search_catalog.py "Open a Jira ticket for the failing deploy"

Grounded in https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from typing import Any, Dict, List

MODEL = "claude-sonnet-5-5"
HOT = {"github_search_code", "slack_post_message", "jira_create_issue"}  # 3-5 non-deferred
SEARCH_TOOL = {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"}

SERVICES = {
    "github": ["search_code", "get_pr", "list_prs", "comment_pr", "merge_pr", "get_file",
               "list_issues", "create_issue", "close_issue", "list_workflows"],
    "slack": ["post_message", "search_messages", "list_channels", "get_thread", "add_reaction"],
    "jira": ["create_issue", "get_issue", "transition_issue", "search_jql", "add_comment"],
    "sentry": ["list_issues", "get_event", "resolve_issue", "search_traces"],
    "grafana": ["query_prometheus", "get_dashboard", "list_alerts", "silence_alert"],
}


def build_catalog(pad_to: int = 150) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for svc, verbs in SERVICES.items():
        for verb in verbs:
            name = "%s_%s" % (svc, verb)  # service prefix -> one search hits the group
            tools.append({
                "name": name,
                "description": "%s: %s. Keywords: %s, %s." % (
                    svc.capitalize(), verb.replace("_", " "), svc, verb.split("_")[0]),
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "free text or id"}},
                    "required": ["query"],
                },
            })
    i = 0
    while len(tools) < pad_to:  # stand-ins for the long tail of internal tools
        tools.append({
            "name": "internal_report_%03d" % i,
            "description": "Internal BI report %03d: weekly revenue cut by region and SKU." % i,
            "input_schema": {"type": "object", "properties": {}, "required": []},
        })
        i += 1
    for t in tools:
        if t["name"] not in HOT:
            t["defer_loading"] = True  # still sent every request; only enters context on discovery
    return [SEARCH_TOOL] + tools  # never defer the search tool itself


def lint(tools: List[Dict[str, Any]]) -> int:
    problems = 0
    names = [t.get("name") for t in tools]
    dupes = [n for n, c in Counter(names).items() if c > 1]
    if dupes:
        print("duplicate names:", dupes)
        problems += 1
    if all(t.get("defer_loading") for t in tools):
        print("400 risk: every tool is deferred")
        problems += 1
    for t in tools:
        if t.get("defer_loading") and "cache_control" in t:
            print("400 risk: deferred tool with cache_control:", t["name"])
            problems += 1
        if "type" not in t and not re.match(r"^[a-z]+_", t["name"]):
            print("no service prefix:", t["name"])
            problems += 1
        if "type" not in t and len(t.get("description", "")) < 25:
            print("description too thin to be found:", t["name"])
            problems += 1
    deferred = sum(1 for t in tools if t.get("defer_loading"))
    print("tools=%d deferred=%d hot=%d problems=%d" % (len(tools), deferred, len(tools) - deferred - 1, problems))
    return problems


def run(prompt: str, tools: List[Dict[str, Any]]) -> None:
    import anthropic  # imported lazily so --lint works without the SDK

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system="You can search for tools to work with GitHub, Slack, Jira, Sentry, Grafana and internal BI reports.",
        tools=tools,
        messages=[{"role": "user", "content": prompt}],
    )
    for b in resp.content:
        if b.type == "server_tool_use":
            print("search:", json.dumps(b.input))
        elif b.type == "tool_search_tool_result":
            refs = getattr(b.content, "tool_references", None) or []
            print("discovered:", [r.tool_name for r in refs])
        elif b.type == "tool_use":
            print("call:", b.name, json.dumps(b.input))
        elif b.type == "text":
            print(b.text)
    print("stop_reason:", resp.stop_reason, "input_tokens:", resp.usage.input_tokens)
    # Next turn: append resp.content unchanged (server_tool_use + tool_search_tool_result
    # included), add tool_result only for the client tool_use ids, resend the SAME tools list.


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--lint", action="store_true")
    a = ap.parse_args()
    catalog = build_catalog()
    if lint(catalog) or a.lint or not a.prompt:
        raise SystemExit(0)
    run(a.prompt, catalog)
