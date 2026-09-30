#!/bin/bash
# Mirror the lab state that is not in git to hw248, so another control machine can reproduce everything
# (env.md). Run on the old control Mac. Resumable: re-running skips a bundle only when hw248 holds exactly the
# local content (same SHA256SUMS, verified there), so a re-run right before switching machines refreshes the
# boards and generation-state.
#
#   push_lab_state.sh [--steps live,git,vm,archives] [--wait-pid PID]
#
# live      directory rsync of what a run needs: the OLP boards (git-ignored on purpose), current generation packages, per-board generation state,
#           JARs, westlake-inputs (tools, WebView, APK corpus), VM build toolchains; SHA256SUMS per bundle
# git       `git bundle --all` of this repo (every branch incl. wip/*), in case GitHub is unreachable
# vm        VM source needed to rebuild (android-source, build inputs, westlake-all0925, art-108, manifest)
# archives  deduplicating tar.zst of everything else: untracked/ignored files of every worktree (raw runs,
#           bms/src/.work), older generation packages and one-off trees, companion repos' untracked files
# Before each upload it refuses to go on when hw248 has less than MIN_FREE_GB (default 30) left.
set -euo pipefail
# workspaces = $WORKSPACES, else the nearest ancestor of this script that holds westlake-inputs/ (works from
# scripts/lab/ in the repo and from its copy in westlake-inputs/tools/); no user-specific literals (AGENTS.md)
lab_workspaces() { local d; d=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
  while [ "$d" != / ] && [ ! -d "$d/westlake-inputs" ]; do d=$(dirname "$d"); done
  [ -d "$d/westlake-inputs" ] && echo "$d"; }
STEPS=live,git,vm,archives; WAIT=
while [ $# -gt 0 ]; do case $1 in --steps) STEPS=$2; shift 2;; --wait-pid) WAIT=$2; shift 2;; *) exit 2;; esac; done
W=${WORKSPACES:-$(lab_workspaces)}; [ -n "$W" ] || { echo "cannot find the workspaces dir; set WORKSPACES"; exit 2; }
H=${LAB_STATE_HOST:-hw248}
DEST=${LAB_STATE_DIR:?set LAB_STATE_DIR to the mirror dir on hw248 (env.md §5)}
OUT=${LAB_STATE_STAGE:-$W/_lab-state-stage}
MIN_FREE_GB=${MIN_FREE_GB:-30}
PACK="python3 $W/westlake-harness/scripts/lab/pack_lab_archive.py"
export RSYNC_RSH="ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=10"
mkdir -p "$OUT"; ssh "$H" "mkdir -p $DEST"
retry() { local i; for i in 1 2 3 4 5 6; do "$@" && return 0; echo "retry $i: $*" >&2; sleep 20; done; return 1; }
has() { case ",$STEPS," in *",$1,"*) return 0;; esac; return 1; }
space() {
  local free; free=$(ssh "$H" "df -BG --output=avail $DEST | tail -1 | tr -dc 0-9")
  [ "$free" -ge "$MIN_FREE_GB" ] || { echo "STOP: hw248 has ${free}G free (< ${MIN_FREE_GB}G) before $1"; exit 3; }
}
verified() { ssh "$H" "cd $DEST${2:+/$2} && test -f $DEST/$1.SHA256SUMS && sha256sum -c --quiet $DEST/$1.SHA256SUMS" 2>/dev/null; }
current() { # hw248 already holds exactly what the local SHA256SUMS describes
  ssh "$H" "cat $DEST/$1.SHA256SUMS" 2>/dev/null | cmp -s - "$OUT/$1.SHA256SUMS" && verified "$@"; }
sums() { (cd "$W" && find "${@:2}" -type f ! -name .DS_Store -print0 | sort -z | xargs -0 shasum -a 256) > "$OUT/$1.SHA256SUMS"; }
push_dirs() { # <bundle> <path relative to W>...
  sums "$@"
  current "$1" && { echo "$1: already on hw248, unchanged"; return; }
  space "$1"
  (cd "$W" && retry rsync -aR --partial --exclude .DS_Store "${@:2}" "$H:$DEST/")
  scp -q "$OUT/$1.SHA256SUMS" "$H:$DEST/"
  verified "$1" && echo "$1: verified on hw248 ($(wc -l < "$OUT/$1.SHA256SUMS") files)"
}
push_file() { # <bundle> <local file>: one file into $DEST/<bundle>/
  local f=$2 b; b=$(basename "$f")
  (cd "$(dirname "$f")" && shasum -a 256 "$b") > "$OUT/$1.SHA256SUMS"
  current "$1" "$1" && { echo "$1: already on hw248, unchanged"; return; }
  space "$1"; ssh "$H" "mkdir -p $DEST/$1"
  retry rsync --partial --inplace "$f" "$H:$DEST/$1/$b"
  scp -q "$OUT/$1.SHA256SUMS" "$H:$DEST/"
  verified "$1" "$1" && echo "$1: verified on hw248 ($(du -h "$f" | cut -f1))"
}

