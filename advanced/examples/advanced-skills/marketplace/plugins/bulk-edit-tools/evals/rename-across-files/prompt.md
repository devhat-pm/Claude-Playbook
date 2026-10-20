---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, smoke]
---

Rename getUser to fetchUser everywhere in this repo. It's used in src/api.py, src/main.py and src/jobs.py.
