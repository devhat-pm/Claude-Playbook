# Biologists and life scientists

For bench scientists, bioinformaticians, postdocs and PIs who already use Claude and want concrete workflows: paper triage, protocol drafting, CSV-to-figure analysis, primer sanity checks, grant writing. This guide does not cover clinical or diagnostic use, and it is no substitute for your lab's validated tools or your biosafety committee. For the basics (Projects, connectors, skills, privacy), see [_shared-setup.md](_shared-setup.md).

Anthropic ships two official things for this field: **Claude for Life Sciences**, a set of connectors and skills that work in claude.ai and Claude Code, and **Claude Science**, a separate beta desktop app that runs code in a local sandbox and has 60+ scientific database connectors built in. Everything below works in plain claude.ai unless it says otherwise.

## 1. Quick wins

### Triage a stack of papers into a decision table

```text
Here are [N] papers (attached / or: search PubMed for "<query>" since 2024).
For each, give one row: PMID or DOI | organism/system | n and design |
main claim (one line) | strongest evidence | biggest weakness | relevance to
my question (High/Med/Low) with one-line reason.
My question: <your question>.
Only use what is in the abstract or full text you actually read. If you only
had the abstract, say "abstract only" in the row. Then list the 3 I should
read in full first, and why.
```

- **Setup:** Attach PDFs, or turn on the PubMed connector (Settings > Connectors > PubMed > Connect). See [_shared-setup.md#connectors](_shared-setup.md#connectors).
- **Output:** A markdown table, one row per paper, plus a short "read first" list. The connector gets full text only for PubMed Central articles. Everything else is abstract only, so check the "abstract only" flags.
- Source: https://academy.claude.com/tutorials/using-the-pubmed-connector-in-claude · https://www.anthropic.com/news/claude-for-life-sciences

### CSV to stats to figure, with assumptions stated

```text
Attached: <file>.csv. Columns: <describe>. Design: <e.g. 3 conditions,
n=4 biological replicates each, 3 technical replicates averaged>.
1. Load it and print shape, dtypes, missing values and per-group n.
2. Before testing anything, state the test you propose and its assumptions
   (independence, normality, equal variance). Check each assumption with a
   plot or test and report the result.
3. Run the test. Report the effect size with 95% CI, the exact p-value and
   the multiple-comparison correction used.
4. Plot every data point (no bar-only charts) and save a PNG and an SVG.
5. Give me the full Python code so I can rerun it.
Do not drop outliers unless I say so; flag them instead.
```

- **Setup:** Turn on code execution and file creation (Settings > Capabilities on Free, Pro and Max; on Team and Enterprise an owner controls it). Files can be up to 30 MB. For long or heavy analyses, Claude Science runs Python and R locally and keeps a provenance record.
- **Output:** A short data summary, an assumptions table (assumption | check | result), test results, a downloadable PNG and SVG, and a code block.
- Source: https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude · https://claude.com/docs/claude-science/overview

### Primer and oligo sanity check

```text
Check these primers. Use code to compute, and show the method and the
parameters you used (Tm model, Na+/Mg2+ and oligo concentration).
F: 5'-...-3'
R: 5'-...-3'
Template (optional): <paste or attach FASTA>
For each primer: length, GC%, Tm, 3' GC clamp, runs of 4+ identical bases,
hairpin and self-dimer risk, and heterodimer risk for the F/R pair.
If I gave a template, confirm both primers bind on opposite strands and give
the amplicon size. Flag anything outside: 18-25 nt, 40-60% GC, Tm 55-65 C,
F/R Tm within 3 C.
```

- **Setup:** Code execution on. Paste sequences as plain text or FASTA.
- **Output:** A per-primer table with flags. Treat it as a first pass. Tm values depend on the model and salt correction, and Claude is not running a specificity search. **Always confirm in a dedicated tool**: Primer-BLAST for specificity against the genome, and your oligo vendor's analyzer for Tm and dimers at your buffer conditions.
- Source: https://www.ncbi.nlm.nih.gov/tools/primer-blast/ · https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude

### Turn bench notes into a protocol draft

```text
Turn these notes into a protocol in our format: Purpose, Materials (with
catalogue numbers where I gave them; write "TBD" otherwise), Safety,
Step-by-step (numbered, one action per step, volumes and times explicit),
Critical steps, Expected results, Troubleshooting.
Do not invent concentrations, incubation times or reagents. Where something
is missing, write [MISSING: ...] in place.
Notes: <paste>
```

- **Setup:** Optional Benchling connector so Claude can pull notebook entries and link back to them. An admin adds it, then users sign in through Settings > Connectors.
- **Output:** A formatted protocol with `[MISSING: ...]` markers. Expect a gap list longer than you'd like. That's the point.
- Source: https://claude.com/connectors/benchling · https://claude.com/resources/tutorials/using-the-benchling-connector-in-claude

### Stress-test a Specific Aims page

```text
Act as a study-section reviewer for <NIH R01 / ERC / Wellcome / other>.
Score this Aims page on significance, innovation and approach using that
funder's criteria. Then list: the 3 weaknesses most likely to sink it, any aim
that depends on another aim succeeding, claims without preliminary data, and
jargon a non-specialist reviewer will trip on. Do not rewrite it yet.
<paste Aims page>
```

- **Setup:** None. Attach the funder's call text or review criteria if you have them, because Claude's knowledge of current funder rules may be out of date.
- **Output:** A score-style critique and a ranked weakness list. Ask for a rewrite in a second turn, once you've decided which criticisms to accept.
- Source: https://support.claude.com/en/articles/8241126-upload-files-to-claude

## 2. Deeper setups

### (a) A "Lab methods and analysis" Project

- **Setup:** Create a Project ([_shared-setup.md#projects](_shared-setup.md#projects)). Upload your lab's SOP template, a house statistics policy (default tests, alpha, how you handle replicates), the reagent list, and 2–3 protocols you consider well written. Paste the instructions from section 6.
- **Use:** Run every protocol draft, analysis and methods section in this Project, so formatting and stats defaults stay consistent without re-prompting.

```text
Using our SOP template and stats policy in this Project, draft the methods
section for the experiment in the attached analysis notebook. Match the
tense and level of detail of the example protocols. List every value you
took from the notebook vs. from Project files.
```

- **Output:** A methods paragraph in house style, followed by a provenance list (value -> source file).
- Source: https://support.claude.com/en/articles/9517075-what-are-projects

### (b) A custom skill: qPCR delta-delta-Ct analysis

- **Setup:** Create a skill folder and upload it as a zip (Settings > Capabilities > Skills) or import it in Claude Science (Settings > Skills > Add skill). See [_shared-setup.md#skills](_shared-setup.md#skills). Code execution must be on.

```markdown
---
name: qpcr-ddct
description: Analyses qPCR Ct exports with the delta-delta-Ct method and produces a fold-change table and plot. Use when the user uploads a qPCR/Ct export, asks for relative expression, fold change, or ddCt.
---

# qPCR ddCt analysis

## Inputs
- Ct export (CSV/XLSX): sample, target, Ct, and optionally well and plate.
- Ask for these if not given: reference gene(s), control condition, and
  which samples are biological vs technical replicates.

## Workflow
- [ ] 1. Report Ct range per target; flag Ct > 35 and "Undetermined".
- [ ] 2. Flag technical replicates with SD > 0.3 Ct. Do not drop them silently.
- [ ] 3. Average technical reps, then compute dCt = Ct(target) - Ct(ref).
       With 2+ reference genes, use the mean of their Cts.
- [ ] 4. ddCt = dCt(sample) - mean dCt(control); fold change = 2^-ddCt.
- [ ] 5. Do stats on dCt values (not on fold change). State the test and n.
- [ ] 6. Plot per-replicate points with the mean; log2 y-axis.

## Rules
- State the assumption of ~100% primer efficiency. If the user supplies
  efficiencies, use the Pfaffl method and say so.
- Never invent a reference gene or control.
- End with: assumptions, flagged wells, and the code used.
```

- **Output:** A QC flags table, a fold-change table (target | condition | mean fold change | 95% CI | n), a PNG plot and the code.
- Source: https://support.claude.com/en/articles/12512180-use-skills-in-claude · https://claude.com/docs/claude-science/connectors-and-skills

### (c) A scheduled weekly literature watch

- **Setup:** PubMed connector on. Create a scheduled task ([_shared-setup.md#scheduled-tasks](_shared-setup.md#scheduled-tasks)). Each run starts fresh, so the prompt has to work on its own.

```text
Every Monday 07:30. Search PubMed for papers from the last 7 days matching:
("<gene/pathway>"[tiab] OR "<synonym>"[tiab]) AND ("<organism>" OR
"<model system>"). Also check bioRxiv if that connector is available.
For each hit: PMID/DOI, title, one-line finding, method used, and
"why it matters to us" against these lab interests: <3-5 bullets>.
Sort by relevance. Max 15 items. If nothing relevant, say "No relevant
papers this week" and stop. Do not summarise papers you could not open
beyond the abstract; label them "abstract only".
```

- **Output:** A short ranked digest delivered as a notification each week. Check the query on its first two runs. PubMed rate limits and abstract-only coverage both show up there.
- Source: https://support.claude.com/en/articles/13854387 · https://academy.claude.com/tutorials/using-the-pubmed-connector-in-claude

## 3. Prompts that work in this field

```text
Before analysing, restate my experimental design back to me: unit of
replication, what is paired, what is nested. Wait for my confirmation.
```
Why it's phrased this way: pseudoreplication (treating wells or cells as n) is the most common analysis error. Confirming the design first catches it.

```text
Give me two analyses of this dataset: the one you'd choose and the one a
skeptical reviewer would demand. Show where they disagree.
```
Why: it surfaces how sensitive your result is to the choice of analysis before a reviewer does.

```text
For each claim in this draft results section, mark: supported by a figure
(which), supported by a citation (which), or unsupported.
```
Why: it ties every sentence to evidence. That's the fastest way to find overreach.

```text
Summarise this paper's methods only as a checklist I could use to reproduce
it. Mark anything not specified as [NOT REPORTED].
```
Why: it shows reproducibility gaps instead of hiding them under smooth prose.

```text
Here is my plate layout and the reader export. Map wells to conditions,
show the mapping table first, then analyse.
```
Why: most errors come from mis-mapping wells. Seeing the table first lets you catch them.

```text
Convert this protocol from 6-well to 96-well format. Show the scaling
factor for each volume and flag steps that don't scale linearly.
```
Why: wash steps, cell seeding density and evaporation don't scale linearly. Asking for flags forces Claude to think about them.

```text
Write a lay summary (Grade 8 reading level, 150 words) of this abstract for a
patient advocacy group. Keep every hedge in the original.
```
Why: simplifying a summary tends to drop hedges ("may", "in mice"). Asking to keep them prevents that.

```text
Draft a response-to-reviewers table: reviewer comment | our response |
change made (page/line) | status. Be concise and non-defensive.
```
Why: reviewers and editors expect this format, and asking for "status" makes you track what's still open.

```text
List every assumption you made in this analysis that I did not state. Rank
by how much the conclusion would change if the assumption were wrong.
```
Why: hidden defaults (two-sided tests, equal variance, imputation) become explicit decisions you can review.

```text
I need a figure legend for this plot. Include n, what error bars show, the
test and the exact p-values. Ask me for anything you can't see in the file.
```
Why: incomplete legends are a frequent reviewer complaint, and "ask me" stops Claude from guessing n.
## 4. Guardrails

Biology is the one field where Claude applies safeguards beyond its usual judgment, and they are tuned to err on the side of declining. What to expect:

- Fable 5.1 carries additional biology safeguards. Anthropic doesn't recommend it for professional biology research; biology-flagged requests may be routed to another model or declined. Opus 5.5 and Sonnet 5.5 are the practical defaults for day-to-day lab and analysis work.
- Dual-use boundaries: anything resembling enhancement, synthesis, acquisition or weaponisation of pathogens/toxins is declined regardless of framing or credentials. Reframing ("for a review", "hypothetically") doesn't change the answer and wastes turns.
- What stays fully available: literature synthesis, statistics and plotting, protocol formatting and clarity edits, experimental design critique, sequence and primer sanity checks on sequences you supply, grant and manuscript writing, teaching materials.
- For teams doing legitimate work that keeps hitting the line: Anthropic runs a Life Sciences Verification Program (beta) for Team, Enterprise and API customers, and Claude Science is the research workbench built for this use. Claude Mythos 5.1 (Fable without the extra safeguards) is only available to vetted organisations.
- Honesty habit: Claude will not fabricate a citation, but it can mis-remember one. Verify every DOI before it goes in a manuscript.

Sources: https://support.claude.com (search "Life Sciences Verification"), https://www.anthropic.com/glasswing, https://platform.claude.com/docs/en/models/fable-5-1/overview

## 5. Suggested connectors and skills

| Need | Use |
|---|---|
| Papers and PDFs | Google Drive / Zotero-style connector if available; otherwise attach PDFs, Claude reads them in the sandbox |
| Data analysis | Built-in sandbox (pandas, scipy, matplotlib) — attach CSV/XLSX; use the `xlsx` skill for deliverables |
| Lab notebook / protocols | Docs artifacts; a `protocol-formatting` skill with your lab's template |
| Literature monitoring | Research + a weekly scheduled task writing to a Sheets literature matrix |
| Figures | Inline charts for exploration; Design artifact for publication-ready layouts |
| Team requests | Claude Tag in Slack |

## 6. Sample Project instructions

```text
You are assisting a <field> research group. Default model guidance: use Opus 5.5 for analysis and writing.
- Stats: always state the test used, assumptions checked, n, effect size and CI; show the code.
- Literature: never cite from memory; search, then cite DOI and year. Flag retractions.
- Protocols: format to our template (attached); never alter reagent amounts or steps without flagging the change in bold.
- Writing: Nature-style concision; active voice; define abbreviations once.
- Decline-and-redirect: if a request touches dual-use biology, say so in one line and offer the nearest safe help.
```

Last checked: 2026-10-20
