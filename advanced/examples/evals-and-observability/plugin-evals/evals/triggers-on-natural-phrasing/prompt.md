---
description: The release-notes skill should fire on a natural request and produce grouped notes.
tags: [smoke]
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---
Can you turn these merged PR titles into release notes for customers?
- fix: crash when uploading files over 2GB (#412)
- feat: shared folders can now be password protected (#398)
- chore: bump lodash (#401)
- feat: dark mode for the web app (#377)
