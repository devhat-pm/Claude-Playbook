# Claude-Playbook
Practical playbook for getting the most out of Claude: coding (chat, Claude Code, API), design &amp; visuals, skills, connectors (MCP), prompting, which model to use when, voice, Claude in Chrome, automations and scheduled tasks, Cowork-style handoffs — plus the hidden capabilities most people never find. Includes copy-paste templates.

Last reviewed: 2026-10-20

[Changelog](CHANGELOG.md) · [What has been verified](advanced/README.md#verification-status)

## Fundamentals

| Guide | What it covers |
|---|---|
| [Hidden gems](docs/00-hidden-gems.md) | Power-user tricks most people never find |
| [Code](docs/01-code.md) | Chat vs Claude Code vs API, CLAUDE.md, coding prompts |
| [Graphics & design](docs/02-graphics-and-design.md) | Visuals, artifacts, design work |
| [Skills](docs/03-skills.md) | Writing and using skills |
| [Connectors (MCP)](docs/04-connectors.md) | Connecting Claude to your tools |
| [Prompting](docs/05-prompting.md) | Prompting effectively |
| [Choosing a model](docs/06-choosing-a-model.md) | Which model, when |
| [Voice](docs/07-voice.md) | Voice mode |
| [Claude in Chrome](docs/08-claude-in-chrome.md) | Browser automation basics |
| [Automations](docs/09-automations.md) | Scheduled, triggered and unattended work |
| [Cowork & the Claude app](docs/10-cowork-and-the-claude-app.md) | Cowork handoffs and the desktop app |

Templates: [CLAUDE.md](templates/CLAUDE.md) · [SKILL.md](templates/SKILL.md) · [Prompt](templates/prompt-template.md) · [Scheduled task](templates/scheduled-task-prompt.md)

## By role

What to do on Monday in your job: workflows with copy-paste prompts, setup and guardrails. Start with the [shared setup](roles/_shared-setup.md), then see the [role index](roles/README.md).

| Role | Best first workflow |
|---|---|
| [Doctors & clinicians](roles/doctors-and-clinicians.md) | Patient handout at a set reading level (not a clinical decision tool) |
| [Developers](roles/developers.md) | Onboard to an unfamiliar codebase in one session |
| [Designers](roles/designers.md) | Mock up a screen in Claude Design on your design system |
| [Biologists & life scientists](roles/biologists-and-life-scientists.md) | CSV to stats to figure, assumptions stated |
| [Researchers & academics](roles/researchers-and-academics.md) | Citation audit of a reference list |
| [SEO & content](roles/seo-and-content.md) | Cluster a keyword CSV into topics |
| [HR & recruiters](roles/hr-and-recruiters.md) | Structured interview kit with a scoring rubric |
| [Marketers](roles/marketers.md) | Campaign brief from a messy kickoff |
| [Finance specialists](roles/finance-specialists.md) | Variance analysis from an uploaded .xlsx |

## Advanced

Recipes for daily users: problem, exact setup, output, failure modes. Start with [advanced/README.md](advanced/README.md) for the reading order.

| # | Guide | What it covers |
|---|---|---|
| 1 | [Context engineering](advanced/context-engineering.md) | CLAUDE.md hierarchies, rules, multi-hour runs, compaction, context editing, memory tool |
| 2 | [Multi-agent orchestration](advanced/multi-agent-orchestration.md) | Orchestrator/worker, custom subagents, worktrees, fan-out, cost |
| 3 | [Hooks & guardrails](advanced/hooks-and-guardrails.md) | Protected paths, auto-lint, secret scanning, test gates, permissions, sandboxing |
| 4 | [Building MCP servers](advanced/building-mcp-servers.md) | Remote servers in TS/Python, auth, tool design, tunnels, custom connectors |
| 5 | [Advanced skills](advanced/advanced-skills.md) | Scripts and validators, eval harness, trigger tuning, plugins, org rollout |
| 6 | [API cost & latency](advanced/api-cost-and-latency.md) | Caching, effort, fast mode, batch, token counting, routing, benchmark |
| 7 | [Agentic API patterns](advanced/agentic-api-patterns.md) | Tool runner, programmatic tool calling, tool search, structured outputs, Managed Agents |
| 8 | [Browser & computer automation](advanced/browser-and-computer-automation.md) | Build-test-verify in Chrome, GIF bug reports, scraping, injection defenses |
| 9 | [Artifacts as apps](advanced/experimental/artifacts-as-apps.md) *(experimental)* | Runtime capabilities, shared DB, design systems, design sync, multi-file. Page-side API is undocumented. |
| 10 | [Unattended pipelines](advanced/unattended-pipelines.md) | Scheduled tasks, routines, GitHub Actions headless, Slack, idempotency |
| 11 | [Security & prompt injection](advanced/security-and-prompt-injection.md) | Threat model, confirmation gates, least privilege, audit, red-teaming |
| 12 | [Evals & observability](advanced/evals-and-observability.md) | Eval sets, LLM-as-judge, CI regression, OpenTelemetry, usage APIs |

Runnable examples live in [`advanced/examples/`](advanced/examples/).
