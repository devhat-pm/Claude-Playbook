# Agentic API patterns

Seven patterns for building agents directly on the Messages API and on Managed Agents. Scripts: [`examples/agentic-api-patterns/`](examples/agentic-api-patterns/). Every script reads `ANTHROPIC_API_KEY` from the environment, compiles under Python 3.9, and has no hardcoded secrets. Model IDs used: `claude-opus-5-5`, `claude-sonnet-5-5` (swap in `claude-fable-5-1` or `claude-haiku-5-5` where the feature lists them).

| You need | Pattern |
|---|---|
| A local tool loop with a human gate, without writing the loop yourself | 1. Tool runner |
| One question that fans out to 20–200 tool calls | 2. Programmatic tool calling |
| More than ~30 tools, or MCP servers that together have 100+ | 3. Tool search |
| Output that a parser consumes, or tool inputs that must not be malformed | 4. Structured outputs + strict tools |
| Production robustness | 5. Stop-reason dispatch and refusal fallback |
| Long sessions that stay cached and keep their reasoning | 6. Append-only history + mid-conversation system messages |
| Hours-long, scheduled or unattended work with memory | 7. Managed Agents |

---

## 1. Tool runner with an approval gate

**Problem.** A hand-written `while stop_reason == "tool_use"` loop tends to drift: it forgets `is_error`, drops blocks when it appends history, and has no iteration cap. You also want a "y/N" prompt before anything irreversible.

**Setup.** [`tool_runner_loop.py`](examples/agentic-api-patterns/tool_runner_loop.py). The core:

```python
runner = client.beta.messages.tool_runner(
    model="claude-sonnet-5-5", max_tokens=1024, max_iterations=8,
    tools=[get_order, refund_order],          # @beta_tool functions; schema from type hints + docstring
    messages=[{"role": "user", "content": prompt}])
for message in runner:
    risky = [b for b in message.content if b.type == "tool_use" and b.name in DESTRUCTIVE]
    if risky and input("Allow? ") != "y":
        runner.append_messages(message, {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": "Denied by operator.", "is_error": True}
            for b in message.content if b.type == "tool_use"]})
        continue                               # you took over history for this turn only
    resp = runner.generate_tool_call_response()  # runs the tools; inspect is_error before Claude sees it
```

The runner's rules, from the docs:
- If you don't touch history, it appends the assistant turn and the tool results, then calls the API again. It stops when a turn has no tool call or when it hits `max_iterations`.
- `append_messages()` inside the loop means you own history for that iteration. You must then append the assistant message and a `tool_result` for every `tool_use` yourself.
- `set_messages_params(lambda p: {...})` changes request params such as `max_tokens` without taking over history.
- A tool that raises is returned to Claude as `is_error: true`. In Python the result carries the exception type and message, and the full stack trace goes to `logging`. Set `ANTHROPIC_LOG=debug` to see it.
- For async code, use `@beta_async_tool` with `async def`.

**Output.** Claude looks up the order, then the script pauses at `Allow [('refund_order', {'order_id': '1042'})]? [y/N]`. Answering `n` sends Claude an error result. Claude explains it can't refund, and the loop ends.

**Failure modes.**
- A turn that stops on `max_tokens` with no tool call ends the loop. The script re-runs with a bigger budget, which **replays your tools**, so make them idempotent or record what already ran.
- Calling `generate_tool_call_response()` runs the tools. The docs don't say whether the runner reuses that result or runs the tools again on its auto-append (unverified), so keep tools free of side effects or gate them as shown.
- Automatic compaction in the runner exists only in the TypeScript and Ruby SDKs. In Python, long loops grow without limit, so cap `max_iterations`.
- Go, Java, C# and PHP runners can't intercept tool errors before they're sent. Catch errors inside the tool.

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner

---

## 2. Programmatic tool calling for fan-out

**Problem.** Checking 20 employees' expenses takes 20 model round trips and puts thousands of rows into context. You want Claude to write the loop, run it next to your tool, and read only the result.

**Setup.** [`ptc_manual_loop.py`](examples/agentic-api-patterns/ptc_manual_loop.py). Add the code execution tool, and mark your tool as callable only from code:

```python
tools = [{"type": "code_execution_20260120", "name": "code_execution"},
         {"name": "get_expenses", "description": "... Output: JSON array of {date, category, amount_usd} ...",
          "input_schema": {...}, "allowed_callers": ["code_execution_20260120"]}]
```

