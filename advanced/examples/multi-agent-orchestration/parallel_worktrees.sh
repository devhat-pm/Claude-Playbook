#!/usr/bin/env bash
# Fan out independent tasks to headless Claude Code sessions, one git worktree each,
# then collect results and show what each branch changed so a reviewer can merge.
#
# tasks file format, one task per line (blank lines and # comments ignored):
#   <name>|<model alias>|<prompt>
# e.g.
#   fix-date-parse|sonnet|Fix the timezone bug in src/dates.py; run pytest tests/test_dates.py until green; commit.
#   bump-lint|haiku|Upgrade ruff config to the new rule names in pyproject.toml; run ruff; commit.
#
# Usage:
#   ./parallel_worktrees.sh tasks.txt [max_parallel=3] [budget_usd_per_task=2]
#   DRY_RUN=1 ./parallel_worktrees.sh tasks.txt      # print commands only
#   REVIEW=1  ./parallel_worktrees.sh tasks.txt      # add an Opus read-only review of all branches
#
# Works with macOS bash 3.2 (no wait -n). Requires git, claude; jq optional.
set -euo pipefail

TASKS="${1:?usage: $0 tasks.txt [max_parallel] [budget_per_task]}"
MAX_PAR="${2:-3}"
BUDGET="${3:-2}"
OUT=".claude/fanout-results"
mkdir -p "$OUT"

run_task() {
  local name="$1" model="$2" prompt="$3"
  local full="$prompt

Constraints: you are in an isolated worktree. Touch only files this task needs.
Commit your work on this branch with a message starting '$name:'. Do not push.
Finish with a 3-line summary: what changed, how you verified it, anything left undone."
  if [ -n "${DRY_RUN:-}" ]; then
    echo "claude -p <prompt> --worktree $name --model $model --output-format json --max-turns 40 --max-budget-usd $BUDGET --permission-mode acceptEdits"
    return 0
  fi
  claude -p "$full" \
    --worktree "$name" \
    --model "$model" \
    --output-format json \
    --max-turns 40 \
    --max-budget-usd "$BUDGET" \
    --permission-mode acceptEdits \
    > "$OUT/$name.json" 2> "$OUT/$name.err" || echo "{\"is_error\":true,\"name\":\"$name\"}" > "$OUT/$name.failed"
}

names=()
while IFS='|' read -r name model prompt; do
  case "$name" in ''|'#'*) continue ;; esac
  while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAX_PAR" ]; do sleep 2; done
  echo ">> start $name ($model)"
  run_task "$name" "$model" "$prompt" &
  names+=("$name")
done < "$TASKS"
wait
[ -n "${DRY_RUN:-}" ] && exit 0

echo
echo "== results =="
total=0
for n in "${names[@]}"; do
  f="$OUT/$n.json"
  if [ -s "$f" ] && command -v jq >/dev/null; then
    cost=$(jq -r '.total_cost_usd // 0' "$f")
    printf '%-24s $%-8s %s\n' "$n" "$cost" "$(jq -r '.result // "" | split("\n") | .[-3:] | join(" / ")' "$f" | cut -c1-120)"
    total=$(python3 -c "print(round($total + $cost, 4))")
  else
    printf '%-24s %s\n' "$n" "no JSON result (see $OUT/$n.err)"
  fi
done
echo "total ~\$$total"

echo
echo "== branches (default name worktree-<name>) =="
base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo main)
for n in "${names[@]}"; do
  b="worktree-$n"
  if git rev-parse --verify -q "$b" >/dev/null; then
    echo "-- $b vs $base"
    git log --oneline "$base..$b" | head -5
    git diff --stat "$base...$b" | tail -1
  fi
done

# Overlap check: files touched by more than one branch will conflict on merge.
echo
echo "== files touched by more than one branch =="
for n in "${names[@]}"; do
  git rev-parse --verify -q "worktree-$n" >/dev/null && git diff --name-only "$base...worktree-$n"
done | sort | uniq -d

if [ -n "${REVIEW:-}" ]; then
  branches=""
  for n in "${names[@]}"; do branches="$branches worktree-$n"; done
  claude -p "Review these branches against $base:$branches. For each: run git diff $base...<branch>, check it does only what its commit says, flag risky changes and overlaps, and give a merge order. Do not modify anything." \
    --model opus --permission-mode plan --output-format text
fi

echo
echo "Merge: git merge --no-ff worktree-<name> (in the order above)."
echo "Cleanup (-p runs are not auto-removed): git worktree remove .claude/worktrees/<name> && git branch -d worktree-<name>"
