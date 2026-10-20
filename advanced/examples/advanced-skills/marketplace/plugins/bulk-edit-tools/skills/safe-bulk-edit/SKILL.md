---
name: safe-bulk-edit
description: Plans, validates and applies the same text change across many files (renaming a function, API, config key or import path across a codebase) with a dry-run diff and backups. Use when the user asks to rename, replace or migrate an identifier or string in more than two files. Not for a single-file fix.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/validate_plan.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/apply_plan.py *)
---

# Safe bulk edit

Never edit the files directly. Every change goes through a plan file that a script validates.

## Workflow (copy this checklist and tick it off)

- [ ] 1. Find every occurrence (Grep). Decide per file whether it is in scope.
- [ ] 2. Write `changes.json` at the repo root (format below). Set `expect_count` on every edit.
- [ ] 3. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_plan.py changes.json`
- [ ] 4. If it prints `ERROR`, fix the plan and go back to step 3. Do not continue until it prints `OK`.
- [ ] 5. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/apply_plan.py changes.json --dry-run` and show the user the diff summary.
- [ ] 6. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/apply_plan.py changes.json`. It must print `VERIFY OK`.
- [ ] 7. Run the project's tests. Report the backup path printed in step 6.

## Plan format

```json
{
  "edits": [
    {"file": "src/api.py", "find": "getUser", "replace": "fetchUser", "expect_count": 2, "word": true}
  ]
}
```

- `file` is relative to the plan's directory. `word: true` matches whole identifiers only. Use it for symbol renames.
- One edit per (file, find) pair. If one replacement contains a later `find`, the validator rejects the plan. Reorder or merge the edits.
- Leave out generated, vendored and lock files. The validator rejects files over 2 MB.

## Rules

- Treat validator output as ground truth. When it lists "Close matches", use one of those names. Do not guess.
- Delete `changes.json` after a successful apply unless the user asks to keep it.
