# Skills

A skill is a folder with a `SKILL.md` (and optionally scripts and reference files) that teaches Claude how to do a specific kind of task well. Only the name + description are loaded up front; the body loads when relevant; bundled files load (or scripts run) only when needed. This "progressive disclosure" is why you can have 100+ skills without blowing up context.

Skills work in the Claude app, Claude Code, the API and Managed Agents.

## When to make one

- You've explained the same process/preferences twice.
- A task has a fragile sequence (migrations, release checklist, data pipeline).
- You want teammates to get the same result you do.
- You want Claude to use a specific library/tool/format every time.

Fastest route: do the task once in chat, then say **"turn this into a skill."** Claude writes the SKILL.md and offers to save it. Or use the `skill-creator` skill, which also runs evals and tunes the description for triggering.

## Anatomy

```
my-skill/
  SKILL.md          # required: frontmatter + instructions (<500 lines)
  reference.md      # loaded only when needed
  scripts/do_it.py  # executed, not read into context
```

Frontmatter rules (validated):
- `name`: ≤64 chars, lowercase letters/numbers/hyphens, no "claude"/"anthropic".
- `description`: ≤1024 chars, **third person**, says what it does *and when to use it* with the trigger words users actually say.

Template: [`templates/SKILL.md`](../templates/SKILL.md).

## Authoring rules that matter

1. **Concise.** Claude is already smart; only add what it doesn't know. Cut every sentence that explains something general.
2. **Match freedom to fragility.** Open-ended task → heuristics. Fragile task → exact script, "do not modify."
3. **One level of references.** SKILL.md → reference files. Never reference → reference → reference.
4. **Scripts solve, don't defer.** Handle errors in the script; no magic constants.
5. **Feedback loops.** "Run validator → fix → repeat" patterns raise quality a lot.
6. **No time-sensitive text.** Put old ways in a collapsed "old patterns" section.
7. **Fully-qualified MCP tool names** (`GitHub:create_issue`).
8. **Forward slashes always.**
9. **Test with every model you'll run it on** — Haiku may need more detail than Opus.
10. **Evals before docs.** Three test scenarios, baseline without the skill, then write just enough to pass.

Official guide: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

## Where skills live

- **Claude app:** Settings → Skills (personal or org). `/` in the chat box lists them. Org admins can publish org-wide.
- **Claude Code:** `.claude/skills/<name>/SKILL.md` (project) or `~/.claude/skills/` (user). Also distributed via plugins. `/skill-doctor` reports triggering health.
- **API:** upload via the Skills endpoints; attach to requests. Note API code execution has no network / package install.

## Lesser-known

- Built-in skills you can call by name: `docx`, `pptx`, `xlsx`, `pdf`, `frontend-design`, `deep-research`, `skill-creator`, `morning`, `setup-claude`, `explain-usage`, `cowork-plugin`, `plugin-authoring`.
- Claude will **propose** a skill on its own when it notices a repeated multi-step procedure in a session; you review and save from a card.
- A skill can be *user-triggered only* (slash command) or *auto-triggered*; the description decides. If two overlap, the description wins — so to customise a built-in, make a new one with a description that says when to prefer it.
- Plugins = bundles of skills + hooks + MCP servers + agents, installable from marketplaces. Good unit for sharing a whole workflow across a team.
- Skills + scheduled tasks = unattended workflows (e.g. a `weekly-report` skill run every Monday).
