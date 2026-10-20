# Advanced skills: scripts, validators, evals, distribution

Everything below ships as runnable files in [`examples/advanced-skills/`](examples/advanced-skills/):

```
examples/advanced-skills/
  marketplace/.claude-plugin/marketplace.json
  marketplace/plugins/bulk-edit-tools/
    .claude-plugin/plugin.json
    skills/safe-bulk-edit/SKILL.md
    skills/safe-bulk-edit/scripts/{validate_plan.py, apply_plan.py}
    evals/{rename-across-files, ignores-single-typo}/   # `claude plugin eval` format
  evals/cases.json, evals/run_evals.py, evals/variants/desc-b.md   # portable harness
  org/managed-settings.json
```

---

## Recipe 1: Plan, validate, execute with bundled scripts

**Problem.** For multi-file mechanical changes (renames, import moves, config-key migrations), Claude's direct edits usually go wrong in three ways: it misses a call site, it edits a substring it shouldn't (`getUser_cache`), or a second edit rewrites the output of the first. You only find out from the test run, after the files are already changed.

**Setup.** Make the model write an intermediate artifact (`changes.json`). A script validates that artifact, and only a script applies it. The model owns judgement: which files are in scope and what the counts should be. The scripts own correctness.

`SKILL.md` (full file in the examples; this is the part that matters):

```markdown
---
name: safe-bulk-edit
description: Plans, validates and applies the same text change across many files (renaming a function, API, config key or import path across a codebase) with a dry-run diff and backups. Use when the user asks to rename, replace or migrate an identifier or string in more than two files. Not for a single-file fix.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/validate_plan.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/apply_plan.py *)
---
- [ ] 2. Write `changes.json` ... Set `expect_count` on every edit.
- [ ] 3. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_plan.py changes.json`
- [ ] 4. If it prints `ERROR`, fix the plan and go back to step 3. ...
- [ ] 5. ... `apply_plan.py changes.json --dry-run` ...
- [ ] 6. ... `apply_plan.py changes.json`. It must print `VERIFY OK`.
```

Why each piece is there:

- `${CLAUDE_SKILL_DIR}` appears in both the body and `allowed-tools`. Claude Code expands both to the same path, so the exact command the skill tells Claude to run is pre-approved for that turn and nothing else is.
- The validator's errors say how to fix the problem, because the model reads them as its next instruction: `"getUsr" not found in src/main.py. Close matches in file: getUser.` and `file not found: src/nope.py. Similar files: api.py.`
- `expect_count` turns "I think there are 3 call sites" into a claim the script can falsify.
- `apply_plan.py` re-runs validation itself, so a model that skips step 3 still can't write a bad plan. It also backs up to `.bulk-edit-backup/<UTC>/` and runs a verification pass afterwards.
- Constants are justified in comments (`MAX_FILE_BYTES`, `MAX_EDITS`). If the script can't explain a number, Claude can't either.

Try the scripts without Claude:

```bash
cd examples/advanced-skills/marketplace/plugins/bulk-edit-tools/skills/safe-bulk-edit/scripts
python3 validate_plan.py /path/to/repo/changes.json          # exit 0 OK, 1 errors, 2 unreadable plan
python3 apply_plan.py /path/to/repo/changes.json --dry-run   # unified diff only
python3 apply_plan.py /path/to/repo/changes.json             # backup, write, verify
```

**Output.** Run against a two-file fixture with one typo and one missing file, the validator prints:

```
ERROR edits[1]: "getUsr" not found in src/main.py. Close matches in file: getUser.
ERROR edits[2]: file not found: src/nope.py. Similar files: api.py.
FAILED (2 error(s)): 3 edit(s), 1 file(s), 2 replacement(s)
```

After the fix: `OK: 2 edit(s), 2 file(s), 4 replacement(s)`, then a dry-run diff, then `Applied: 2 file(s) changed. Backup: …` and `VERIFY OK`. `word: true` left `getUser_cache` alone.

**Failure modes.**
- *Claude skips the checklist and uses Edit directly.* Skill text is guidance, not enforcement. If that's unacceptable, add a `PreToolUse` hook in the skill's `hooks` frontmatter that blocks `Edit`. A hook runs every time, whether or not Claude is following the skill. Skill hooks register on invocation and stay active for the rest of the session, so scope the matcher tightly.
- *Portability.* `${CLAUDE_SKILL_DIR}` and a Bash-pattern `allowed-tools` only work in Claude Code. A claude.ai upload or the Skills API accepts only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools` in frontmatter, and rejects any other key with a hard error. Body features specific to Claude Code don't run there.
- *API runtime.* Skills on the API run code with no network access and no package installs. Keep the scripts stdlib-only, as these are.
- *Compaction.* After compaction Claude Code may keep only the start of an invoked skill, so keep the checklist near the top.

Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices · https://code.claude.com/docs/en/skills

