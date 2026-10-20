"""Append-only conversation store that keeps thinking blocks valid and the cache warm.

- system + tools frozen at construction; messages can only grow
- every request re-verifies that the previously sent prefix is byte-identical
- new instructions go in as mid-conversation {"role": "system"} messages, placed legally
- Sonnet 5.5 / Haiku 5.5: user input typed mid-loop rides in the tool_result user turn instead

Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
Run:      python3 append_only_conversation.py --selftest     # offline, no API calls

Grounded in:
  https://platform.claude.com/docs/en/build-with-claude/thinking
  https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
  https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from typing import Any, Dict, List, Optional

SYSTEM_AFTER_TOOL_RESULT_UNSAFE = {"claude-sonnet-5-5", "claude-haiku-5-5"}


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    if isinstance(obj, list):
        return [_dump(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    return obj


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(_dump(obj), sort_keys=True).encode()).hexdigest()


class PrefixEdited(RuntimeError):
    pass


class Conversation:
    def __init__(self, model: str, system: str, tools: Optional[List[Dict[str, Any]]] = None):
        self.model = model
        self._system = system
        self._tools = copy.deepcopy(tools or [])
        self._frozen = _digest([system, self._tools])
        self.messages: List[Dict[str, Any]] = []
        self._sent: List[str] = []  # digest of each message as it was last sent

    # ---------- appends ----------
    def user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def assistant(self, content: Any) -> None:
        # Store EXACTLY what the API returned: thinking (incl. empty + signature),
        # redacted_thinking, fallback, server_tool_use, tool_use, text. No filtering.
        self.messages.append({"role": "assistant", "content": _dump(content)})

    def tool_results(self, results: List[Dict[str, Any]], relayed_user_text: Optional[str] = None) -> None:
        content = list(results)
        if relayed_user_text and self.model in SYSTEM_AFTER_TOOL_RESULT_UNSAFE:
            content.append({"type": "text", "text": relayed_user_text})
            relayed_user_text = None
        self.messages.append({"role": "user", "content": content})
        if relayed_user_text:
            self.system_note("The user sent this while you were working: " + relayed_user_text)

    def system_note(self, text: str) -> None:
        if not self.messages:
            raise ValueError("first instruction belongs in the top-level system field")
        last = self.messages[-1]
        ok = last["role"] == "user" or (
            last["role"] == "assistant"
            and isinstance(last["content"], list)
            and last["content"]
            and str(last["content"][-1].get("type", "")).endswith("_tool_result")
        )
        if not ok:
            raise ValueError("system message must follow a user turn (or a server tool result)")
        self.messages.append({"role": "system", "content": text})

    # ---------- send ----------
    def request(self, **extra: Any) -> Dict[str, Any]:
        if _digest([self._system, self._tools]) != self._frozen:
            raise PrefixEdited("system or tools changed; use system_note / tool_addition instead")
        for i, d in enumerate(self._sent):
            if _digest(self.messages[i]) != d:
                raise PrefixEdited("message %d was edited after it was sent" % i)
        self._sent = [_digest(m) for m in self.messages]
        body = dict(model=self.model, system=self._system, messages=self.messages,
                    cache_control={"type": "ephemeral"}, **extra)
        if self._tools:
            body["tools"] = self._tools
        return body

    def send(self, client: Any, **extra: Any) -> Any:
        resp = client.messages.create(**self.request(**extra))
        self.assistant(resp.content)
        return resp


def selftest() -> None:
    c = Conversation("claude-opus-5-5", "You are a release bot.")
    c.user("Run the tests.")
    c.assistant([{"type": "thinking", "thinking": "", "signature": "sig1"},
                 {"type": "tool_use", "id": "toolu_1", "name": "run_tests", "input": {}}])
    c.request(max_tokens=10)
    c.tool_results([{"type": "tool_result", "tool_use_id": "toolu_1", "content": "12 passed"}],
                   relayed_user_text="also bump the changelog")
    assert c.messages[-1]["role"] == "system"
    c.request(max_tokens=10)
    c.messages[1]["content"][0]["thinking"] = "edited"  # simulate a bad middleware
    try:
        c.request(max_tokens=10)
        raise AssertionError("edit not caught")
    except PrefixEdited as e:
        print("caught:", e)

    s = Conversation("claude-sonnet-5-5", "x")
    s.user("go")
    s.assistant([{"type": "tool_use", "id": "t", "name": "n", "input": {}}])
    s.tool_results([{"type": "tool_result", "tool_use_id": "t", "content": "ok"}], "and lint")
    assert s.messages[-1]["role"] == "user" and s.messages[-1]["content"][-1]["type"] == "text"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        import anthropic

        conv = Conversation("claude-opus-5-5", "You are terse.")
        conv.user("Name three prime numbers.")
        r = conv.send(anthropic.Anthropic(), max_tokens=512, thinking={"type": "adaptive", "display": "summarized"})
        print([b.type for b in r.content], r.stop_reason)
