#!/bin/bash
# Pack everything a second control Mac needs into one folder to AirDrop or copy by disk (env.md §5).
# Same content as the hw248 mirror plus git bundles of every repo, so the new Mac needs no network for code.
# Unpack there with the unpack_airdrop.sh this puts into the folder.
#
#   pack_airdrop.sh [out dir]          (default <workspaces>/_airdrop-<date>)
#
# Companion repos default to $HOME-relative locations; override with WESTLAKE_REPO, ZERO_WORKSPACE_REPO,
# HARMONY_REPO. Agent tooling (octos, octoscode, herdr, CLIs) is installed on the new Mac, not shipped here.
#
# Big members are split into 4000 MB parts, so a failed AirDrop resends one part. Reuses the archives that
# push_lab_state.sh packed in _lab-state-stage/ (harness-untracked, workspaces-history, companion-untracked).
# Idempotent: a member whose parts already exist is not packed again, except the small ones that change
# often (the boards and westlake-inputs/tools), which are repacked on every run; delete git/<repo>.bundle
# to refresh a repo.
set -euo pipefail
# workspaces = $WORKSPACES, else the nearest ancestor of this script that holds westlake-inputs/ (works from
# scripts/lab/ in the repo and from its copy in westlake-inputs/tools/); no user-specific literals (AGENTS.md)
lab_workspaces() { local d; d=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
  while [ "$d" != / ] && [ ! -d "$d/westlake-inputs" ]; do d=$(dirname "$d"); done
  [ -d "$d/westlake-inputs" ] && echo "$d"; }
W=${WORKSPACES:-$(lab_workspaces)}; [ -n "$W" ] || { echo "cannot find the workspaces dir; set WORKSPACES"; exit 2; }
H=$W/westlake-harness
OUT=${1:-$W/_airdrop-$(date +%Y%m%d)}; STAGE=$W/_lab-state-stage
PACK="python3 $H/scripts/lab/pack_lab_archive.py"; PART=4000m
mkdir -p "$OUT/git"
have() { [ -e "$OUT/$1.part00" ]; }
split_file() { split -b $PART -d -a 2 "$1" "$OUT/$(basename "$1").part"; }

# 1. code: one bundle per repo (every ref) + where each checkout and worktree goes on the new Mac
: > "$OUT/git/repos.tsv.new"; : > "$OUT/git/worktrees.tsv.new"
repo() { # <name> <repo> <dest: ROOT/... or $HOME-relative> <branch> <url>
  git -C "$2" rev-parse -q --verify "refs/heads/$4" >/dev/null || { echo "no local branch $4 in $2"; exit 1; }
  if [ "$(git -C "$2" rev-parse --is-shallow-repository)" = true ]; then  # a bundle cannot carry a shallow boundary
    [ -s "$OUT/git/$1.tar" ] || tar -cf "$OUT/git/$1.tar" -C "$2" .   # whole checkout, .git and local edits included
  else [ -s "$OUT/git/$1.bundle" ] || git -C "$2" bundle create -q "$OUT/git/$1.bundle" --all; fi
  printf '%s\t%s\t%s\t%s\n' "$1" "$3" "$4" "$5" >> "$OUT/git/repos.tsv.new"
  local p h b; p=; h=; b=  # worktrees of this repo that live under $W: <repo> <path under ROOT> <branch|@sha>
  while IFS= read -r l; do case $l in
    "worktree "*) p=${l#worktree }; h=; b=;; "HEAD "*) h=${l#HEAD };; "branch refs/heads/"*) b=${l#branch refs/heads/};;
    "") if [ -n "$p" ] && [ "$p" != "$2" ] && [ -d "$p" ] && [ "${p#$W/}" != "$p" ]; then
          printf '%s\t%s\t%s\n' "$1" "${p#$W/}" "${b:-@$h}" >> "$OUT/git/worktrees.tsv.new"; fi; p=;;
  esac; done < <(git -C "$2" worktree list --porcelain; echo)
}
repo westlake-harness "$H" ROOT/westlake-harness master https://github.com/a2hlab/westlake-harness.git
repo westlake "${WESTLAKE_REPO:-$HOME/orca/westlake}" orca/westlake main https://github.com/A2OH/westlake.git
repo 00.Workspace "${ZERO_WORKSPACE_REPO:-$HOME/orca/00.Workspace}" ROOT/00.Workspace main https://github.com/a2hlab/00.Workspace.git
repo real-work "$W/01.OH61AOSP16/real-work" ROOT/01.OH61AOSP16/real-work zhao git@github.com:a2hlab/01.OH61AOSP16.git
repo harmony "${HARMONY_REPO:-$HOME/orca/harmony}" orca/harmony main https://github.com/a2hlab/harmony
mv "$OUT/git/repos.tsv.new" "$OUT/git/repos.tsv"; mv "$OUT/git/worktrees.tsv.new" "$OUT/git/worktrees.tsv"
echo "git: $(wc -l < "$OUT/git/repos.tsv") repos, $(wc -l < "$OUT/git/worktrees.tsv") worktrees"

