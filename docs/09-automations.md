# Automations: scheduled, triggered and unattended work

## The options

| Mechanism | Where | Runs when | Good for |
|---|---|---|---|
| **Scheduled tasks (cloud)** | Claude app / claude.ai/code/scheduled | On a cron schedule, your machine can be off | Daily briefs, weekly reports, triage, dependency bumps, monitoring |
| **Scheduled tasks (desktop)** | Claude desktop app → "Scheduled" | Only while your computer is awake and the app is open | Jobs that need local files, local apps, or your browser |
| **"Remind me in this chat"** | Any chat | Once, at a time you set, *back into the same conversation* | Check on a deploy, follow up a thread, resume a task |
| **`/loop` in Claude Code** | A running session | On an interval inside that session; expires in 7 days | Poll CI, re-run tests, watch a file |
| **Routines / API triggers** | Claude Code + API | Fired by API call or schedule | Integrate with your own systems |
| **GitHub Actions** | CI | On repo events | PR review, issue triage |
| **Claude Tag** | Slack | Proactively, when mentioned or when it notices something | Team-facing automations |
| **Managed Agents scheduled deployments** | API | Cron, hosted by Anthropic | Production agents |

Docs: https://support.claude.com/en/articles/13854387 · https://code.claude.com/docs/en/scheduled-tasks

## How a scheduled task behaves

- Each run is a **fresh session** with no memory of the chat you created it in. The prompt must stand alone. Template: [`templates/scheduled-task-prompt.md`](../templates/scheduled-task-prompt.md).
- Runs get your connectors, skills, plugins and (if required) your computer.
- Each task has an approval setting. If a run hits something that needs approval and nobody's there, it stops. Switch the task to "Automatically approve" if you trust it.
- Push and/or email notification when a run produces something noteworthy.
- Cloud coding tasks only push to `claude/`-prefixed branches by default.
- Runs may start a few minutes late; avoid scheduling on :00 if timing matters.

## Writing prompts that survive unattended runs

1. State the goal, the inputs (which connector, which folder, which repo), and exactly what "done" looks like.
2. Say what to do on ambiguity: *"take the most reasonable reading and note it at the top; only stop for irreversible decisions."*
3. Name the output: a Docs artifact, a Slack message, a PR, a file in a folder.
4. Give a verification step: *"re-run the numbers; open the deck and check every slide renders."*
5. Keep secrets out of the prompt; use connectors' own auth.

Ask Claude to set it up: *"every weekday at 8:30 Karachi time, read my calendar and inbox, and post a brief to #me in Slack"* — it will ask a couple of multiple-choice questions and create it.

## Patterns people actually use

- **Morning brief** (`/morning` skill or your own): calendar + inbox + tickets → one page.
- **Inbox zero assistant**: drafts replies for review, never sends.
- **Weekly metrics**: pull from a sheet or DB connector, update a Dashboard artifact.
- **Nightly repo hygiene**: run tests, open a PR for failures, bump safe deps.
- **Content pipeline**: skill writes post → design artifact for the image → waits for your approval.
- **Competitor watch**: search, diff against last run's notes file, alert on change.

## Lesser-known

- Claude can **schedule its own follow-ups** while working on something for you ("I'll check whether the build finished in 20 minutes").
- A scheduled task can be **fired manually** from its page or via API — handy for testing.
- Tasks that need the device (local files, Chrome, desktop apps) must declare it at creation; otherwise they run in the cloud without those tools.
- Reminders on your phone are different from scheduled tasks: "remind me at 3pm to call the bank" goes to the Reminders app and alerts you even if you never reopen Claude.
- Artifact pages can **ask Claude a question** from inside the page at runtime — a form of user-triggered automation without any schedule.