Loop rules the script enforces:
1. Each `tool_use` has a `caller`. `{"type": "code_execution_20260120", "tool_id": "srvtoolu_..."}` means Claude's code is paused and waiting for your result.
2. Read `resp.container.id` and send it back as `container=` on every later request. While a call is pending, the API rejects a request that omits it.
3. The user turn that answers programmatic calls may contain **only** `tool_result` blocks: no text, and string or text content only (no images).
4. Send the same `tools` array every time. Code execution has to be present for the paused code to resume.
5. Treat `pause_turn` as "send the assistant content back as-is".

Tool functions appear to Claude's code as `async` functions that take a dict and return a string, so Claude can run them in parallel with `asyncio.gather`. Describe the output format in the tool description so the code can `json.loads` it.

**Output.** One code-execution run makes 20 `get_expenses` calls, which your loop serves one after another. Claude's context receives only the script's stdout (the over-limit table). `served get_expenses via code_execution_20260120` prints 20 times, and `input_tokens` stays flat as N grows.

**Failure modes.**
- **~4 minute timeout per pending call.** If you answer late, Claude's code gets `TimeoutError` in stderr and usually retries. Idle containers are reclaimed after ~5 minutes, so watch `expires_at`.
- These are rejected or unsupported: `strict: true` on a PTC tool, forcing PTC through `tool_choice`, `disable_parallel_tool_use: true`, MCP connector tools, and the `computer_toolset_20260801` and `browser_toolset_20260801` toolsets.
- A recursive `$ref` in `input_schema` returns 400 `Circular $ref detected`. Keep that tool `["direct"]` or unroll the recursion.
- `allowed_callers` guides Claude but isn't enforced, so handle a direct call too. The script logs `via direct` in that case.
- Tool output runs through Claude's code. Treat external data in it as possible code injection.
- Not ZDR-eligible.

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling

---

## 3. Tool search across 150 tools

**Problem.** GitHub, Slack, Jira, Sentry and Grafana together are about 55k tokens of definitions, and tool-choice accuracy drops past 30–50 tools.

**Setup.** [`tool_search_catalog.py`](examples/agentic-api-patterns/tool_search_catalog.py) builds a 151-entry `tools` array and lints it offline (`--lint`):

```python
tools = [{"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"},   # never deferred
         {"name": "jira_create_issue", ...},                                             # hot: not deferred
         {"name": "sentry_get_event", ..., "defer_loading": True}, ...]                  # rest deferred
```

Decisions that matter:
- **Choose a variant.** `tool_search_tool_regex_20251119` has Claude write Python `re.search` patterns (case-insensitive, 200 characters max). `tool_search_tool_bm25_20251119` takes natural-language queries (500 characters max). Pick BM25 when your users phrase tasks loosely.
- **Send everything every time.** `defer_loading` controls what enters context, not what you send, so deferred definitions still go in `tools` on every request.
- **Keep 3–5 hot tools undeferred.** The lint fails if every tool is deferred, because that returns a 400.
- **Name with a service prefix** (`github_`, `slack_`) so one search returns the whole group. Search covers names, descriptions, argument names and argument descriptions.
- **Name the categories in the system prompt**, for example "You can search for tools to work with GitHub, Slack, Jira…".
- **For MCP connector servers**, set `defer_loading` in the `mcp_toolset` `default_config`, not per tool.

**Output.** Response blocks arrive in this order: `server_tool_use` (the query), `tool_search_tool_result` (with `tool_references`, 5 by default), then your `tool_use`. On the next turn, append the content **unchanged**, return `tool_result` only for your own `toolu_` IDs (never for the `srvtoolu_` search), and resend the same `tools`.

**Failure modes.**
- `defer_loading` together with `cache_control` on the same tool returns 400. Put the cache breakpoint on a hot tool.
- A `tool_reference` to a tool that isn't in `tools` returns 400.
- Search errors come back as HTTP 200 with an `error_code`: `invalid_tool_input`, `unavailable`, `too_many_requests` or `execution_time_exceeded`. Handle them like a tool error.
- If expected tools aren't found, the descriptions are too thin. Add the words users actually say. The lint flags descriptions under 25 characters.
- Search isn't billed as a server tool, but loaded definitions count as input tokens.
- The limit is 10,000 deferred tools per request. On Bedrock, search works only through InvokeModel, not Converse.

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

---

## 4. Structured outputs + strict tools

**Problem.** A downstream parser needs exact JSON, and one tool's inputs must never be malformed.

