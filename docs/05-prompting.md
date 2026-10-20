# Prompting effectively

Current Claude models follow instructions precisely. That's the single most useful thing to know: vague prompts get vague answers; exact prompts get exact work. Think of Claude as a brilliant new colleague with zero context on your norms.

**Golden rule:** if a colleague with no context would be confused by your prompt, so will Claude.

## Core moves

1. **Be explicit about the output.** Format, length, audience, what "done" looks like. If you want ambitious, say "go beyond the basics, include every relevant feature."
2. **Give the why.** Claude generalises from reasons. *"Output is read by a screen reader, so no tables"* beats *"no tables."*
3. **Examples > adjectives.** 3–5 diverse examples in `<example>` tags steer tone/format far better than descriptions. Ask Claude to critique or extend your examples.
4. **XML tags to separate parts.** `<instructions>`, `<context>`, `<documents>`, `<input>`. Consistent names. Nest when natural.
5. **Role in the system prompt.** One sentence sharpens behaviour.
6. **Long inputs first, question last.** Up to ~30% better on multi-document tasks. For long docs, ask it to *quote the relevant bits first*, then answer.
7. **Positive instructions.** "Write flowing prose" rather than "no markdown." Match your prompt's style to the output you want (a markdown-free prompt yields less markdown).
8. **Imperative for actions.** "Suggest changes" → suggestions. "Make the changes" → edits.
9. **Self-check.** "Before finishing, verify against [criteria]." Reliable for code and maths (skip on Opus 5, which already over-verifies).
10. **Don't over-prompt.** Older "CRITICAL: you MUST…" language now causes over-triggering. Normal sentences are enough.

Template: [`templates/prompt-template.md`](../templates/prompt-template.md).

## Thinking

- Current models think *adaptively*: more on hard problems, less or none on easy ones. "Think thoroughly" > a hand-written step list.
- If it thinks too much: *"choose an approach and commit; don't revisit unless new information contradicts you."* On the API, lower `effort`.
- Don't ask the latest models to *write out* their reasoning in `<thinking>` tags — they may decline; rely on built-in thinking.

## Agentic / long tasks

- Ask for progress updates explicitly if you want narration; Fable 5.1 is terse between tool calls by default.
- Reversibility rule: free to edit/test locally; ask before destructive, force-push, or anything visible to others.
- Scope rule for coding: only what's asked; no extra abstractions or defensive code.
- Subagents: "parallel when independent; direct when sequential or context-heavy."
- Multi-session work: tests in `tests.json`, notes in `progress.txt`, git as checkpoints; new context windows start by reading those.

## Research prompts

- State success criteria. Ask for cross-source verification. For deep work: *"develop competing hypotheses, track confidence, keep a research-notes file."*

## Formatting controls

- Want plain text maths? Say "no LaTeX, use ^ and /."
- Want fewer bullets? Ask for prose paragraphs; reserve markdown for code and headings. (Fable 5.1 already formats lightly; don't over-suppress.)
- Want a doc/deck/sheet? Say so — it becomes an editable artifact you can download in the format you need.

## In the Claude app specifically

- **Projects** hold instructions + files + chats; put your standing context there instead of repeating it.
- **Memory / personal preferences** can hold tone and format rules ("British English, no emoji, always metric").
- Mid-conversation model switching is fine; earlier replies stay.
- `https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview` for the full guide; per-model pages (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5) list model-specific quirks.

## Lesser-known

- Claude can **improve your prompt**: paste it and ask "rewrite this as a production system prompt with examples and XML structure."
- Ask Claude to **generate the eval set** for your prompt before you tune it.
- On the API, `effort` + adaptive thinking replaced `budget_tokens`; prefill is gone — use structured outputs or tool enums for format locking.
- Mid-conversation **system messages** are the right way to change instructions in a long agent loop without invalidating thinking blocks.
- The "frontend aesthetics" block and the "investigate before answering" block from Anthropic's docs are both copy-paste ready: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
