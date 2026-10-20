# Claude for developers

For engineers who already have Claude Code installed and want repeatable workflows for the work around the code: onboarding, review, incidents, migrations, tests, and checking UI changes in a real browser. This is not a Claude Code tutorial (see [../docs/01-code.md](../docs/01-code.md)) and it doesn't repeat the [Advanced](../advanced/) recipes. It links to them. Basics such as Projects, connectors and Chrome setup are in [_shared-setup.md](_shared-setup.md).

## 1. Quick wins

### Onboard to an unfamiliar codebase in one session

Setup: run `claude` in the repo root, then `/init` to generate a starter `CLAUDE.md`. Edit it down to the commands and gotchas Claude can't guess ([../templates/CLAUDE.md](../templates/CLAUDE.md)). For a large repo, read [context engineering, Recipe 1](../advanced/context-engineering.md#recipe-1-instruction-tree-for-a-large-repo-with-progressive-disclosure) before the tree gets out of hand.

```text
Use a subagent to map this repo. Then give me:
1. A 10-line architecture summary: entry points, main modules, data stores, external services.
2. How a request flows from the edge to the database for the most-used endpoint. Cite file:line.
3. A glossary of the 15 project-specific terms I'll hit first.
4. How to run, test and lint locally, taken only from scripts and CI config. Mark guesses as guesses.
5. Five places where the code contradicts the README.
Don't edit any files.
```

Output: a short Markdown brief with `file:line` citations, e.g. `POST /orders -> api/routes/orders.ts:42 -> services/order.ts:118 -> db/orders.sql`, plus a "README drift" list you can turn into a docs PR.

Source: https://code.claude.com/docs/en/common-workflows · https://code.claude.com/docs/en/commands · https://code.claude.com/docs/en/sub-agents

### Review a PR before a human does

Setup: none for the local review. `/code-review` (alias `/review`) is a bundled skill and works on any plan. It takes an effort level (`low` to `max`, or `ultra` for the cloud review), `--comment` to post inline comments on the PR, and `--fix` to apply findings. For security-only checks, use `/security-review`, which needs an `origin` remote.

```text
/code-review high 1234
```

Then follow up:

```text
For each finding: is it reachable from a real caller? Show the call path. Drop anything you can't
show a path for. Then list what the PR doesn't test that it should, as test names, not prose.
```