---

## Recipe 2: Eval-driven skill development (two harnesses)

**Problem.** Seeing a skill fire tells you it was found, not that it helped. You need two numbers, and a baseline to compare them against: does Claude invoke the skill on the prompts it should (and only those), and does the result pass objective checks when it does?

**Setup A: the official harness, `claude plugin eval`** (Claude Code v2.1.269+). Each case is a directory under the plugin's `evals/`:

```
evals/rename-across-files/
  prompt.md        # frontmatter: max_turns, timeout_seconds, allowed_tools, tags; body: the prompt
  case.yaml        # schema_version "1.1", name, context.scaffold_script: fixture.sh
  fixture.sh       # seeds the empty workspace (runs only with --scaffold)
  graders/skill-fired.md             # type: tool_used, tool: Skill, input_match on the skill name
  graders/validated-before-apply.md  # type: tool_order, validate_plan.py before apply_plan.py
  graders/no-old-name.md             # type: regex over src/jobs.py, match: not_contains
evals/ignores-single-typo/graders/skill-not-fired.md   # tool_used min: 0, max: 0, arm: both
```

```bash
cd examples/advanced-skills/marketplace/plugins/bulk-edit-tools
claude plugin eval . --scaffold --allow-tools Write Edit "Bash(python3 *)" "Bash(git *)"
claude plugin eval . --case rename-across-files --runs 1 --ablation none   # fast iteration on one case
```

Each case runs 3 times with the plugin and 3 times without it, in isolated `claude -p` sessions. Your settings, CLAUDE.md, MCP servers and other plugins don't load, and the agent can't read the eval directory. Runs never prompt for permissions: `Bash`, `Write`, `Edit` and web tools are removed unless you grant them with `--allow-tools`. Neither the case's `allowed_tools` nor the skill's own `allowed-tools` can widen that grant.

**Setup B: a portable harness** ([`evals/run_evals.py`](examples/advanced-skills/evals/run_evals.py) plus [`cases.json`](examples/advanced-skills/evals/cases.json), stdlib only). Use it when you want trigger precision and recall as explicit numbers, custom checks, or a description A/B without restructuring the plugin. It drives `claude -p --output-format stream-json --verbose --plugin-dir …` in a fresh temp workspace per run. It counts a trigger when it sees a `Skill` `tool_use` whose `input.skill` matches (with or without the `plugin:` prefix), then applies regex checks to the final reply or to workspace files. The `input.skill` key matches the `tool_used` grader pattern in the plugin-eval docs. Reading the final reply and `total_cost_usd` from a closing `{"type":"result"}` stream event is (unverified): the docs show those fields for `--output-format json`. The parser falls back to the last assistant text block.

```bash
cd examples/advanced-skills/evals
python3 run_evals.py cases.json --dry-run                 # validates cases, prints commands, no calls
python3 run_evals.py cases.json --runs 3 --baseline --json out.json \
  --min-recall 0.8 --max-false-trigger 0.2 --min-pass 0.9   # exit 1 if any gate fails
```

`cases.json` is one shared fixture plus cases shaped like `{"id", "prompt", "should_trigger", "checks": [{"type":"regex","target":"result"|"file:<path>","pattern","absent"}]}`. The runner refuses suites with fewer than 3 positive and 3 negative cases.

**Output.** Official harness:

```
CASE                  WITH  W/OUT Δ      RUNS COST    NOTES
rename-across-files   …     …     …      6    $…
```

`aggregate-result.json` (`aggregates.overallScore`, `cases[].aggregates.delta`, …) and a self-contained `report.html` go to `evals/results/<timestamp>/`. Add `results/` to `.gitignore`. The portable harness prints one line per run (`with rename-casual run2 fired checks 1/1 41.3s`), then:

```
WITH   recall 0.87  false-trigger 0.08  check-pass 0.93  cost $…      <- example shape, not a real run
W/OUT  check-pass 0.71  cost $…   delta check-pass +0.22
```

**Failure modes.**
- *Δ ≈ 0 and `tool_used: Skill` fails.* Claude isn't choosing the skill on natural phrasing. Go to Recipe 3.
- *The skill fired, checks passed, but Δ is negative.* Suspect the `llm` judge before the plugin. Re-run with `--judge-model sonnet` and write rubrics as concrete PASS and FAIL lines. For long outputs, prefer `regex` over a file.
- *Inflated Δ.* `tool_used: Skill` graders can never pass without the plugin, so `claude plugin eval` reports them with `scored: false` in two-arm runs. Use `arm: both` only for "must not fire" checks.
- *Portable harness leaks.* Unlike the official harness, `run_evals.py` runs in your normal environment, so personal skills, user hooks and CLAUDE.md files from parent directories can affect the result. Treat its numbers as relative between variants, not absolute.
- *Cost.* Every run and every judge call is billed. In CI, set `--max-cost-usd` (exit 2 means partial results) and pin `--model` and `--judge-model`, so that a model rollout doesn't show up as a regression in your skill.
- *skill-creator's `evals/evals.json` is a third format.* Neither tool reads the other's case files.

