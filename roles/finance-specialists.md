# Claude for finance specialists

For FP&A analysts, corporate finance, IB/PE/ER associates and controllers who already have Claude and want repeatable workflows: live-formula models, variance analysis, IC and board memos, sensitivity tables and SEC filing summaries. This is not investment advice tooling and it doesn't replace your review. Every number Claude produces is a draft until you tie it out. Basics such as Projects, connectors and privacy settings are in [_shared-setup.md](_shared-setup.md).

Three surfaces matter here, all on Pro, Max, Team and Enterprise:
- **Claude for Excel**, an add-in (listed as "Claude for Microsoft 365" on AppSource). It edits the open workbook, cites cells and keeps formula links intact. It does **not** support Excel Data Tables, macros or VBA.
- **Claude for Google Workspace** (beta), a sidebar in Sheets, Docs and Slides. It works on native Google files only, and each operation is capped at six minutes.
- **The Claude app** with code execution and file creation turned on. It reads an uploaded .xlsx (30 MB per file) and returns a new .xlsx with working formulas.

## 1. Quick wins

### Build a model with live formulas, not pasted values

Setup: install Claude for Excel from AppSource, open Excel, activate the add-in, sign in. In Sheets: Extensions > Claude > Open Claude. Put house conventions in the add-in's Settings > Instructions field. Excel instructions apply only in Excel.

```text
Build a 5-year revenue build on a new tab "Rev". Inputs on tab "Inputs" only: starting units,
unit growth by year, price, price escalator. Every cell on "Rev" must be a formula that references
"Inputs". No hardcoded numbers outside "Inputs". Blue font for inputs, black for formulas.
When done, list every cell you created with its formula, and confirm the count of hardcoded
constants outside "Inputs" is zero.
```

Output: an `Inputs` tab with about 8 blue cells, and a `Rev` tab where e.g. `C6 = B6*(1+Inputs!C4)`. The sidebar reply lists each formula with clickable cell citations. Change one input and check that the totals move.

Source: https://claude.com/docs/office-agents/excel · https://support.claude.com/en/articles/16951679-use-claude-in-google-docs-sheets-and-slides

### Variance analysis from an uploaded .xlsx

Setup: turn on Settings > Capabilities > "Code execution and file creation" (Team/Enterprise: an owner enables it under Organization settings). Upload the actuals vs budget export.

```text
Attached: FY26 actuals vs budget by cost center and GL account, monthly.
1. Before analysing, tell me: sheet names, row count, period columns, units (k or $), and the
   grand total of actuals and budget. I will check those against the source before you go on.
2. Then build a variance workbook: $ and % variance by line, YTD and current month,
   sign convention favourable = positive for revenue and negative for cost. Use formulas.
3. Flag lines with |variance| > 5% AND > $50k. For each, give the 3 largest GL drivers.
4. Draft commentary for flagged lines only. Write "driver unknown" rather than guess a cause.
```

Output: step 1 is a five-line inventory you check against the source, e.g. "Actuals total 41,872.3 (k)". After that, a downloadable `.xlsx` with a `Variance` tab (formulas), a `Flags` tab and about 10 lines of draft commentary, each tagged with the GL accounts behind it.

Source: https://support.claude.com/en/articles/12111783

### First draft of an IC or board memo from your materials