**Setup.** [`structured_extract.py`](examples/agentic-api-patterns/structured_extract.py).
- **JSON output:** pass a Pydantic model to `client.messages.parse(..., output_format=Invoice)` and read `resp.parsed_output`. The SDK converts the model to `output_config.format` (`type: json_schema`) and validates the response.
- **Strict tool:** set `"strict": True` on the tool, with `additionalProperties: False` and every property listed in `required`.
- **Both at once:** `output_config.format` and a strict tool can go in the same request (the `reconcile()` step).

Limits to design around:

| Limit | Value |
|---|---|
| Strict tools per request | 20 |
| Optional params across all strict schemas | 24 |
| Params with `anyOf` / type arrays | 16 |
| `minItems` | 0 or 1 only |
| Not supported | recursive schemas, `minimum`/`maximum`, `minLength`/`maxLength`, lookaround/backrefs/`\b` in `pattern`, external `$ref` |

**Output.** An `Invoice` object every time the stop reason is `end_turn`. The first request with a new schema is slower while its grammar compiles. Compiled grammars are cached for 24 hours, and changing only `name` or `description` doesn't invalidate the cache.

**Failure modes.**
- **Enum casing isn't guaranteed.** `"Conversation topic 3"` can come back as `"Conversation Topic 3"`, so compare case-insensitively (the script normalizes it).
- **Required fields come first** in the output, followed by optional ones in schema order.
- **A field named `reasoning` or `thinking` can trigger a `reasoning_extraction` refusal.** Use `short_rationale` instead, and read the thinking blocks if you need the reasoning.
- **Truncated JSON never matches the schema.** On `max_tokens`, retry with a larger budget.
- **Some features return 400 with JSON output.** Citations and prefill are incompatible. A complex schema returns "Schema is too complex for compilation": mark fewer tools strict, make parameters required, and flatten nesting.
- **Changing `output_config.format` invalidates the prompt cache** for that thread.

Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs · https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use

---

## 5. Stop-reason dispatch and refusal fallback

**Problem.** Agents that only check for `tool_use` silently ship truncated answers and ignore refusals, which arrive as HTTP 200.

**Setup.** Branch on every value:

| `stop_reason` | Do |
|---|---|
| `end_turn` | Use the response. |
| `tool_use` | Run the tools and return `tool_result`s. |
| `pause_turn` | A server-tool loop hit its cap (10 iterations by default). Append `resp.content` as the assistant turn and resend unchanged. |
| `max_tokens` | Raise `max_tokens` and retry (required for structured output), or continue the response. |
| `stop_sequence` | Read `resp.stop_sequence`. |
| `refusal` | Read `stop_details.category` (`cyber`, `bio`, `frontier_llm`, `reasoning_extraction`, `general_harms`, or `null`). Show `explanation`; don't parse it. Discard any partial output. |
| `model_context_window_exceeded` | The response is truncated by the context window. Compact or chunk. Typed only in the SDK beta namespace. |

To retry refusals on another model inside the same call, use server-side fallback (beta, Claude API only):

```python
resp = client.beta.messages.create(
    model="claude-fable-5-1", max_tokens=1024, messages=msgs,
    fallbacks="default",                          # or [{"model": "claude-opus-5-5"}], up to 3
    betas=["server-side-fallback-2026-07-01"])
served_by_fallback = resp.stop_reason != "refusal" and any(
    it.type == "fallback_message" for it in (resp.usage.iterations or []))
```

**Output.** `resp.model` names the model that actually answered. A `fallback` content block marks where one model handed off to the next.

**Failure modes.**
- **Echoing a fallback turn back.** Keep the `fallback` block exactly where it appeared. Drop `thinking`, `redacted_thinking`, `connector_text` and client `tool_use` blocks that come before the final `fallback`. Keep `server_tool_use` only when its result is paired with it.
- **Haiku 5.5 has no server-side fallback.** Use the SDK middleware or your own retry.
- **No support on Batches** (the item errors), Bedrock, Google Cloud or Foundry.
- **Some refusals are billed.** A refusal before any output is billed for the `bio`, `frontier_llm` and `reasoning_extraction` categories, and a mid-stream refusal bills what already streamed.
- **Fallback capacity.** If the fallback model is rate-limited, you get the original refusal plus `stop_details.recommended_model`.

Source: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons · https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback

---

## 6. Append-only history with thinking blocks + mid-conversation system messages

