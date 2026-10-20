# Hooks & guardrails: permissions, sandbox, hooks that enforce

Runnable files are in [`examples/hooks-and-guardrails/`](examples/hooks-and-guardrails/):

```
examples/hooks-and-guardrails/
  settings.json               # permissions + sandbox + all four hooks, drop into .claude/settings.json
  protect-paths.py            # PreToolUse  Edit|Write|NotebookEdit -> deny with "do this instead"
  lint-on-edit.sh             # PostToolUse Edit|Write -> format, lint, feed remaining errors back
  secret-scan.py              # PreToolUse  Bash, if "Bash(git commit *)" -> exit 2 on credentials
  require-tests-on-stop.sh    # Stop -> run tests on a dirty tree, block the stop until they pass
```

Install: `mkdir -p .claude/hooks && cp examples/hooks-and-guardrails/*.{py,sh} .claude/hooks/ && chmod +x .claude/hooks/*`, then merge `settings.json` into `.claude/settings.json`. Check what loaded with `/hooks`, which is a read-only browser that labels each hook with its source.

There are three layers, and each one stops something different:

| Layer | Enforced by | Covers | Doesn't cover |
|---|---|---|---|
| Permission rules (`permissions.deny/ask/allow`) | Claude Code, before the tool runs | Every tool, including Read/Edit/WebFetch/MCP | Bash commands written in a form the pattern doesn't match (`git -C . push`) |
| Sandbox (`sandbox.*`) | The OS (Seatbelt on macOS, bubblewrap on Linux/WSL2) | Bash commands and every child process: file writes, reads, network | Built-in file tools, WebFetch, MCP servers, hooks. All of these run outside it |
| Hooks | Your script | Anything you can express in code: path logic, scanning content, running tests | Nothing on its own. A PreToolUse `allow` can't override a deny or ask rule |

Mechanics you'll rely on below:

- **Exit codes.** `0` means stdout is parsed as JSON if it's a single object. `2` is a blocking error and its stderr becomes the reason. Any other code is a non-blocking error: the action goes ahead and you see a `hook error` notice.
- **Stdin fields.** Every event gets `session_id`, `cwd`, `permission_mode` and `hook_event_name`. Tool events add `tool_name`, `tool_input` and `tool_use_id`, and PostToolUse also adds `tool_response`. File tools always get an absolute `tool_input.file_path`, because `~` and relative paths are expanded before your hook sees them.
- **Matchers.** `Edit|Write` is an exact-name list. Anything containing other characters is treated as an unanchored JS regex (`mcp__github__.*`). The `if` field takes one permission rule (`"Bash(git commit *)"`) and only applies to tool events. It's best-effort, and when Claude Code can't tell which command will run, the hook runs anyway.
- **`${CLAUDE_PROJECT_DIR}`** is exported to hooks and stays fixed even inside a worktree. Use it for script paths.

---

## Recipe 1: A deny-first baseline with permissions and the sandbox

**Problem.** You want to run Claude in `acceptEdits` (or auto) without babysitting it, but it must not read `.env` or `~/.aws`, force-push, `curl` arbitrary hosts, or touch applied migrations. Even if a Bash pattern misses, the OS should still stop exfiltration.

