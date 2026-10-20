# Claude for marketers

For product, content, growth and brand marketers who already use Claude and want repeatable workflows: briefs, positioning, copy variants, launch decks, weekly metrics, team requests in Slack. This is not an ad-buying tool, not a claims-review service, and not a substitute for legal sign-off. Basics (Projects, connectors, skills, scheduled tasks) live in [_shared-setup.md](_shared-setup.md); this page assumes you've read the relevant sections.

## 1. Quick wins

### Campaign brief from a messy kickoff

```text
Turn the attached kickoff notes and Slack export into a one-page campaign brief.
Sections, in order: Objective (one measurable goal + deadline), Audience (one
primary segment, what they believe today), Single-minded proposition (one
sentence), Proof points (each tagged SOURCE: <doc/page> or NEEDS SOURCE),
Mandatories, Channels, Budget, Success metric, Open questions.
Do not invent numbers. If a field has no input, write "TBD: ask <role>".
```

Setup: none beyond file upload. For repeat use, run it inside your campaign Project ([_shared-setup.md#projects](_shared-setup.md#projects)) so the brand guide and past briefs are already loaded. If the notes live in Drive, connect Google Workspace ([_shared-setup.md#connectors](_shared-setup.md#connectors)) and name the file instead of attaching it.

Output: a one-page brief. Proof points read like `"Cuts onboarding to 1 day" — NEEDS SOURCE`. The "Open questions" list is the useful part: it's what you take back to the stakeholder.

Source: https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects · https://support.claude.com/en/articles/10166901-use-google-workspace-connectors

### Positioning doc (April Dunford's five components)

```text
Draft a positioning doc for <product> using April Dunford's five components
from "Obviously Awesome": competitive alternatives, unique attributes, value
(and proof), target customers who care most, market category.
Inputs: attached win/loss notes, 3 customer call transcripts, competitor pages.
Rules: alternatives must include "do nothing" and spreadsheets/DIY if they
appear in the transcripts. Every value claim cites a transcript line or is
marked HYPOTHESIS. End with 3 candidate category framings and the risk of each.
```

Setup: upload transcripts and win/loss notes (strip customer names first; see [_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist)). The framework is Dunford's, not Claude's; Claude has no built-in "positioning" feature.

Output: a five-row table (component, our answer, evidence) followed by category options. Expect several HYPOTHESIS tags on a first pass; that's the honest result when you have few calls.

Source: https://www.aprildunford.com/books (Obviously Awesome, "five component pieces")

### Multi-variant copy with a fixed variants format

```text
Write 6 variants of the paid-social ad for <offer>. Audience: <segment>.
Return a table with columns: ID | Angle | Headline (<=40 chars) | Body (<=125
chars) | CTA | Char counts | Claim that needs proof.
Angles: 2 pain-led, 2 outcome-led, 1 social-proof (use ONLY the quotes I
pasted below, verbatim, with attribution), 1 contrarian.
No superlatives ("best", "#1", "fastest") unless I supplied the proof.
Then recommend 2 to test head-to-head and say what the test isolates.
```

Setup: paste real customer quotes with permission to use them. Character limits are yours to set per platform; recheck counts in the ad tool before launch.

Output sketch:

```text
ID | Angle    | Headline                       | Body                         | CTA        | H/B   | Claim needing proof
A1 | Pain     | Month-end close in 2 days      | Stop chasing receipts in...  | See how    | 26/98 | "2 days" -> case study?
A2 | Outcome  | Your team, back on Friday      | Automate approvals so...     | Start free | 25/87 | none
S1 | Proof    | "We closed in half the time"   | - Dana R., Ops lead, Acme    | Read story | 28/24 | quote on file, consent?
```

Source: https://www.ftc.gov/business-guidance/resources/advertising-faqs-guide-small-business

### Launch deck in Claude Slides

```text
Turn the attached launch brief and positioning doc into a 10-slide deck for
Thursday's sales kickoff. Audience: AEs who have not seen the product.
Slide order: problem, who it's for, what's new (3 slides max), how to pitch
it in one sentence, top 3 objections + answers, pricing, launch timeline, asks.
One idea per slide, speaker notes on every slide. Use our design system.
```

Setup: Claude Slides is an official artifact type, available on every plan; on Team and Enterprise an Owner can turn it on or off in **Organization settings > Artifacts**. Ask for a deck in any chat, or open **Artifacts > Make something new**. Pick a brand look with **+ > Design system** in the message box, or attach an old deck and ask Claude to match it. If you need a native .pptx edited in PowerPoint instead, ask for "a .pptx" by name (file creation must be on under **Settings > Capabilities**).

Output: a deck beside the chat that you edit, present and share. Export to PDF, .html, .png (current slide), PowerPoint (current or basic fonts), or Google Slides via **Share > Export** with Drive connected. In PowerPoint export, charts and icons become pictures and transitions are dropped.

Source: https://academy.claude.com/tutorials/using-claude-design-for-presentations-and-slide-decks · https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them · https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude

### Team requests through Claude Tag in Slack

```text
@Claude draft 3 subject lines and a 60-word preview for the webinar invite
in this thread. Use the brief pinned in this channel. Flag any claim that
isn't in the brief. Post as a numbered list so we can vote with reactions.
```

Setup: the official name is **Claude Tag** (public beta). It replaced the earlier Claude in Slack app. Team and Enterprise only; an Owner runs setup at `claude.ai/admin-settings/claude-tag` with a Slack workspace admin. As a user you install nothing: `/invite @Claude` in your channel. Set standing rules once: `@Claude remember for this channel: we write in sentence case and never promise delivery dates.`

Output: a threaded reply anyone in the channel can steer. Channel work uses admin-configured access and bills to the org; one-to-one DMs run on your own claude.ai account and connectors. Claude Tag can't read Slack canvases.

Source: https://claude.com/docs/claude-tag/users/getting-started · https://claude.com/docs/claude-tag/admins/setup-overview · https://www.anthropic.com/news/introducing-claude-tag

## 2. Deeper setups

### (a) A "Launch room" Project per product line

```text
Using this Project's files, draft the launch plan for <feature>, shipping <date>.
Return: tiering decision (T1/T2/T3) with reasoning, channel plan by week,
asset list with owner and due date, and the claims inventory: every claim
we'll make, its proof file, and status (approved / needs legal / no proof).
```

Setup: create a Project ([_shared-setup.md#projects](_shared-setup.md#projects)); upload the brand guide, positioning doc, approved claims list, last two launch retros and the persona sheet. Paste the instructions from [section 6](#6-sample-project-instructions). On Team/Enterprise, share it with the org so PMMs and content writers use the same context. Set a house Style for tone ([_shared-setup.md#writing-styles](_shared-setup.md#writing-styles)).

Output: a plan with a claims inventory table at the bottom. The inventory is the asset legal actually wants to see.

Source: https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects · https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features

### (b) Brand voice as a custom skill

A skill travels across chats and Projects, and an Owner can provision it to the whole org. Minimal `brand-voice/SKILL.md`:

```markdown
---
name: brand-voice
description: Rewrites or reviews marketing copy in Acme's brand voice. Use for any ad, email, landing page, social post or deck copy, or when asked to "check voice".
---

# Acme brand voice

## Voice
- Plain, specific, a little dry. Short sentences. Second person ("you").
- Sentence case for headlines. No exclamation marks.
- Banned: "revolutionary", "seamless", "unlock", "game-changer", "best-in-class".

## Claims
- Use only claims in `approved-claims.md`. Anything else: mark [NEEDS PROOF].
- No invented customer quotes, names, ratings or review counts.

## Review mode
When asked to "check voice", return a table: line | issue | rewrite.

## Example
Before: "Unlock seamless collaboration with our revolutionary platform!"
After: "Share a draft, get comments, ship it. All in one place."
```

Setup: put `SKILL.md` and `approved-claims.md` in a folder named `brand-voice`, zip the folder (folder at the zip root), then **Customize > Skills > + > Create skill > Upload a skill**. Name max 64 characters, description max 200. Code execution must be on. Team/Enterprise Owners can upload it once for everyone. See [_shared-setup.md#skills](_shared-setup.md#skills). Anthropic also publishes a Marketing plugin (`/brand-review`, `/draft-content`, `/campaign-plan`, `/performance-report`) for Cowork if you'd rather start from that.

Output: copy that comes back in voice without you pasting the guide, and a line-by-line table in review mode.

Source: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills · https://support.claude.com/en/articles/13119606-provision-and-manage-skills-for-your-organization · https://claude.com/marketplace/plugins/marketing

### (c) Weekly metrics: a Claude Dashboard plus a scheduled Monday summary

Step 1, build the dashboard once:

```text
Build a dashboard from HubSpot: marketing-sourced pipeline by week (last 12
weeks), MQL->SQL conversion by channel, email open/click by campaign, top 5
landing pages by conversions. Under each chart, one line on what changed
vs. the prior 4-week average. I want to know which channel is slipping.
```

Step 2, schedule the written summary:

```text
Every Monday 8:00 my time: pull last week's marketing email analytics and
campaign attribution from HubSpot. Compare to the prior 4 weeks. Write 5
bullets: biggest mover, biggest drop, one anomaly worth checking, one
experiment to run, and data gaps. Post to #marketing-metrics in Slack.
Never post raw contact data. If HubSpot fails, post "metrics run failed: <reason>".
```

Setup: Claude Dashboards is a beta artifact template (Pro, Max, Team, Enterprise; off by default on Enterprise until an Owner enables it in **Organization settings > Artifacts**). Ask for a dashboard in chat or pick **Output > Dashboards**. Sources are data warehouses (Redshift, BigQuery, ClickHouse, Databricks, Snowflake) or connected apps; the help page names Salesforce, and HubSpot via its connector should behave the same way (unverified). Each chart shows its query and last refresh; you ask Claude to refresh it. For step 2, create a scheduled task ([_shared-setup.md#scheduled-tasks](_shared-setup.md#scheduled-tasks)) with HubSpot and Slack connectors; it runs in the cloud; posts appear under your Slack account (unverified). Whether a scheduled task can refresh a dashboard artifact isn't documented, so keep the two separate.

Output: a shareable dashboard (private until you **Share**; viewers use their own connections, so someone without HubSpot access sees an error) and a five-bullet Slack post each Monday.

Source: https://support.claude.com/en/articles/17454700-get-started-with-claude-dashboards · https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork · https://claude.com/connectors/hubspot

Alternative for teams on Claude Tag: `@Claude every Monday at 9am Eastern, post a summary of ...` in the channel sets up a Tag routine using the channel's connectors (schedules run in UTC; name the timezone). Source: https://claude.com/docs/claude-tag/users/proactivity

## 3. Prompts that work in this field

```text
Before writing, ask me up to 5 questions about audience, offer, proof and
constraints. Then write.
```
Why: briefs are usually missing the proof and the constraint. Asking first is cheaper than three rewrites.

```text
Rewrite this for <persona>. Keep every factual claim identical. List any
sentence where you had to change meaning to fit.
```
Why: separates tone changes from claim changes, so a "polish" never quietly adds a promise.

```text
Here are 40 customer quotes. Cluster them into jobs-to-be-done. For each
cluster: count, 2 verbatim quotes, the words customers use (not ours).
```
Why: "the words customers use" gives you headline language grounded in evidence instead of brainstorm adjectives.

```text
Act as a skeptical buyer at <company type>. Read this landing page and list
the 5 places you'd stop believing us, with the line quoted.
```
Why: a role with a specific stance produces concrete objections, not generic "consider adding social proof".

```text
Compare our page and these 3 competitor pages (attached). Table: claim |
us | A | B | C. Mark claims nobody else makes. Don't judge which is true.
```
Why: "don't judge which is true" keeps it to what the pages say, which is all Claude can see.

```text
Write the email sequence (5 emails) as a table first: day | goal | subject |
one-line body summary | CTA. Wait for my OK before full drafts.
```
Why: approving structure first avoids rewriting five full emails when the arc is wrong.

```text
Give me 10 headline options ranked by clarity, not cleverness. Under 8
words each. Flag any that make a comparative or numeric claim.
```
Why: ranking criteria up front stops "clever" from winning by default; the flag feeds your claims review.

```text
Turn this webinar transcript into: 1 blog outline, 3 LinkedIn posts, 5
pull quotes with timestamps. Quotes must be verbatim from the transcript.
```
Why: timestamps and "verbatim" make every quote checkable against the source.

```text
Here is last quarter's campaign data (CSV). What's the one decision this
data supports, and what would you need to be confident? Show the math.
```
Why: asking for one decision and the missing evidence beats a ten-chart readout nobody acts on.

```text
Localize this ad for <market>. Keep claims identical, adapt idioms and
units. List anything that may need local legal review (pricing, guarantees,
comparative claims).
```
Why: localization is where claims drift; making Claude list risk items gives your reviewer a checklist.

## 4. Guardrails

- **Fake reviews and testimonials.** Claude will decline to invent customer reviews, star ratings, review counts or quotes attributed to real or made-up people, and Anthropic's Usage Policy prohibits fake personas and fake reviews. In the US, the FTC's Consumer Reviews and Testimonials Rule (16 CFR Part 465, in effect since Oct 21, 2024) bans reviews from people who don't exist, including AI-generated ones. Legitimate path: paste real quotes with consent; ask Claude to select and trim them without changing meaning; use clearly labelled placeholders (`[CUSTOMER QUOTE: ops lead, mid-market]`) in drafts.
- **Claims substantiation.** The FTC requires a reasonable basis (objective evidence) before an ad runs; health and safety claims usually need competent and reliable scientific evidence. Claude can't verify your numbers. Expect it to caveat superlatives and stats. Legitimate path: keep an approved-claims file in the Project or skill, and have Claude tag everything else NEEDS PROOF for legal.
- **Endorsements and typicality.** Endorsements must reflect honest experience; paid or gifted relationships need clear disclosure; atypical results need the typical result stated. Ask Claude to add disclosure lines and flag "results may vary" gaps.
- **Impersonation.** Claude won't write copy posing as a real person, competitor or outlet, or fake "independent" content. Comparative copy about named competitors is fine when it's accurate and sourced; keep parody clearly labelled.
- **AI-content disclosure.** Rules vary. The EU AI Act Article 50 adds transparency duties for deepfakes and some AI-generated text on matters of public interest (commentary only; check the final text and dates with counsel). Platforms and clients may have their own rules. Claude can draft disclosure labels; deciding where they're required is yours.
- **Data.** Don't upload customer lists or PII to a chat that doesn't need them. See [_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist). Claude Tag isn't available to orgs with Zero Data Retention because it stores channel memory.

Source: https://www.ftc.gov/business-guidance/resources/consumer-reviews-testimonials-rule-questions-answers · https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials · https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking · https://www.ftc.gov/business-guidance/resources/advertising-faqs-guide-small-business · https://www.anthropic.com/legal/aup · https://artificialintelligenceact.eu/transparency-rules-article-50/

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| HubSpot connector | Campaign attribution, email analytics, CRM lookups | Sign-in required; Team/Enterprise Owner enables first, then each user authenticates | https://claude.com/connectors/hubspot |
| Google Workspace (Drive, Docs, Gmail, Calendar) | Pull briefs and decks, export Slides to Google Slides | Connect from the **+** menu or Settings | https://support.claude.com/en/articles/10166901-use-google-workspace-connectors |
| Slack connector | Read channel context, post metric summaries from a scheduled task | Scheduled-task posts appear under your account (unverified) | https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities |
| Claude Tag | Team requests and routines in Slack channels | Team/Enterprise, public beta; Owner + Slack admin run setup | https://claude.com/docs/claude-tag/admins/setup-overview |
| Canva, Figma connectors | Pull or create on-brand assets alongside copy | Directory listing; interactive in chat | https://claude.com/marketplace/connectors-plugins |
| Marketing plugin (Anthropic) | `/campaign-plan`, `/brand-review`, `/performance-report`, `/seo-audit`, `/email-sequence` | Install in Cowork; set brand voice in plugin settings | https://claude.com/marketplace/plugins/marketing |
| Custom `brand-voice` skill | House voice + claims rules everywhere | Zip and upload under **Customize > Skills** | https://support.claude.com/en/articles/12512198-how-to-create-custom-skills |
| Claude Slides / Dashboards | Launch decks; weekly metric views | Artifact templates; Dashboards is beta | https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them |

No official Google Analytics connector turned up in the directory search; Amplitude is the analytics connector Anthropic's Marketing plugin suggests. Check the directory before assuming one exists.

## 6. Sample Project instructions

```text
You are the marketing co-pilot for <Company>, working with the <team> team.

Context files in this Project: brand-guide.pdf, positioning.md,
approved-claims.md, personas.md, past launch retros. Prefer them over
general knowledge. If they conflict, say so and ask.

Voice: plain, specific, second person, sentence case, no exclamation marks.
Banned words: revolutionary, seamless, unlock, game-changer, best-in-class.

Claims: use only claims in approved-claims.md, cited as [claim-ID]. Any other
factual, numeric, comparative or superlative claim gets [NEEDS PROOF].
Never invent customer quotes, names, logos, ratings, review counts or stats.
Use labelled placeholders instead: [QUOTE: role, segment].

Formats:
- Copy variants: table with ID | Angle | Headline | Body | CTA | Char counts
  | Claim needing proof. Respect the character limits I give.
- Briefs: Objective, Audience, Proposition, Proof, Mandatories, Channels,
  Budget, Metric, Open questions.
- Decks: one idea per slide, speaker notes on every slide.

Before long outputs (sequences, decks, plans), show the outline and wait.
When data is missing, say what's missing; don't estimate silently.
Add a disclosure line for any paid partnership or endorsement.
```

Last checked: 2026-10-20
