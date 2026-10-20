# Researchers and academics

For faculty, postdocs, PhD students and research staff who already use Claude and want repeatable workflows for literature work, reviewing, teaching and submissions. This is not a guide to getting Claude to write your paper, and it does not replace your field's methods training or your institution's AI policy. Basics (Projects, connectors, skills, scheduling) are in [_shared-setup.md](_shared-setup.md).

One rule runs through every section: **a citation Claude produced is a lead, not a reference.** Before anything goes into a draft, open the source, confirm the DOI resolves to the paper you think it does, and find the quoted sentence on the page.

## 1. Quick wins

### 1.1 Scoped literature scan with Research

```text
Use Research. Question: what is the current evidence on <topic> in <population/system> since <year>?
Scope: peer-reviewed articles and preprints; exclude opinion pieces.
Return:
1. A 150-word state-of-the-field summary.
2. A table: first author, year, venue, DOI, design, n, main finding, your confidence (high/med/low).
3. A list of claims you could NOT tie to a specific source you opened.
Rules: give a DOI only if you saw it on the source page. If you did not open the full text, say "abstract only".
```

Setup: paid plan, web search on, then **+ > Research** in the chat box ([shared setup](_shared-setup.md#connectors)). Research uses its own model regardless of your selector, and it uses up your limits faster than a normal chat.
Output: a report with inline citations, then the table and the "unsupported claims" list. Treat that last list as your to-do list. Run every DOI through 1.2 before using it.
Source: https://support.claude.com/en/articles/11088861-use-research-on-claude, https://claude.com/blog/integrations

### 1.2 Citation audit of a reference list

```text
Below is my reference list and the sentences in my draft that cite each one.
For every reference:
- Look up the DOI (or search title + first author if no DOI).
- Report: DOI resolves? (yes/no/not checked) | title/authors/year match? | retracted or corrected? | does the cited sentence fairly reflect the source (supported / overstated / not found / could not access)?
- Quote the exact passage from the source that supports the sentence, or write NONE.
Never fill a cell from memory. If you could not open the source, write "not checked".
[paste references + citing sentences]
```

Setup: web search on. For bulk checks, use Crossref's public REST API (`https://api.crossref.org/works/<DOI>`) in Claude Code or your own script. Crossref metadata includes Retraction Watch data.
Output: one row per reference. Expect some "not checked" rows for paywalled papers. Those are yours to open by hand.
Source: https://www.crossref.org/documentation/retrieve-metadata/rest-api/

### 1.3 Literature matrix in Google Sheets

```text
Create a Google Sheet called "Lit matrix – <project>" with one tab "matrix" and these columns:
ID | Citation (APA) | DOI | Verified (Y/N/blank) | Design | Sample | Measures | Key finding | Limitation | Relevance to RQ1/RQ2 | Notes
Fill rows only from the PDFs I attached. Leave Verified blank; I fill it.
Add a second tab "gaps" listing questions none of the papers address.
```

Setup: the Google Sheets connector (beta) for create/edit, or the Claude for Google Workspace add-on (public beta, paid plans) in the Sheets sidebar. On Team/Enterprise an owner must enable the connectors first. No Google? Ask for an `.xlsx` instead; file creation handles Excel. See [connectors](_shared-setup.md#connectors).
Output: a sheet with one row per paper and an empty `Verified` column. Each change shows as an approval card unless you switch to "Accept all edits".
Source: https://claude.com/blog/claude-now-works-in-google-docs-sheets-and-slides, https://support.claude.com/en/articles/12111783

### 1.4 Reviewer 2 pass on your own draft

```text
You are a demanding but fair reviewer for <journal/venue>. Review the attached manuscript.
Give: (1) a 3-sentence summary of what the paper claims; (2) major concerns ranked by how likely they are to cause rejection, each tied to a section/line; (3) minor issues; (4) the single analysis or control that would most strengthen it.
Do not praise. Do not suggest citations unless you can give a DOI you verified in this session.
```

Setup: upload the PDF or paste the text. Use your own unpublished work only. See guardrail 4.3 on others' manuscripts.
Output: a ranked list of concerns, each one specific enough that you can act on it ("Table 2 reports p-values without a correction for 14 comparisons").
Source: https://support.claude.com/en/articles/9519177

### 1.5 Conference abstract to a hard word limit

```text
Turn the attached paper into a conference abstract for <venue>.
Limit: <N> words including headings; structure: Background / Methods / Results / Conclusions.
Use only numbers that appear in the paper; quote each number's source table/figure in a list after the abstract.
Then give the exact word count and list what you cut.
```

Setup: none. Check the count yourself (paste into your submission system or `wc -w`). Model word counts can be off by a few words.
Output: the abstract, a numbers-to-source list, a word count, and a "cut" list so you can swap content back in.
Source: https://support.claude.com/en/articles/12111783

## 2. Deeper setups

### 2.1 A Project per paper or grant

Create one Project per manuscript or proposal ([projects](_shared-setup.md#projects)). Put the draft, the reviewer guidelines or call text, your verified reference list (BibTeX or the Sheet export), and your lab's style notes into project knowledge. Chats don't share context unless it lives in knowledge, so re-upload the latest draft as you revise.

```text
Project instructions:
This project supports the manuscript "<title>" for <venue>. I am the author; you are an editor and critic.
- Cite only from references.bib in project knowledge. If a claim needs a source not in that file, write [CITATION NEEDED: <what kind of evidence>] instead of inventing one.
- Never produce a DOI, page number or quote you did not read in an attached file or a source opened this session.
- Keep my voice; propose edits as tracked suggestions (old -> new), not rewrites.
- Flag any sentence that states causation from correlational data.
```

Output: every chat in the project respects the bibliography, so you get `[CITATION NEEDED]` markers where you used to get invented references.
Source: https://support.claude.com/en/articles/9519177

### 2.2 A "cite-check" custom skill

Package your audit routine once so it runs the same way every time ([skills](_shared-setup.md#skills)). Zip the folder with the folder itself at the root, then upload it under Skills. Code execution must be on.

```markdown
---
name: cite-check
description: Audits a manuscript's references and in-text citations. Use when the user asks to check, verify or audit citations, a bibliography, DOIs or quotes in a draft. Not for formatting references into a style.
---
# Cite-check

1. Extract every in-text citation and the sentence it supports. Extract the reference list.
2. Flag mismatches: cited but not listed, listed but never cited, year/author disagreements.
3. For each reference, try to confirm the DOI resolves and the title/authors match. Record the URL you opened.
4. For each direct quote, find it verbatim in the source. Report the page/section or "NOT FOUND".
5. Output a table: ref | DOI status | metadata match | retraction/correction | claim support | evidence URL.
6. Never mark a row verified without an evidence URL. Unopened sources are "not checked".
7. End with a list of the rows the author must check by hand.
```

Output: the same table as 1.2 every time, plus a hand-check list. Add a `scripts/` file that calls the Crossref API if you run this in Claude Code, where network access is under your control.
Source: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills, https://support.claude.com/en/articles/12512180-using-skills-in-claude

### 2.3 Weekly new-literature digest (scheduled task)

```text
Every Monday 07:00: search PubMed and the web for papers published in the last 7 days on <topic keywords>.
For each: title, authors, venue, DOI link, one-sentence finding, why it matters to my project "<name>".
Skip anything already listed in the "matrix" tab of my Lit matrix sheet.
Max 10 items. If nothing relevant, say so in one line. Do not summarize papers you could not open; list them as "title only".
```

Setup: in Cowork, type `/schedule` or use **Scheduled** in the sidebar ([scheduled tasks](_shared-setup.md#scheduled-tasks)). Scheduled tasks can use connectors, so add the PubMed connector and Google Sheets if you want deduplication. The support docs disagree on whether tasks run while the desktop app is closed. Check your first few runs.
Output: a short Monday list with DOI links, ready to triage into the matrix after you verify each one.
Source: https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork, https://claude.com/connectors/pubmed

## 3. Prompts that work in this field

```text
Before answering, list what you would need to see to answer this confidently, and which of those you actually have.
```
Why it's phrased this way: it makes gaps visible before Claude fills them with plausible-sounding text.

```text
For each claim below, label it: (a) directly stated in the attached source, (b) inferred from it, (c) from your general knowledge. Give the page for (a).
```
Why it's phrased this way: it separates evidence from background knowledge, and (c) is where hallucinated citations come from.

```text
Here is a quote I want to use: "<quote>". Find it verbatim in the attached PDF and give the page. If the wording differs at all, show both versions.
```
Why it's phrased this way: paraphrased "quotes" are a common integrity failure, and verbatim matching catches them.

```text
Write the strongest argument AGAINST my main hypothesis, citing only papers in references.bib. Then tell me which of those arguments my current data can't rule out.
```
Why it's phrased this way: it gives you a steelman you can use in your limitations section, grounded in your own bibliography.

```text
Act as Reviewer 2 for a methods-focused venue. Find the three weakest inferential steps between the data and the conclusions. Quote the sentence for each.
```
Why it's phrased this way: quoting pins each critique to the text, so you get findings you can check instead of general unease.

```text
Draft a problem set of 6 questions on <topic> for <course level>. For each: the question, a full worked solution, the misconception it targets, and the learning objective it maps to (from the attached syllabus).
```
Why it's phrased this way: tying each question to an objective and a misconception produces problems that assess something, not filler.

```text
Build an analytic rubric for <assignment> with 4 criteria x 4 levels. Each cell must describe observable evidence in the student work, not adjectives like "good" or "excellent".
```
Why it's phrased this way: observable descriptors make grading consistent across TAs and easier to defend in appeals.

```text
Outline a 50-minute lecture on <topic>: timing per segment, one worked example, two check-for-understanding questions, and the one slide students should remember. Flag any fact I should verify before teaching it.
```
Why it's phrased this way: timing makes the plan usable in the room, and the verify list keeps errors out of your slides.

```text
Cut this abstract from 312 to 250 words. Keep every number. Show the cuts as strikethrough so I can approve them.
```
Why it's phrased this way: you keep editorial control and the numbers stay intact.

```text
Write a one-paragraph AI-use disclosure for this manuscript, based on how I used Claude: <list uses>. Follow <journal>'s policy text pasted below.
```
Why it's phrased this way: disclosure wording varies by venue, so give Claude the policy rather than asking it to recall one.

## 4. Guardrails

**4.1 Fabricated or misattributed citations.** Every model can produce a reference that looks right and doesn't exist, or a real DOI attached to the wrong claim. Claude will often caveat that it can't verify a citation. Take the caveat seriously. Use connectors that return DOIs from a real index (PubMed, Wiley Scholar Gateway), make Research report "abstract only" when it didn't read full text, and run 1.2 or the 2.2 skill before submission. If a reference fails verification, delete it. Don't search for a paper that happens to fit the sentence.

**4.2 Ghost-writing submitted work.** Anthropic's Usage Policy prohibits plagiarism and submitting AI-assisted work "without proper permission or attribution". Claude may decline to write a student's graded assignment or a thesis chapter to be passed off as the student's own. The legitimate path: use Claude to critique, explain, outline and edit work you author, and disclose that use the way your venue requires. COPE's position: AI tools cannot be listed as authors, authors must disclose how they used them, and authors remain responsible for the content. Journal and funder policies vary. Paste the actual policy into the chat rather than relying on memory.
Source: https://www.anthropic.com/legal/aup, https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools

**4.3 Peer review confidentiality.** Many journals and funders forbid uploading manuscripts or proposals under review into AI tools (check each one; there is no universal rule). Use the 1.4 prompt on your own drafts. For refereeing, write your review yourself, and at most use Claude on your own notes after you remove identifying content, if the venue allows it.

**4.4 Academic misconduct decisions.** The Usage Policy treats "making a determination of academic misconduct" as a high-risk use that needs human review and disclosure. Don't use Claude's output as evidence that a student cheated. It can help you write a policy or a conversation guide.

**4.5 Student and participant data.** Identifiable student records and human-subjects data fall under your IRB/ethics approval and institutional data rules. Check the [data and privacy checklist](_shared-setup.md#data-and-privacy-checklist) and your IRB protocol before uploading anything.

**4.6 Teaching with Claude.** For student-facing use, Anthropic's Claude for Education offering includes a Learning mode that guides reasoning rather than giving answers. Check the announcement and your institution for current availability.
Source: https://www.anthropic.com/news/introducing-claude-for-education

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| Research (claude.ai) | Multi-search literature scans with citations | Paid plans; web search on; **+ > Research**. The launch post calls it "advanced Research". Reports usually take 5–15 min | https://support.claude.com/en/articles/11088861-use-research-on-claude |
| PubMed connector | Biomedical search, metadata, PMC full text, ID conversion | Anthropic verified; no sign-in | https://claude.com/connectors/pubmed |
| Wiley Scholar Gateway | Answers grounded in Wiley peer-reviewed content with DOI links | Sign-in required | https://claude.com/connectors/scholar-gateway |
| Google Sheets connector / Claude for Google Workspace | Literature matrices, grading sheets | Both in beta; Team/Enterprise owner enables the connectors | https://claude.com/blog/claude-now-works-in-google-docs-sheets-and-slides |
| xlsx / file creation | Matrix as an Excel file when you don't use Google | Code execution and file creation on | https://support.claude.com/en/articles/12111783 |
| bio-research plugin | Life-sciences literature (PubMed, bioRxiv, ClinicalTrials.gov and others), target prioritization | Install from Anthropic's knowledge-work-plugins (Cowork/Claude Code) | https://github.com/anthropics/knowledge-work-plugins |
| Claude for Life Sciences | Benchling, PubMed, Synapse.org, 10x Genomics, BioRender connectors | Org-level offering; plan details not stated on the launch page | https://www.anthropic.com/news/claude-for-life-sciences |
| Custom `cite-check` skill | Repeatable citation audit (2.2) | Upload zip under Skills; code execution on | https://support.claude.com/en/articles/12512198-how-to-create-custom-skills |
| Claude in Chrome | Reading your library database or LMS pages you're logged into | Paid plans; review site permissions first ([setup](_shared-setup.md#claude-in-chrome)) | https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome |
| Crossref REST API (external) | DOI resolution, metadata, retraction flags | Free, no key; call from Claude Code or a script | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ |

A standalone "deep-research" skill: (unverified: no official page found). Use Research or the plugins above.

## 6. Sample Project instructions

```text
Role: You support an academic researcher in <field> at <institution>. I am the author of all submitted work; you critique, explain, organize and edit.

Citations and evidence
- Treat every citation you generate as unverified. Mark it [UNVERIFIED] unless you opened the source in this session or it is in project knowledge.
- Never invent DOIs, page numbers, sample sizes or quotes. If you don't have one, write [NEEDED].
- When summarizing a paper, state whether you read the full text or only the abstract.
- Separate "the source says" from "I infer" from "general knowledge".

Writing
- Keep my voice. Propose edits as old -> new pairs with a one-line reason.
- Respect stated word limits exactly and report the count.
- Flag causal language unsupported by the design, missing multiple-comparison corrections, and unreported effect sizes.

Teaching materials
- Map every question or rubric criterion to a learning objective from the syllabus in project knowledge.
- Include worked solutions and the misconception each item targets.

Integrity
- Don't write graded student work or text meant to be submitted as solely my own without disclosure.
- If I ask for a disclosure statement, base it on the venue policy I paste, not on memory.
- Don't process manuscripts or proposals I'm reviewing for someone else.
- Remind me to remove identifiers before I share student or participant data.
```

Last checked: 2026-10-20
