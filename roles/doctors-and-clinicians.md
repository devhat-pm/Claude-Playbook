# Doctors and clinicians

For physicians, NPs, PAs, pharmacists and nurses who already have Claude and want working patterns for reading, writing and preparing. **Claude is not a clinical decision tool.** It doesn't diagnose, choose treatment or set doses for a patient. You do, and you check every number against the primary source. Basics such as Projects, connectors and privacy are covered in [_shared-setup.md](_shared-setup.md). Start with [the data and privacy checklist](_shared-setup.md#data-and-privacy-checklist).

**Default rule for every workflow below:** no PHI unless your organization runs HIPAA-ready Claude Enterprise with the BAA accepted, and even then only in the features the BAA covers (see [Guardrails](#4-guardrails)). Otherwise de-identify first.

## 1. Quick wins

### Literature summary with real citations

```
Using the PubMed connector, find studies from the last 5 years on <question, e.g. "SGLT2 inhibitors in HFpEF, hospitalization outcomes">.
Prefer RCTs, meta-analyses and major guidelines. For each paper give: PMID, design, n, population, primary outcome and effect size with CI, and one line on limitations.
Then write a 150-word bottom line that separates what is established from what is uncertain.
Cite a PMID for every claim. If an abstract is all you could read, say so.
```

- **Setup:** The PubMed connector (Anthropic-verified, no sign-in). See [connectors](_shared-setup.md#connectors). Without it, turn on web search and require links.
- **Output:** A table of 6 to 12 papers with PMIDs, then a short "established / uncertain" summary. Open the 2 or 3 papers that carry the conclusion and read them yourself.
- Source: https://claude.com/connectors/pubmed · https://www.anthropic.com/news/healthcare-life-sciences

### Patient handout at a set reading level

```
Write a patient handout on <condition/procedure> for adults reading at a US grade 6 level.
Audience: <e.g. newly diagnosed, English as a second language>.
Sections: What it is / Why it matters / What you can do / When to call us / When to go to the ER.
Short sentences, common words, no unexplained jargon. Do not include drug doses. Write "[CLINIC TO FILL]" where our own instructions belong.
After the handout, list every medical claim you made so I can check them, and give an estimated reading grade.
```

- **Setup:** None. To keep tone consistent across handouts, save a [writing style](_shared-setup.md#writing-styles) built from two of your existing handouts.
- **Output:** A one-page handout, a claim list to check, and a grade estimate. Confirm the grade with a readability tool you trust, because Claude's estimate is approximate (unverified).
- Source: https://www.anthropic.com/news/healthcare-life-sciences (Claude is designed to add disclaimers and refer people to professionals)

### Differential sounding board (de-identified)

```
Educational case discussion, de-identified. I am the treating clinician and will make all decisions.
<age band, sex, key history, exam, labs. No names, dates, MRN or location>
Act as a colleague I'm thinking out loud with. Give me:
1. Differentials I may be under-weighting, each with the single finding that would argue for or against it.
2. Can't-miss diagnoses and the fastest way to exclude each one.
3. Questions or exam findings I haven't mentioned that would most change the picture.
Don't rank to a final diagnosis and don't recommend treatment.
```

- **Setup:** Strip the 18 Safe Harbor identifiers first (see [Guardrails](#4-guardrails)).
- **Output:** Three short lists. Use it as a prompt for your own reasoning, then document what you decided and why.
- Source: https://www.anthropic.com/legal/aup · https://www.law.cornell.edu/cfr/text/45/164.514

### Medication label lookup (DailyMed / FDA label)

```
Use web search to find the current FDA label for <drug, formulation, manufacturer if known> on DailyMed (dailymed.nlm.nih.gov).
Quote the label verbatim, with its section number, for: <e.g. renal dose adjustment / boxed warning / pregnancy / interactions with X>.
Give the DailyMed SET ID and label revision date. If you can't open the label itself, say so. Don't fill gaps from memory.
```

- **Setup:** Web search on. Anthropic's own dosing guidance tells Claude to confirm a label "against an official copy of the same label, such as DailyMed." This prompt applies the same rule to your adult and professional lookups.
- **Output:** Quoted label text with section numbers, the SET ID and the revision date. Open the link and check it before you act on anything.
- Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices · https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm

### Note template from your own style

```
Here are 3 of my de-identified <clinic/progress/discharge> notes. Build a reusable template that matches my structure and phrasing.
Use [BRACKETED] placeholders for every patient-specific field. Include a short "pertinent negatives" checklist for <visit type>.
Leave out any clinical content that isn't a placeholder. Output plain text I can paste into an EHR smart phrase.
```

- **Setup:** De-identified sample notes. Save the result as a Project file (see [Deeper setups](#2-deeper-setups)).
- **Output:** One template made of headed sections and placeholders, plus a checklist. It shouldn't contain any clinical facts.
- Source: https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers

## 2. Deeper setups

### (a) Project: "Clinical reading and writing desk"

- **Setup:** Create a [Project](_shared-setup.md#projects). Upload your handout style guide, your note templates, your institution's formulary or protocol PDFs if policy allows, and the guidelines you cite most. Paste in the instructions from [section 6](#6-sample-project-instructions).
- **Use:** Run every quick win above inside this Project so Claude applies the same rules (citations, no doses, de-identification check) every time.
- **Output:** Answers that cite your uploaded documents by name and section, and that flag when your local protocol and the national guideline disagree.
- **PHI note:** Under a HIPAA-ready Enterprise org, Projects in chat are BAA-eligible. Projects in other products are not.
- Source: https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers

### (b) Custom skill: guideline comparison

Use it to compare two or more guidelines (for example, ACC/AHA against ESC) on the same question. It produces the same table every time. See [skills](_shared-setup.md#skills) and [../templates/SKILL.md](../templates/SKILL.md).

```markdown
---
name: guideline-compare
description: Compare clinical practice guidelines on one question. Use when the user asks how two or more guidelines differ, or uploads guideline PDFs for comparison.
---

# Guideline comparison

1. Confirm the clinical question, population and the guidelines being compared (society, year, version).
2. Read only from the uploaded PDFs or official society pages found via web search. Never compare from memory.
3. Output one table: Recommendation | Guideline A (class/level, section, page) | Guideline B (class/level, section, page) | Agree? 
4. Below the table: "Real disagreements" (max 5 bullets), "Differences only in wording" and "Not addressed by one side".
5. Quote recommendation text verbatim for every disagreement.
6. End with: "Comparison for education and protocol work. Not a recommendation for an individual patient."
7. Don't add doses unless they're quoted verbatim from a guideline, with the page number.
```

- **Output:** A sourced comparison table you can take to a protocol committee or teaching session.
- **PHI note:** Skills are listed as not covered under the BAA, so use this skill only on guideline documents, never on patient data.
- Source: https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers · https://github.com/anthropics/healthcare

### (c) Scheduled task: weekly literature watch

```
Every Monday 7am: using the PubMed connector, find papers published in the last 7 days on:
<topic 1>, <topic 2>, <topic 3>.
Keep only RCTs, meta-analyses, guidelines and large cohorts (n > 1,000). For each one: PMID, journal, one-line finding, why it might change practice (or "unlikely to change practice").
Max 10 items. If nothing qualifies, say "No practice-relevant papers this week."
```

- **Setup:** A [scheduled task](_shared-setup.md#scheduled-tasks) plus the PubMed connector. Contains no PHI, so the BAA doesn't apply. Use [../templates/scheduled-task-prompt.md](../templates/scheduled-task-prompt.md) as the scaffold.
- **Output:** A short Monday digest, which you triage in about 5 minutes.
- Source: https://claude.com/connectors/pubmed · https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers

## 3. Prompts that work in this field

```
Before answering, tell me what you'd need to know to answer this well and what you're unsure of. Then answer.
```
Why it's phrased this way: it brings uncertainty to the top first, instead of leaving it buried in a confident paragraph.

```
Summarize this paper as a journal club critique: PICO, randomization and blinding, attrition, primary vs secondary endpoints, absolute risk reduction and NNT where calculable, and the one bias most likely to change the result.
```
Why: naming the appraisal items stops Claude from giving you a plain summary when you asked for an appraisal.

```
Rewrite this discharge instruction at a grade 5 level in <language>. Keep every number exactly as written and list them back to me at the end.
```
Why: the read-back lets you confirm in seconds that no number changed in translation.

```
Here's the guideline PDF. Answer only from it, quoting section and page. If it doesn't address my question, say "not addressed" rather than filling in.
```
Why: restricting Claude to the document plus a named fallback reduces confident gap-filling.

```
I'm preparing for a family meeting about <topic>. Give me plain-language phrasing for the 3 hardest questions they're likely to ask, and the phrases to avoid.
```
Why: this is communication rehearsal, where Claude is strong and no clinical decision is delegated.

```
Turn these de-identified bullet points into a referral letter to <specialty>. Keep it under 250 words, state the specific question for the consultant in the first line, and mark anything you inferred with [CHECK].
```
Why: [CHECK] tags make inferred content visible before you sign.

```
List the drug-drug interactions documented in the FDA labels for <drug A> and <drug B>. Quote the label text and link each label. Don't rate severity yourself.
```
Why: this keeps Claude to label text and leaves severity judgment with you or your interaction database.

```
Explain <mechanism/test/condition> to a third-year medical student, then give 5 board-style questions with explanations.
```
Why: teaching content is general education, which the usage policy explicitly separates from individual advice.

```
Compare these two protocol drafts and list every change in criteria, thresholds or monitoring, in a table with old vs new text.
```
Why: a diff-style table catches silent threshold changes that prose summaries miss.

```
Draft a prior-auth appeal letter from these de-identified facts and the payer policy text I pasted. Cite the policy section for each argument. Leave the clinical justification for me to write in [CLINICIAN].
```
Why: Claude does the structure and the policy citations, while the medical necessity argument stays yours.

## 4. Guardrails

**Claude is not a clinical decision tool.** Anthropic's healthcare launch says Claude is designed to add contextual disclaimers, acknowledge uncertainty and "direct users to healthcare professionals for personalized guidance." Expect caveats. Don't try to remove them. Instead, state your role and purpose ("I'm the treating clinician, this is for my own reasoning") so Claude can drop the generic warnings that don't apply to you.

**Dosing guardrail Anthropic documents.** Anthropic publishes a `<medical_guidance>` system prompt block for applications. Under it, when a person says an over-the-counter medicine is for a child, Claude takes the dose only from the product label, confirms it "against an official copy of the same label, such as DailyMed" when web search is available, and otherwise "doesn't give a number from memory." It points the person to the label's dosing chart, a pharmacist or the child's doctor. The block explicitly excludes "a healthcare professional asking for work." Some model versions also decline dose or limit questions when the person mentions emotional distress. The honest way to work with this is to ask for the label, quoted, with the SET ID (see the label lookup quick win), and then apply your own judgment.

**Usage Policy for anything patient-facing.** Anthropic's Usage Policy (version effective 12 November 2026) classes "recommending, starting, stopping, or adjusting a treatment or medication, including dose" as high-risk. Before such a recommendation reaches an individual, "a qualified person must meaningfully review" it, with authority to change it, and the individual "must be clearly told that AI was used to produce it." General educational content, such as "how a condition or treatment works", is excluded. In practice, review and sign every handout or message that touches a specific patient. If anything you build sends AI output to patients, disclose that AI was used.

**HIPAA and the BAA.**
- Anthropic signs a BAA for the first-party API, Claude in Microsoft Foundry and Enterprise plans. Consumer plans (Free, Pro, Max) are handled in a separate article and don't have this coverage.
- On Enterprise, coverage starts only after the Primary Owner turns on HIPAA compliance in organization settings under "Data and privacy" and accepts the BAA.
- Covered in chat on a HIPAA-ready Enterprise org: chat, Projects (chat only), web search and memory.
- Not covered: connectors and MCP (third-party data flows), Claude in Chrome and Skills. Cowork is covered only in Claude Desktop with the HIPAA configuration, and cloud routines aren't available.
- Check the live page before relying on any of this, because the feature table changes.

**De-identification habits.** HIPAA allows two methods: Expert Determination, or Safe Harbor, which removes 18 identifier types and requires no actual knowledge that the remaining data could identify the person. Remove names, any geography smaller than a state, all date elements except year, ages over 89, phone and fax numbers, emails, SSNs, MRNs and plan IDs, device and account numbers, URLs and IPs, biometrics, full-face photos and any other unique code. Habits that help:
- Use age bands ("60s") and relative time ("day 3").
- Paste summaries, not exported notes.
- Never put PHI through a connector, a skill or Chrome.
- When unsure, check with your privacy officer, not Claude.

Source: https://www.anthropic.com/news/healthcare-life-sciences · https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices · https://www.anthropic.com/legal/aup · https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers · https://www.law.cornell.edu/cfr/text/45/164.514

## 5. Suggested connectors and skills

| Name | What for | Setup note | Source |
|---|---|---|---|
| PubMed connector | Literature search, abstracts, PMC full text | Anthropic-verified, no sign-in. Don't send PHI | https://claude.com/connectors/pubmed |
| ICD-10 Codes connector | Code lookup and validation for documentation and billing | Settings > Connectors. Claude Code: `anthropics/healthcare` plugin | https://claude.com/connectors/icd-10-codes |
| CMS Coverage connector | Medicare NCD/LCD lookups for prior auth and appeals | Covers Medicare Part B only, not Part D formularies | https://claude.com/resources/tutorials/using-the-cms-coverage-connector-in-claude |
| NPI Registry connector | Provider lookup for referrals and letters | Individual: Settings > Connectors > NPI Registry > Connect | https://academy.claude.com/tutorials/using-the-npi-registry-connector-in-claude |
| Web search | DailyMed/FDA label lookups, society guideline pages | BAA-eligible in chat on HIPAA-ready Enterprise | https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers |
| `healthcare` plugin (skills: clinical-note-extract, icd10-cm, prior-auth, fhir and others) | Coding, extraction and prior-auth workflows in Claude Code | `/plugin marketplace add anthropics/healthcare`, then `/plugin install healthcare@healthcare` | https://github.com/anthropics/healthcare |
| guideline-compare (custom, above) | Repeatable guideline tables | Upload as a skill. Guideline documents only | [Skills setup](_shared-setup.md#skills) |

For model choice on long guideline PDFs, see [choosing a model](_shared-setup.md#choosing-a-model). For more on connectors, see [../docs/04-connectors.md](../docs/04-connectors.md).

## 6. Sample Project instructions

```
You support a practicing clinician with reading, writing and preparation. You are not a clinical decision tool.

Rules:
- Never diagnose, choose treatment, or state a dose for a specific patient. For drug information, quote the current FDA label (DailyMed preferred) verbatim with section and SET ID; if you can't open the label, say so and give no number.
- Cite every factual claim: PMID, guideline name + section/page, or URL. If you can't cite it, mark it [UNSOURCED].
- Separate "established", "uncertain" and "my inference" explicitly.
- If pasted text contains likely identifiers (names, full dates, MRNs, addresses, phone numbers, ages over 89), stop and ask me to de-identify before continuing.
- Patient materials: default US grade 6 reading level, short sentences, "[CLINIC TO FILL]" for local instructions, no doses, and a list of every medical claim for my review.
- Differential discussions: widen the differential and list can't-miss diagnoses with the fastest way to exclude each; no final ranking, no treatment plan.
- Prefer my uploaded protocols and guidelines over general knowledge, and flag where they conflict with current national guidance.
- Be brief. Tables over prose for comparisons. No reassurance padding.
```

Last checked: 2026-10-20
