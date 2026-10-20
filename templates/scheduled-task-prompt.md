# Scheduled-task prompt template

Every run starts fresh with no memory of this chat. The prompt must contain everything.

```
GOAL
Produce <output> for <audience> covering <scope/time window, e.g. the last 24 hours>.

INPUTS
- <Connector A>: what to read (e.g. Gmail: unread in "Clients" label)
- <Connector B>: ...
- Folder/repo: <path or repo>, if any
- Last run's notes: read `runs/latest.md` if it exists and diff against it

STEPS
1. ...
2. ...
3. Verify: <re-run numbers / open the artifact / run tests>

OUTPUT
- Update the Dashboard artifact "<name>" (do not create a new one)   — or —
- Post to Slack #<channel> as a short message with a link            — or —
- Open a PR on branch claude/<topic>
Keep it under <length>. Lead with what changed.

DECISIONS
- If something is ambiguous, take the most reasonable reading and say which one at the top.
- Only stop and ask if an action is irreversible or visible to others (sending, deleting, paying).
- Never <hard rule>.

HOUSEKEEPING
Write a 5-line summary to `runs/latest.md` for the next run.
```
