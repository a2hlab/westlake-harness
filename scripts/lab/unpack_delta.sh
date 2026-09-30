#!/bin/bash
# Apply a folder made by pack_delta.sh on the new control Mac, after unpack_airdrop.sh (env.md §5).
#
#   bash <folder>/unpack_delta.sh <workspaces root>       e.g. bash ~/Downloads/_airdrop-delta/unpack_delta.sh ~/alvin
#
# 1 verifies the folder; 2 unpacks delta (new packages, runs) then the boards (newest wins); 3 repairs worktree
# .git links of every repo checkout under <root> and ~/orca; 4 fetches a2hlab/origin and fast-forwards each clean
# checkout whose branch exists there (dirty or diverged checkouts are listed, never touched).
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "${1:?usage: unpack_delta.sh <workspaces root>}" && pwd -P)
(cd "$SRC" && shasum -a 256 -c --quiet SHA256SUMS) && echo "all files match SHA256SUMS"
for m in delta octos-state; do
  [ -e "$SRC/$m.tar.zst.part00" ] || continue
  cat "$SRC/$m.tar.zst".part* | zstd -q -d --long=31 | tar -xf - -C "$ROOT"; echo "$m -> $ROOT"
done
mains=(); for d in "$ROOT"/* "$ROOT"/01.OH61AOSP16/real-work "$HOME"/orca/*; do [ -d "$d/.git" ] && mains+=("$d"); done
for m in "${mains[@]}"; do
  paths=$(git -C "$m" worktree list --porcelain | awk '/^worktree /{print substr($0,10)}' | tail -n +2)
  [ -n "$paths" ] && git -C "$m" worktree repair $paths 2>/dev/null || true
done
echo "worktrees repaired in ${#mains[@]} repos"
for m in "${mains[@]}"; do
  remote=$(git -C "$m" remote | grep -x a2hlab || git -C "$m" remote | head -1)
  git -C "$m" fetch -q "$remote" 2>/dev/null || { echo "fetch failed: $m ($remote) -- network?"; continue; }
  git -C "$m" worktree list --porcelain | awk '/^worktree /{p=substr($0,10)} /^branch /{print p "\t" substr($2,12)}' |
  while IFS=$'\t' read -r wt br; do
    git -C "$wt" rev-parse -q --verify "refs/remotes/$remote/$br" >/dev/null || continue
    [ "$(git -C "$wt" rev-parse HEAD)" = "$(git -C "$wt" rev-parse "$remote/$br")" ] && continue
    if [ -n "$(git -C "$wt" status --porcelain --untracked-files=no)" ]; then echo "dirty, left alone: $wt"; continue; fi
    git -C "$wt" merge -q --ff-only "$remote/$br" 2>/dev/null && echo "fast-forwarded $wt ($br)" || echo "diverged, left alone: $wt ($br)"
  done
done