**Setup.** This is the relevant part of [`settings.json`](examples/hooks-and-guardrails/settings.json):

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": ["Bash(npm run *)", "Bash(git diff *)", "Bash(git commit *)"],
    "ask":   ["Bash(git push *)", "Bash(npm publish *)"],
    "deny":  ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)", "Read(~/.ssh/**)", "Read(~/.aws/**)",
              "Edit(/db/migrations/**)", "Edit(/.github/workflows/**)",
              "Bash(git push --force *)", "Bash(git reset --hard *)", "Bash(rm -rf *)", "Bash(curl *)", "Bash(wget *)"],
    "disableBypassPermissionsMode": "disable"
  },
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "filesystem": { "denyRead": ["~/.ssh", "~/.aws", "~/.config/gcloud"], "allowWrite": ["~/.cache"] },
    "network": { "allowedDomains": ["registry.npmjs.org", "pypi.org", "files.pythonhosted.org", "github.com"] }
  }
}
```

Rules that decide whether this works:

- Evaluation order is **deny → ask → allow**, and the first match wins regardless of how specific the rule is. `Bash(aws *)` in deny beats `Bash(aws s3 ls)` in allow, so you can't carve an exception out of a deny.
- Put the `*` after the subcommand. `Bash(git log *)` allows only `git log`, while `Bash(git *)` allows every git subcommand, including `git -c core.fsmonitor=<script>`.
- Path anchors differ by rule type. In Read/Edit rules, `/x` is relative to the settings file's project, `//x` is an absolute filesystem path, `~/x` is under home, and `x` or `./x` is relative to cwd. A single leading slash is **not** absolute. Sandbox paths use normal conventions (`/tmp/build`, `~/.kube`).
- Rules for `Write(...)`, `NotebookEdit(...)` or `Glob(...)` paths are accepted but never consulted, and Claude Code warns at startup. Use `Edit(...)` and `Read(...)`.
- `.claudeignore` does nothing. Move its entries into `Read` deny rules.
- `allowUnsandboxedCommands: false` makes Claude Code ignore the `dangerouslyDisableSandbox` retry, so a failing command can't escape by asking. Add `"failIfUnavailable": true` under `sandbox` if a missing bubblewrap should stop Claude Code from starting rather than silently running unsandboxed.
- Make it org-wide with managed settings (`managed-settings.json`). There, `disableBypassPermissionsMode`, `allowManagedPermissionRulesOnly` and `allowManagedHooksOnly` can't be overridden by a repo.

**Output.** `cat .env` and the Read tool on `.env` are both refused. `git push origin main` prompts. `curl https://evil.example` is denied by rule, and `python3 -c "import urllib.request; urllib.request.urlopen('https://evil.example')"` (which no Bash rule matches) is blocked by the sandbox proxy because the host isn't in `allowedDomains`. Claude sees the denied host named in the command's result. Sandboxed commands run without prompts, since `autoAllowBashIfSandboxed` defaults to `true`.

**Failure modes.**
- Bash patterns are string matches. `git -C . push`, `sh -c 'curl …'`, `/usr/bin/curl` and `URL=…; curl $URL` all slip past `Bash(curl *)` / `Bash(git push *)`. The sandbox is what actually stops network egress, so treat Bash deny rules as speed bumps.
- `denyRead` in the sandbox doesn't stop the **Read tool**, and `allowedDomains` doesn't limit **WebFetch**. You need both the permission rule and the sandbox entry.
- MCP servers and hooks run outside the sandbox with your full user permissions. A malicious `.mcp.json` server isn't contained by it. Project `.mcp.json` servers need explicit approval, so read them before approving.
- The sandbox doesn't run on native Windows (use WSL2). Without `failIfUnavailable` it degrades silently.
- `allowWrite` and the other array keys **merge** across scopes, so a developer's local settings can widen an org policy unless managed settings lock it.

Source: https://code.claude.com/docs/en/permissions, https://code.claude.com/docs/en/sandboxing

---

## Recipe 2: Protected paths that tell Claude what to do instead

**Problem.** `Edit(/db/migrations/**)` in deny stops the edit, but Claude only learns that permission was denied, so it often tries `sed -i` next or gives up. You want the refusal to carry a team-specific instruction ("create a new migration"), and you want the rules in a file that non-experts can edit.

**Setup.** [`protect-paths.py`](examples/hooks-and-guardrails/protect-paths.py) handles PreToolUse with matcher `Edit|Write|NotebookEdit`. It reads `tool_input.file_path` (or `notebook_path`), normalises `\` to `/`, makes the path relative to `$CLAUDE_PROJECT_DIR`, and matches it against `.claude/protected-paths.txt`:

```
# glob                 what to do instead
db/migrations/*        Never edit an applied migration. Create a new file with `make migration name=...`.
.github/workflows/*    CI config is owned by platform. Write the proposed diff into PLATFORM_REQUEST.md.
*.lock                 Lockfiles change only via the package manager.
```

On a hit it prints this and exits 0:

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
  "permissionDecisionReason": "db/migrations/001.sql is protected (rule: db/migrations/*). Never edit an applied migration. Create a new migration file instead."}}
```

Close the Bash bypass at the OS level by adding the same paths to `sandbox.filesystem.denyWrite` (for example `"denyWrite": ["./db/migrations"]`). In project settings a relative sandbox path resolves against the project root. In `~/.claude/settings.json` it would resolve against `~/.claude`.

Test it without Claude:

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/db/migrations/001.sql"}}' \
  | CLAUDE_PROJECT_DIR=$PWD python3 .claude/hooks/protect-paths.py
```

**Output.** Claude gets the reason as the tool result, writes `db/migrations/002_add_index.sql` instead, and says so. Other paths produce no output and the normal permission flow continues.

**Failure modes.**
- Keep the `Edit(...)` deny rule as well. If the hook fails (bad interpreter path, timeout), the action **goes ahead**: on PreToolUse a crashed or timed-out hook doesn't block unless you set `"onFailure": "block"` on it (Claude Code v2.1.295+). Watch for the `hook error` notice the first time it runs.
- Matching with `^/src/` against an absolute path never matches, and Windows paths arrive with backslashes. The script normalises both. Copy that if you write your own.
- `fnmatch` `*` crosses `/`, so `vendor/*` covers nested files. Narrow the globs if you need to.
- A hook `allow` doesn't skip deny/ask rules. Don't try to use this hook to *grant* edits.

Source: https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/permissions

---

## Recipe 3: Auto-format and lint every edit, feed failures back

**Problem.** Claude's edits pass review but fail CI on formatting and lint. Running the linter at the end of a long task produces 40 errors across 12 files, and fixing them all at once is where regressions creep in.

**Setup.** [`lint-on-edit.sh`](examples/hooks-and-guardrails/lint-on-edit.sh) handles PostToolUse with matcher `Edit|Write` and `timeout: 60`. Based on the file extension it runs `ruff format` + `ruff check --fix`, the repo-local `prettier --write` + `eslint --fix`, `gofmt -w` + `go vet`, or `shellcheck`. Tools that aren't installed are skipped. If anything is still failing after auto-fix, it prints:

```json
{"decision": "block", "reason": "Lint still failing after auto-fix for src/api.py:\nsrc/api.py:14:5: F841 Local variable `resp` is assigned to but never used\nFix these before moving on."}
```

For PostToolUse, `decision: "block"` puts `reason` next to the tool result. The edit has already happened and Claude still sees the original output. The script caps the output at 40 lines because Claude needs the first errors, not the full log.

**Output.** Each edit lands formatted. Lint errors show up in the same turn as the edit that caused them, and Claude fixes them before it touches the next file. A clean edit produces no output and no extra tokens.

**Failure modes.**
- PostToolUse fires only for `Edit|Write`. When Claude rewrites a file through Bash (`sed -i`, codegen), the hook doesn't run. Either add a `FileChanged` hook, or use matcher `*` and discover changes with `git status --porcelain`.
- The formatter rewrites the file after Claude has seen its own version, so the next `Edit`'s `old_string` can stop matching and Claude has to re-read. That costs a turn now and then. Exclude formatters that make big rewrites (import sorting across the whole file) if it happens often.
- Slow linters (type-checking the whole project on every edit) cost a lot over a 200-edit session. Lint the single file here and leave project-wide checks to Recipe 5.
- `npx eslint` without a local install may download packages. The script only calls `node_modules/.bin/*`.

Source: https://code.claude.com/docs/en/hooks (PostToolUse input and decision control), https://code.claude.com/docs/en/hooks-guide

---

## Recipe 4: Block commits that contain secrets

**Problem.** Claude creates a `.env.example` with a real key pasted in, or hard-codes a token in a test fixture, and commits it. Your git pre-commit hook may not exist in every clone, and when it does fire, the failure comes back as noise Claude has to interpret.

**Setup.** [`secret-scan.py`](examples/hooks-and-guardrails/secret-scan.py) is registered under PreToolUse `Bash` with `"if": "Bash(git commit *)"`. It scans the **added** lines of `git diff --cached -U0`, plus the unstaged tracked diff when the command uses `-a`/`--all`, for AWS key IDs, private-key blocks, GitHub/Slack/Stripe/Google/Anthropic-style tokens, JWTs and `password = "…"` style assignments. Lock files, minified JS and SVGs are skipped. Findings are redacted (`AKIAAB...OP`) so the secret isn't copied into the transcript. On a hit it exits **2**:

```
Commit blocked: possible secrets in the change.
  cfg.py:1  AWS access key id  (AKIAAB...OP)
Move the value to an env var or secret manager, unstage it (git restore --staged <file>), and commit again.
If it is a test fixture, add the comment 'secret-scan: allow' on that line and tell the user you did.
```

For a policy hook, add `"onFailure": "block"` (v2.1.295+) so a crashed or timed-out scan stops the commit too.

**Output.** The commit never runs. Claude reads the stderr as the reason, moves the value to `os.environ[...]`, unstages the file, and commits again. The allow marker leaves an audit trail for fixtures.

**Failure modes.**
- `if` is best-effort, and commits made indirectly (`npm run release`, a Makefile target) may not match it. The script re-checks for `git` + `commit` in the command, and Claude Code runs the hook whenever it can't determine the command. Commits from inside a script still go unscanned, so keep a real `pre-commit`/gitleaks hook for humans and CI.
- Regexes produce false positives on high-entropy test data. That's what the allow marker is for. Review where it gets used.
- This only guards Claude's commits. A secret that's already in the working tree can still reach Claude's context through a Read. Pair it with the `Read(./.env*)` deny rules from Recipe 1.
- Use one signalling style per hook: exit 2 + stderr, or exit 0 + JSON. If you mix them, exit 2 still blocks and Claude Code reads the JSON fields as well, which makes the result hard to reason about.

Source: https://code.claude.com/docs/en/hooks (exit codes, `if`, `onFailure`)

---

## Recipe 5: Don't let Claude stop until the tests pass

**Problem.** "Done! All changes are complete." Then the tests fail. Telling Claude to run tests in the prompt works most of the time, and you want it to work every time a turn ends with source changes.

**Setup.** [`require-tests-on-stop.sh`](examples/hooks-and-guardrails/require-tests-on-stop.sh) is a `Stop` hook with `timeout: 600`:

1. It exits 0 at once if `stop_hook_active` is `true`, which means Claude is already continuing because of a Stop hook.
2. It exits 0 if `git status --porcelain` shows no non-doc changes.
3. It hashes the tree state (`git diff HEAD` + untracked file list). If that hash already passed, it exits 0.
4. It runs `$CLAUDE_STOP_TEST_CMD`, or auto-detects `npm test` / `pytest -q -x` / `go test ./...` / `cargo test`.
5. On failure it prints `{"decision":"block","reason":"Tests fail (...). Fix the code, not the tests, then finish. Tail: ..."}` with the last 60 lines.

```bash
export CLAUDE_STOP_TEST_CMD="npm run test:unit -- --silent"   # scope it; full e2e on every stop is too slow
```

**Output.** Claude's turn can't end on a red suite. It reads the failure tail, fixes the code, and tries to stop again. The second stop arrives with `stop_hook_active: true` and is let through, so you get at most one forced continuation per stop attempt. If you'd rather it keep going until green, remove step 1 and rely on the cap below.

**Failure modes.**
- Infinite loops. Claude Code caps Stop-hook continuations at **8 in a row** (the count resets whenever Claude calls a tool). `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` raises the cap. Flaky tests will burn all 8, so quarantine them.
- Test gaming. The reason text says "fix the code, not the tests". To enforce that, add `Edit(/tests/**)` to `ask` for long autonomous runs.
- `decision: "block"` shows up as a hook error in the transcript. For a softer nudge, use `hookSpecificOutput.additionalContext` in the Stop output: it gets the same loop protections and is labelled `Stop hook feedback`.
- The Stop hook doesn't fire on a user interrupt, and API errors fire `StopFailure` instead.
- For a one-off session the built-in `/goal` command is a session-scoped prompt-based Stop hook, so you don't need this script.

Source: https://code.claude.com/docs/en/hooks (Stop input and decision control)

---

## Rollout and debugging

- **Test hooks offline first.** Every script here reads JSON on stdin, so pipe in a fixture: `echo '{"stop_hook_active":false}' | CLAUDE_STOP_TEST_CMD='exit 1' ./require-tests-on-stop.sh`. Do this in CI too.
- **See what loaded.** `/hooks` lists hooks by source. `claude --debug` logs hook execution. A mistyped script path shows a `hook error` notice on first use and then does nothing.
- **Kill switch.** `"disableAllHooks": true` in settings, or `claude --settings '{"disableAllHooks": true}'` for one run. It can't disable managed hooks unless it's set in managed settings.
- **Merge semantics.** Hooks from user, project, local and plugins all run. They add up and don't replace each other. When PreToolUse hooks disagree, precedence is `deny` > `defer` > `ask` > `allow`.
- **Hook output is untrusted.** `additionalContext` is capped at 10,000 characters and injected as a system reminder. Write it as factual statements, because imperative text can trip prompt-injection defences.

Source: https://code.claude.com/docs/en/hooks
