# Unverified claims

Every claim still marked "(unverified)" in `advanced/`, as of 2026-10-20. To clear one, check it against the URL, then either drop the marker or fix the claim, and tick it here.

## Guides

- [ ] **building-mcp-servers.md** (Recipe 4): `cloudflared tunnel --url http://localhost:3000` is the right quick-tunnel command. The connector docs name Cloudflare Tunnel and ngrok but give no command.
  Verify: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/
- [ ] **building-mcp-servers.md** (Recipe 5): whether the MCP tunnel proxy forwards the original `Host` header or the upstream's, and so whether `orders-mcp:*` needs to be in `allowed_hosts`.
  Verify: https://platform.claude.com/docs/en/agents-and-tools/mcp-tunnels/concepts.md
- [ ] **api-cost-and-latency.md** (Recipe 2): `output_config` and `speed` can be passed as keyword arguments to `client.messages.stream` (the docs only show them on `messages.create`). `bench.py` relies on this.
  Verify: https://platform.claude.com/docs/en/build-with-claude/effort and the Python SDK's `messages.stream` signature
- [ ] **context-engineering.md** (Recipe 4): threshold compaction (`compact_20260112`) and `clear_tool_uses_20250919` can be combined in one request.
  Verify: https://platform.claude.com/docs/en/build-with-claude/compaction-threshold.md, https://platform.claude.com/docs/en/build-with-claude/context-editing.md
- [ ] **agentic-api-patterns.md** (Recipe 1): whether the tool runner reuses the result of `generate_tool_call_response()` or runs the tools again when it auto-appends.
  Verify: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner
- [ ] **agentic-api-patterns.md** (Recipe 7): `deployments.create` takes memory stores in a field named `resources`, mirroring `sessions.create`. Also in `examples/agentic-api-patterns/managed_agent_nightly.py`.
  Verify: https://platform.claude.com/docs/en/managed-agents/scheduled-deployments, https://platform.claude.com/docs/en/managed-agents/memory
- [ ] **agentic-api-patterns.md** (Recipe 7): the SDK method `client.beta.deployment_runs.retrieve`, inferred from `GET /v1/deployment_runs/{id}`. Also in `examples/agentic-api-patterns/webhook_receiver.py`.
  Verify: https://platform.claude.com/docs/en/managed-agents/scheduled-deployments and the Python SDK reference
- [ ] **advanced-skills.md** (Recipe 2): `claude -p --output-format stream-json` ends with a `{"type":"result"}` event carrying the final reply and `total_cost_usd`. The docs only show these fields for `--output-format json`. `run_evals.py` falls back to the last assistant text block if it's missing.
  Verify: https://code.claude.com/docs/en/headless, https://code.claude.com/docs/en/cli-reference
- [ ] **browser-and-computer-automation.md** (Recipe 5): `tabs_create_mcp` can accept a URL that the domain-guard hook doesn't inspect.
  Verify: https://code.claude.com/docs/en/chrome, plus the tool's schema in a live Claude Code session
- [ ] **security-and-prompt-injection.md** (Recipe 2): where the per-tool `ask`/`blocked` connector controls live in the claude.ai admin console.
  Verify: https://support.claude.com (search "connector tool permissions"), https://code.claude.com/docs/en/mcp.md
- [ ] **security-and-prompt-injection.md** (Recipe 5): a mocked MCP server in `claude plugin eval` registers its tools as `mcp__plugin_<plugin>_<server>__<tool>`.
  Verify: https://code.claude.com/docs/en/plugin-evals.md
- [ ] **evals-and-observability.md** (Recipe 5): the Docker tag `otel/opentelemetry-collector-contrib:0.111.0`. Also in `examples/evals-and-observability/otel-collector.yaml`.
  Verify: https://hub.docker.com/r/otel/opentelemetry-collector-contrib/tags
- [ ] **experimental/artifacts-as-apps.md** (Recipe 1): multi-file artifacts with relative supporting files. Claude Code's Artifact tool contract accepts them, but the public docs still describe one page with no relative links.
  Verify: https://code.claude.com/docs/en/artifacts
- [ ] **experimental/artifacts-as-apps.md** (Recipe 2): the artifact database tool is available inside a cloud scheduled run. The routines docs cover only artifact publishes.
  Verify: https://code.claude.com/docs/en/routines, https://code.claude.com/docs/en/artifacts

## Derived or sourced from tooling, not marked inline

- [ ] **api-cost-and-latency.md**: the Opus 5.5 fast-mode cache prices ($10 / $16 / $0.40 per MTok) are derived by applying cache multipliers to fast-mode rates. The table footnotes them as derived.
  Verify: https://platform.claude.com/docs/en/about-claude/pricing
- [ ] **browser-and-computer-automation.md**: the Chrome tool names and parameters (`gif_creator`, `javascript_tool`, `browser_batch`, etc.) come from Claude Code's live tool schemas, not a docs page. The guide says so.
  Verify: https://code.claude.com/docs/en/chrome
- [ ] **experimental/artifacts-as-apps.md**: the whole page-side runtime API was checked only against the type definitions bundled with Claude Code 2.1.304 (runtime contract 0.2.87). There is no public reference. Re-check whenever the contract version changes.
  Verify: the `artifact-capabilities` skill's `.d.ts` files in your Claude Code install
