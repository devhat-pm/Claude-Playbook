# Claude in Chrome

A Chrome extension that lets Claude read, click, type and navigate websites *with your logins*. Paid plans (Pro, Max, Team, Enterprise). Launch from the Chrome side panel, from the Claude desktop app (as a connector), or from Claude Code.

Chrome only — not other Chromium browsers, not mobile. Usage counts against your normal plan limits.

Docs: https://support.claude.com/en/articles/12012173 · Safety: https://support.claude.com/en/articles/12902428 · Permissions: https://support.claude.com/en/articles/12902446

## Good uses

- Anything behind a login with no connector: internal admin panels, SaaS back-ends, bank/vendor portals, government forms.
- Filling and submitting forms, multi-step flows ("apply the discount code, pick the Tuesday slot, check out").
- Reading pages that plain web fetch can't render (JS-heavy dashboards).
- **Build-test-verify with Claude Code**: Claude writes the feature, opens it in your browser, reads console/network errors, screenshots, fixes, repeats.
- Recording a **GIF** of a flow for a bug report or a how-to.
- Research across sites where you're already signed in.

## Safety model (read this once)

- Per-site permissions: you decide which sites Claude may act on, and whether it may act autonomously or must ask.
- Claude pauses for confirmation on sensitive actions (purchases, sending messages, deleting) unless you've granted otherwise.
- **Prompt injection** is the real risk: a web page can contain text that tries to instruct Claude. Classifiers help, but keep Claude off sites you don't trust, and report odd behaviour from the side panel.
- Avoid dialogs (alerts/confirms) that block automation; Claude is trained to steer around them.
- Enterprise admins control availability (admin controls article).

## Built-in browser vs Claude in Chrome

| | Claude in Chrome | Built-in browser (desktop app pane) |
|---|---|---|
| Logins | Your real Chrome sessions | Its own, separate |
| Where | Your Chrome | Pane inside Claude desktop |
| Choose with | "Preferred browser" setting, or ask by name | same |

Pick Chrome when the task needs your existing sign-ins; pick the built-in pane when you'd rather Claude not touch your real browser.

## Lesser-known

- Say *"use the built-in browser"* / *"use Chrome"* to override your default for one task.
- Claude can read **console logs and network requests** — faster debugging than screenshots.
- It can run **JavaScript on the page** when you allow it (scrape a table into a sheet, say).
- It works in a *new tab* in your session and can see your open tabs' titles to pick context.
- Scheduled tasks that need your browser must be marked as requiring your computer, and only run while the desktop app is open.
- Troubleshooting: update Chrome, update the desktop app, toggle the connector off/on. https://support.claude.com/en/articles/12902405
