# Multi-agent orchestration

More agents means more tokens and more chances to fail. Each extra agent has to pay for itself with parallelism, context isolation or cheaper tokens. Use the recipes below when it does. Use Recipe 5 to stop Claude from delegating when it doesn't.

Scripts and agent files: [`examples/multi-agent-orchestration/`](examples/multi-agent-orchestration/).

## Pick the pattern

| Pattern | Mechanism | Use when | Don't use when |
|---|---|---|---|
| Orchestrator → workers (in session) | Claude Code subagents (`.claude/agents/*.md`) | Side work would flood the main context: wide searches, test runs, log triage | The task is a handful of tool calls, or the phases share lots of context |
| Orchestrator → workers (API) | Your code: one planner call, N parallel worker calls, one merge call | A batch job over many independent inputs: audits, extraction, classification | Workers need to see each other's results mid-run |
| Executor + advisor | `advisor_20260301` server tool | A long agent loop where most turns are mechanical but the plan matters | Single-turn Q&A; tasks where every turn needs the big model |
| Parallel sessions in worktrees | `claude -p --worktree`, `isolation: worktree` | Independent code changes that would collide in one checkout | Changes touch the same files (partition them first) |
| Agent teams | Shared task list + messaging (experimental, off by default) | Workers must coordinate while they run | Anything a fan-out + merge can do. Teams cost roughly 7x a standard session in plan mode |
| Dynamic workflows | A script that runs many subagents and cross-checks them | 500-file migrations, codebase-wide audits that outgrow a handful of subagents | One-off small jobs |

Source: https://code.claude.com/docs/en/agents, https://code.claude.com/docs/en/costs, https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool.md

## Cost tables

API list prices, USD per million tokens (checked 2026-10-20):

| Model | ID | Input | Output | Cache hit | Notes |
|---|---|---|---|---|---|
| Fable 5.1 | `claude-fable-5-1` | $10 | $50 | $0.25 | Hardest reasoning, long-horizon |
| Opus 5.5 | `claude-opus-5-5` | $4 | $20 | $0.20 | Default recommendation for most work |
| Sonnet 5.5 | `claude-sonnet-5-5` | $2 | $10 | $0.10 | |
| Haiku 5.5 | `claude-haiku-5-5` | $0.10 / **$0.50** | $0.50 / **$2.50** | $0.01 / $0.05 | Bold = prompts over 100k tokens |

Batch API is 50% off. A 5-minute cache write is 1.25x input, a 1-hour write is 2x.

Worked example: audit 600k tokens of source and produce 40k tokens of findings. Orchestrator plan + merge = 30k in / 12k out. Single-pass arithmetic. Real agent loops re-send history every turn, which widens the gap further.

| Configuration | Workers | Orchestrator | Total |
|---|---|---|---|
| Fable 5.1 does everything | | | $8.00 |
| Opus 5.5 does everything | | | $3.20 |
| Opus 5.5 orchestrator + Sonnet 5.5 workers | $1.60 | $0.36 | $1.96 |
| Fable 5.1 orchestrator + Haiku 5.5 workers | $0.08 | $0.90 | $0.98 |
| **Opus 5.5 orchestrator + Haiku 5.5 workers** | $0.08 | $0.36 | **$0.44** |
| Same, but each Haiku worker prompt is 150k tokens | $0.40 | $0.36 | $0.76 |

The last row is the Haiku tier trap: one oversized worker prompt costs 5x. Keep each worker under 100k tokens. [`fanout.py`](examples/multi-agent-orchestration/fanout.py) packs at most ~75k.