Source: https://code.claude.com/docs/en/plugin-evals · https://code.claude.com/docs/en/skills#evaluate-and-iterate-on-a-skill · https://code.claude.com/docs/en/headless · https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#evaluation-and-iteration

---

## Recipe 3: Tune the triggering description against a labelled set

**Problem.** Some skills never fire on casual phrasing ("switch it to fetchUser in every file"). Others fire on near-misses (a one-word typo fix, a read-only "where is X used?"). Description edits made by feel tend to fix one of these and break the other.

**Setup.**
1. Keep a labelled set of at least 5 should-trigger prompts in users' own words and at least 4 near-miss negatives. `cases.json` ships this set: casual rename, import migration, "replace every occurrence", plus negatives for a single-file rename, a typo fix, an explanation and find-usages-only.
2. Get a baseline: `python3 run_evals.py cases.json --runs 3 --json a.json`.
3. Write one variant at a time as a full SKILL.md copy ([`variants/desc-b.md`](examples/advanced-skills/evals/variants/desc-b.md) changes only `description`), then A/B it:
   ```bash
   python3 run_evals.py cases.json --runs 3 --skill-md variants/desc-b.md --json b.json
   ```
   The harness copies the plugin to a temp dir, swaps in the SKILL.md and runs the same cases.
4. Keep the variant only if recall rises and false-trigger doesn't. In the plugin-eval format, re-run after each description change and watch the `tool_used: Skill` indicator together with the `min: 0, max: 0` negatives.

Description rules that move these numbers:
- Third person, what it does first, then "Use when …" with the verbs users actually type ("change X to Y everywhere", "update all the imports"), then an explicit "Not for …" clause naming your negatives.
- Combined `description` and `when_to_use` is cut to 1,536 characters in the Claude Code listing. When there are many skills, descriptions of the least-used skills get dropped first to fit a budget of 1% of the context window. Put the trigger words in the first sentence. `/doctor` shows the listing cost and `/skill-doctor` shows per-skill cost and usage.
- If the skill should never auto-fire, don't tune it. Set `disable-model-invocation: true`. To scope it to a file type, use `paths:` globs.

**Output.** A results pair you can diff. Example shape (illustrative numbers): `A: recall 0.60 false-trigger 0.25` → `B: recall 0.93 false-trigger 0.00`. Variant B's "Not for single-file edits, typo fixes, or read-only questions about usages" is what removes the negatives.

**Failure modes.**
- *Overfitting to the set.* Hold back 2–3 prompts that you never tune against, and check them last.
- *Malformed YAML.* The skill still loads with empty metadata, so `/name` works but auto-trigger never does. Run `claude plugin validate .claude/skills` (v2.1.233+) or `--debug`.
- *Name collisions.* A built-in or another plugin's skill with an overlapping description can win. Make the negatives cover that skill's territory.
- *Single-run noise.* One run per case is anecdote. Decide at `--runs 3` or more.

Source: https://code.claude.com/docs/en/skills#troubleshooting · https://code.claude.com/docs/en/skills#frontmatter-reference · https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#writing-effective-descriptions

---

## Recipe 4: Package as a plugin and publish a marketplace

**Problem.** Copying a skill folder into everyone's `~/.claude/skills/` has two problems: you can't push updates, and the bundled scripts drift between copies.

**Setup.** `marketplace/.claude-plugin/marketplace.json` requires `name`, `owner` and `plugins[]`, and each entry requires `name` and `source`:

```json
{
  "name": "your-org-tools",
  "owner": { "name": "Developer Productivity" },
  "plugins": [
    { "name": "bulk-edit-tools", "source": "./plugins/bulk-edit-tools",
      "description": "Safe multi-file renames with a validated plan, dry-run diff and backups" }
  ]
}
```

`plugins/bulk-edit-tools/.claude-plugin/plugin.json`: only `name` is required. Set `version` and bump it with every release, because installed copies stay pinned to it.

```json
{ "name": "bulk-edit-tools", "displayName": "Bulk Edit Tools", "version": "1.0.0",
  "description": "Plan-validate-apply workflow for multi-file renames and replacements",
  "author": { "name": "Your Team" }, "license": "MIT" }
```

The loop:

```bash
cd examples/advanced-skills
claude plugin validate ./marketplace/plugins/bulk-edit-tools   # add --strict in CI
claude plugin validate ./marketplace
claude plugin marketplace add ./marketplace
claude plugin install bulk-edit-tools@your-org-tools
claude plugin details bulk-edit-tools        # Component inventory should list safe-bulk-edit
# push ./marketplace to git, then teammates run:
claude plugin marketplace add your-org/claude-plugins
```

