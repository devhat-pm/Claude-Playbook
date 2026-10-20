#!/usr/bin/env bash
# Seeds the empty run workspace. Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
mkdir -p src
printf 'def getUser(uid):\n    return {"id": uid}\n' > src/api.py
printf 'from api import getUser\nprint(getUser(1))\n' > src/main.py
printf 'from api import getUser\n\ndef job():\n    return getUser(2)\n' > src/jobs.py
git init -q && git add -A && git -c user.email=e@x -c user.name=eval commit -qm fixture
