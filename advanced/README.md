# Advanced

For people who already use Claude every day, have Claude Code installed and know what skills, connectors and artifacts are. This section skips feature tours. Each guide is a set of recipes, and each recipe has a real problem, the exact setup (files, commands, prompts, config), what you get and how it fails. Claims cite the official page they were checked against, and anything that couldn't be checked is marked "(unverified)". Scripts live in [`examples/`](examples/), one folder per guide.

## Reading order

1. [Context engineering](context-engineering.md): everything else depends on keeping context under control.
2. [Hooks & guardrails](hooks-and-guardrails.md): set up guardrails before you give agents more autonomy.
3. [Multi-agent orchestration](multi-agent-orchestration.md)
4. [Advanced skills](advanced-skills.md)
5. [Building MCP servers](building-mcp-servers.md)
6. [Browser & computer automation](browser-and-computer-automation.md)
7. [Artifacts as apps](experimental/artifacts-as-apps.md) *(experimental: undocumented page-side API)*
8. [Unattended pipelines](unattended-pipelines.md)
9. [Security & prompt injection](security-and-prompt-injection.md): read this before you ship anything from steps 5–8.
10. [Agentic API patterns](agentic-api-patterns.md): for building on the API directly.
11. [API cost & latency](api-cost-and-latency.md)
12. [Evals & observability](evals-and-observability.md): close the loop, so every change above gets measured.

API-only builders: read 1, 9, 10, 11, 12 in that order.

## Verification status

As of 2026-10-20. Only `bench.py` and `cache_probe.py` have been run against the paid Claude API, once each. Open doc questions are tracked in [UNVERIFIED.md](UNVERIFIED.md).

**Ran end-to-end (locally)**
- Both MCP servers in [`examples/building-mcp-servers/`](examples/building-mcp-servers/): Python under 3.12 via `uv`, TypeScript via `npm install`. Both passed the 401 challenge, `initialize`, `tools/list` and `tools/call`, including the error paths (bad enum value, unknown order id, refund over the order total). The Output sections quote these real responses.
- API cost and latency: `bench.py` (Haiku, Sonnet and Opus 5.5 × low, medium and high effort × 5 runs on `task.json`) and `cache_probe.py` (Sonnet 5.5 with `--warm`) against the Claude API on 2026-10-20. The guide's tables and Output sections quote these runs. Raw output is in `results-2026-10-20.json` and `cache-results-2026-10-20.txt`. Fast mode, Fable 5.1 and `--ttl 1h` weren't exercised.
- Hook scripts, fed sample hook JSON on stdin: `protect-paths.py`, `secret-scan.py`, `require-tests-on-stop.sh`, `readonly-bash.sh`, `chrome_domain_guard.py`, `confirm_gate.py`, `injection_tripwire.py`.

**Ran offline only (dry-run, fixtures or self-test; no API calls)**
- Context engineering: `audit_instructions.py`, `session_state.py` and the `memory_agent.py` path guard ran against this repo. `relay.py` and `memory_agent.py` ran with `--dry-run`.
- Multi-agent orchestration: `fanout.py` and `advisor_executor.py` with `--dry-run`, and `parallel_worktrees.sh` with `DRY_RUN=1`.
- Advanced skills: `validate_plan.py` + `apply_plan.py` against a temp fixture, and `run_evals.py --dry-run`.
- API cost and latency: `pricing.py` (totals checked by hand), plus `batch_pipeline.py` and `route.py` in dry-run or offline mode.
- Agentic API patterns: `tool_search_catalog.py --lint` and `append_only_conversation.py --selftest`.
- Browser and computer automation: `rows_to_csv.py`.
- Artifacts as apps: `build_metrics_doc.py`.
- Unattended pipelines: `triage_apply.py` with `DRY_RUN=1`. `fire-routine.sh` ran only its error path, against an unreachable host.
- Security: `compliance_watch.py` (fixture mode) and `screen_tool_output.py` (dry run).
- Evals and observability: `run_evals.py` in replay mode, and `usage_cost_report.py` on sample JSON.

**Compiled only (`py_compile` / `node --check` / `bash -n`)**
- Agentic API patterns: `tool_runner_loop.py`, `ptc_manual_loop.py`, `structured_extract.py`, `managed_agent_nightly.py`, `webhook_receiver.py`.
- Evals and observability: `otel_tracing.py`.
- Browser and computer automation: `extract_table.js`.
- Artifacts as apps: `standup-board/app.js`. The artifact has not been published.
- Hooks: `lint-on-edit.sh`, because no linter is installed on the test machine.

**Template only (syntax-valid, never exercised)**
- GitHub Actions workflows: `examples/unattended-pipelines/pr-review.yml`, `examples/unattended-pipelines/issue-triage-headless.yml` and `examples/evals-and-observability/ci/prompt-evals.yml`. None has run on GitHub yet.
- Config: every `settings.json`, `org/managed-settings.json`, `settings.untrusted-content.json`, `agents/*.md`, `plugin.json`, `marketplace.json` and `otel-collector.yaml`.
- `claude plugin eval` suites under `examples/advanced-skills/`, `examples/security-and-prompt-injection/redteam-evals/` and `examples/evals-and-observability/plugin-evals/`. None has been run.