# 2. the OLP boards (git-ignored by design), packed fresh every run so the newest board travels
rm -f "$OUT"/octos-state.tar.zst.part*
$PACK "$OUT/octos-state.tar.zst" --root "$W" --path "$H/.octos/boards" --path "$H/.octos/OUTER_LOOP_REVIEW.md" \
  --path "$H/.octos/EVOLUTION.md" --path "$H/.octos/archive"
split_file "$OUT/octos-state.tar.zst"; rm -f "$OUT/octos-state.tar.zst"

# 3a. the lab scripts' live copy (lanes call westlake-inputs/tools/*) and env-mac.sh, repacked every run
rm -f "$OUT"/inputs-tools.tar.zst.part*
$PACK "$OUT/inputs-tools.tar.zst" --root "$W" --path "$W/westlake-inputs/tools" --path "$W/westlake-inputs/env-mac.sh"
split_file "$OUT/inputs-tools.tar.zst"; rm -f "$OUT/inputs-tools.tar.zst"

# 3. what a board run needs: generation packages, per-board state, JARs, inputs incl. the APK corpus
if ! have live.tar.zst; then
  INP=(); for f in $(cd "$W" && /bin/ls -A westlake-inputs); do case $f in venv|tools) ;; *) INP+=(--path "$W/westlake-inputs/$f");; esac; done
  $PACK "$OUT/live.tar.zst" --root "$W" --level 3 "${INP[@]}" \
    --path "$W/westlake-generation-v3c-candidate" --path "$W/westlake-generation-n2-51a78bde" \
    --path "$W/westlake-generation-n1-aa57845c" --path "$W/westlake-runtime-asset-fd-53f00423" \
    --path "$W/westlake-installer-background-launcher-6aadb8b4" --path "$W/westlake-installer-background-launcher-6aadb8b4-5cd" \
    --path "$W/westlake-installer-background-launcher-6aadb8b4-61b" \
    --path "$W/westlake-installer-background-launcher-6aadb8b4-source.tar.gz" \
    --path "$W/westlake-generation-state" --path "$W/vm-copies" --path "$W/oh61-bms-kit" --path "$W/westlake-b90-controls-inputs"
  split_file "$OUT/live.tar.zst"; rm -f "$OUT/live.tar.zst"
fi

# 4. the VM's build side: locked toolchains, AOSP source subset, build inputs, westlake source, manifest
have a2hlab-vm.tar.zst || orb -m a2hlab bash -lc 'cd ~/a2hlab && tar -cf - ws/toolchains ws/android-source ws/inputs ws/westlake ws/westlake-all0925 ws/art-108-e6af1cd8 tools manifest' \
  | zstd -q -T0 -3 --long=31 -c | split -b $PART -d -a 2 - "$OUT/a2hlab-vm.tar.zst.part"

# 5. archival state already packed for hw248
for a in harness-untracked workspaces-history companion-untracked; do
  have "$a.tar.zst" || split_file "$STAGE/$a.tar.zst"; cp "$STAGE/$a.tar.zst.files" "$OUT/"
done

cp "$H/scripts/lab/unpack_airdrop.sh" "$OUT/"
(cd "$OUT" && find . -type f ! -name SHA256SUMS ! -name .DS_Store | sort | xargs shasum -a 256 > SHA256SUMS)
du -sh "$OUT"; echo ALL-DONE
