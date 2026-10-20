"""Managed Agents webhook receiver: verify, dedupe, fetch-by-id, post the final report.

Requires: pip install anthropic flask
Env:      ANTHROPIC_API_KEY, ANTHROPIC_WEBHOOK_SIGNING_KEY (whsec_... shown once at endpoint creation)
Run:      flask --app webhook_receiver run --port 8080   (expose via HTTPS:443, public hostname)
Subscribe the endpoint (Console > Webhooks) to: session.status_idled, session.status_terminated,
session.budget_reached, deployment_run.failed, deployment.paused.

Grounded in https://platform.claude.com/docs/en/managed-agents/webhooks
and https://platform.claude.com/docs/en/managed-agents/events-and-streaming
"""
from __future__ import annotations

import sqlite3
from typing import Optional

import anthropic
from flask import Flask, request

client = anthropic.Anthropic()  # also reads ANTHROPIC_WEBHOOK_SIGNING_KEY
app = Flask(__name__)
db = sqlite3.connect("webhook_seen.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")


def first_time(event_id: str) -> bool:
    try:
        db.execute("INSERT INTO seen VALUES (?)", (event_id,))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # retry of an event we already handled


def final_report(session_id: str) -> Optional[str]:
    text = None
    for ev in client.beta.sessions.events.list(session_id, types=["agent.message"]):
        parts = [b.text for b in ev.content if b.type == "text"]
        if parts:
            text = "".join(parts)  # keep the last agent message
    return text


def notify(msg: str) -> None:
    print(msg)  # swap for Slack/email; keep it outside the request path if slow


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = client.beta.webhooks.unwrap(request.get_data(as_text=True), headers=dict(request.headers))
    except Exception:
        return "invalid signature", 400
    if not first_time(event.id):
        return "", 204
    kind, obj_id = event.data.type, event.data.id

    if kind == "session.status_idled":
        session = client.beta.sessions.retrieve(obj_id)  # payload is thin: always re-fetch
        notify("session %s idle (%s):\n%s" % (obj_id, getattr(session, "status", "?"), final_report(obj_id)))
    elif kind == "session.budget_reached":
        notify("session %s hit its budget; raise or remove it to resume" % obj_id)
    elif kind == "deployment_run.failed":
        run = client.beta.deployment_runs.retrieve(obj_id)  # (unverified) SDK method name
        notify("deployment run failed: %s" % run.error)
    elif kind in ("deployment.paused", "session.status_terminated"):
        notify("%s: %s" % (kind, obj_id))
    return "", 204  # any 2xx acks; never redirect (3xx disables the endpoint)
