# Context engineering

Context is the budget every other technique spends. The rules below are about what enters the window, when it gets there, what survives compaction, and when to throw the window away.

Scripts: [`examples/context-engineering/`](examples/context-engineering/).

## Load map (Claude Code)

| Source | Enters context | After `/compact` or auto-compact |
|---|---|---|
| Managed `CLAUDE.md`, `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md` | At launch | Re-injected from disk (project root and unscoped) |
| `CLAUDE.md` / `CLAUDE.local.md` in cwd and every ancestor | At launch, root-first, so the file nearest cwd is read last | Project-root file re-injected from disk |
| `CLAUDE.md` in a subdirectory of cwd | When Claude reads, writes or edits a file there | Summarized away; reloads on next touch |
| `.claude/rules/*.md` without `paths:` | At launch, same priority as `.claude/CLAUDE.md` | Re-injected |
| `.claude/rules/*.md` with `paths:` | When a matching file is read, written or edited | Summarized away; reloads on next match |
| `@path` imports | Expanded at launch with the importing file, up to 4 hops | Same as importing file |
| Auto memory `MEMORY.md` | First 200 lines or 25KB | Re-injected |
| Skill bodies | When invoked | Re-injected, 5k tokens per skill, 25k total, oldest dropped first |
| Files Claude read | When read | Up to 5 most recently modified re-read; files over 5k tokens come back as a path only |
| `SessionStart` hook with matcher `compact` | After each compaction | Hook output is added |
| HTML block comments in CLAUDE.md | Never (stripped) | n/a |

Two consequences people miss. First, **imports don't save context**: an `@import` costs the same as pasting the file inline. Only `paths:` rules, subdirectory CLAUDE.md files and skills defer cost. Second, **path-scoped rules don't survive compaction**: if a rule must hold for the whole run, drop its `paths:` or move it to the root file.

Source: https://code.claude.com/docs/en/memory, https://code.claude.com/docs/en/context-window

## Compact, rewind, or start fresh

