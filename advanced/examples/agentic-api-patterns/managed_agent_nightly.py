"""Managed Agents worked example: a nightly dependency-triage agent with memory,
a cron deployment, a per-run budget, and a manual test run.

Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
Run:      python3 managed_agent_nightly.py setup      # creates store, agent, env, deployment
          python3 managed_agent_nightly.py run        # fires one manual run now, streams nothing
          python3 managed_agent_nightly.py runs       # deployment run history (errors included)
          python3 managed_agent_nightly.py memories   # what the agent has learned so far
IDs are cached in ./managed_ids.json (no secrets in it).

Grounded in:
  https://platform.claude.com/docs/en/managed-agents/quickstart
  https://platform.claude.com/docs/en/managed-agents/memory
  https://platform.claude.com/docs/en/managed-agents/scheduled-deployments
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict

import anthropic

IDS_FILE = "managed_ids.json"
MODEL = "claude-sonnet-5-5"

SYSTEM = """You triage dependency updates for the repo in your working directory.
Before starting, read /mnt/memory/dependency-triage/ for known-bad versions, flaky tests
and team conventions. After finishing, write ONE short dated note per new lesson as its own
file under /mnt/memory/dependency-triage/lessons/. Never store secrets or tokens.
Output: a markdown report with Upgrade / Hold / Investigate sections."""

TASK = "Run tonight's dependency triage. Check outdated packages, run the test suite, report."


def load() -> Dict[str, str]:
    return json.load(open(IDS_FILE)) if os.path.exists(IDS_FILE) else {}


def save(ids: Dict[str, str]) -> None:
    json.dump(ids, open(IDS_FILE, "w"), indent=2)


def setup(client: anthropic.Anthropic) -> None:
    ids = load()
    if "store" not in ids:
        store = client.beta.memory_stores.create(
            name="Dependency Triage",
            description="Known-bad versions, flaky tests and upgrade conventions for this repo.",
        )
        client.beta.memory_stores.memories.create(
            store.id, path="/conventions.md",
            content="Pin majors in package.json. Never auto-upgrade the ORM. Flaky: tests/e2e/checkout.spec.ts",
        )
        ids["store"] = store.id
    if "agent" not in ids:
        agent = client.beta.agents.create(
            name="Nightly dependency triage",
            model=MODEL,
            system=SYSTEM,
            tools=[{"type": "agent_toolset_20260401"}],
        )
        ids["agent"] = agent.id
    if "env" not in ids:
        env = client.beta.environments.create(
            name="triage-env",
            config={"type": "cloud", "networking": {"type": "limited", "allow_package_managers": True}},
        )
        ids["env"] = env.id
    if "deployment" not in ids:
        dep = client.beta.deployments.create(
            name="Nightly dependency triage",
            agent=ids["agent"],
            environment_id=ids["env"],
            # Repo access would be a github_repository resource here; see managed-agents/github.
            # Field name `resources` mirrors sessions.create (unverified for deployments.create).
            resources=[{
                "type": "memory_store",
                "memory_store_id": ids["store"],
                "access": "read_write",
                "instructions": "Check before starting; append lessons after.",
            }],
            initial_events=[{"type": "user.message", "content": [{"type": "text", "text": TASK}]}],
            schedule={"type": "cron", "expression": "30 4 * * 1-5", "timezone": "UTC"},  # avoid DST gaps
            budget={"type": "limit", "max_list_cost": {"amount": "5", "currency": "USD"}},
        )
        ids["deployment"] = dep.id
        print("next runs:", dep.schedule.upcoming_runs_at)
    save(ids)
    print(json.dumps(ids, indent=2))


def manual_run(client: anthropic.Anthropic) -> None:
    run = client.beta.deployments.run(load()["deployment"])
    print("manual run:", run)  # manual runs emit no deployment_run.* webhooks; session.* ones still fire


def runs(client: anthropic.Anthropic) -> None:
    for r in client.beta.deployment_runs.list(deployment_id=load()["deployment"]):
        print(r.created_at, r.session_id or (r.error.type + ": " + r.error.message))


def memories(client: anthropic.Anthropic) -> None:
    page = client.beta.memory_stores.memories.list(load()["store"], path_prefix="/")
    for item in page.data:
        print(item.type, item.path)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    c = anthropic.Anthropic()
    {"setup": setup, "run": manual_run, "runs": runs, "memories": memories}[cmd](c)
