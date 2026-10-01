#!/bin/bash
# Find board writes that went somewhere other than the canonical board (EVO-0060, family wrong-board-file):
# cc-t3 wrote three hand-offs into an untracked `app-lighting` file in its own worktree, so the outer loop saw
# nothing and recorded it as "did not post". Lists, for every lane worktree next to this repo:
#   * any file named app-lighting* outside .octos/boards/ (untracked stray copies), and
#   * an uncommitted change to the worktree's own tracked .octos/boards/app-lighting.md (a lane appending there).
# Exit 1 when anything is found. Run it in the patrol.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd)
WS=$(dirname "$REPO")
found=0
for wt in "$WS"/westlake-harness-*/; do
  [ -e "$wt/.git" ] || continue
  while IFS= read -r f; do
    echo "STRAY board copy: $f ($(wc -l < "$f" | tr -d ' ') lines, modified $(date -r "$f" +%H:%M:%S))"; found=1
  done < <(find "$wt" -maxdepth 2 -name 'app-lighting*' -type f -not -path '*/.octos/boards/*' 2>/dev/null)
  if git -C "$wt" diff --quiet -- .octos/boards/app-lighting.md 2>/dev/null; then :; else
    echo "STRAY board append: ${wt}.octos/boards/app-lighting.md has uncommitted changes in the lane worktree"; found=1
  fi
done
[ $found = 0 ] && echo "no stray board writes"
exit $found