| Situation | Do this |
|---|---|
| Same task, history is mostly useful, nearing the limit | `/compact <what to keep>`; e.g. `/compact keep the failing test names, the schema decision, and the list of files touched` |
| A long detour (debugging, exploration) is done and its details are noise | `/rewind`, pick the message, **Summarize from here**. Keeps everything before the detour verbatim |
| Switching to unrelated work | `/clear` (it's free; `/compact` is a large request because it reads everything it summarizes) |
| Multi-hour task with state on disk (tests, progress notes, git) | Fresh window per leg (Recipe 3). Current models recover state from the filesystem well, and nothing gets summarized lossily |
| Auto-compact fires too late and quality drops first | Lower the window: `/autocompact 400k`, `"autoCompactWindow": 400000` in settings, or `CLAUDE_CODE_AUTO_COMPACT_WINDOW` in CI |
| A subagent has its own long loop | `autoCompactWindow:` in its frontmatter (100000–1000000) |
| API agent with heavy tool output | Context editing + memory tool (Recipe 4) |
| API chat that must run indefinitely | Server-side compaction (Recipe 4, last block) |

Source: https://code.claude.com/docs/en/context-window, https://code.claude.com/docs/en/costs, https://code.claude.com/docs/en/model-config, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.md

---

## Recipe 1: Instruction tree for a large repo with progressive disclosure

**Problem.** Root CLAUDE.md is 600 lines covering five packages. Claude follows it less reliably as it grows, and every session pays for instructions about code it never touches.

**Setup.**

Layout:

```text
CLAUDE.md                         # <80 lines: commands, commit rules, never-do list
.claude/
  rules/
    security.md                   # unscoped: always loaded, must survive compaction
    migrations.md                 # paths: ["**/migrations/**"]
    api-handlers.md               # paths: ["packages/api/src/handlers/**/*.ts"]
  skills/
    release/SKILL.md              # multi-step procedure: loads only when invoked
  settings.json                   # Read deny rules for generated/vendored code
packages/api/CLAUDE.md            # owned by the API team; loads when Claude touches packages/api
packages/web/CLAUDE.md
```

What goes where:

| Content | Home | Why |
|---|---|---|
| Build/test commands, commit format, "never edit generated/" | Root `CLAUDE.md` | Needed in every session, survives compaction |
| Rule for one file type or directory | `.claude/rules/x.md` with `paths:` | Zero cost until a matching file is touched |
| Conventions owned by a package team | `packages/<pkg>/CLAUDE.md` | Versioned with the code; loads on demand |
| Multi-step procedure (release, migration, incident) | Skill | Only the description sits in context until invoked |
| Notes for human maintainers | `<!-- ... -->` in CLAUDE.md | Stripped before injection |
| Anything that must happen every time (lint, block a path) | Hook or `permissions.deny` | CLAUDE.md is advisory; hooks and deny rules are enforced |

`.claude/rules/migrations.md`:

```markdown
---
paths:
  - "**/migrations/**"
---
- Never edit a migration that has merged. Add a new one.
- Every migration needs a down step; run `make migrate-roundtrip` before committing.
```

`.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Read(./**/dist/**/*)",
      "Read(./**/vendor/**/*)",
      "Read(./**/*.generated.*)"
    ]
  }
}
```

Your own `.claude/settings.local.json` (other teams' packages you never work in):

```json
{ "claudeMdExcludes": ["**/packages/legacy-*/**"] }
```

Audit before and after the split. The audit script estimates what loads at launch from a given cwd and flags files over 200 lines, broken imports and big unscoped rules:

```bash
python3 advanced/examples/context-engineering/audit_instructions.py . --cwd packages/api
```

Then confirm inside a session: `/context` (Memory files list and token split), `/doctor prompt-audit` (stale or conflicting instructions). To trace lazy loads, log them with an `InstructionsLoaded` hook.

**Output.** The launch footprint drops to the root file plus unscoped rules. Package conventions arrive only when Claude opens that package. The audit gives you a per-file token table you can diff in PR review.

**Failure modes.**
- Splitting into `@imports` and expecting savings. Imports load in full at launch.
- A `paths:` rule that must hold all session gets summarized away at compaction and doesn't reload until a matching file is touched again. Make it unscoped.
- YAML that doesn't parse makes a rule load **unscoped** without warning. Run `claude --debug` to see the parse error.
- User rule and project rule contradict. Neither one overrides the other, so Claude may follow either.
- Testing a new subdirectory CLAUDE.md: create it from your shell, not by asking Claude to write it, then have Claude read a file in that directory and look for the `Loaded` line.
- Brace-heavy `paths:` globs share a budget of 1,000 expansions. Over budget, the pattern is used literally and matches nothing.

Source: https://code.claude.com/docs/en/memory, https://code.claude.com/docs/en/large-codebases, https://code.claude.com/docs/en/costs

---

## Recipe 2: Survive compaction inside one long session

**Problem.** Two hours into a session, auto-compact fires. Claude forgets the decision you made in hour one, re-reads files it already understood, and drifts from the plan.

**Setup.**

1. Tell the summarizer what matters. Add this to the root `CLAUDE.md`:

   ```markdown
   # Compact instructions
   When compacting, preserve: open decisions and their rationale, exact failing test names
   and error messages, files modified so far, and the next 3 steps. Drop exploration output.
   ```

2. Re-inject live state after every compaction instead of relying on the summary. In `.claude/settings.json`:

   ```json
   {
     "hooks": {
       "SessionStart": [
         {
           "matcher": "compact",
           "hooks": [
             {
               "type": "command",
               "command": "python3 \"$CLAUDE_PROJECT_DIR\"/advanced/examples/context-engineering/session_state.py --dir \"$CLAUDE_PROJECT_DIR\""
             }
           ]
         }
       ]
     }
   }
   ```

   [`session_state.py`](examples/context-engineering/session_state.py) prints about 30 lines: counts from `tests.json`, failing and next tests, the tail of `progress.txt`, the last commits, and the number of uncommitted paths. Hook stdout goes into context.

3. Compact earlier and on your terms: `/autocompact 400k` (saved per model), or compact manually at a natural boundary with a focus string. For a detour, `/rewind` → **Summarize from here** beats a whole-conversation compact.

4. Tell the model compaction exists so it doesn't wrap up early (from the prompting guide):

   ```text
   Your context window will be automatically compacted as it approaches its limit, allowing
   you to continue working indefinitely from where you left off. Do not stop tasks early due
   to token budget concerns. As you approach the limit, save progress and state to
   progress.txt and commit before the context window refreshes.
   ```

**Output.** After each compaction, Claude sees the summary plus a fresh, disk-truthful state brief, the re-read root CLAUDE.md, and up to five recently edited files. `/usage` reports an "expected rebuild" for the compaction's cache miss, so you can tell it apart from a real cache miss.

**Failure modes.**
- Hook context added *before* compaction is summarized like everything else. Only the `compact`-matched SessionStart output arrives fresh.
- Re-injected skill bodies are truncated from the end. Keep critical instructions at the top of `SKILL.md`.
- `/compact` on a huge context is itself expensive. If you were going to restart anyway, `/clear` costs nothing.
- Background subagents keep running through compaction. Claude is reminded they exist, but their earlier partial output is gone.
- `Autocompact is thrashing`: compaction succeeded but one oversized file or tool output refilled the window several times in a row. Read the file in line ranges, `/compact` with a focus that drops the big output, or push that work to a subagent.

Source: https://code.claude.com/docs/en/hooks-guide, https://code.claude.com/docs/en/context-window, https://code.claude.com/docs/en/costs, https://code.claude.com/docs/en/troubleshooting, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.md

---

## Recipe 3: Fresh windows instead of compaction (the relay)

**Problem.** An overnight build of a 40-requirement feature. Compaction is lossy and compounds: by the third summary, constraints are gone. You want every leg to start clean and rebuild its state from disk.

**Setup.** Put three files and a git repo in the project:

- `tests.json`: the scope, as structured data. Only the `status` field ever changes.
- `progress.txt`: free-form notes per session (what was done, what's next, gotchas).
- `init.sh`: starts services, runs the suite. Each leg's first action.

```json
{ "tests": [
  { "id": 1, "name": "auth_login_happy_path", "status": "passing" },
  { "id": 2, "name": "auth_lockout_after_5_failures", "status": "failing" },
  { "id": 3, "name": "export_csv_utf8_bom", "status": "not_started" }
] }
```

Run the relay ([`relay.py`](examples/context-engineering/relay.py)):

```bash
python3 advanced/examples/context-engineering/relay.py \
  --dir ./my-feature --model opus --legs 12 --max-turns 60 \
  --leg-budget 3 --total-budget 25 --permission-mode acceptEdits
python3 advanced/examples/context-engineering/relay.py --dir ./my-feature --dry-run  # show prompts
```

The first leg gets a scaffolding-only prompt: write `tests.json` from `SPEC.md`, write `init.sh` and the tests, commit, implement nothing. Every later leg is a new `claude -p` process. Its prompt includes the `session_state.py` brief and a fixed start ritual:

```text
Call pwd; you may only read and write inside this directory.
Read progress.txt, tests.json and `git log --oneline -15`. Run ./init.sh.
Run one end-to-end check of something already marked passing before new work.
Pick the lowest-id failing or not_started test ... Only change a test's "status" field.
After each test goes green: update tests.json, append to progress.txt, git commit.
```

Between legs the harness commits anything left uncommitted, reads `total_cost_usd` from `--output-format json`, and stops in four cases: everything passes, the budget is spent, the leg cap is hit, or two legs in a row produce no commit and no status change.

**Output.** One commit per passing test plus a checkpoint commit per leg, a `progress.txt` you can read in the morning, and a per-leg cost line. Any leg can be killed and resumed, because nothing lives only in a context window.

**Failure modes.**
- Test gaming: the model edits or deletes tests to go green. Keep the "only `status` changes" rule, and add a `PreToolUse` hook that blocks edits to `tests/` after leg 1 if you need it enforced.
- No end-to-end check at the start of a leg. A regression from leg 4 then surfaces at leg 9. Keep step 2 of the ritual.
- `--max-budget-usd` is a client-side estimate and can overshoot. Leave headroom in `--total-budget`.
- `--max-turns` ends the leg with an error. Work in progress gets committed as a checkpoint, so tell the model to stop starting new tests near the end of its turns.
- `--permission-mode acceptEdits` covers reads, file edits and common filesystem commands, not your test runner. Pre-allow `./init.sh` and the test command in `permissions.allow`, or the leg can't verify anything. Never use `bypassPermissions` outside a sandbox.

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.md (multi-context-window workflows, state management), https://code.claude.com/docs/en/cli-reference, https://code.claude.com/docs/en/headless, https://code.claude.com/docs/en/permission-modes, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md (multisession pattern)

---

## Recipe 4: API agents: context editing, memory tool, server-side compaction

**Problem.** Your own agent loop reads hundreds of files. Tool results fill the window by step 30, and old results you no longer need cost input tokens on every request.

**Setup.** [`memory_agent.py`](examples/context-engineering/memory_agent.py) runs a manual tool loop with:

```python
client.beta.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    system=SYSTEM,            # "record findings in /memories before moving on"
    messages=messages,        # full, unmodified history kept client-side
    tools=[{"type": "memory_20250818", "name": "memory"}, read_file, list_files],
    betas=["context-management-2025-06-27"],
    context_management={"edits": [
        # thinking clearing must be listed first when combining strategies
        {"type": "clear_thinking_20251015", "keep": {"type": "thinking_turns", "value": 2}},
        {"type": "clear_tool_uses_20250919",
         "trigger": {"type": "input_tokens", "value": 60000},
         "keep": {"type": "tool_uses", "value": 4},
         "clear_at_least": {"type": "input_tokens", "value": 15000},
         "exclude_tools": ["memory"]},
    ]},
)
```

How the pieces fit:

| Knob | Default | Set it because |
|---|---|---|
| `trigger` | 100k input tokens | Clear well before quality degrades, not at the wall |
| `keep` | 3 tool uses | Recent results the model is actively using |
| `clear_at_least` | none | Clearing invalidates the prompt cache. Only clear when enough is freed to pay for the cache rewrite |
| `exclude_tools` | none | Never clear memory reads, or the model loses its own notes |
| `clear_tool_inputs` | false | Set true when tool *inputs* are large (e.g. file writes) |
| `clear_thinking` `keep` | model-dependent (current models keep all) | Set it explicitly if you run across model tiers. Keeping thinking preserves cache hits |

When the context nears the clearing threshold, Claude gets an automatic warning and can write to `/memories` before results disappear. The memory tool is client-side: the script's `MemoryStore` implements `view/create/str_replace/insert/delete/rename` against a local directory. Paths are resolved with `Path.resolve()` + `relative_to()`, `%2e` and backslashes are rejected, and file size and view length are capped. The memory tool itself needs no beta header; context editing does.

```bash
python3 advanced/examples/context-engineering/memory_agent.py --task "Audit ./src for SQL built by string concatenation; record findings" --root ./src
python3 advanced/examples/context-engineering/memory_agent.py --task x --dry-run   # config only, no API call
```

For an agent that must run indefinitely, swap in threshold compaction (a different beta). It summarizes server-side when input reaches the trigger:

```python
resp = client.beta.messages.create(
    betas=["compact-2026-01-12"],
    model="claude-opus-5-5", max_tokens=4096, messages=messages, tools=tools,
    context_management={"edits": [{
        "type": "compact_20260112",
        "trigger": {"type": "input_tokens", "value": 150000},   # minimum 50,000
        "instructions": "Summarize the transcript inside <summary></summary> tags. Include "
            "what is needed to continue the task in a new context window. Do not call any "
            "tools while writing this summary; respond with text only.",
    }]},
)
messages.append({"role": "assistant", "content": resp.content})  # API drops pre-compaction blocks
```

On-demand compaction (`compact-2026-09-04`, top-level `compaction` parameter) is the docs' recommended default when you need to choose the moment or keep recent turns verbatim. Combining threshold compaction and `clear_tool_uses` in one request isn't shown in the docs (unverified).

**Output.** Each response carries `context_management.applied_edits` (e.g. `cleared_tool_uses: 8, cleared_input_tokens: 50000`), which the script logs. Input tokens per step stay flat instead of climbing. `/memories/findings.md` holds the durable result, so a crash or a new conversation resumes from it.

**Failure modes.**
- You edit history client-side to "help". Server-side clearing never invalidates thinking blocks on current models, but your own edits to earlier turns can, and new accounts get rejected requests for replayed invalidated blocks.
- No `clear_at_least`: small clears break the cache every few steps and cost more than they save.
- Compaction with tools defined sometimes returns a `compaction` block with `content: null` because the model called a tool instead of summarizing. Use the no-tools `instructions` above.
- Compaction billing is easy to undercount. Top-level `usage` excludes the compaction iteration, so sum `usage.iterations` instead.
- Threshold compaction always summarizes with the request's model. There's no cheaper-summarizer option.
- Memory handler without traversal checks: `/memories/../../.env` is a real attack path when tool results contain injected text.

Source: https://platform.claude.com/docs/en/build-with-claude/context-editing.md, https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md, https://platform.claude.com/docs/en/build-with-claude/compaction.md, https://platform.claude.com/docs/en/build-with-claude/compaction-threshold.md, https://platform.claude.com/docs/en/build-with-claude/compaction-on-demand.md