Setup: a Project ([_shared-setup.md#projects](_shared-setup.md#projects)) with the model output, management deck and your last approved memo uploaded as the format reference.

```text
Draft an investment committee memo using only the files in this Project. Follow the section
order and length of "IC memo - Project Alder (approved).docx". For every number, put the
source in brackets: [Model!Returns!F22] or [CIM p.14]. If a number isn't in the files, write
[MISSING: what's needed]. Don't round differently from the source. End with a list of the
5 weakest points in the thesis and the open diligence items. No recommendation language;
the deal team writes the recommendation.
```

Output: a 3–5 page memo draft where every figure carries a bracketed source and gaps show as `[MISSING: FY25 churn by cohort]`, followed by a risks and open items list. You write the recommendation.

Source: https://support.claude.com/en/articles/12111783 · https://github.com/anthropics/financial-services

### Sensitivity grid that recalculates

Setup: an existing model open in Claude for Excel or Sheets. Excel's What-If Data Table is unsupported in Claude for Excel, so ask for an explicit formula grid.

```text
On a new tab "Sens", build a 5x5 sensitivity of equity value to WACC (rows: 7.0% to 9.0%,
step 0.5%) and terminal growth (cols: 1.5% to 3.5%, step 0.5%). Do NOT use a What-If data
table. Write each cell as a formula that recomputes equity value from the model's cash
flows with that row's WACC and that column's g. Then check: the centre cell must equal
the base case on "DCF" exactly. Report the base case, the centre cell, and the difference.
```

Output: a 5x5 grid with row and column headers as input cells and conditional formatting, plus a reconciliation line such as "Base 1,284.6; centre 1,284.6; diff 0.0". A non-zero diff means a formula is wrong. Don't present the grid until the diff is zero.

Source: https://claude.com/docs/office-agents/excel · https://support.claude.com/en/articles/16951679-use-claude-in-google-docs-sheets-and-slides

### Summarise a 10-K or 10-Q straight from EDGAR

Setup: web search and fetch on in the app. Give Claude the filing URL from sec.gov. For anything scripted (Claude Code, a pipeline), EDGAR's fair-access rules require a `User-Agent` header with your company name and contact email, and cap traffic at 10 requests per second. The JSON APIs on data.sec.gov (`submissions/CIK##########.json`, `api/xbrl/companyfacts/...`) need no API key. If the fetch is blocked, download the filing and upload it.

```text
Fetch this filing: <sec.gov URL to the 10-K primary document>.
Give me: (1) segment revenue and operating income, current vs prior year, with the page or
section heading each number came from; (2) changes in revenue recognition, segments or
non-GAAP definitions vs the prior year; (3) new or expanded risk factors, quoted; (4) liquidity:
cash, debt maturities, covenants. Show units as reported (thousands vs millions). If you
could not read a section, say so. Do not fill it in from memory.
```

Output: four short sections with tables. Every figure is tagged like "(Item 7, Segment Results)" with units stated, and anything Claude couldn't read is listed as such.

Source: https://www.sec.gov/os/accessing-edgar-data · https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## 2. Deeper setups

### (a) A "Deal / Close" Project that enforces tie-outs

Setup: one Project per deal or per close cycle. Upload the model export, the source documents and a style reference memo. Paste the instructions from [section 6](#6-sample-project-instructions). Turn memory off for MNPI work or keep it Project-scoped ([_shared-setup.md#memory](_shared-setup.md#memory)). Run through [_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist) before you upload anything confidential.

```text
Using the Project files, produce the tie-out table for the draft memo I'm pasting below:
one row per number in the memo | value in memo | source file + location | value at source |
match (Y/N) | note. Flag any number with no source.
```

Output: a table with one row per figure, e.g. `EBITDA FY25 | 48.2 | Model.xlsx Summary!D14 | 48.2 | Y`. Mismatches and unsourced numbers sort to the top. Nothing goes into the deck until every row reads Y.

Source: https://claude.com/docs/office-agents/excel · https://support.claude.com/en/articles/12111783

### (b) A custom skill: `variance-commentary`

Setup: save as a folder with `SKILL.md` and upload it ([_shared-setup.md#skills](_shared-setup.md#skills), template in [../templates/SKILL.md](../templates/SKILL.md)). Skills you enable in Claude settings also apply inside Claude for Excel, PowerPoint and Word, and you can call one there by typing `/` in the sidebar. For prebuilt finance skills (`/comps`, `/dcf`, `/debug-model`, `/ic-memo`, `/earnings`), look at Anthropic's `financial-services` plugin repo before you write your own.

```markdown
---
name: variance-commentary
description: Writes month-end budget vs actual variance commentary from a variance table. Use when the user asks for variance commentary, flux analysis, or BvA explanations.
---
# Variance commentary
1. Restate: period, entity, units, and grand totals of actual and budget. Stop and ask if any is unclear.
2. Recompute every variance from actual and budget; report any line where the given variance differs.
3. Sign convention: favourable positive for revenue, negative for cost. State it in the output.
4. Comment only on lines above the threshold the user gives (default |5%| and $50k).
5. Each comment: driver, $ impact, one-off vs run-rate. If the driver isn't in the data, write "driver unknown - ask <owner>".
6. Never introduce a number that isn't in the input or computed from it. End with a list of computed figures.
```

Output: a fixed-format commentary block per flagged line and a "computed figures" appendix you can tick off.

Source: https://claude.com/docs/office-agents/connectors-and-skills · https://support.claude.com/en/articles/12512180-use-skills-in-claude · https://github.com/anthropics/financial-services

### (c) Scheduled task: weekly filings watch on your coverage list

Setup: in the Claude app, open Scheduled > New task ([_shared-setup.md#scheduled-tasks](_shared-setup.md#scheduled-tasks)), weekly, with web access. Keep it read-only and don't let it write to shared files until you've reviewed a few runs.

```text
For each ticker in this list: <AAPL, MSFT, ...>, check EDGAR for 8-K, 10-Q, 10-K, DEF 14A
and S-1/S-3 filings dated in the last 7 days. For each new filing: form type, filing date,
direct sec.gov link, and 3 bullets on what changed (guidance, leadership, capital structure,
material agreements). If nothing was filed, say "no new filings". Never infer content from
the filing title alone; if you couldn't open it, say so.
```

Output: a Monday digest with a table per ticker and links. Empty weeks say "no new filings" instead of padding. Treat it as a pointer to read the filing yourself, not a summary to forward.

Source: https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork · https://www.sec.gov/os/accessing-edgar-data

## 3. Prompts that work in this field

```text
Before you change anything in this workbook, trace how Summary!C42 is calculated back to its
inputs. List each precedent cell and formula. Don't edit.
```
Why: read-only tracing first catches broken links and plugs before you build on them. The Excel add-in returns clickable cell citations.

```text
Change the discount rate to 8% and update dependent calculations. Then list every cell whose
value changed by more than 1%, with old and new values.
```
Why: Claude for Excel keeps formula links when it changes assumptions. The change log lets you see the blast radius.

```text
Find every hardcoded number inside a formula on tabs DCF and Rev (e.g. =B5*1.05). List cell,
formula, and the input cell it should reference. Don't fix yet.
```
Why: buried constants are the most common model error. Separating "find" from "fix" keeps you in control.

```text
Find the source of the #REF! error on Summary and any circular references. Explain the root
cause, propose the fix, and wait for my OK.
```
Why: root-cause debugging is a documented strength. Waiting for your OK keeps edits reviewable.

```text
Recompute every subtotal and total in the attached P&L from its components. Report any line
where the stated total differs from the recomputed one by more than 0.1.
```
Why: this makes Claude check arithmetic, not just read it. It catches sign flips and missing rows in source exports.

```text
State the units, currency, period end, and fiscal-year convention for each table you used.
Flag any table where they differ from the others.
```
Why: thousands vs millions and FY vs CY mismatches cause most tie-out failures.

```text
Turn this variance table into board-level commentary: 5 bullets max, largest $ impact first,
each with driver and whether it recurs. Use only numbers in the table.
```
Why: the length cap and "only numbers in the table" stop it padding or importing outside figures.

```text
Rewrite this IC memo section for a skeptical committee member: list the three assumptions the
returns are most sensitive to and what each would have to be for IRR to fall below 15%.
```
Why: it turns sensitivity output into the question an IC will actually ask. It's analysis, not a recommendation.

```text
Compare revenue recognition and segment notes between these two 10-K URLs on sec.gov. Quote the
changed language side by side. Don't paraphrase the accounting policy.
```
Why: quotes are verifiable against the filing. Paraphrased accounting policy is where errors creep in.

```text
Build the three-statement links for this trial balance: net income to retained earnings, D&A
and working capital to cash flow, ending cash to the balance sheet. Add a check row that must
equal zero every period.
```
Why: a balance check row turns "looks right" into a pass/fail test you can see.

## 4. Guardrails

- **Not financial advice.** Anthropic's Usage Policy treats "a personalized recommendation to buy, sell, hold, or allocate among specific investment products" as high-risk. A qualified person must review it with authority to change it, and the recipient must be told AI was used. Expect Claude to caveat or decline personal "should I buy X" questions. The legitimate path is to ask for analysis (scenarios, comps, risks, sensitivities) and make the call yourself under your firm's process. Anthropic's finance repo says the same: outputs are drafts "for review by a qualified professional".
- **Verification is your job.** Anthropic's own Excel docs say Claude for Excel is not recommended for final client deliverables without human review or audit-critical calculations without verification. The habits:
  - tie every figure to a source location
  - recompute totals
  - check signs, units, currency and periods
  - reconcile sensitivity centre cells to the base case
  - never paste an unverified number into a deliverable
- **Claude caveats what it can't see.** If a filing didn't load or a page was truncated, it should say so. Your prompts should require that ("say so, don't fill in from memory"). Don't remove that line to get a cleaner-looking answer.
- **MNPI and confidentiality.** Treat any chat as a disclosure. Use a Team or Enterprise workspace for deal or pre-release data, keep one Project per deal, and follow your wall-crossing and info-barrier policies. Know the data settings ([_shared-setup.md#data-and-privacy-checklist](_shared-setup.md#data-and-privacy-checklist)): on Team and Enterprise, Anthropic doesn't train on your data by default. Consumer plans have their own model-training setting, so check it.
- **Add-in specifics for compliance.**
  - Claude for Excel deletes inputs and outputs within 30 days and keeps chat history in your local browser.
  - It does **not** inherit your org's custom retention settings and is **not** in Enterprise audit logs. Enterprise Compliance API coverage is in public beta.
  - The Google Workspace beta doesn't support Zero Data Retention or HIPAA use.
  - Ask compliance before you put regulated data through either add-in.
- **Prompt injection in third-party files.** Anthropic warns that external spreadsheets (vendor files, downloaded templates) can carry hidden instructions. Open untrusted files on a copy and read every confirmation prompt.

Source: https://www.anthropic.com/legal/aup · https://claude.com/docs/office-agents/excel · https://support.claude.com/en/articles/16951679-use-claude-in-google-docs-sheets-and-slides · https://claude.com/solutions/financial-services · https://github.com/anthropics/financial-services

## 5. Suggested connectors and skills

Anthropic's announcements and solutions page name these finance data partners. Check the connector directory in your workspace for what's actually available to you, and expect most to need your own subscription with the provider ("MCP access may require a subscription or API key from the provider").

| Name | What for | Setup note | Source |
|---|---|---|---|
| S&P Global (Capital IQ) | Fundamentals, comps, transactions | Named as a connector in Claude for Excel/M365 docs; needs a provider subscription | https://claude.com/docs/office-agents/connectors-and-skills |
| LSEG | Market data, pricing, analytics | Listed in the claude.com connector directory ("LSEG AI") | https://claude.com/connectors |
| Daloopa | Historical KPIs pulled from filings | Named in Claude for Excel/M365 docs | https://claude.com/docs/office-agents/connectors-and-skills |
| FactSet | Prices, fundamentals, consensus | Named as a pre-built connector on the solutions page; directory listing not confirmed (unverified) | https://claude.com/solutions/financial-services |
| PitchBook | Private company and deal data | Named in July 2025 and May 2026 announcements | https://www.anthropic.com/news/advancing-claude-for-financial-services |
| Morningstar | Fund and equity research data | Named in July 2025 and May 2026 announcements | https://www.anthropic.com/news/finance-agents |
| Moody's | Credit data (launched as an MCP app) | Named in May 2026 announcement | https://www.anthropic.com/news/finance-agents |
| Box / Egnyte | Data rooms, approved models | Enterprise content connectors; admin enables | https://claude.com/solutions/financial-services |
| `financial-analysis` plugin (anthropics/financial-services) | `/comps`, `/dcf`, `/lbo`, `/3-statement-model`, `/debug-model` | Cowork: Settings > Plugins > Add plugin, paste repo URL. Claude Code: `claude plugin marketplace add anthropics/financial-services` | https://github.com/anthropics/financial-services |
| `private-equity`, `equity-research`, `investment-banking` plugins | `/ic-memo`, `/returns`, `/earnings`, `/model-update`, `/cim` | Install after `financial-analysis` | https://github.com/anthropics/financial-services |
| Your `variance-commentary` skill | House-style BvA commentary | Section 2(b) | https://support.claude.com/en/articles/12512180-use-skills-in-claude |

Connector basics: [_shared-setup.md#connectors](_shared-setup.md#connectors). Model choice for long models and memos: [_shared-setup.md#choosing-a-model](_shared-setup.md#choosing-a-model).

## 6. Sample Project instructions

```text
You are supporting a finance professional. Your output is a draft for review, never a final
deliverable and never investment advice.

Numbers
- Use only numbers from the Project files, the open workbook, or sources I give you. If a number
  is missing, write [MISSING: what's needed]. Never estimate silently.
- Cite every figure: [file, tab!cell] or [document, page/section].
- State units, currency, period end and fiscal-year convention at the top of every output.
- Recompute totals and subtotals from components; report any difference > 0.1.
- Sign convention: favourable variance positive for revenue, negative for cost. Say so.

Spreadsheets
- Inputs on an Inputs tab in blue; every other cell is a formula referencing inputs.
- No hardcoded constants inside formulas. Add a check row (balance, cash, totals) that must be 0.
- Don't use What-If Data Tables or macros; build sensitivity grids as explicit formulas and
  reconcile the base-case cell to the model.
- Before editing a workbook, describe the change and wait for my OK.

Writing
- Memos: follow the structure of the approved example in this Project. Short sentences.
- No buy/sell/hold language or recommendations. List risks, sensitivities and open items instead.
- If you couldn't read a file, page or filing, say so explicitly.

Confidentiality
- Treat everything in this Project as confidential and possibly MNPI. Don't fetch external URLs
  that include deal names or company identifiers unless I ask.
```

Last checked: 2026-10-20
