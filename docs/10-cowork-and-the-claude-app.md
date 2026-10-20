# Cowork & the Claude app

**Cowork's capabilities are now part of the main Claude app.** You'll still see "Cowork" in older help articles and in some menus; it means the agentic, hand-it-off-and-walk-away mode of Claude for knowledge work. Development tasks route to Claude Code; everything else is Cowork-style work inside Claude.

## What "handing off work" looks like

1. You describe an outcome: *"Turn these five interview transcripts into a findings deck for the exec review."*
2. Claude says in one sentence what it's about to do and starts — no plan-for-approval unless the task is expensive to redo or contradictory.
3. A **task list** appears beside the chat; items tick off as it works. The last item is always a check of the work.
4. Drafts arrive as soon as they're useful so you can redirect early.
5. You get a finished artifact (deck/doc/sheet/design/dashboard) or a file, with sources if research was involved — not a diary of effort.

You can leave. It keeps running in a private cloud workspace and you can pick it up from your phone.

## Setting it up for leverage

- **Projects** for standing context (instructions, files, style).
- **Connectors** for your data (see [Connectors](04-connectors.md)).
- **Skills/plugins** for your team's processes (see [Skills](03-skills.md)). `/setup-claude` is a guided onboarding that installs a role-matched plugin.
- **Desktop app** for file access, local shell, computer use, built-in browser, and desktop scheduled tasks.
- **Mobile app** for dispatching tasks to your desktop from your phone ("Assign tasks from anywhere"), voice, and phone-native tools.
- **Writing style profile** so drafts sound like you.
- **Memory & preferences** so you stop repeating yourself.

## Working with Claude on a task

- Tell it how you want ambiguity handled: *"ask first"* vs *"make the call and flag it."* It respects that except for irreversible decisions.
- If you're away, say so; it will assume you're not there to answer.
- Ask for **a separate reviewer** on anything high-stakes.
- Give it the **real files** (attach or connect) rather than describing them.
- When you say "share this with my manager," it turns the reply into an artifact with a link.
- When it can't edit an original (e.g. a Google Doc with no Docs connector), it gives you a Claude Docs version with the changes and says which connection would fix that.

## Plans & admin

Message limits, plan features, pricing: https://support.claude.com (Claude doesn't know your account specifics). Team/Enterprise owners control network access, connectors, Chrome, Cowork-in-cloud, voice, and design features from Admin settings.

## Lesser-known

- Cowork **plugins** (`cowork-plugin` skill) let you package a department's workflow — connectors + skills + instructions — and install it for everyone.
- You can **customise Claude's own interface** with mods (panels, status lines, toasts, slash commands, tool hooks) via the plugin-authoring skill.
- "Explain my usage" (`explain-usage`) shows where a session's tokens went.
- Scheduled tasks created in Cowork run remotely now — the old "computer must be awake" rule only applies to tasks that explicitly need your device.
- Claude in Chrome, Claude Design and Claude Code all draw from the **same usage pool** as chat.
