# SEO and content

For in-house SEOs, content leads and agency strategists who already have Claude and want repeatable work: clustering, briefs, on-page audits, schema, refreshes. It is not a rank-tracking tool, a Core Web Vitals meter, or a content farm. Basics (Projects, connectors, skills, scheduled tasks, Chrome) live in [_shared-setup.md](_shared-setup.md).

Ground rule for everything below: Claude drafts and checks, a named human with real expertise edits and signs. Google asks you to "manually factcheck and review all AI-generated content", including titles, meta descriptions and structured data.

## 1. Quick wins

### 1.1 Cluster a keyword export into topics

```text
Attached: keywords.csv exported from [Search Console / Ahrefs / Semrush].
1. Load it with pandas. Print the columns, row count and 5 sample rows before doing anything.
2. Normalize: lowercase, strip, dedupe. Drop rows with 0 impressions/volume.
3. Cluster by search intent and shared head term (not just string similarity). Name each cluster
   with the query a human would type. Tag intent: informational / commercial / transactional / navigational.
4. For each cluster: total volume (or impressions), top 5 queries, current best URL if the export
   has one, and "new page" vs "existing page" recommendation.
5. Output clusters.xlsx (one sheet per view: clusters, query-to-cluster map, unassigned) and a
   10-line summary. List any query you could not place instead of forcing it.
```

