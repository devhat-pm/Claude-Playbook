# Hidden gems & power-user tricks

The capabilities that aren't obvious from the UI, plus habits that separate casual users from people who get real leverage.

---

## 1. Claude remembers more than you think — if you ask

- **Search past chats.** Claude can search and read your previous conversations when the feature is on (Settings → "Search and reference chats"). Just write as if it already knows: *"continue the budget sheet we built last week"*. Inside a Project it only searches that Project's chats; outside, only non-Project chats.
- **Memory from chat history.** Separate toggle. Claude builds a profile of how you work and what you've told it. You can edit it, and you can tell Claude directly: *"remember that I prefer British spelling and no bullet points."*
- **Writing-style profile.** Ask Claude to *learn your writing style* once; afterwards emails/posts it drafts "as you" sound like you. When a draft is off, say *"that doesn't sound like me"* and it updates the profile instead of starting over. Note: custom writing styles are migrating to skills (June 2026). A migrated style starts turned off under Customize → Skills and runs as `/<name>-style`. See [shared setup: writing styles](../roles/_shared-setup.md#writing-styles).
- **Incognito chats** exist for the opposite case: nothing saved to memory, nothing searchable later.

## 2. "Artifacts" are a whole suite of editable document types

Most people think an artifact is a code preview. It's a published, shareable page with its own URL, and Claude can create *typed* artifacts that open in a purpose-built editor:

| Say this | You get |
|---|---|
| "make a deck / slides / presentation" | **Slides** — editable, exports to PPTX or PDF |
| "write a doc / memo / spec / report" | **Docs** — editable, shareable, comments, exports to Word/PDF/Markdown/Google Docs |
| "a tracker / budget / table with formulas" | **Sheets** |
| "mock up the screen / a landing page / poster" | **Design** — canvas you can edit; part of Claude Design |
| "brainstorm board / architecture sketch / flowchart" | **Whiteboard**: artifact type; availability varies by account, no public docs yet |
| "to-do list / project tasks with owners and dates" | **Tasks**: artifact type; availability varies by account, no public docs yet |
| "dashboard / KPI page / scorecard" | **Dashboard** — can hold a tiny shared database that Claude updates later without rebuilding the page |
| "a brand/design system" | **Design System** — reusable across every deck and design you make afterwards |
| "short animation" / "a watercolour to paint by hand" | **Motion** / **Watercolor** |

Tricks:
- You don't need to say ".pptx". Say "deck" and download the PPTX from the artifact. Only name a file format if you need the raw file.
- **Pin** an artifact to your sidebar if you'll reopen it (ask Claude to pin it).
- Artifact pages can be granted runtime powers — remember what viewers did (polls, sign-ups), keep shared state, know who's viewing, ask Claude a question, accept file uploads. Ask: *"make this page remember responses."*
- Comments left on a published artifact can be routed back to Claude: *"watch this doc and respond to comments."*
- Claude can **read** any claude.ai artifact link you paste, including other people's shared ones.

## 3. Claude will keep working after you walk away

- In the Claude app, tasks run in a private cloud workspace. Close the tab, open it later on your phone, the work continues. Say *"I'll check back later, don't wait for me"* and Claude will make reasonable calls instead of asking.
- The **task list widget** beside the chat is how you see what got done.
- **"Remind me in this chat in 2 hours to check the deploy"** — Claude can schedule a message back into the same conversation (not just a recurring job).
- **Scheduled tasks** run as fresh sessions on a cron schedule, with your connectors and skills, even when your laptop is off. See [Automations](09-automations.md).

## 4. Claude can reach your computer and your apps

- **Device bridge.** When a chat is linked through the desktop app, Claude can read/write files in folders you've connected — and, if enabled, run a shell on your machine scoped to those folders. Deleting files requires explicit permission each time.
- **Computer use.** Claude can take screenshots and click/type in *native desktop apps* through the desktop app. Websites go through a browser instead.
- **Two browsers:** *Claude in Chrome* (your real Chrome, your logins) and the *built-in browser* (a pane inside the desktop app with its own logins). Set "Preferred browser" in settings. See [Claude in Chrome](08-claude-in-chrome.md).
- **Phone-side tools** on mobile: calendar search/create/update, Reminders (one reminder per shopping-list item if you ask), location, weather, charts of health data, maps and place search, recipe cards with scalable servings.

## 5. Claude can run code, build files and verify its own work

- Claude has a real Linux sandbox with Python, Node, document/data/media tools. "Analyze this CSV" means it actually loads the data and computes — not estimates in prose.
- It reads PDFs, DOCX, XLSX, images, audio, video, archives you attach. If it says it *can't* open something, ask it to try again — it's supposed to attempt first.
- It can **install packages** (pip/npm) and pull from GitHub. Other arbitrary websites are blocked from the shell; it uses web fetch instead.
- Ask for the **check step**: *"before you finish, verify the numbers by re-running them"* or *"have a fresh reviewer agent check this"*. For high-stakes work Claude will spawn a separate agent that hasn't seen the work being made so the work isn't grading itself.
- **Subagents.** Claude can fan out parallel research/search agents. Useful phrasing: *"run three parallel investigations and combine them."* Equally useful: *"don't delegate, just grep it yourself"* when it over-delegates.

## 6. Skills: turn any chat into a reusable workflow

- If you find yourself explaining the same process twice, say *"turn what we just did into a skill."* Claude writes a proper `SKILL.md` and offers to save it. From then on it triggers automatically when relevant, or by `/skill-name`.
- Skills can bundle scripts Claude *executes* without reading them into context — cheap and reliable.
- Built-in skills you can invoke by name include document builders (`docx`, `pptx`, `xlsx`, `pdf`), `frontend-design`, `deep-research`, `skill-creator`, `morning` (a daily brief), `setup-claude` (guided onboarding).
- See [Skills](03-skills.md).

## 7. Prompting tricks that actually move the needle

- **Explain *why*.** "Never use ellipses" is weaker than "the output is read by a TTS engine, so never use ellipses." Claude generalises from reasons.
- **Say "do it", not "could you suggest".** Current models follow instructions literally; "suggest changes" gets suggestions, "make these changes" gets edits.
- **Long documents go at the top, your question at the bottom.** Measured improvement up to ~30% on multi-document tasks.
- **Ask for quotes first** on long-document tasks: "pull the relevant quotes into `<quotes>` tags, then answer." Focuses attention.
- **3–5 examples in `<example>` tags** beat paragraphs of description for format/tone.
- **"Go beyond the basics; include as many relevant features as possible."** The models deliver minimal by default; ask for ambitious explicitly.
- **Positive framing.** "Write in flowing prose" works better than "don't use markdown."
- **Effort over model-switching.** On the API, tuning the `effort` parameter often beats changing models.
- **Tell it to clean up** temp files, or to commit to one approach rather than revisiting decisions, if it over-explores.
- See [Prompting](05-prompting.md).

## 8. Research mode is more than web search

- Claude does *agentic* research: one finding shapes the next search, it fetches full pages, cross-checks, and ends with a Sources list.
- "Advanced Research" (when enabled) launches a long-running research agent that searches the web *and* your connected drives and returns a cited report.
- It will search automatically for anything that may have changed since its training (who holds a role, prices, current versions). You don't need to ask "search the web for…".
- Connected apps are searched *before* the web for anything that's "yours" (our Q3 deck, my calendar, the Jira ticket).

## 9. Feedback is a channel, not a vent

- Thumbs-down goes to Anthropic and is read. Use it on bad refusals.
- Claude won't pretend to be a different model, and will tell you the model and cutoff if asked. You can switch models *mid-conversation*; earlier turns may have come from a different one.

## 10. Things Claude will refuse, so you don't waste a turn

Reproducing song lyrics/poems/long passages, drawing known characters or brands (it will invent an original one instead), building look-alike login pages or fake receipts "for a demo", malware, weapons/drug synthesis, doxxing a private person. Reframing doesn't help; ask for the original/honest version instead and it's usually happy to do that.

## 11. Small quality-of-life things

- `/` in the chat box lists available skills.
- Claude can draw inline SVG/HTML diagrams and interactive widgets directly in a chat reply — ask "show me a diagram of…" rather than asking for a file.
- Ask Claude to **critique its own design** for accessibility/contrast/hierarchy before you ship it.
- Paste a URL and Claude fetches it; paste a GitHub repo and (in agentic sessions) it can attach and clone it.
- Message limits, plans, pricing: https://support.claude.com — Claude itself doesn't know your account details.
