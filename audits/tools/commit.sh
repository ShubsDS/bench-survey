#!/bin/bash
# Commit one audit folder without touching anyone else's work.
#
#   audits/tools/commit.sh audits/<benchmark> "message"
#
# Several agents share this working tree. This script stages and commits only the
# given folder (git commit --only), and retries when another agent holds the index
# lock. Never run `git add -A`, `git commit -a`, `git checkout`, `git stash`,
# `git reset` or `git rebase` in this repository.
set -u
dir="${1:?usage: commit.sh <folder> <message>}"
msg="${2:?usage: commit.sh <folder> <message>}"
root="$(git rev-parse --show-toplevel)" || exit 1
cd "$root" || exit 1
case "$dir" in audits/*) ;; *) echo "refusing: folder must be under audits/" >&2; exit 2 ;; esac
[ -d "$dir" ] || { echo "no such folder: $dir" >&2; exit 2; }

# Refuse files over 2 MB: data stays in the ignored data/ folder.
big="$(find "$dir" -type f -size +2M -not -path '*/data/*' -not -path '*/inference/cache/*' | head -5)"
if [ -n "$big" ]; then echo "refusing: files over 2 MB (move to data/ or summarise):" >&2; echo "$big" >&2; exit 3; fi

for attempt in $(seq 1 30); do
  if git add -- "$dir" 2>/dev/null; then
    if git diff --cached --quiet -- "$dir"; then echo "nothing to commit in $dir"; exit 0; fi
    if git commit -q --only -m "$msg

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "$dir" 2>/dev/null; then
      git log --oneline -1
      exit 0
    fi
  fi
  sleep $(( (RANDOM % 4) + 1 ))
done
echo "commit failed after 30 attempts (index lock?)" >&2
exit 1
