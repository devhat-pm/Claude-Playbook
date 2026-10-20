# Contributing

This repo goes stale fast. Rules to keep it useful:

1. **Date your claims.** Every doc has a "last reviewed" line at the top of README; bump it when you verify a page.
2. **Link the source.** Product facts (plan availability, model names, limits) must cite an official page: platform.claude.com/docs, code.claude.com/docs, support.claude.com, anthropic.com/news.
3. **Hidden gems need a repro.** For anything in `docs/00-hidden-gems.md`, include the phrasing that triggers it so others can confirm.
4. **Paraphrase, don't paste** official docs.
5. **One idea per PR.** Easier to review, easier to revert when a product changes.

## Quick refresh with Claude

Paste this into Claude:

> Read this repo. For each doc, check the cited official pages and list anything that's changed since the "last reviewed" date. Propose edits as a diff.

## Structure

```
README.md              index + product map
docs/00-hidden-gems.md lesser-known capabilities (keep this the best page)
docs/01..10-*.md       one topic each; end with a "Lesser-known" section
templates/             copy-paste starters
```
