# CLAUDE.md — <project name>

Onboarding notes for Claude Code. Keep this short; Claude reads the code itself.

## What this is
One paragraph: what the project does, who uses it, the main entry points.

## Commands
- Install: `pnpm install`
- Dev: `pnpm dev`
- Test: `pnpm test` (run `pnpm test -- --watch` while iterating)
- Lint/format: `pnpm lint && pnpm format`
- DB migrations: `pnpm db:push` — never hand-edit SQL in `migrations/`

## Conventions that differ from defaults
- TypeScript strict; no `any` without a comment.
- Server code lives in `apps/api`, UI in `apps/web`; shared types in `packages/types`.
- Errors: throw `AppError` subclasses; never swallow.
- Commit messages: Conventional Commits.

## Gotchas
- `.env.local` is required; copy from `.env.example`.
- Tests hit a local Postgres on port 5433, not 5432.

## Never
- Don't push to `main`; open a PR.
- Don't delete or weaken tests to make them pass — tell me if a test is wrong.
- Don't run `git push --force`, `rm -rf`, or anything visible to others without asking.

## Scope
Only change what's asked. No new abstractions, no defensive code for impossible cases, no docstrings on untouched code.

## See also
@docs/architecture.md