Output: a ranked list of correctness findings with file and line, followed by a short list of missing tests such as `test_refund_rejects_amount_over_order_total`. Team and Enterprise orgs can turn on managed Code Review, which posts findings automatically on GitHub PRs. To run review in your own CI, see [unattended pipelines, Recipe 3](../advanced/unattended-pipelines.md#recipe-3-pr-review-in-github-actions-with-guard-rails).

Source: https://code.claude.com/docs/en/commands · https://code.claude.com/docs/en/code-review

### Draft an incident write-up from raw material

Setup: export the incident channel, the alert timeline and the relevant log excerpt into a folder, or connect Sentry and Slack (Slack as a directory connector: unverified). See [_shared-setup.md#connectors](_shared-setup.md#connectors). Redact customer data first ([_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist)).

```text
Read incident/ (Slack export, alert timeline, logs) and the diff of commit <sha>.
Write a blameless post-incident review with these sections: Summary (3 lines), Impact (users,
duration, data), Timeline in UTC (every entry cites its source file), Root cause, Contributing
factors, What went well, Action items (owner: TBD, each one testable).
If two sources disagree on a time or a fact, list both under "Open questions". Don't pick one.
```

Output: a 1–2 page doc with a timeline like `14:02 UTC  p99 latency alert fires  [alerts.csv:17]`. An "Open questions" section catches contradictions instead of hiding them.

Source: https://support.claude.com/en/articles/11724452-browsing-and-connecting-to-tools-from-the-directory · https://code.claude.com/docs/en/common-workflows

### Plan a migration before touching code

Setup: start in plan mode with `claude --permission-mode plan`, press `Shift+Tab` until the status bar shows `⏸ plan mode on`, or type `/plan <task>`. Claude reads the code and proposes a plan, but makes no edits until you approve.

```text
/plan Migrate from <lib v1> to <lib v2>.
Inventory every call site (count them, grouped by pattern). Note which patterns have no direct v2
equivalent. Propose an order of independent, separately-mergeable steps, each with the tests
that prove it. Name the riskiest step and a rollback for it. Estimate files touched per step.
```

Output: a plan file listing call-site counts per pattern, about 4–8 ordered steps and a risk note. Once it's approved, `/batch <instruction>` can split mechanical work into 5–30 units and run each in its own worktree. For hand-run parallel worktrees, see [multi-agent orchestration, Recipe 4](../advanced/multi-agent-orchestration.md#recipe-4-parallel-worktree-sessions-then-merge).

Source: https://code.claude.com/docs/en/common-workflows · https://code.claude.com/docs/en/commands · https://claude.com/blog/ai-code-migration

### Generate tests that match house style

Setup: make sure `CLAUDE.md` names the test command. Point Claude at one good existing test file as the pattern.

```text
Find functions in src/billing/ with no test coverage. For the top 5 by risk, write tests in the
style of tests/billing/test_invoice.py: same fixtures, same assertion style. Cover boundary values
and error paths, not just the happy path. Run them. If a test fails, tell me whether the test or
the code is wrong before changing either.
```

Output: new test files plus a short table of `function | cases added | pass/fail`. Any failure comes with a verdict on whether the test or the code is wrong. To stop Claude from finishing while tests are red, add the Stop hook from [hooks & guardrails, Recipe 5](../advanced/hooks-and-guardrails.md#recipe-5-dont-let-claude-stop-until-the-tests-pass).

Source: https://code.claude.com/docs/en/common-workflows · https://code.claude.com/docs/en/hooks

## 2. Deeper setups

### (a) A claude.ai Project for design reviews and RFCs

Use this for work that isn't in the terminal, such as reading RFCs, comparing designs and writing ADRs. Create a Project ([_shared-setup.md#projects](_shared-setup.md#projects)). Add the repo through the GitHub integration (knowledge "+" → GitHub, then choose files and folders, and use **Sync** to refresh). Add your ADR template and two past ADRs. Paste the instructions from section 6.

```text
Here is RFC-212 (attached). Against the synced repo and our ADRs: list the assumptions it makes about
current code, mark each true/false with a file reference, then give the three strongest objections
a senior reviewer would raise. End with a draft ADR in our template.
```

Output: an assumptions table (`assumption | true/false | evidence`), three objections, and a draft ADR.

Source: https://support.claude.com/en/articles/10167454-using-the-github-integration

### (b) A custom `incident-writeup` skill

Turn the quick win above into a project skill so everyone's write-ups share the same format. Save this as `.claude/skills/incident-writeup/SKILL.md`. Template: [../templates/SKILL.md](../templates/SKILL.md). Basics are in [_shared-setup.md#skills](_shared-setup.md#skills).

```markdown
---
name: incident-writeup
description: Draft a blameless post-incident review from a folder of Slack exports, alerts and logs. Use when the user asks for a postmortem, incident review or PIR.
argument-hint: "[incident-folder]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
---

Draft a post-incident review from $ARGUMENTS.

1. Read every file in the folder. Build a UTC timeline; each entry cites file:line.
2. Sections: Summary, Impact, Timeline, Root cause, Contributing factors, What went well, Action items.
3. Blameless: describe systems and decisions, never name individuals as causes.
4. Conflicting sources go under "Open questions". Never resolve them silently.
5. Action items must be testable ("add alert on X > Y"), owner "TBD".
6. Write to $ARGUMENTS/review.md. Do not post anywhere.
```

Run it with `/incident-writeup incidents/2026-10-14-checkout`. To add bundled scripts, validators and evals, see [advanced skills](../advanced/advanced-skills.md).

Source: https://code.claude.com/docs/en/skills

### (c) Claude Code + Claude in Chrome verify loop

The loop: make a change, open the page, check the console, network and visuals, then iterate. Setup: install the Claude in Chrome extension (1.0.36+), sign in with `/login` (API-key auth keeps Chrome off), and start `claude --chrome` or turn on **Enabled by default** under `/chrome`. More in [_shared-setup.md#claude-in-chrome](_shared-setup.md#claude-in-chrome). Put the verification rules in `CLAUDE.md`. The full block, a Desktop `launch.json` alternative and the failure modes are in [browser automation, Recipe 1](../advanced/browser-and-computer-automation.md#1-build--test--verify-loop-with-console-and-network-evidence).

```text
Fix the date picker so it respects the user's locale. Then open localhost:3000/settings in a new
tab, read console messages matching "error|warn|Uncaught", read network requests to /api/,
and screenshot the picker in en-US and de-DE. Done = no new console errors, no 4xx/5xx, both
screenshots show the right format. Max 3 iterations, then stop and show me the failing evidence.
```

Output: each iteration ends with a line like `/settings | 0 errors | GET /api/prefs 200 (90ms)` plus screenshots. Without a browser, `/verify` builds and runs the app to check a change, and `/run-skill-generator` records how your project launches. To file a bug with a GIF repro, see [Recipe 2](../advanced/browser-and-computer-automation.md#2-gif-repro-for-a-bug-report).

Source: https://code.claude.com/docs/en/chrome · https://code.claude.com/docs/en/skills · https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome

## 3. Prompts that work in this field

```text
Before changing anything, tell me how you'll verify this works. Then make the change and run that check.
```
Why: setting the check up front stops Claude from calling something done before anything has run.

```text
Use a subagent to investigate how token refresh works. Return only file:line references and a 10-line summary.
```
Why: the file reads happen in the subagent's context, so your main session stays clean for the actual change.

```text
Trace <symptom> to its root cause. List three hypotheses, the evidence that would rule each out, then test them in order.
```
Why: listing hypotheses that can be ruled out stops Claude from patching the first plausible cause.

```text
Refactor <module> in steps that each keep the tests green. Run the tests after every step and stop on the first red.
```
Why: small verified steps keep each diff reviewable and easy to roll back.

```text
Review my diff as a hostile reviewer. Only report issues you can show with a concrete input or call path.
```
Why: asking for a concrete input or call path cuts out style nits and speculative findings.

```text
Write the PR description: what changed, why, how it was tested (actual commands run), risk, rollback.
```
Why: asking for the commands actually run stops vague "tested locally" claims.

```text
List every place this change could break a caller outside this package. Search, don't guess.
```
Why: "search, don't guess" makes Claude grep for callers instead of reasoning from names.

```text
Explain this stack trace in two lines, then point to the single most likely frame in our code and why.
```
Why: forcing a single frame gets you a commitment you can check quickly.

```text
Summarize what changed in this session as a CLAUDE.md diff: only rules a new teammate would need next time.
```
Why: it keeps the project memory short and current ([_shared-setup.md#memory](_shared-setup.md#memory)).

```text
Write tests that fail on the current code and pass after the fix. Show me the failing run first.
```
Why: a test that's red first proves it checks the bug rather than restating the code.

## 4. Guardrails

- **Malicious code.** Claude declines malware, credential theft and exploits against systems you don't own, under Anthropic's Usage Policy. Authorized security work is fine. Say what it is ("our staging app, we own it, pentest ticket SEC-88"), and use `/security-review` on your own branch. See [security & prompt injection](../advanced/security-and-prompt-injection.md).
- **Secrets and production access.** Don't paste live credentials. Deny reads of `.env` and keys, and block secret commits with a hook ([hooks & guardrails, Recipes 1 and 4](../advanced/hooks-and-guardrails.md)). Claude in Chrome won't upload files named like credentials (`.env`, `.pem`, `.key`, `.ssh/`).
- **Login pages and CAPTCHAs.** Claude in Chrome pauses and asks you to handle these. Do them yourself. Don't script around them.
- **"No findings" is not a security sign-off.** The Code Review docs say this explicitly. Keep human review and CI gates.
- **Hallucinated APIs.** Claude can invent a method that "should" exist. Require a passing run or a cited file:line, and say "search, don't guess".
- **Regulated data.** HIPAA-enabled Enterprise orgs have Claude in Chrome off by default, and managed Code Review isn't available with Zero Data Retention or HIPAA. Check [_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist) before using either on regulated code.
- **Untrusted content.** READMEs, issues and web pages can carry prompt injection. Don't let a session that reads them also hold write tokens. See [browser automation, Recipe 5](../advanced/browser-and-computer-automation.md#5-prompt-injection-defenses-for-a-browsing-agent).

Source: https://www.anthropic.com/legal/aup · https://code.claude.com/docs/en/code-review · https://code.claude.com/docs/en/chrome

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| GitHub integration (claude.ai) | Repo context in Projects | Project knowledge "+" → GitHub. Private repos need GitHub App access | https://support.claude.com/en/articles/10167454-using-the-github-integration |
| Claude GitHub App | `@claude` in PRs, Actions, Code Review | `/install-github-app` (github.com only) | https://code.claude.com/docs/en/github-actions |
| Code Review (managed) | Automatic PR review with inline findings | Team/Enterprise. An Owner enables it | https://code.claude.com/docs/en/code-review |
| Sentry connector | Pull errors into incident write-ups | From the connectors directory | https://support.claude.com/en/articles/11724452-browsing-and-connecting-to-tools-from-the-directory |
| Linear / Atlassian connectors | Turn findings and action items into tickets | From the connectors directory. Jira named specifically (unverified) | https://support.claude.com/en/articles/11724452-browsing-and-connecting-to-tools-from-the-directory |
| Claude in Chrome | Verify loop, console and network reads, GIF repros | Extension 1.0.36+, `claude --chrome` | https://code.claude.com/docs/en/chrome |
| `/code-review`, `/security-review`, `/simplify` | Local review: bugs, security, cleanup | Built in | https://code.claude.com/docs/en/commands |
| `/verify`, `/run`, `/run-skill-generator` | Check changes against the running app | Run the generator once per project | https://code.claude.com/docs/en/skills |
| `/batch` | Large mechanical migrations in parallel worktrees | Needs a git repo | https://code.claude.com/docs/en/commands |
| Custom subagents | Read-only reviewer, explorer | `.claude/agents/<name>.md`. Roster in [multi-agent, Recipe 1](../advanced/multi-agent-orchestration.md#recipe-1-a-subagent-roster-with-hard-tool-boundaries) | https://code.claude.com/docs/en/sub-agents |

## 6. Sample Project instructions

```text
You are a senior engineer on <team>, working in <languages/frameworks>. Our repo is synced as
project knowledge. ADR template and past ADRs are attached.

How to answer:
- Cite file:line for every claim about our code. If you can't find it, say "not found in synced
  files" instead of guessing. Remember the sync may be stale.
- Separate facts (from code/docs) from opinions (your judgement). Label opinions.
- Prefer the smallest change that solves the problem. Name the trade-off you're accepting.
- For any proposed change: how it's tested, how it's rolled back, who/what calls it.
- Security: flag auth, input validation, secrets and data-exposure risks explicitly.
- Write for engineers: short sentences, code over prose, no marketing tone.
- For incident or postmortem material: blameless, UTC timestamps, unresolved conflicts listed
  as open questions.

Never: invent APIs, flags or config keys; paste credentials back; claim something was run when
it was only reasoned about.
```

Last checked: 2026-10-20
