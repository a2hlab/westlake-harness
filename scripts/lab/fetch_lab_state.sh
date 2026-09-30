#!/bin/bash
# Pull the lab state that push_lab_state.sh mirrored to hw248 into the layout env.md describes, verifying
# every bundle against its SHA256SUMS. Run on the new control machine. Resumable (rsync --partial).
#
#   fetch_lab_state.sh --list
#   fetch_lab_state.sh [--into-vm] [bundle...]
#
# Default bundles (what a board run needs): octos-state generations generation-state vm-copies inputs apks a2hlab-toolchains
# Archival bundles (ask for them by name): git a2hlab-source harness-untracked workspaces-history
#                                           companion-untracked dot-octos-outer
# VM-side bundles (a2hlab-toolchains, a2hlab-source) land in $A2HLAB_STAGE (default $WORKSPACES/_a2hlab);
# --into-vm then copies that into the OrbStack VM's ~/a2hlab (the VM sees the Mac's /Users paths).
set -euo pipefail
# workspaces = $WORKSPACES, else the nearest ancestor of this script that holds westlake-inputs/ (works from
# scripts/lab/ in the repo and from its copy in westlake-inputs/tools/); no user-specific literals (AGENTS.md)
lab_workspaces() { local d; d=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
  while [ "$d" != / ] && [ ! -d "$d/westlake-inputs" ]; do d=$(dirname "$d"); done
  [ -d "$d/westlake-inputs" ] && echo "$d"; }
H=${LAB_STATE_HOST:-hw248}
DEST=${LAB_STATE_DIR:?set LAB_STATE_DIR to the mirror dir on hw248 (env.md §5)}
W=${WORKSPACES:-$(lab_workspaces)}; [ -n "$W" ] || { echo "cannot find the workspaces dir; set WORKSPACES"; exit 2; }
A2=${A2HLAB_STAGE:-$W/_a2hlab}
ARC=$W/_lab-archives
export RSYNC_RSH="ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=10"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
retry() { local i; for i in 1 2 3 4 5 6; do "$@" && return 0; echo "retry $i: $*" >&2; sleep 20; done; return 1; }

INTO_VM=; BUNDLES=()
for a in "$@"; do case $a in
  --list) ssh "$H" "cd $DEST && ls *.SHA256SUMS && du -sh --apparent-size * 2>/dev/null | grep -v SHA256SUMS"; exit;;
  --into-vm) INTO_VM=1;;
  *) BUNDLES+=("$a");;
esac; done
[ ${#BUNDLES[@]} -gt 0 ] || BUNDLES=(octos-state generations generation-state vm-copies inputs apks a2hlab-toolchains)
mkdir -p "$W" "$A2" "$ARC"

dirs() { # bundle whose SHA256SUMS paths are relative to $W and mirrored as-is under $DEST
  local s=$ARC/$1.SHA256SUMS
  scp -q "$H:$DEST/$1.SHA256SUMS" "$s"
  cut -c67- "$s" > "$s.paths"
  retry rsync -a --partial --files-from="$s.paths" "$H:$DEST/" "$W/"
  (cd "$W" && sha -c --quiet "$s") && echo "$1: $(wc -l < "$s") files verified in $W"
}
archive() { # <bundle> <extract root>: one tar.zst in $DEST/<bundle>/
  local s=$ARC/$1.SHA256SUMS f
  scp -q "$H:$DEST/$1.SHA256SUMS" "$s"; f=$(cut -c67- "$s")
  mkdir -p "$ARC/$1"; retry rsync --partial "$H:$DEST/$1/$f" "$ARC/$1/"
  (cd "$ARC/$1" && sha -c --quiet "$s") || { echo "$1: checksum mismatch"; exit 1; }
  case $f in
    *.tar.zst) mkdir -p "$2"; zstd -q -d --long=31 -c "$ARC/$1/$f" | tar -xf - -C "$2"; echo "$1: verified, unpacked into $2";;
    *) echo "$1: verified at $ARC/$1/$f";;
  esac
}

for b in "${BUNDLES[@]}"; do case $b in
  octos-state|generations|generation-state|vm-copies|inputs|apks) dirs "$b";;
  a2hlab-toolchains)
    scp -q "$H:$DEST/$b.SHA256SUMS" "$ARC/$b.SHA256SUMS"; mkdir -p "$A2/ws"
    retry rsync -a --partial "$H:$DEST/a2hlab/ws/toolchains" "$A2/ws/"
    (cd "$A2/ws" && sha -c --quiet "$ARC/$b.SHA256SUMS") && echo "$b: verified in $A2/ws";;
  a2hlab-source) archive "$b" "$A2";;
  dot-octos-outer) archive "$b" "$HOME/.octos";;
  harness-untracked|workspaces-history|companion-untracked) archive "$b" "$W";;
  git) archive git "";;
  *) echo "unknown bundle $b (try --list)"; exit 2;;
esac; done

if [ -n "$INTO_VM" ]; then
  orb -m a2hlab bash -lc "mkdir -p ~/a2hlab && rsync -a '$A2'/ ~/a2hlab/" && echo "copied $A2 into VM ~/a2hlab"
fi