**Output.** `✔ Validation passed` for both. Install prints `✔ Successfully installed plugin: bulk-edit-tools@your-org-tools (scope: user)`. In a session the skill is namespaced as `bulk-edit-tools:safe-bulk-edit`.

**Failure modes.**
- *`Source path does not exist`* means a relative `source` was written from the wrong directory. Paths resolve from the marketplace root, the directory that contains `.claude-plugin/`, and can't use `..`.
- *`Plugin "<x>" not found in marketplace`* means the entry `name` and the `plugin.json` `name` differ. Keep them identical.
- *Reserved names.* Plugin names that start with `claude-` or `anthropic-` fail validation. The exact official marketplace names, such as `claude-plugins-official`, pass validation but are refused when you add the marketplace.
- *Wrong locations.* Only `plugin.json` goes inside `.claude-plugin/`. `skills/`, `hooks/` and everything else sit at the plugin root. A root `CLAUDE.md` isn't loaded, so put that guidance in a skill.
- *Local edits.* With a local path marketplace, edits apply on `/reload-plugins` without a version bump. Remote users only receive a change after you bump `version`.

Source: https://code.claude.com/docs/en/plugin-marketplaces · https://code.claude.com/docs/en/plugins-reference

---

## Recipe 5: Org rollout with policy and a CI gate

**Problem.** You want every developer, CI runner and Cowork user on the same reviewed version, and no unvetted marketplaces.

**Setup.**
1. **Claude Code fleet.** Deliver [`org/managed-settings.json`](examples/advanced-skills/org/managed-settings.json) via server-managed settings (claude.ai → Organization settings → Claude Code → Managed settings; Owner role), MDM, or a `managed-settings.json` file:
   ```json
   { "strictKnownMarketplaces": [
       { "source": "github", "repo": "anthropics/claude-plugins-official" },
       { "source": "github", "repo": "your-org/*" }, { "source": "skills-dir" } ],
     "extraKnownMarketplaces": { "your-org-tools": {
       "source": { "source": "github", "repo": "your-org/claude-plugins" }, "autoUpdate": true } },
     "enabledPlugins": { "bulk-edit-tools@your-org-tools": true } }
   ```
   Add `disableSideloadFlags` to block `--plugin-dir` and `--plugin-url`, and `strictPluginOnlyCustomization` to block skills that don't come from plugins.
2. **claude.ai chat and Cowork.** Sync the same repo in Organization settings → Plugins & skills and set availability (for example **Required**). Organization sync rejects plugins with a top-level `bin/` directory, which is why scripts here live inside the skill.
3. **CI and containers.** Install into a seed at build time: `CLAUDE_CODE_PLUGIN_CACHE_DIR=/opt/claude-seed claude plugin install …`, then set `CLAUDE_CODE_PLUGIN_SEED_DIR=/opt/claude-seed` at runtime. Set `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1` so `-p` runs wait for the install.
4. **Release gate** on the marketplace repo:
   ```bash
   claude plugin validate ./plugins/bulk-edit-tools --strict
   claude plugin eval ./plugins/bulk-edit-tools --trust-plugin --scaffold \
     --allow-tools Write Edit "Bash(python3 *)" "Bash(git *)" \
     --model claude-sonnet-5-5 --threshold 0.8 --no-publish --max-cost-usd 20 --json results.json
   ```
   Exit 0 means the suite passed, 1 means a case was below threshold or a load or run error occurred, 2 means a partial run (cost ceiling or auth).

**Output.** On the next session start, `/plugin` on any machine lists `your-org-tools` and the enabled plugin. If a user disables it at their own scope, it still loads. In CI, `claude -p --output-format stream-json --verbose` emits an `init` event whose `plugins` array shows the path, under the seed, of each plugin that loaded.

**Failure modes.**
- *Only one managed source applies.* Server-managed beats MDM, which beats the file. One unrelated server-managed key shadows plugin keys in your MDM file unless `managedSourcesBehavior: "merge"` is set.
- *Allowlist set without `{ "source": "skills-dir" }`.* Users' skills-directory plugins stop loading. Plain `SKILL.md` folders keep working.
- *Private repo.* Each machine clones with its own git credentials. In GitHub Actions, export `GH_TOKEN` and run `gh auth setup-git`, or use a seed.
- *Duplicate copies.* A developer who gets the plugin both from claude.ai sync and from managed settings loads the managed copy, and the synced copy shows as not loaded.

Source: https://code.claude.com/docs/en/plugins/org · https://claude.com/docs/plugins/org-rollout · https://code.claude.com/docs/en/plugin-evals#run-evals-in-ci