Executor/advisor example: 25-turn agent loop, ~750k cumulative executor input, 20k output, 3 advisor consults on a 40k transcript, ~1.6k advisor output each (the docs' typical range including thinking):

| Configuration | Executor | Advisor | Total |
|---|---|---|---|
| Opus 5.5 alone | $3.40 | | $3.40 |
| Haiku 5.5 + Fable 5.1 advisor | $0.085 | $1.44 | $1.53 |
| Haiku 5.5 + Opus 5.5 advisor | $0.085 | $0.58 | $0.66 |

Caching lowers both columns. Quality is task-dependent, so evaluate on your own workload before switching.

Source: https://platform.claude.com/docs/en/about-claude/pricing.md, https://platform.claude.com/docs/en/about-claude/models/overview.md, https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool.md

---

## Recipe 1: A subagent roster with hard tool boundaries

**Problem.** Claude spawns general-purpose subagents on your main model for everything. They can edit anything, they inherit your whole CLAUDE.md, and a "quick search" costs Opus rates.

**Setup.** Copy the three definitions into `.claude/agents/` and the hook into `.claude/hooks/`:

```bash
mkdir -p .claude/agents .claude/hooks
cp advanced/examples/multi-agent-orchestration/agents/*.md .claude/agents/
cp advanced/examples/multi-agent-orchestration/readonly-bash.sh .claude/hooks/ && chmod +x .claude/hooks/readonly-bash.sh
```

| Agent | Model | Tools | Key fields | Job |
|---|---|---|---|---|
| [`scout`](examples/multi-agent-orchestration/agents/scout.md) | `haiku` | `Read, Grep, Glob` | `omitClaudeMd: true`, `effort: low`, `maxTurns: 25` | Locate code; returns `path:line` list in a fixed shape |
| [`implementer`](examples/multi-agent-orchestration/agents/implementer.md) | `sonnet` | inherited minus `WebFetch, WebSearch, Agent` | `isolation: worktree`, `permissionMode: acceptEdits` | One change, own branch, commits, reports the verifying command |
| [`reviewer`](examples/multi-agent-orchestration/agents/reviewer.md) | `opus` | `Read, Grep, Glob, Bash` | `PreToolUse` hook blocks writes and non-inspection git | Independent review of a finished branch |

Frontmatter for the reviewer:

```yaml
---
name: reviewer
description: Independent reviewer that has not seen the work being made. Use once per finished branch...
tools: Read, Grep, Glob, Bash
model: opus
maxTurns: 30
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./.claude/hooks/readonly-bash.sh"
---
```

Session-wide caps go in `.claude/settings.json` ([example](examples/multi-agent-orchestration/settings.json)):

```json
{
  "env": {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4"
  },
  "permissions": { "deny": ["Bash(git push *)"] },
  "worktree": { "baseRef": "head", "symlinkDirectories": ["node_modules"] }
}
```

Depth `1` turns nesting off (the default allows 3 layers). Concurrency defaults to 20. `baseRef: "head"` makes worktree subagents branch from your current work instead of the remote default branch. Without it, the implementer won't see your unpushed commits.

Drive it explicitly:

```text
Use scout to find every caller of LegacyBilling.charge. Then, for each of the three call
sites it reports, run one implementer in parallel to migrate it to Billing.charge (acceptance:
`pytest tests/billing -q`). When all three finish, run reviewer on each branch. Merge only
branches with VERDICT: merge.
```

**Output.** Searches run at Haiku rates and return under 40 lines each. Edits land on separate `worktree-*` branches, each with a commit and a test command. Reviews come back in a fixed VERDICT/BLOCKERS shape you can grep. `/tasks` shows each subagent's model and effort.

**Failure modes.**
- Misspelled frontmatter keys are ignored silently (`maxturns` ≠ `maxTurns`). Check with `claude --debug` and search the log for `does not recognize or apply`.
- `tools:` entries that resolve to nothing make the spawn fail with "zero tools".
- `disallowedTools: Bash(git push *)` removes **all** of Bash. Command-level blocks belong in `permissions.deny`.
- Frontmatter hooks in project agents don't run until you accept workspace trust for that folder, and a `-p` session doesn't count as trusted. In headless runs the reviewer runs **without** its read-only hook. Put the hook in `settings.json` instead, or use a user-level agent.
- `readonly-bash.sh` is a best-effort denylist. Chained commands such as `git log && git push` get past its git check. Keep `permissions.deny` as the hard stop for anything that must never happen.
- Background subagents (the default) only get a fixed list of built-in tools. Anything outside it is dropped even if listed in `tools`.
- Subagents don't inherit your auto memory or conversation. If the scout needs a rule like "ignore `legacy/`", it has to be in the delegation prompt, especially with `omitClaudeMd: true`.
- A worktree subagent loads instruction files from the main checkout, not from its branch.
- `permissionMode: acceptEdits` doesn't cover your test runner. Add `Bash(pytest *)` (or your equivalent) to `permissions.allow`, or the implementer can't run its acceptance command.

Source: https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/worktrees

---

## Recipe 2: API fan-out with a Haiku workforce and an Opus or Fable planner

**Problem.** You need findings across 2,000 files. A single agent loop on a big model re-reads its growing history every turn, and the bill scales with history times turns.

**Setup.** [`fanout.py`](examples/multi-agent-orchestration/fanout.py) runs three stages:

1. **Plan.** The orchestrator (`claude-opus-5-5`, or `claude-fable-5-1` with `--orchestrator fable`) gets the job plus the *file list* only, never contents. It returns `{"subtasks":[{"id","instruction","files"}]}` via `output_config.format` with a JSON schema, capped at `--max-workers`. The prompt says "prefer fewer, larger subtasks; if one worker can do it, return one."
2. **Fan out.** `AsyncAnthropic` runs `claude-haiku-5-5` workers under an `asyncio.Semaphore(--concurrency)`. Each worker sees only its instruction and its files (line-numbered, ~75k-token cap), and returns `{"findings":[{file,line,claim,evidence}],"unsure":[...]}`. Evidence must be a quoted line. One worker's exception becomes an empty result with `error`, not a crash.
3. **Merge.** Python dedupes on `(file, line, claim[:80])` first. The orchestrator then sees only findings, unsure items and failed subtask IDs, drops claims the evidence doesn't support, and lists failures as coverage gaps.

```bash
python3 advanced/examples/multi-agent-orchestration/fanout.py --job "Find SQL built by string concatenation" \
  --root ./src --glob "**/*.py" --dry-run           # file count, token estimate, cost estimate
python3 advanced/examples/multi-agent-orchestration/fanout.py --job "..." --root ./src --max-workers 8 --concurrency 4
```

**Output.** A severity-grouped report on stdout. Plan, worker and merge cost go to stderr from each response's `usage`. Raw source never enters the orchestrator's context.

**Variations.**
- Not latency-bound? Send the worker stage through the Batch API for 50% off.
- On Opus 5.5 as the lead in an agentic version, append `elapsed 340s / 1200s` to each turn. The prompting guide reports this improves parallel pacing.
- On Fable 5.1 as lead, make the spawn tool return immediately and deliver results in later user messages, so the lead keeps working while workers run.

**Failure modes.**
- The planner over-splits (30 subtasks of 3 files each). Hard-cap `--max-workers` and keep the "fewer, larger" instruction.
- Workers hallucinate when asked to judge without evidence. The `evidence` field plus the merge step's "drop unsupported claims" catches most of it. Spot-check a sample.
- Overlapping `files` across subtasks produce duplicate findings worded differently. Exact-key dedupe misses those, and the orchestrator merge has to catch them.
- 429s at high concurrency. Lower `--concurrency`. A worker that fails is reported as a coverage gap, not retried by the script.
- Schema features outside the supported JSON Schema subset (e.g. `minimum`) are rejected or stripped. Keep schemas plain with `additionalProperties: false`.

Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md, https://platform.claude.com/docs/en/about-claude/pricing.md, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5.md, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1.md

---

## Recipe 3: Executor/advisor with a cheap executor and a strong advisor

**Problem.** A coding agent on Opus is good but expensive per turn, and most turns are `ls`, `cat`, `pytest`. On Haiku it's cheap but picks bad approaches.

**Setup.** [`advisor_executor.py`](examples/multi-agent-orchestration/advisor_executor.py):

```python
client.beta.messages.create(
    model="claude-haiku-5-5",                    # executor: all tool calls and output
    betas=["advisor-tool-2026-03-01"],
    system=SYSTEM,                                # docs' Haiku coding block, abridged
    tools=[{
        "type": "advisor_20260301", "name": "advisor",
        "model": "claude-opus-5-5",               # or claude-fable-5-1
        "max_uses": 2,                            # per request
        "max_tokens": 2048,                       # per advisor call (min 1024)
        "caching": {"type": "ephemeral", "ttl": "5m"},
    }, read_file, write_file, run_cmd],
    messages=messages, max_tokens=8000,
)
```

Key moves, all from the advisor docs:
- **System prompt.** Call the advisor after orientation and before the first write. Call it again before declaring done, after making the result durable. Hard rule for Haiku on coding work: no state-changing call before an advisor call.
- **Short advice.** Append `(Advisor: please keep your guidance under 80 words.)` to the user message. Instructions addressed to the advisor directly work best.
- **Conversation cap.** Count `advisor_message` entries in `usage.iterations` and remove the tool after `--advisor-cap`. Old `advisor_tool_result` blocks can stay in history. The script never removes the tool while a call is pending, which would be a 400.
- **`pause_turn`.** Append the assistant content unchanged and resend with the tool still present.
- **Cost.** Top-level `usage` counts executor tokens only. Bill `advisor_message` iterations at the advisor's rate.

```bash
python3 advanced/examples/multi-agent-orchestration/advisor_executor.py --workdir ./sandbox \
  --task "Implement slugify() in slug.py with pytest tests; run them until green" --advisor opus --advisor-cap 4
```

**Output.** The final executor message, plus a stderr line: `advisor calls=3 executor=$0.0xx advisor=$0.xx total=$0.xx`. Every file write and command ran at Haiku rates.

**Failure modes.**
- Invalid pairs get a 400. The advisor must be at least as capable as the executor. A Fable 5.1 executor can only take a Fable/Mythos 5.1 advisor.
- Under-calling: Haiku skips the advisor unless prompted. Over-calling: the "hard rule" block on an Opus executor made it consult on trivial first steps. The docs say not to add it to Opus by default.
- The mixed-workload penalty: the Haiku coding block cost ~4 points on a browse/lookup benchmark. Gate it on workload type.
- Advisor tokens don't count toward the executor's `max_tokens` or task budget. Cap them with tool `max_tokens` and `max_uses`.
- Platform: Claude API and Claude Platform on AWS only, not Bedrock, Google Cloud or Foundry.
- `run_cmd` executes shell in `--workdir`. Use a throwaway directory or container.

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool.md

---

## Recipe 4: Parallel worktree sessions, then merge

**Problem.** Six independent fixes sit in the backlog. Done serially in one session, context bloats and each fix waits for the last. Done in parallel in one checkout, the edits collide.

**Setup.** `tasks.txt`:

```text
# name|model|prompt
fix-date-parse|sonnet|Fix the timezone bug in src/dates.py; run pytest tests/test_dates.py until green; commit.
ruff-rules|haiku|Rename deprecated ruff rule codes in pyproject.toml; run ruff check .; commit.
api-retry|sonnet|Add exponential backoff to src/client.py per docs/retry.md; run pytest tests/test_client.py; commit.
```

```bash
echo ".claude/worktrees/" >> .gitignore
printf '.env\n.env.local\n' > .worktreeinclude      # gitignored files copied into each worktree
DRY_RUN=1 advanced/examples/multi-agent-orchestration/parallel_worktrees.sh tasks.txt
REVIEW=1  advanced/examples/multi-agent-orchestration/parallel_worktrees.sh tasks.txt 3 2
```

[`parallel_worktrees.sh`](examples/multi-agent-orchestration/parallel_worktrees.sh) runs each line as:

```bash
claude -p "$prompt ...commit on this branch, do not push, 3-line summary" \
  --worktree "$name" --model "$model" --output-format json \
  --max-turns 40 --max-budget-usd "$BUDGET" --permission-mode acceptEdits
```

It runs at most N at a time (bash 3.2 safe), writes each JSON result to `.claude/fanout-results/`, and then prints:
- per-task cost from `total_cost_usd` and the last lines of `result`
- for each `worktree-<name>` branch, its commits and diffstat against the default branch
- **files touched by more than one branch** (your merge-conflict list)
- with `REVIEW=1`, one Opus pass in `--permission-mode plan` over all branches that proposes a merge order

**Output.** N branches named `worktree-<name>`, each with one focused commit, plus a cost summary, a conflict list and a reviewed merge order. You merge with `git merge --no-ff worktree-<name>`.

**Failure modes.**
- `-p` worktrees aren't cleaned up and keep a lock. Clean them with `git worktree remove .claude/worktrees/<name>` (`git worktree unlock` first if refused).
- New worktrees branch from the remote default branch unless `worktree.baseRef` is `"head"`. Tasks that depend on unpushed work see stale code.
- Fresh checkouts lack deps and `.env`. Use `.worktreeinclude`, `worktree.symlinkDirectories` for `node_modules`, or put the setup step in the prompt.
- Interactive `--worktree` needs workspace trust; `-p` skips the trust check.
- Overlapping files mean the work wasn't independent. Re-partition rather than resolving conflicts by hand every run.
- In a large monorepo, set `worktree.sparsePaths` so each worktree checks out only the packages it needs.

Source: https://code.claude.com/docs/en/worktrees, https://code.claude.com/docs/en/cli-reference, https://code.claude.com/docs/en/headless, https://code.claude.com/docs/en/large-codebases

---

## Recipe 5: Damp over-delegation

**Problem.** Opus 5 and later delegate readily. You see three subagents spawned to answer a question one `grep` would answer, a "verifier" subagent double-checking trivial edits, and a bill several times what the task needed.

**Setup.** Layer three controls, cheapest first.

1. **Prompt** (CLAUDE.md, `--append-system-prompt`, or your API system prompt). This is the docs' sample:

   ```text
   Delegate to a subagent only for large tasks that are genuinely independent and
   parallelizable, such as a wide multi-file investigation. Do not delegate work you can
   finish yourself in a handful of tool calls, and do not use subagents to verify or
   double-check your own work. If one subagent can complete the task, use one rather than
   several, and keep spawn counts low.
   ```

2. **Deterministic caps.** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=2..4` in `settings.json` `env`. For headless and SDK runs, add `--max-budget-usd` (counts subagent spend). The SDK option is `max_budget_usd` / `maxBudgetUsd`.

3. **Make the unavoidable delegation cheap.** A project agent named `Explore` overrides the built-in and keeps its own `model`:

   ```markdown
   ---
   name: Explore
   description: Fast read-only codebase search
   tools: Read, Grep, Glob
   model: haiku
   ---
   Search and report file:line locations. No edits. At most 40 lines.
   ```

   Or force every subagent onto one model: `"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"` plus `"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"`. This ignores per-agent `model` fields, so use it only when no subagent needs a big model.

   To remove a subagent type entirely: `"permissions": {"deny": ["Agent(Explore)"]}`.

**Output.** Fewer spawns, Haiku-priced exploration, and a hard ceiling on nesting and spend. To verify, run `/tasks` during a session (model per subagent) and `/usage` afterwards. Over several sessions, the subagent share of spend should fall.

**Failure modes.**
- Depth `1` also disables legitimate nesting, such as a reviewer that dispatches per-finding verifiers. Raise it per task.
- The concurrency cap only blocks new Agent-tool spawns. Resumed subagents and `/subtask` forks still take slots and can push past it.
- `SUBAGENT_MODEL_FORCE` with an empty `SUBAGENT_MODEL` runs subagents on the **main** model, not on Haiku.
- Claude Code adds its own delegation guidance on Opus 5 only with the `claude_code` system prompt preset. With a custom SDK system prompt, you must add the damping text yourself.
- The opposite failure is real too: with depth and concurrency at the minimum, a wide audit runs serially in one context and hits compaction. Damp delegation; don't ban it.

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5.md, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.md, https://code.claude.com/docs/en/sub-agents