if has archives; then  # packing is local CPU/disk only, so it runs while an earlier upload holds the link
  cd "$W"
  [ -s "$OUT/harness-untracked.tar.zst" ] || $PACK "$OUT/harness-untracked.tar.zst" --root "$W" \
    $(git -C westlake-harness worktree list --porcelain | awk -v w="$W/" '/^worktree /{p=substr($0,10); if (index(p,w)==1 && system("test -d \""p"\"")==0) print "--untracked "p}')
  LIVE='^(westlake-inputs|westlake-generation-state|vm-copies|westlake-generation-v3c-candidate|westlake-generation-n2-51a78bde|westlake-generation-n1-aa57845c|westlake-runtime-asset-fd-53f00423|westlake-installer-background-launcher-6aadb8b4.*|oh61-bms-kit|westlake-b90-controls-inputs|_lab-state-stage|00\.Workspace|01\.OH61AOSP16|westlake-bms-suite|harmony-main-adapter)$'
  HIST=(); for d in *; do [[ $d =~ $LIVE ]] && continue; git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && [ "$(git -C "$d" rev-parse --git-common-dir)" = "$W/westlake-harness/.git" ] && continue
    [[ $d == westlake-harness* ]] && continue; HIST+=(--path "$d"); done
  [ -s "$OUT/workspaces-history.tar.zst" ] || $PACK "$OUT/workspaces-history.tar.zst" --root "$W" "${HIST[@]}"
  [ -s "$OUT/companion-untracked.tar.zst" ] || $PACK "$OUT/companion-untracked.tar.zst" --root "$W" \
    --untracked 00.Workspace --untracked 01.OH61AOSP16/real-work --untracked westlake-bms-suite \
    --untracked harmony-main-adapter
  [ -s "$OUT/dot-octos-outer.tar.zst" ] || $PACK "$OUT/dot-octos-outer.tar.zst" --root "$HOME/.octos" --path "$HOME/.octos/outer"
fi
if [ -n "$WAIT" ]; then while kill -0 "$WAIT" 2>/dev/null; do sleep 30; done; fi

if has live; then
  push_dirs octos-state westlake-harness/.octos/boards westlake-harness/.octos/OUTER_LOOP_REVIEW.md \
    westlake-harness/.octos/EVOLUTION.md westlake-harness/.octos/archive
  push_dirs generations westlake-generation-v3c-candidate westlake-generation-n2-51a78bde westlake-generation-n1-aa57845c \
    westlake-runtime-asset-fd-53f00423 westlake-installer-background-launcher-6aadb8b4 \
    westlake-installer-background-launcher-6aadb8b4-5cd westlake-installer-background-launcher-6aadb8b4-61b \
    westlake-installer-background-launcher-6aadb8b4-source.tar.gz
  push_dirs generation-state westlake-generation-state
  push_dirs vm-copies vm-copies
  push_dirs inputs westlake-inputs/tools westlake-inputs/board westlake-inputs/webview westlake-inputs/toolshim \
    westlake-inputs/static100-tooling westlake-inputs/audit-static100-cache westlake-inputs/app-inputs.lock.json \
    westlake-inputs/env-mac.sh westlake-inputs/mise.toml westlake-inputs/HANDOFF.md oh61-bms-kit \
    westlake-b90-controls-inputs $(cd "$W" && ls westlake-inputs/*.json)
  orb -m a2hlab bash -lc 'cd ~/a2hlab/ws && find toolchains -type f -print0 | sort -z | xargs -0 sha256sum' > "$OUT/a2hlab-toolchains.SHA256SUMS"
  if ! current a2hlab-toolchains a2hlab/ws; then
    space a2hlab-toolchains
    orb -m a2hlab bash -lc 'cd ~/a2hlab/ws && tar -cf - toolchains' | ssh "$H" "mkdir -p $DEST/a2hlab/ws && tar -xf - -C $DEST/a2hlab/ws"
    scp -q "$OUT/a2hlab-toolchains.SHA256SUMS" "$H:$DEST/"
    verified a2hlab-toolchains a2hlab/ws && echo "a2hlab-toolchains: verified on hw248"
  fi
  push_dirs apks westlake-inputs/apks
fi
if has git; then
  git -C "$W/westlake-harness" bundle create "$OUT/westlake-harness-all.bundle" --all
  push_file git "$OUT/westlake-harness-all.bundle"
fi
if has vm; then
  [ -s "$OUT/a2hlab-source.tar.zst" ] || { orb -m a2hlab bash -lc \
    'cd ~/a2hlab && tar -cf - ws/android-source ws/inputs ws/westlake-all0925 ws/art-108-e6af1cd8 tools manifest' \
    | zstd -q -T0 -6 --long=31 -c > "$OUT/a2hlab-source.tar.zst.part" && mv "$OUT/a2hlab-source.tar.zst.part" "$OUT/a2hlab-source.tar.zst"; }
  push_file a2hlab-source "$OUT/a2hlab-source.tar.zst"
fi
if has archives; then
  for a in dot-octos-outer harness-untracked workspaces-history companion-untracked; do
    push_file "$a" "$OUT/$a.tar.zst"; scp -q "$OUT/$a.tar.zst.files" "$H:$DEST/$a/"
  done
fi
ssh "$H" "df -h $DEST | tail -1; du -sh $DEST"
echo ALL-DONE
