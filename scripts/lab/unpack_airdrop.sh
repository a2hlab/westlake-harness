#!/bin/bash
# Unpack a folder made by pack_airdrop.sh on a new control Mac (env.md §5).
#
#   bash <folder>/unpack_airdrop.sh <workspaces root>      e.g. bash ~/Downloads/_airdrop-20260930/unpack_airdrop.sh ~/alvin
#
# 1 verifies every file against SHA256SUMS; 2 clones every repo from its bundle and points the remote back at
# GitHub; 3 recreates the worktrees; 4 unpacks the lab state (boards last, so the newest board wins); then
# repoints absolute symlinks that targeted the old machine's tree (old paths come from meta.env).
# <root> is the workspaces dir: the repo lands in <root>/westlake-harness and the lab scripts find <root> by
# themselves (nearest ancestor holding westlake-inputs/), so no symlinks and no user-specific paths.
# Re-running skips what is already there. Needs zstd (brew install zstd) and ~200 GB free.
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
ROOT=$(mkdir -p "${1:?usage: unpack_airdrop.sh <workspaces root>}" && cd "$1" && pwd -P)
for t in zstd git shasum tar; do command -v $t >/dev/null || { echo "missing $t (brew install $t)"; exit 2; }; done

echo "== 1/4 verify"
(cd "$SRC" && shasum -a 256 -c --quiet SHA256SUMS) && echo "all files match SHA256SUMS"

mkdir -p "$HOME/orca"
dest() { case $1 in ROOT/*) echo "$ROOT/${1#ROOT/}";; *) echo "$HOME/$1";; esac; }
echo "== 2/4 repos"
while IFS=$'\t' read -r name d ref url; do
  p=$(dest "$d")
  if [ -e "$p/.git" ]; then echo "have $name at $p"; continue; fi
  if [ -d "$p" ] && [ -n "$(/bin/ls -A "$p")" ]; then echo "REFUSE: $p exists, is not a git checkout and is not empty"; exit 2; fi
  mkdir -p "$(dirname "$p")"
  if [ -f "$SRC/git/$name.tar" ]; then  # shallow clone shipped as a whole checkout
    mkdir -p "$p"; tar -xf "$SRC/git/$name.tar" -C "$p"; git -C "$p" remote set-url origin "$url"
    echo "unpacked $name -> $p ($(git -C "$p" branch --show-current))"; continue; fi
  git clone -q --no-checkout "$SRC/git/$name.bundle" "$p"
  git -C "$p" checkout -q "$ref"
  if [ "$name" = westlake-harness ]; then  # this lab pushes to a2hlab; A2OH is the read-only upstream
    git -C "$p" remote rename origin a2hlab; git -C "$p" remote set-url a2hlab "$url"
    git -C "$p" remote add origin https://github.com/A2OH/westlake-harness
  else git -C "$p" remote set-url origin "$url"; fi
  echo "cloned $name -> $p ($ref)"
done < "$SRC/git/repos.tsv"

echo "== 3/4 worktrees"
n=0
while IFS=$'\t' read -r name rel ref; do
  p="$ROOT/$rel"; [ -e "$p/.git" ] && continue
  main=$(dest "$(awk -F'\t' -v n="$name" '$1==n{print $2}' "$SRC/git/repos.tsv")")
  mkdir -p "$(dirname "$p")"
  case $ref in @*) git -C "$main" worktree add -q --detach "$p" "${ref#@}";; *) git -C "$main" worktree add -q "$p" "$ref";; esac
  n=$((n+1))
done < "$SRC/git/worktrees.tsv"
echo "worktrees added: $n (listed: $(wc -l < "$SRC/git/worktrees.tsv"))"

echo "== 4/4 lab state"
un() { [ -e "$SRC/$1.part00" ] || { echo "skip $1 (not in this folder)"; return; }
  mkdir -p "$2"; cat "$SRC/$1".part* | zstd -q -d --long=31 | tar -xf - -C "$2"; echo "$1 -> $2"; }
un live.tar.zst "$ROOT"
un inputs-tools.tar.zst "$ROOT"
un workspaces-history.tar.zst "$ROOT"
un companion-untracked.tar.zst "$ROOT"
un harness-untracked.tar.zst "$ROOT"
un octos-state.tar.zst "$ROOT"
un a2hlab-vm.tar.zst "$ROOT/_a2hlab"
un bridge-payload.tar.zst "$HOME/orca"

echo "== repair worktree links"  # an archive may carry a worktree's .git file with the old machine's absolute path
while IFS=$'\t' read -r name rel ref; do
  main=$(dest "$(awk -F'\t' -v n="$name" '$1==n{print $2}' "$SRC/git/repos.tsv")")
  [ -e "$ROOT/$rel/.git" ] && git -C "$main" worktree repair "$ROOT/$rel" 2>/dev/null || true
done < "$SRC/git/worktrees.tsv"

echo "== relink absolute symlinks that pointed into the old machine's tree"
OLD_WORKSPACES=; OLD_HOME=; [ -f "$SRC/meta.env" ] && . "$SRC/meta.env"
n=0
if [ -n "$OLD_WORKSPACES" ]; then
  while IFS= read -r -d '' l; do t=$(readlink "$l")
    case $t in "$OLD_WORKSPACES"/*) nt="$ROOT/${t#"$OLD_WORKSPACES"/}";; "$OLD_HOME"/*) nt="$HOME/${t#"$OLD_HOME"/}";; *) continue;; esac
    ln -sfn "$nt" "$l"; n=$((n+1))
  done < <(find "$ROOT" "$HOME/orca" -type l -print0 2>/dev/null)
fi
echo "relinked: $n"

cat <<EOF

Done. Next (env.md):
- tools §4, credentials §8 (ssh hw248 key, gh auth for a2hlab, model API keys; not in this folder)
- VM §6: orb create --arch amd64 ubuntu:noble a2hlab, then
    orb -m a2hlab bash -lc "mkdir -p ~/a2hlab && rsync -a '$ROOT/_a2hlab/' ~/a2hlab/"
  and bind-mount ~/a2hlab/ws at the author path /home/dspfac/a2hlab/source-closure/verify (env.md §6)
- smoke checks §9, then read-only board checks before any dispatch (§10)
EOF