**Setup.** Settings > Capabilities > "Code execution and file creation" on. Uploads up to 30 MB per file. Export from your tool's UI (Search Console's Performance report has an export button). Never paste client exports into a personal account if your contract forbids it: see [data and privacy](_shared-setup.md#data-and-privacy-checklist).

**Output.** An `.xlsx` with roughly: `cluster | intent | queries | volume | best_url | action`, e.g. `"invoice template word" | transactional | 14 | 9,800 | /templates/invoice | expand existing`, plus an unassigned sheet.

Source: https://support.claude.com/en/articles/12111783 · https://support.google.com/webmasters/answer/7576553

### 1.2 Content brief from a cluster

```text
Write a content brief for the cluster "[cluster name]" (queries pasted below).
Audience: [who]. Our product's relevant angle: [one line]. Our existing pages to link: [URLs].
Include: primary query, search intent, the reader's job-to-be-done, proposed H1 and H2/H3
outline, questions the page must answer, first-hand material we need from a subject-matter
expert (data, screenshots, quotes we actually have), internal links in and out, and what
NOT to cover. Do not invent statistics or sources; mark any claim that needs a citation [CITE].
```

**Setup.** None beyond a chat; better inside the Project from 2.1 so voice and site map are preloaded.

**Output.** One page: intent line, outline, a "needs SME input" list (e.g. "real onboarding time from our support data"), link targets, exclusions.

Source: https://developers.google.com/search/docs/fundamentals/creating-helpful-content

### 1.3 On-page audit of one URL with Claude in Chrome

```text
Open [URL]. Read the rendered page, not just the source. Report:
- <title> (length in characters) and meta description (length)
- canonical, robots meta, hreflang if present
- H1 count and the full heading outline (H1-H3)
- internal links: count, anchor texts, any pointing to redirects or 404s you can see
- images missing alt text
- JSON-LD blocks present (types only)
Then give the 5 highest-impact fixes, each with the exact replacement text.
Do not estimate Core Web Vitals; say "measure in PageSpeed Insights".
```

**Setup.** Claude in Chrome extension (paid plans, Chrome only): [_shared-setup.md#claude-in-chrome](_shared-setup.md#claude-in-chrome). It can read pages, DOM state and console output.

**Output.** A table of found values with pass/flag, then a numbered fix list: `Title is 74 chars, truncates. Replace with: "..." (58 chars)`.

**Caveat.** Claude cannot measure real Core Web Vitals. Field data (LCP under 2.5 s, INP under 200 ms, CLS under 0.1) comes from PageSpeed Insights and the Search Console Core Web Vitals report. Paste those numbers in if you want Claude to prioritize fixes.

Source: https://support.claude.com/en/articles/12012173 · https://developers.google.com/search/docs/appearance/core-web-vitals · https://pagespeed.web.dev/

### 1.4 JSON-LD for a page that already shows the facts

```text
Generate JSON-LD for this page. Type: [Article / Product / FAQPage / Organization / BreadcrumbList].
Use ONLY facts visible in the page text pasted below. If a required property has no visible
source on the page, leave it out and list it under "Missing on page" instead of inventing it.
No aggregateRating or review unless real user reviews are shown on the page.
Return one <script type="application/ld+json"> block and the missing-properties list.
```

**Setup.** Paste the rendered page text, or run it in Chrome. Validate every output in Google's Rich Results Test and the Schema Markup Validator before shipping.

**Output.** One script block plus `Missing on page: author.url, dateModified`.

Source: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data · https://search.google.com/test/rich-results · https://validator.schema.org/

### 1.5 Title and meta rewrite batch

```text
Attached: pages.csv with url, current_title, current_meta, primary_query, clicks, impressions, ctr.
For pages with impressions > [N] and CTR below the sheet median: propose a new title (<= 60 chars)
and meta description (<= 155 chars) that match the query's intent and what the page actually
contains. Keep brand suffix "[| Brand]". Return a CSV with old, new, char counts and a one-line reason.
Flag any page where the content does not satisfy the query: rewriting the snippet won't fix that.
```

**Setup.** Code execution on. Join a Search Console page export with your crawl's title/meta columns first, or ask Claude to merge two files.

**Output.** `rewrites.csv`, plus a short "content mismatch" list that becomes refresh candidates for 2.3.

Source: https://support.claude.com/en/articles/12111783 · https://developers.google.com/search/docs/fundamentals/using-gen-ai-content

## 2. Deeper setups

### 2.1 Project: "SEO desk" for one site or client

**Setup.** Create a Project ([_shared-setup.md#projects](_shared-setup.md#projects)). Knowledge: style guide, a sitemap or URL list with page purpose, author bios with real credentials, product facts sheet, last quarter's cluster file. Instructions: paste section 6. One Project per client keeps data separated. Sharing a Project with colleagues needs Team or Enterprise.

**Prompt to start each session.**

```text
Using the site map and style guide in this Project, [task]. Before answering, list which
Project files you used. If a fact is not in the files or the material I paste, ask.
```

**Output.** Answers that cite the internal files they drew on, use house terminology, and route claims to named authors.

Source: https://support.claude.com/en/articles/9517075

### 2.2 Custom skill: on-page audit checklist

Package your audit rubric once so every audit is the same shape. Folder `seo-onpage-audit/`, zipped with the folder at the ZIP root, uploaded and enabled under Customize > Skills ([_shared-setup.md#skills](_shared-setup.md#skills)). Requires code execution.

```markdown
---
name: seo-onpage-audit
description: Audit one URL's on-page SEO (title, meta, headings, links, alt, schema) and return a fix list. Use when asked to audit or review a page.
---
# On-page audit

1. Collect: title + length, meta description + length, canonical, robots, H1-H3 outline,
   internal links (anchor, target), images without alt, JSON-LD types.
2. Score each item pass / flag using these limits: title <= 60 chars, meta <= 155,
   exactly one H1, no internal links to redirects, every content image has alt.
3. Never report LCP, INP or CLS values. Write: "Core Web Vitals: check PageSpeed Insights
   and Search Console (field data)."
4. Schema: list types found. Flag review/aggregateRating markup on the site's own
   LocalBusiness or Organization pages (self-serving, ineligible for star snippets).
5. Output: table of findings, then max 7 fixes ordered by impact, each with exact new text.
6. Do not invent page facts, stats, authors or reviews. If unknown, say "not found".
```

**Output.** Same table and fix list every time, so audits are comparable across pages and staff.

Source: https://support.claude.com/en/articles/12512198 · https://developers.google.com/search/docs/appearance/structured-data/review-snippet · [../templates/SKILL.md](../templates/SKILL.md)

### 2.3 Scheduled task: weekly content refresh queue

**Setup.** A scheduled task ([_shared-setup.md#scheduled-tasks](_shared-setup.md#scheduled-tasks)) on Pro, Max, Team or Enterprise; cadence hourly/daily/weekly/weekdays/manual. It has your connectors and skills. Feed it data through a connector, e.g. Google Drive (drop the weekly Search Console export into a fixed folder) or the Ahrefs / Semrush connectors. There is no Search Console connector in the Claude directory that we could find, so the export step stays manual or goes through your own pipeline.

```text
Every Monday 08:00. Read the newest file in Drive folder "SEO/gsc-weekly".
Compare to the previous week's file in the same folder.
List pages where clicks dropped > 20% week-over-week AND impressions > 500, max 15.
For each: likely cause (position drop vs CTR drop vs impressions drop), the queries that moved,
and a refresh action (update facts/dates, expand section X, new title test, merge with URL Y).
Write the list to a new Google Doc "Refresh queue <date>" in the same folder.
Do not edit any live page. If either file is missing, write a doc that says so and stop.
```

**Output.** A weekly doc: `/pricing-guide | clicks -34% | avg position 4.1 -> 7.8 on "x pricing" | refresh: update 2025 prices, add comparison table`. A human picks what to ship.

**Browser alternative.** Save the 1.3 audit as a Claude in Chrome shortcut and schedule it from the extension's clock icon (daily/weekly/monthly/annually) for your top 10 money pages.

Source: https://support.claude.com/en/articles/13854387 · https://claude.com/connectors/google-drive · https://support.claude.com/en/articles/12012173

## 3. Prompts that work in this field

```text
Here is the SERP (top 10 titles and URLs) for "[query]". Classify each result's format and
intent. What format is Google rewarding, and would our page type fit?
```
Why it's phrased this way: you supply the SERP, so Claude analyzes real results instead of guessing what ranks.

```text
Rewrite this intro so the first two sentences answer "[query]" directly. Keep every fact;
add none. Show a diff.
```
Why: "add none" plus a diff stops silent fact invention and makes review fast.

```text
Find cannibalization: in this export, list query groups where 2+ of our URLs get impressions.
For each, recommend one canonical owner and what the others should do (merge, redirect, retarget).
```
Why: it asks for a decision per group, not a description of the data.

```text
List the claims in this draft that need a source. For each, say what kind of source would
satisfy a skeptical reader. Do not supply sources yourself.
```
Why: separates "needs evidence" from "find evidence"; Claude-supplied citations must still be checked.

```text
Interview me as an editor for 10 minutes about [topic]. Ask one question at a time, aimed at
first-hand experience only I have. Then turn my answers into notes for the draft.
```
Why: E-E-A-T's "experience" has to come from you; this extracts it instead of faking it.

```text
Suggest 10 internal links for this new page from the URL list in the Project. For each: source
page, exact anchor text already present on that page (quote it), target section.
```
Why: quoting existing anchor text forces links that fit the source page rather than invented sentences.

```text
Write a "How we made this" note for this article: who wrote it, their relevant experience
[facts], what AI assistance was used and for what, and who reviewed it.
```
Why: maps to Google's "Who, How, Why" disclosure guidance with real facts you provide.

```text
Draft an FAQ section from these real customer questions (pasted from support tickets).
Only answer from the product docs attached. Mark unanswerable ones [ASK PRODUCT].
```
Why: real questions beat invented ones, and the doc constraint keeps answers accurate.

```text
Turn this cluster sheet into a 12-week publishing plan. Constraint: [N] pieces/week,
[M] SME hours/week. Prioritize by volume x feasibility; justify the top 5.
```
Why: explicit capacity limits stop plans that need more expert time than you have.

```text
Review this page against Google's spam policies (doorway abuse, scaled content abuse, thin
affiliation, keyword stuffing). Quote the passages at risk and why.
```
Why: names specific policies, so the review is checkable rather than a vague "is this SEO-safe?".

## 4. Guardrails

**What Claude will decline.** Anthropic's Usage Policy (effective 12 Nov 2026) prohibits fake reviews and astroturfing, impersonating real individuals or entities, sites that mimic legitimate webpages, distributing content through "networks of fake or ostensibly independent outlets, websites, or accounts", generating or distributing spam, and attempts to "manipulate the sources from which search engines or AI systems draw answers". Expect refusals for: fake reviews or testimonials, lookalike pages for a competitor or brand, invented "independent" review sites for your own products, hundreds of city/keyword doorway pages, PBN content, and concealed sponsorship.

**What Google penalizes anyway.** The same work breaks Google's spam policies: doorway abuse, scaled content abuse ("many pages ... generated for the primary purpose of manipulating search rankings"), site reputation abuse, thin affiliation, and scam-and-fraud impersonation. Review markup must reflect genuine experiences; self-serving `LocalBusiness`/`Organization` reviews are ineligible for stars. In the US the FTC's rule bans fake and AI-generated reviews and testimonials and undisclosed insider reviews.

**The legitimate path.**
- *Reviews:* ask real customers (Claude can draft the request email and a disclosure line for any incentive), then summarize and quote the real ones with permission.
- *Location pages:* one page per location with genuinely local content (staff, hours, photos, local FAQs). Claude can template the structure; you supply the local facts.
- *Competitor comparisons:* fine when accurate, sourced and clearly yours. Ask Claude to flag every claim about the competitor that needs a dated source.
- *Programmatic pages:* fine when each page has unique, useful data. Have Claude check a sample for near-duplicates before launch.

**E-E-A-T honesty.** E-E-A-T is not a single ranking factor, but trust is "most important". Do not invent author bios, credentials, quotes, case studies or "we tested" claims. Bylines name real people who reviewed the piece. Disclose AI assistance "when it would be reasonably expected".

**Caveats Claude will give.** No real CWV numbers, no live rankings or volumes unless a connector supplies them, and traffic forecasts are estimates. Keep those caveats in client deliverables.

Source: https://www.anthropic.com/legal/aup · https://developers.google.com/search/docs/essentials/spam-policies · https://developers.google.com/search/docs/appearance/structured-data/review-snippet · https://developers.google.com/search/docs/fundamentals/creating-helpful-content · https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| Code execution and file creation | Clustering CSVs, merging exports, `.xlsx` output | Settings > Capabilities; 30 MB per file | https://support.claude.com/en/articles/12111783 |
| Claude in Chrome | Rendered-page audits, scheduled shortcut checks | Paid plans, Chrome only; admins can allow/block sites | https://support.claude.com/en/articles/12012173 |
| Ahrefs connector | Keywords, backlinks, rankings, competitor data | Lite plan or higher; uses Ahrefs API units | https://claude.com/connectors/ahrefs · https://help.ahrefs.com/en/articles/13913559-getting-started-with-ahrefs-mcp |
| Semrush connector | Keyword research, domain/backlink data, site audit | Customize > Connect your apps > Semrush; uses Semrush API units, eligible plans only | https://claude.com/connectors/semrush · https://developer.semrush.com/api/v4/introduction/semrush-mcp/ |
| Google Drive connector | Read weekly exports, write briefs and refresh docs | Sign in with Google; scope to one folder by convention | https://claude.com/connectors/google-drive |
| Custom skill `seo-onpage-audit` | Consistent audit format (2.2) | Zip folder, enable in Customize > Skills | https://support.claude.com/en/articles/12512198 |
| Scheduled tasks | Weekly refresh queue (2.3) | Pro, Max, Team, Enterprise | https://support.claude.com/en/articles/13854387 |

Connector basics: [_shared-setup.md#connectors](_shared-setup.md#connectors). Model choice for long audits vs quick rewrites: [_shared-setup.md#choosing-a-model](_shared-setup.md#choosing-a-model). Brand voice: [_shared-setup.md#writing-styles](_shared-setup.md#writing-styles).

## 6. Sample Project instructions

```text
You are the SEO and content assistant for [Brand] ([domain]). Audience: [who].

Sources of truth: the files in this Project (style guide, site map, product facts, author bios)
and whatever I paste. If a fact, number, author credential or review is not in those, ask.
Never invent statistics, quotes, testimonials, reviews, case studies or "we tested" claims.
Mark anything needing a citation [CITE] and anything needing expert input [SME].

Work style:
- Keyword work: state intent per cluster; prefer improving an existing URL over a new page.
- Briefs: H1/H2 outline, questions to answer, internal links (from the site map only), exclusions.
- Titles <= 60 chars, meta descriptions <= 155, one H1. Show character counts.
- JSON-LD: only facts visible on the page; no review/aggregateRating on our own
  LocalBusiness/Organization pages. Remind me to validate in the Rich Results Test.
- Never estimate Core Web Vitals; point to PageSpeed Insights / Search Console.
- Refuse and explain: fake reviews, lookalike or impersonation pages, doorway pages,
  mass thin pages, undisclosed sponsorship. Offer the legitimate alternative.
- Bylines name a real reviewer. Suggest a short AI-assistance disclosure where readers
  would reasonably expect one.

Output: lead with the answer or table, then reasons. No filler. British/American: [pick].
```

Last checked: 2026-10-20
