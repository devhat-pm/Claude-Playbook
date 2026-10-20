# Changelog

## v0.1.0 — 2026-10-20

First public release.

- **Fundamentals docs.** 11 guides in `docs/`: hidden gems, code (chat, Claude Code, API), graphics and design, skills, connectors (MCP), prompting, choosing a model, voice, Claude in Chrome, automations, and Cowork and the Claude app. Copy-paste templates are in `templates/`.
- **12 advanced guides** in `advanced/`, written as recipes (problem, setup, output, failure modes) with runnable examples: context engineering, multi-agent orchestration, advanced skills, building MCP servers, hooks and guardrails, agentic API patterns, API cost and latency, browser and computer automation, unattended pipelines, security and prompt injection, evals and observability, and (experimental) artifacts as apps.
- **Measured benchmark and cache-probe results.** The placeholder cost table in `advanced/api-cost-and-latency.md` is replaced with one measured run from 2026-10-20: Haiku, Sonnet and Opus 5.5 × low, medium and high effort × 5 runs on a committed 20-item spam/ham dataset, with latency, cost and pass rate. A Sonnet 5.5 prompt-cache probe recorded the real `cache_creation_input_tokens` and `cache_read_input_tokens`. Raw output is committed next to the scripts.
- **Verification status.** `advanced/README.md#verification-status` lists every example as ran end-to-end, ran offline only, compiled only, or template only.
- **UNVERIFIED checklist.** `advanced/UNVERIFIED.md` tracks every claim still marked "(unverified)", with the URL to check it against.
