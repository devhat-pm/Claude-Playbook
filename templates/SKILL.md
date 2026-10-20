---
name: writing-release-notes
description: Drafts customer-facing release notes from merged PRs and commit messages in the house style. Use when the user asks for release notes, a changelog, "what shipped", or a launch announcement for a version.
---

# Writing release notes

## Inputs
- Version tag and date.
- List of merged PRs since the last tag: run `scripts/list_prs.sh <last-tag>`.

## Workflow
Copy and tick off:
```
- [ ] 1. Gather PRs (run the script; do not read git log manually)
- [ ] 2. Group: Features / Improvements / Fixes / Breaking
- [ ] 3. Rewrite each item for a customer (what they can now do, not what we changed)
- [ ] 4. Flag anything Breaking with a migration note
- [ ] 5. Validate: `scripts/check_notes.py notes.md` must print OK
```

## Style
- Lead with the benefit. "You can now export to CSV" not "Added CSV exporter".
- No internal ticket numbers. No engineer names.
- One line per item; link the PR in parentheses.

## Example
Input: `feat(export): add CSV export for reports (#412)`
Output: `- Export any report to CSV from the Share menu. (#412)`

## References
- Tone guide: [STYLE.md](STYLE.md)