**Problem.** After many turns you need to add a rule ("parameterized SQL only"), relay a message the user typed while tools were running, or drop a tool. Editing `system` or `tools`, or rewriting earlier messages, does two kinds of damage:
- It restarts the prompt cache.
- On Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5, it invalidates every later thinking block. You get a 400 with `Invalid signature in thinking block … bound to a different conversation`.

**Setup.** [`append_only_conversation.py`](examples/agentic-api-patterns/append_only_conversation.py) (`--selftest` runs offline). It enforces these rules:
- **`system` and `tools` are frozen** for the session. `messages` only grows, and each request checks that everything already sent is byte-identical.
- **Assistant turns are stored exactly as returned:** empty `thinking` blocks with their signatures, `redacted_thinking`, `fallback`, `server_tool_use`. On 5.x models `display` defaults to `"omitted"`, so the `thinking` text is empty but the block is still required.
- **New instructions are appended as `{"role": "system", "content": ...}`.** Such a message must directly follow a user turn (or an assistant turn that ends in a server tool result). It must be the last message or be followed by an assistant turn. It can't be the first message, and it can't sit between a `tool_use` and its `tool_result`.
- **User input typed mid-loop** goes in as a system note after the `tool_result` turn: "The user sent this while you were working: …". On `claude-sonnet-5-5` and `claude-haiku-5-5` it is appended as a `text` block inside the `tool_result` user turn instead, because those models can treat a system message after a tool result as untrusted.
- **Tool changes** use `tool_addition` and `tool_removal` blocks inside a system message, with the `inline-tools-2026-09-15` beta header. Don't edit `tools`.
- **Per-turn nudges** use `clear_at: "next_user_message"` (beta header `mid-conversation-system-clear-at-2026-08-21`), so only the newest copy renders.
- **Effort changes** go in a per-message `output_config` on a system message (beta). Effort, `max_tokens`, `tool_choice` and `thinking.display` are outside the prefix check, so changing them doesn't invalidate thinking.

```python
conv.tool_results([{"type": "tool_result", "tool_use_id": "toolu_01", "content": "12 passed"}],
                  relayed_user_text="also update the changelog")
conv.system_note("From now on, write all SQL as parameterized queries.")
resp = conv.send(client, max_tokens=4096, thinking={"type": "adaptive", "display": "summarized"})
```

**Output.** Each request reads the earlier prefix from cache (top-level `cache_control={"type": "ephemeral"}`), the thinking blocks stay valid, and the self-test catches a middleware edit before it reaches the API.

**Failure modes.**
- **Thinking mode switched mid-turn.** A tool loop is a single assistant turn. Toggling thinking partway through doesn't error, but thinking is silently disabled, so switch only between turns.
- **Forced tool choice.** With manual `thinking: {type: "enabled"}`, `tool_choice` `any` or `tool` returns 400. On 5.x models `enabled` with `budget_tokens` returns 400 anyway, so use `adaptive`.
- **Pruning thinking blocks from the middle.** That creates a gap. You may drop from the oldest end, from the newest end, or all of them.
- **Untrusted text in a system message** gets operator authority. Keep page text, documents and tool output in `tool_result`.
- **Stopgap for a broken prefix.** `thinking.block_binding.prefix_mismatch_behavior: "drop_block"` (beta `thinking-binding-controls-2026-08-01`) keeps requests succeeding. Anthropic measured up to +67% output tokens at max effort when blocks drop every turn.
- **Who is affected.** Accounts created on or after 2026-08-31 have the prefix check enforced by default. Build append-only regardless.

Source: https://platform.claude.com/docs/en/build-with-claude/thinking · https://platform.claude.com/docs/en/build-with-claude/preserved-thinking · https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages

---

## 7. Managed Agents: a nightly triage agent with memory, a schedule and webhooks

**Problem.** You want a dependency-triage agent that runs every weekday at 04:30 UTC in a sandbox, remembers flaky tests and bad versions across runs, stays within a spending cap, and notifies you when it's done. You don't want to run a loop, a sandbox or a cron server yourself.

**Setup.** Two scripts.
- [`managed_agent_nightly.py`](examples/agentic-api-patterns/managed_agent_nightly.py) has subcommands `setup`, `run`, `runs` and `memories`.
- [`webhook_receiver.py`](examples/agentic-api-patterns/webhook_receiver.py) is a Flask app.

All endpoints are beta. The SDK sends `managed-agents-2026-04-01` for you. If you call memory stores over raw HTTP, send `agent-memory-2026-07-22` **instead**: sending both returns 400. Session endpoints, including attaching a store, stay on `managed-agents-2026-04-01`.

