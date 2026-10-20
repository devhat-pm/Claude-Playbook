# Which model, when

As of October 2026. Check https://platform.claude.com/docs/en/models/overview for prices, context windows and anything newer.

## The lineup

| Model | API id | Reach for it when |
|---|---|---|
| **Claude Fable 5.1** | `claude-fable-5-1` | The hardest stuff: agent sessions that run for hours, deep multistep research, analysis carried through to a finished doc/sheet/deck. Most capable model open to everyone. Thinking always on. |
| **Claude Mythos 5.1** | `claude-mythos-5-1` | Same model as Fable 5.1 without the extra bio/cyber/LLM-R&D safeguards; only for organisations verified through Anthropic's programmes (e.g. Cyber Verification). |
| **Claude Opus 5.5** | `claude-opus-5-5` | Default starting point for serious work: multi-hour coding agents, large refactors, systems engineering, vision-heavy and computer-use workflows. Thinking always on. |
| **Claude Sonnet 5.5** | `claude-sonnet-5-5` | Everyday coding, agents and enterprise workloads where speed matters: code gen, data analysis, content, visual understanding, tool use. |
| **Claude Haiku 5.5** | `claude-haiku-5-5` | Lowest latency and price: real-time apps, high-volume processing, sub-agents, cost-sensitive deployments that still need solid reasoning. |

Older Opus/Sonnet/Haiku 4.x and 5.0 models remain available for a while; migration guides exist per model.

## Two sensible strategies

**Efficiency-first** (prototyping, latency-bound, high volume): start on Haiku 5.5, test properly, upgrade only for specific gaps.

**Capability-first** (complex reasoning, accuracy > cost, high-autonomy agents): start on Opus 5.5, tune prompts, then try to *lower effort* or step down models. If `xhigh`/`max` effort on Opus 5.5 still falls short on long-horizon work, move to Fable 5.1.

## Effort is the lever most people forget

Several models expose an `effort` parameter that trades intelligence for latency/cost *within one model*. Tuning it usually beats switching models.

- Fable 5.1, Opus 5, Sonnet 5.5: default `high`; adjust from there.
- Opus 5.5, Haiku 5.5: default `medium`.
- Opus 4.8 / 4.7: `xhigh` is the sweet spot for coding/agentic work.

**Fast mode** gives up to ~2.5x output speed at premium pricing on supported models when latency is the constraint.

## Combine models

Pair a cheap model with a frontier model so most tokens bill at the lower rate:
- **Executor + advisor**: Haiku/Sonnet does the work, escalates hard calls to Opus/Fable.
- **Orchestrator + workers**: Opus/Fable plans, delegates bulk subtasks to Haiku sub-agents.

Measured examples: https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence

## How to decide for real

1. Build an eval set from your actual prompts and data — this is the step that matters.
2. Run it across candidate models.
3. Compare accuracy, quality, edge-case handling.
4. Weigh against cost and latency.

## In the Claude app

- You can switch models mid-chat from the model picker. Earlier messages stay as they were.
- Fable 5.1 is the top tier for chat and knowledge work; Opus 5.5 for most agentic coding; Sonnet/Haiku when you want speed.
- Some surfaces restrict models (e.g. voice mode doesn't offer Fable; Claude in Chrome on Pro was limited to Haiku at one point) — check the surface's help article.
- Mythos-class models and Project Glasswing: https://www.anthropic.com/glasswing

## Lesser-known

- Fable 5.1 cache reads cost a quarter of the input price — big stable system prompts get cheap.
- Opus 5 is *more* verbose than its neighbours and effort doesn't change it; prompt for brevity instead.
- Fable 5.1 writes *fewer* progress updates during agent runs; ask for them.
- Haiku 5.5 is strong enough for most sub-agent work; don't reflexively use Opus for workers.
- Export-control events in June 2026 briefly suspended Fable/Mythos access; restored July 1. Statement: https://www.anthropic.com/news/fable-mythos-access
