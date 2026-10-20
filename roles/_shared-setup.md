# Shared setup for every role

Every role guide in `roles/` links here instead of repeating the basics. Do these once and you are set up by Monday.
Checked against official help pages on 2026-10-20. Menus move, so if a path below is wrong, search the cited article.

## Projects

A Project is a workspace with its own chats, instructions and knowledge files. One per recurring body of work, e.g. "Q4 board pack" or "Cardiology clinic letters". Don't make one per task.

**Create one**
1. Sidebar → **Projects** (or claude.ai/projects) → **+ New Project**.
2. Name and description are for you. Claude does not see them.
3. Team/Enterprise: choose private or shared with your org.
4. **Set project instructions** → paste the template below → **Save instructions**.
5. Knowledge panel (right side) → **+** → upload the reference files.

**What goes where**

| Put it in... | When it is | Examples |
|---|---|---|
| Project instructions | How Claude should behave in every chat | Role, audience, output format, house rules, "never do X" |
| Knowledge files | Material Claude should look things up in | Style guide, templates, past examples, glossary, policy PDFs |
| The chat itself | Specific to this one task | Today's draft, this candidate's CV, this dataset |

**Instructions template** (fill in the brackets and delete any line you don't need):
```
I am a [role] at [org type]. My readers are [audience].
Use this project for [recurring job]. Typical inputs: [what I paste or upload].
Default output: [format, length, structure]. Use [UK/US] spelling and [units/currency].
Always: [e.g. cite the knowledge file and section you relied on; flag assumptions].
Never: [e.g. invent figures, citations or names; give a final answer without a "checks" list].
If something is ambiguous, [ask one question first | state your assumption and continue].
Knowledge files: [file A] is the source of truth for [x]; [file B] is examples only.
```

**What goes wrong**
- Chats in the same Project don't share context. Only the knowledge files and instructions carry over. Put anything you need again into knowledge.
- On paid plans, as knowledge approaches the context limit, Claude switches to retrieval (RAG), which raises capacity up to about 10x. After that it retrieves relevant chunks instead of reading every file, so name files clearly and tell Claude which file and section to use.
- Free plan: maximum 5 Projects. RAG mode is paid plans only. Sharing is Team/Enterprise only ("Can view" or "Can edit").
- The help pages give no file-count or instruction-length limit. Don't rely on one.

Source: https://support.claude.com/en/articles/9517075-what-are-projects · https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects

## Memory

Memory builds a profile of your role, people, projects and preferences from your chats. It is saved topic by topic as you chat, not as a summary afterwards. You can also say "remember this".

| Setting (Settings → **Memory**) | What it does |
|---|---|
| **Generate memory from chats** | Main switch. Turning it off gives **Pause memory** (keep, stop using) or **Reset memory** (deletes everything, project memories included; can't be undone). |
| **Search and reference chats** | Lets Claude search your past chats. Paid plans only. |
| **Include sensitive topics in memory** | Off by default. Health, religion, politics, gender identity are skipped unless this is on. Takes effect going forward only. |
| **Topics** | View, edit (pencil icon) or **Delete** each remembered item. |

- **Defaults.** On by default for Free, Pro and Max. On Team/Enterprise it is off until an Owner enables it (Organization settings → Capabilities) and then each member turns it on. Owners can't read members' memories.
- **Project-scoped memory.** Each Project keeps its own memory. Inside a Project, Claude uses that Project's memory plus your general memory, but never another Project's. To wall a Project off completely, turn off **Use account memory** on the Project page.
- **One chat without memory.** In a new chat, open **+** and turn off **Memory** before the first message. The chat still appears in history and search.
- **Incognito.** Click the ghost icon (top right of a new chat, outside a Project). The chat isn't saved to history or memory, and it's excluded from training. On Team/Enterprise it still appears in exports and follows org retention.
- Never stored, per the help page: government ID numbers, criminal history, financial account numbers, immigration status.

**For clinicians, HR, finance and anyone handling third-party data:** leave sensitive topics off and use incognito or a memory-walled Project for case work. Check **Topics** monthly and delete anything about a named patient, candidate or client. Memory is not available to orgs with HIPAA, public-sector or custom data-retention agreements.

Source: https://support.claude.com/en/articles/11817273 · https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training

## Writing styles

**Styles are being turned into skills.** Per the June 2026 help article (only found in German, "Stile werden zu Skills"):
- Your custom styles migrate automatically to skills, **turned off by default**. Enable them in **Customize → Skills**.
- Most preset styles are removed, and the style menu disappears once migration finishes.
- Run a migrated style with `/<style-name>-style`. The name is lowercased, spaces become hyphens and punctuation is dropped.
- If you'd rather not use skills, put the same behaviour in **Settings → Instructions for Claude**. That applies to all your chats.

**Making a voice from samples now.** Ask Claude to "write a skill that captures my writing voice from these samples" and attach 3–5 pieces you're proud of. Or write the skill yourself ([Skills](#skills)). Including a "don't" list (words you never use) helps more than adjectives.

| Use | For |
|---|---|
| Instructions for Claude (account) | Applies to everything you do: spelling, tone, "no preamble" |
| Project instructions | Applies to one body of work: audience, format, sources |
| Skill | A voice or procedure you switch on by name, used across Projects |

Source: https://support.claude.com/de/articles/10181068-stile-werden-zu-skills · https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features

## Connectors

Connectors let Claude read and act in your apps through MCP. Background and best practice: [docs/04-connectors.md](../docs/04-connectors.md).

**Turn on a directory connector (Google Drive/Gmail/Calendar, Slack, etc.)**
1. **Customize → Connectors** → find the app → **Connect** → sign in with that app's account.
2. In a chat: **+** (bottom left) → **Connectors** → toggle per chat. Use this to keep unrelated connectors out.
3. Team/Enterprise: a connector doesn't appear until an Owner adds it for the org. Then each member connects their own account, and Claude sees only what that account can see.

**Add a custom (remote MCP) connector**
- Individuals: **Customize → Connectors → + Add → Add custom connector** → name → server URL → **Continue** → choose authentication (**Sign in now / Sign in when needed / No sign in**), OAuth client, optional request headers → **Add**.
- Team/Enterprise: **Organization settings → Connectors → Add → Custom → Web**. Only Owners/Primary Owners can do this on Team. On Enterprise, custom roles with "Manage access to Libraries" can too.
- All plans. Free is limited to 1 custom connector. The server must be reachable from Anthropic's cloud (or allowlist Anthropic's IPs). Editing a connector means removing and re-adding it.

**Permissions**
- Click **Allow always** only for tools you'd trust to run unsupervised. Use the **Search and tools** menu to disable tools you don't want called.
- **Research** can call connector tools without asking. Disable write-capable tools before running it.
- Shared API-key connectors give every member the key's access. Scope the key narrowly.

**Prompt injection.** Text that comes out of a connector (an email, a doc comment, a ticket) is data, not orders. If Claude proposes acting on instructions it found inside content, stop and check. Custom connectors aren't verified by Anthropic. Only add servers run by organisations you trust. More: [advanced/security-and-prompt-injection.md](../advanced/security-and-prompt-injection.md).

Source: https://support.claude.com/en/articles/11175166 · https://support.claude.com/en/articles/10166901-use-google-workspace-connectors

## Skills

A skill is a folder with instructions (and optionally scripts) that Claude loads when its description matches the task. Available on all plans. Requires code execution.

**Turn on**
- Free/Pro/Max: **Settings → Capabilities → Code execution and file creation** on.
- Team/Enterprise: an admin enables code execution and **Skills** in **Organization settings → Plugins & skills → Policy** (on by default for Team).
- Everyone: **Customize → Skills** toggles individual skills.

**Built-in skills.** Word, Excel, PowerPoint and PDF. You don't need to invoke them. Ask for "a .docx/.xlsx/.pptx/.pdf" and Claude uses them.

**Upload your own**
1. Make a folder whose name matches the skill `name`, containing `SKILL.md`.
2. Zip the **folder** so the zip contains `my-skill/SKILL.md`, not loose files.
3. **Customize → Skills → + → + Create skill → Upload a skill**.

Minimal `SKILL.md` (full template: [templates/SKILL.md](../templates/SKILL.md)):
```markdown
---
name: clinic-letter
description: Drafts GP referral letters in our clinic format. Use when asked for a referral or clinic letter.
---
# Clinic letter
1. Ask for: reason, history, meds, question for the specialist.
2. Use the structure in reference/format.md.
3. End with a "check before sending" list.
```
- `name` max 64 characters. The help article gives a 200-character limit for `description`. Make it say *what* and *when*.
- Upload fails if the folder name doesn't match, `SKILL.md` is missing, the zip is too large, or name/description has invalid characters.
- Uploaded skills are private to you. Owners can provision org-wide skills and can disable user-created ones.
- Scripts, evals and team rollout: [advanced/advanced-skills.md](../advanced/advanced-skills.md).

Source: https://support.claude.com/en/articles/12512180 · https://support.claude.com/en/articles/12512198-how-to-create-custom-skills

## Scheduled tasks

Recurring work that runs without you, e.g. a Monday digest of inbox + calendar + Slack.

**In the Claude app (Cowork / new Claude experience).** Pro, Max, Team, Enterprise.
- Easiest: in any chat, describe the task and how often → answer Claude's questions → review → **Schedule**.
- Manual: sidebar **Scheduled → New task → Set up manually** → name, prompt, approval mode, frequency (hourly, daily, weekly, weekdays, manual), optional model and folder → **Save**.
- Manage runs, pause, edit or **run now** from **Scheduled**.
- Tasks run remotely, so they continue while your computer sleeps. Tasks that need local files or apps run only on your machine. They use your connectors, so the connector permissions above apply.
- Team/Enterprise admins can switch Cowork (and with it scheduling) off.

**In Claude Code.** `/schedule` creates a cloud **routine**, a research preview also referred to as "cloud scheduled tasks". It needs a claude.ai login, not an API key. Minimum interval is 1 hour. Desktop scheduled tasks run only while the app is open and the machine is awake. `/loop` is session-only.

**What goes wrong:** vague prompts produce vague digests. Write the task prompt like a brief: [templates/scheduled-task-prompt.md](../templates/scheduled-task-prompt.md). Keep write/send actions behind approval until you've watched a few runs. More: [docs/09-automations.md](../docs/09-automations.md) · [advanced/unattended-pipelines.md](../advanced/unattended-pipelines.md).

Source: https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork · https://code.claude.com/docs/en/routines · https://code.claude.com/docs/en/desktop-scheduled-tasks

## Claude in Chrome

A Chrome extension that lets Claude read pages and click, type and navigate for you. Paid plans. **Google Chrome only**: not other Chromium browsers, not mobile.

**Install.** Chrome Web Store → **Add to Chrome** → sign in → pin it (puzzle icon → thumbtack) → grant permissions.

**Permission modes**

| Mode | Behaviour | Use when |
|---|---|---|
| **Manually approve** (formerly "Ask before acting") | Asks before each action | Default for anything new or work-related |
| **Automatically approve** | Checks each action for safety and pauses when needed. Uses more of your limit. | Routine tasks on sites you know |
| **Skip all approvals** | No pauses, no checks | Almost never |

- Per site: **Allow this action** (one action only, safest), **Always allow actions on this site**, or **Decline**. Revoke from extension → **⋯ → Extension settings → Your approved sites**.
- It always asks before granting authorizations, changing permissions or entering sensitive information. It won't do purchases, account creation, card/ID handling, permanent deletions, trades, or "instructions from emails or web content".
- **Don't point it at** banking/investments, legal contracts, medical records, HR systems with other people's data, or regulated data. Anthropic advises against these. Use a separate Chrome profile with no bank, health or government logins.
- Stop the task if it opens unexpected sites, drifts off topic or asks for credentials. That may be prompt injection from page content.
- Team/Enterprise admins can allowlist or blocklist sites.

More: [docs/08-claude-in-chrome.md](../docs/08-claude-in-chrome.md) · [advanced/browser-and-computer-automation.md](../advanced/browser-and-computer-automation.md).

Source: https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome · https://support.claude.com/en/articles/12902446-claude-in-chrome-permissions-guide · https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely

## Data and privacy checklist

Go through this **before** you paste client, patient, candidate or financial data.

- [ ] **Know your plan.** Free/Pro/Max are consumer terms. Team/Enterprise/API are commercial terms. The consumer training changes "do not apply to services under our Commercial Terms."
- [ ] **Consumer: check training.** Settings → **Privacy** (claude.ai/settings/data-privacy-controls) → **Help improve our AI models**. If on, new chats may be kept de-identified for up to 5 years. If off, about 30 days after deletion. Turning it off doesn't remove data from models already trained. Thumbs up/down feedback is kept up to 5 years.
- [ ] **Retention.** Deleted chats leave history at once and back-end storage within 30 days. Flagged content is kept up to 2 years. Enterprise can set custom retention (ask your admin).
- [ ] **Health data (US).** Only **Enterprise** can be HIPAA-ready. The Primary Owner accepts a click-through BAA in org settings, and the change can't be undone. Not every feature is covered: Claude Code/Cowork need a separate local-mode configuration, and cloud features are excluded. Check the Trust Center's HIPAA implementation guide before any PHI. **Team, Pro and Max cannot be HIPAA-ready.**
- [ ] **De-identify by habit.** Replace names, IDs, DOBs, addresses and account numbers with tokens (`[PATIENT_1]`, `[CAND_A]`) before pasting. Keep the key outside Claude.
- [ ] **Memory.** Sensitive topics off. Use incognito or a memory-walled Project for case work ([Memory](#memory)).
- [ ] **Connectors and Chrome.** They pull data in automatically. Connect only the accounts this work needs ([Connectors](#connectors)).
- [ ] **Your employer's policy wins.** If it says "approved tools only", use the org workspace, not a personal account.

Source: https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data · https://privacy.claude.com/en/articles/12109829-how-do-i-change-my-model-improvement-privacy-settings · https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data · https://www.anthropic.com/news/updates-to-our-consumer-terms · https://support.claude.com/en/articles/13296973-hipaa-ready-enterprise-plans

## Choosing a model

- Default to the model the app picks. Change it only when output quality or speed is clearly the problem.
- Long, hard, multistep analysis or documents: the most capable model available on your plan.
- High-volume, quick edits or classification: a faster, cheaper model.
- Full lineup, effort settings and trade-offs: [docs/06-choosing-a-model.md](../docs/06-choosing-a-model.md).

Source: https://platform.claude.com/docs/en/about-claude/models/overview