```text
memory_store  ── seeded with /conventions.md, mounted at /mnt/memory/dependency-triage/
agent         ── model + system + tools=[{"type": "agent_toolset_20260401"}]  (bash, file ops, web)
environment   ── {"type": "cloud", "networking": {"type": "limited", "allow_package_managers": true}}
deployment    ── agent + env + resources[memory_store] + initial_events[user.message]
                 + schedule {"type": "cron", "expression": "30 4 * * 1-5", "timezone": "UTC"}
                 + budget {"type": "limit", "max_list_cost": {"amount": "5", "currency": "USD"}}
webhook       ── Console > Webhooks: HTTPS:443 public URL, whsec_ secret shown once
```

```bash
export ANTHROPIC_API_KEY=... ANTHROPIC_WEBHOOK_SIGNING_KEY=whsec_...
python3 managed_agent_nightly.py setup   # prints upcoming_runs_at; verify the cron before trusting it
python3 managed_agent_nightly.py run     # manual run now (trigger_context.type = "manual")
flask --app webhook_receiver run --port 8080
```

Subscribe the endpoint to `session.status_idled`, `session.budget_reached`, `session.status_terminated`, `deployment_run.failed` and `deployment.paused`. Webhook payloads carry only `type` and `id`. The receiver verifies them with `client.beta.webhooks.unwrap()` (which raises on a bad signature or a payload older than 5 minutes), dedupes on `event.id`, fetches the object with `sessions.retrieve`, reads the last `agent.message` via `sessions.events.list(id, types=["agent.message"])`, and returns 204.

For interactive use instead of a schedule, open `client.beta.sessions.events.stream(session.id)`, then call `events.send(...)` with a `user.message`. Branch on `session.status_idle`'s `stop_reason.type`:
- `end_turn`: send the next message.
- `requires_action`: answer the events listed in `stop_reason.event_ids`.
- `budget_reached`: raise the budget; no event you send resumes the session.

**Output.** Each weekday morning, a deployment run creates a session. The agent reads `/mnt/memory/dependency-triage/`, runs the tests, writes `lessons/*.md` files, and goes idle. Your endpoint posts the Upgrade / Hold / Investigate report. `python3 managed_agent_nightly.py memories` shows what it has learned, and each write is an immutable `memver_` version you can audit or redact.

**Failure modes.**
- **Memory poisoning.** A `read_write` store plus untrusted input (web pages, dependency changelogs) lets a prompt injection persist into future runs. Attach shared reference material as a separate `read_only` store, and review `memory_versions` regularly. Stores can only be attached when the session is created.
- **Memory limits.** Each memory is capped at 100 kB, a store holds at most 10k memories, and a session can attach at most 8 stores. Old versions may be deleted after 30 days, so export them if you need them.
- **Cron edge cases.**
  - Schedules match wall-clock time in the given timezone. On DST days a 2 AM local slot is skipped or runs twice, so use UTC or avoid 1–3 AM.
  - Jitter can be up to 15% of the interval (9 minutes at most).
  - Unpausing doesn't backfill missed runs.
  - The limit is 1,000 deployments per organization.
- **Runs that fail to create a session.** These are recorded as deployment runs with `error.type`: `environment_archived_error`, `agent_archived_error` or `session_rate_limited_error` (rate-limited runs aren't retried). Unrecoverable errors auto-pause the deployment. Archiving the agent archives the deployment.
- **Webhook delivery isn't reliable or ordered.**
  - Events can arrive out of order and as duplicates.
  - There are 3 delivery attempts.
  - A `3xx` response disables the endpoint immediately.
  - Events emitted while the endpoint is disabled or unsubscribed are never replayed.
  - Manual runs emit no `deployment_run.*` events.
  - Drive your state from `GET`, not from event order.
- **Unverified details.** Passing memory stores to `deployments.create` uses the field name `resources`, which mirrors `sessions.create` (unverified for deployments). `client.beta.deployment_runs.retrieve` is inferred from `GET /v1/deployment_runs/{id}` (unverified SDK method name).

Source: https://platform.claude.com/docs/en/managed-agents/overview · https://platform.claude.com/docs/en/managed-agents/quickstart · https://platform.claude.com/docs/en/managed-agents/sessions · https://platform.claude.com/docs/en/managed-agents/events-and-streaming · https://platform.claude.com/docs/en/managed-agents/memory · https://platform.claude.com/docs/en/managed-agents/scheduled-deployments · https://platform.claude.com/docs/en/managed-agents/webhooks
