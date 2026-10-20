# Advanced

For people who already use Claude every day, have Claude Code installed and know what skills, connectors and artifacts are. This section skips feature tours. Each guide is a set of recipes, and each recipe has a real problem, the exact setup (files, commands, prompts, config), what you get and how it fails. Claims cite the official page they were checked against, and anything that couldn't be checked is marked "(unverified)". Scripts live in [`examples/`](examples/), one folder per guide.

## Reading order

1. [Context engineering](context-engineering.md): everything else depends on keeping context under control.
2. [Hooks & guardrails](hooks-and-guardrails.md): set up guardrails before you give agents more autonomy.
3. [Multi-agent orchestration](multi-agent-orchestration.md)
4. [Advanced skills](advanced-skills.md)
5. [Building MCP servers](building-mcp-servers.md)
6. [Browser & computer automation](browser-and-computer-automation.md)
7. [Artifacts as apps](artifacts-as-apps.md)
8. [Unattended pipelines](unattended-pipelines.md)
9. [Security & prompt injection](security-and-prompt-injection.md): read this before you ship anything from steps 5–8.
10. [Agentic API patterns](agentic-api-patterns.md): for building on the API directly.
11. [API cost & latency](api-cost-and-latency.md)
12. [Evals & observability](evals-and-observability.md): close the loop, so every change above gets measured.

API-only builders: read 1, 9, 10, 11, 12 in that order.
