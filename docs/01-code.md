# Code with Claude

Three surfaces, pick by how much autonomy you want:

| Surface | Best for |
|---|---|
| **Claude app (chat)** | Snippets, explanations, debugging a pasted stack trace, scripts up to a few files, data analysis. Claude has a sandbox and will run what it writes. |
| **Claude Code** | Working *inside* your repo: multi-file changes, refactors, tests, PRs. Terminal, VS Code/JetBrains, web (claude.ai/code), desktop and mobile. |
| **API / Agent SDK** | Building your own product or agent on Claude. |

## Claude Code essentials

```bash
npm install -g @anthropic-ai/claude-code
cd your-project && claude
```

- `/init` generates a starter **CLAUDE.md** — the file Claude reads every session. Treat it as onboarding notes for a sharp new hire, not documentation. Put in: build/test commands it can't guess, style rules that differ from defaults, gotchas, what it must never do. Leave out: anything it can learn by reading the code. Check it into git. Template: [`templates/CLAUDE.md`](../templates/CLAUDE.md).
- Hierarchy: `~/.claude/CLAUDE.md` (you, all projects) → `./CLAUDE.md` (team) → `./.claude/rules/*.md` → `./CLAUDE.local.md` (you, this repo, git-ignored). Child directories can have their own; they load when you touch files there. `@path/to/file.md` imports other files.
- **Plan mode** first for anything non-trivial: ask for a plan, review it, then execute. Cheaper than undoing.
- **Fresh session per task.** Long conversations degrade. `/clear`, or start new and point it at `progress.md` + git log.
- **Skills, hooks, subagents, plugins** all live under `.claude/`. Hooks run shell commands on tool events (lint on every edit, block edits to `/migrations`, etc.).
- **Claude Code + Chrome** = build → open in browser → verify → fix loop with no human in the middle.
- **Scheduled tasks**: `/schedule` or claude.ai/code/scheduled for recurring jobs (nightly test triage, dependency bumps). Cloud tasks only push to `claude/`-prefixed branches by default.
- Docs: https://code.claude.com/docs

## Prompts that work for coding

- Be imperative. *"Fix the race in `OrderService.commit`"* not *"any thoughts on the race condition?"*
- Give the verification: *"run `pytest tests/orders` and don't stop until green."*
- For long autonomous runs: ask it to write tests first into `tests.json`, keep `progress.txt`, use git as checkpoints, and *"it is unacceptable to remove or edit tests."*
- Anti-overengineering: *"only change what's asked; no new abstractions, no defensive code for impossible cases, no docstrings on code you didn't touch."*
- Anti-hallucination: *"never speculate about code you haven't opened; read the file first."*
- Anti-test-gaming: *"general solution for all valid inputs; don't hardcode for the tests; tell me if a test is wrong instead of working around it."*
- Reversibility rule: *"local reversible actions freely; ask before anything destructive, force-push, or visible to others."*

## API quick notes (verify at https://platform.claude.com/docs)

- Current models and `effort` parameter: see [Choosing a model](06-choosing-a-model.md).
- **Adaptive thinking** is the default on current models; `budget_tokens` is gone on 4.7+. Control depth with `effort`, cap cost with `max_tokens`.
- **Prefill** on the last assistant turn is no longer supported (4.6+). Use structured outputs / tool enums / "respond without preamble."
- Keep conversation history **append-only** and pass thinking blocks back unchanged; editing earlier turns invalidates later thinking blocks on 5.5-era models. Use mid-conversation system messages and server-side compaction instead.
- **Prompt caching** for anything with a big stable prefix (system prompt, tools, docs). Cache reads on Fable 5.1 are a quarter of input price.
- **Batch API** for anything that can wait — half price.
- Server tools worth knowing: web search, web fetch, code execution, computer use, browser use, memory, tool search (for 100+ tools), programmatic tool calling.
- **Structured outputs** for schema-locked JSON; **strict tool use** for exact tool schemas.
- **Managed Agents** if you want Anthropic to host the agent loop, sandbox, memory and scheduling.
- Ask the `claude-code-guide` agent inside Claude Code for anything SDK/API — it reads the live docs.

## Lesser-known

- Claude can **attach a GitHub repo** mid-chat in the app and clone it into its workspace — ask a question about a repo and it will add it.
- In the app, "more than a few lines of code" is delivered as a **file** by design (code in chat is awkward to use). Ask for a file if you got a snippet.
- You can hand Claude a **screenshot of a UI** and ask for the component; vision on current models is strong enough that cropping/zooming tools are the next lever.
- Claude Code's `/loop` runs a prompt on an interval *inside* the session (expires after 7 days). For durable schedules use Routines / cloud scheduled tasks.
- `claude -p "prompt"` for scripting/CI; pipe output to other tools.
- The frontend-design skill's prompt (avoid Inter/Roboto, purple gradients, cookie-cutter layouts) is public and worth pasting into any UI prompt: https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md
