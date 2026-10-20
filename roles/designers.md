# Claude for product and UX designers

For product, UX and visual designers who already use Claude and want repeatable workflows: mockups on a canvas, hand-off to engineering, accessibility passes, UI copy and critique. This is not a Figma replacement and not an accessibility audit tool. Basics (Projects, connectors, skills, Chrome) live in [_shared-setup.md](_shared-setup.md); this page assumes you've read the relevant sections.

## 1. Quick wins

### Mock up a screen in Claude Design on your design system

```text
/design the empty state and first-run screen for our "Saved reports" page.
Use our published design system only. Three artboards: no reports yet,
1 report, permission denied. Label each artboard with the state name.
```

Setup: Claude Design is an official artifact template on Free, Pro, Max, Team and Enterprise. Open it via **Output > Design** in the message box, the Artifacts tab, or `/design` in Claude Code (v2.1.265+). Enterprise: on by default from Oct 15, 2026; before that an Owner enables it in **Organization settings > Artifacts**. Set up a design system first (see the design-system prompt in [section 3](#3-prompts-that-work-in-this-field) and the second source below), or you get generic styling.

Output: a canvas beside the chat with three artboards. Click an element to edit it; edits save automatically. Export from the **Export** menu: .zip, PDF, PPTX, Google Slides, standalone HTML, or per-artboard PNG/PDF. No version history yet, so ask Claude to save the project before trying a new direction.

Source: https://support.claude.com/en/articles/14604416-get-started-with-claude-design · https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design · https://code.claude.com/docs/en/artifacts#draft-a-design-canvas

### Hand a mockup to Claude Code without a screenshot

```text
Implement artboard 2 from this design in src/components/SavedReports.tsx.
Use existing components from src/ui only. List every element that has no
matching component instead of inventing one. Do not add new colour values.
```

Setup: in Claude Design, **Export > Send to local coding agent** (or **Send to Claude Code Web**). Claude Code then continues from the design artifact. If your components live in a React repo, run `/design-sync` in Claude Code at the repo root first, so the design system matches `main`.

Output: a diff against your component files plus a short "no matching component" list for the engineer to decide on. Re-run `/design-sync` when components change, or the next design drifts.

Source: https://support.claude.com/en/articles/14604416-get-started-with-claude-design · https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design

### WCAG pass on a screenshot or HTML file

```text
Review the attached [screenshot | HTML] against WCAG 2.2 AA.
For each issue give: success criterion number, element, what fails,
severity (blocker/major/minor), concrete fix.
If the input is a screenshot, mark every contrast finding "estimated from
pixels" and list the hex pairs I should verify with a contrast checker.
If it's HTML/CSS, compute contrast ratios from the declared colours.
Separately list what can't be judged from this input (focus order,
screen reader names, motion, timing).
```

Setup: attach a PNG/JPEG (claude.ai: up to 20 images per message, 8000x8000 px max) or paste the HTML. Higher-resolution screenshots work better; Claude's reading of small or low-quality images is less reliable.

Output: a table such as `1.4.3 | "Cancel" ghost button | #9AA3AE on #FFFFFF, ~2.6:1 (estimated) | major | darken to #6B7280 or add outline`, followed by "not checkable from a screenshot" items. Treat it as triage, then confirm with your usual tooling and a real screen reader.

Source: https://platform.claude.com/docs/en/build-with-claude/vision · https://www.w3.org/TR/WCAG22/ · https://support.claude.com/en/articles/14604416-get-started-with-claude-design

### Microcopy, empty states and error messages in one go

```text
Write UI copy for this flow: [paste screen list or attach screenshots].
Voice: plain, calm, second person, no exclamation marks, no blame.
For each screen: headline (<=40 chars), body (<=120 chars), primary CTA
(<=3 words), secondary action. For every error: what happened, why
(if known), what the user can do next. Give 2 variants per string and
flag any string over its limit.
```

Setup: none. Better: keep a voice-and-tone doc in a Project ([projects](_shared-setup.md#projects)) or as a [writing style](_shared-setup.md#writing-styles).

Output: a table per screen with two variants each, character counts, and an "over limit" flag. Paste the winners into your design or string file.

Source: https://support.claude.com/en/articles/14604416-get-started-with-claude-design

### Critique from screenshots

```text
Critique these screens (Image 1 = current, Image 2 = proposed) for a
[persona] trying to [job]. Order findings by impact on that job.
Cover hierarchy, scanning path, affordances, consistency between the two,
and copy. For each finding: what you see, why it matters, one fix.
No general praise. End with the single change you'd make first.
```

Setup: attach screenshots and label them "Image 1", "Image 2" in the prompt; the vision docs recommend labelling multiple images and putting images before the question.

Output: 6–12 ranked findings with fixes, then one "do this first" line. Claude can't see your analytics or research, so paste key findings if you want critique grounded in them.

Source: https://platform.claude.com/docs/en/build-with-claude/vision

## 2. Deeper setups

### (a) A "Design review desk" Project

Create a Project ([projects](_shared-setup.md#projects)) and add as knowledge: your design principles, voice-and-tone guide, component inventory (names plus one-line purpose), and your accessibility target (e.g. WCAG 2.2 AA). Paste the instructions from [section 6](#6-sample-project-instructions). Every critique, copy request and a11y pass in that Project then uses the same rules.

```text
New review: [feature name]. Screens attached in flow order.
Run the standard review: critique, WCAG 2.2 AA triage, copy pass.
```

Output: three sections in a fixed order, each finding tagged with the principle or criterion it maps to. Note: Project files are capped at 30MB each and only their text is extracted (multimodal PDFs aside), so attach screenshots per chat, not as Project files.

Source: https://support.claude.com/en/articles/8241126-upload-files-to-claude

### (b) A custom skill for UI copy

Skills are folders with a `SKILL.md`; available on Pro, Max, Team and Enterprise with code execution on. See [skills](_shared-setup.md#skills) and [../templates/SKILL.md](../templates/SKILL.md).

```markdown
---
name: ui-microcopy
description: Writes and reviews UI strings (buttons, empty states, errors, toasts, confirmations) to our voice rules and length limits. Use for any request about product copy or UI text.
---

# UI microcopy

## Rules
- Second person, present tense, sentence case. No exclamation marks.
- Buttons: verb first, <=3 words. Never "OK" or "Submit" alone.
- Errors: what happened, then what to do. Never blame the user. No error codes in the headline.
- Empty states: why it's empty, the one action that fills it.
- Destructive confirmations: name the object and the consequence ("Delete 3 reports? This can't be undone.").

## Output
Table: location | string | chars | variant B | rule notes.
Flag any string over its limit. Ask for the component name if missing.

## Examples
- Bad: "Oops! Something went wrong."  Good: "We couldn't save your changes. Check your connection and try again."
```

Output: every copy request returns the same table shape with limit checks. Zip the folder (folder name = `name`) and upload it in Claude, or drop it in `.claude/skills/` for Claude Code.

Source: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills · https://support.claude.com/en/articles/12512180-using-skills-in-claude

### (c) Claude in Chrome: keyboard and a11y sweep of a staging build

```text
Open https://staging.example.com/reports. Using only the keyboard (Tab,
Shift+Tab, Enter, Space, Esc), complete: create a report, rename it,
delete it. Record a GIF. At each step note: is focus visible, where does
focus land after dialogs open/close, any trap. Then read the DOM and list
images without alt, buttons without accessible names, heading levels that
skip, and form fields without labels. Output a table and save the GIF.
```

Setup: Claude in Chrome extension, paid plan, ideally from Claude Code with `claude --chrome` ([claude-in-chrome](_shared-setup.md#claude-in-chrome)). Allow only your staging domain in the extension's site permissions. Log in yourself; Claude pauses on login pages and CAPTCHAs.

Output: a step-by-step focus log, a DOM findings table, and a GIF you can attach to the ticket. Review the GIF before sharing; it captures everything visible, including account details.

Source: https://code.claude.com/docs/en/chrome · https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome

## 3. Prompts that work in this field

```text
Before designing anything, ask me up to 5 questions about users, constraints
and success criteria. Then propose 3 directions in one line each. Wait.
```
Why: stops Claude one-shotting a full screen on guesses; Claude Design works best in increments (structure, then content, then polish).

```text
/design 4 distinctly different layouts for the billing settings panel.
Vary density and grouping. One-line trade-off under each artboard.
```
Why: "distinctly different" plus a named axis of variation avoids four near-identical options.

```text
Build a design system from the attached brand guide, logo files, and our
shipped landing page screenshot. Flag any token you had to guess.
```
Why: the official guidance says finished examples help more than specs alone; "flag guesses" surfaces gaps before you publish it.

```text
Rewrite these 12 error messages. Keep the error cause; remove blame and jargon.
Return old | new | chars. Keep each under 90 characters.
```
Why: the old/new table makes review fast and keeps the original cause traceable.

```text
Here's a user flow as a list of steps: [paste]. Draw it as a diagram with
decision points, error paths and the happy path highlighted. Then list
dead ends and steps with no way back.
```
Why: asking for dead ends turns a diagram into a review. Inline diagrams render in chat; with the Figma connector you can ask for a FigJam diagram instead.

```text
From this Figma frame [paste node URL], list every colour, type style and
spacing value used that is NOT a variable in the file.
```
Why: uses the Figma connector's design-context and variable tools to find hard-coded values before hand-off.

```text
Compare Image 1 (design) and Image 2 (built page). List visual differences
in spacing, type, colour and alignment, largest first. Say "approximate"
for any pixel measurement.
```
Why: design-vs-build QA; vision coordinates and measurements are approximate per the docs, so you ask for that label up front.

```text
Write alt text for these 6 images in context: [page purpose]. Mark any image
that should be decorative (alt="") and say why.
```
Why: alt text depends on context; asking for decorative calls avoids redundant screen reader noise.

```text
Act as a first-time user with no context. Walk through these screens in
order and say out loud what you think each control does before "clicking".
Flag every guess that would be wrong.
```
Why: a cheap pre-test for labels and affordances. It does not replace usability testing with real people.

```text
Turn this critique into Jira-ready tickets: title, problem, evidence
(screen + element), proposed fix, acceptance criteria.
```
Why: closes the loop from review to work items without retyping.

## 4. Guardrails

- **Accessibility review is not compliance.** Claude can triage WCAG issues, but screenshots can't show focus order, accessible names, motion or timing, and colour readings from pixels are estimates. Use it to find issues early; sign-off still needs automated tooling, manual screen reader testing and, where it's a legal requirement, a qualified auditor.
- **Other people's IP.** Claude won't recreate third-party logos, brand mascots or copyrighted characters on request, and won't "get close" by tweaking (see [../docs/02-graphics-and-design.md](../docs/02-graphics-and-design.md)). Use your own brand assets, licensed stock, or ask for an original direction. Anthropic's usage policy prohibits infringing IP.
- **People in screenshots.** Claude won't identify real people in images. Crop or blur faces and names in research screenshots; that's also the right privacy call ([data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist)).
- **Deceptive patterns.** Expect Claude to push back on, or caveat, copy and flows meant to mislead users (hidden costs, confirmshaming, forced continuity) (unverified: no official page states this specific behaviour). The legitimate path: state the business goal, and ask for the strongest honest version.
- **Generated images.** Claude draws in SVG/HTML/CSS and on the Design canvas; it doesn't generate photographic raster images itself. For photos, use your stock library or an image-generation connector.
- **Unsupported or rough edges.** Claude Design has no version history yet, multi-person editing is basic, and inline comments can vanish before Claude reads them; paste feedback into chat instead. The Figma connector's `get_screenshot` currently returns only a text description in Claude, so attach real exports when visuals matter.
- **"Whiteboard."** No official Anthropic page describes a Whiteboard feature or template (unverified: no official page found). For user flows, use a chat diagram, a Design artboard, or FigJam via the Figma connector.

Source: https://platform.claude.com/docs/en/build-with-claude/vision · https://www.anthropic.com/legal/aup · https://support.claude.com/en/articles/14604416-get-started-with-claude-design · https://claude.com/connectors/figma

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| Claude Design (artifact template) | Mockups, prototypes, one-pagers on a canvas; export or send to Claude Code | Output > Design, or `/design` in Claude Code v2.1.265+; Enterprise Owner enables before Oct 15, 2026 | https://support.claude.com/en/articles/14604416-get-started-with-claude-design |
| Design systems | Brand/components reused by every design and deck | Pro/Max/Team on by default; Enterprise Owner turns on "Design systems" in Organization settings > Artifacts; publish and set org default | https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design |
| `/design-sync` (Claude Code) | Sync a React component library into a design system | Run at repo root; claude.ai login required | https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design |
| Figma connector (made by Figma, Anthropic verified) | Design context, variables, Code Connect maps, FigJam diagrams | "Add to Claude", sign in to Figma; Team/Enterprise may need admin enablement (unverified) | https://claude.com/connectors/figma |
| Claude in Chrome | Keyboard/a11y sweeps and design-vs-build checks on live pages | Extension + paid plan; `claude --chrome` in Claude Code | https://code.claude.com/docs/en/chrome |
| frontend-design skill | Less generic HTML/CSS output | Paste or install the official skill | https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md |
| Custom `ui-microcopy` skill | Consistent UI copy rules | See section 2(b) | https://support.claude.com/en/articles/12512198-how-to-create-custom-skills |

More on connectors: [connectors](_shared-setup.md#connectors). Model choice for long critiques vs quick copy: [choosing-a-model](_shared-setup.md#choosing-a-model).

## 6. Sample Project instructions

```text
You are a senior product design reviewer for [Company], working with the
design team on [product]. Our users: [1-2 lines]. Accessibility target:
WCAG 2.2 AA.

Knowledge files: design principles, voice-and-tone guide, component
inventory. Treat them as the source of truth. If a request conflicts with
them, say so and cite the file.

When I attach screens:
1. Critique: ranked by impact on the user's job. Each finding = what you
   see, why it matters (cite principle), one fix. No generic praise.
2. Accessibility triage: WCAG criterion number, element, issue, severity,
   fix. Mark contrast from screenshots "estimated". List what can't be
   judged from the input.
3. Copy: follow the voice guide; give old | new | chars.

When I ask for designs: ask up to 5 questions first, use our published
design system, only existing components (list gaps instead of inventing).

Never claim something is "compliant" or "accessible"; say "no issues found
in what I could check". Say when you're unsure. Keep answers short and
use tables for findings.
```

Last checked: 2026-10-20
