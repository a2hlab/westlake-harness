#!/bin/bash
# Run a2hlab builds in OrbStack amd64 docker containers instead of the a2hlab VM's shell.
# The VM's filesystem is bind-mounted in place through OrbStack's /mnt/machines (no copy), at the same
# paths the VM uses -- including the author path /home/dspfac/a2hlab/source-closure/verify, which the
# manifest hashes depend on -- so the existing build scripts run unchanged and write where the VM would.
# Unlike the single VM shell, any number of containers can build side by side.
#
#   dockbuild.sh image                         build the image (once; apt via the huaweicloud mirror)
#   dockbuild.sh run [-n NAME] -- CMD...       run CMD under bash -lc, cwd = $PWD (mounted at the same path)
#   dockbuild.sh cc [clang args...]            OH aarch64 compile/link with the pinned clang-15 + sysroot, cwd = $PWD
#   dockbuild.sh check                         prove the mounts: pinned clang present, author path is the workspace
#
# Board work (probe_source_app.py, hdc) stays in the VM: hdc_mac.sh needs OrbStack's `mac` command.
set -euo pipefail
IMG=${DOCKBUILD_IMAGE:-a2hlab-build:24.04}
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lab_paths.sh" || exit 1
# The container runs as the VM user at the VM user's home, so files written into the shared workspace keep
# their owner and the build scripts see the paths they see in the VM. The Mac and VM user names need not
# match, so ask the VM (override all four: A2HLAB_VM_USER, A2HLAB_VM_UID, A2HLAB_VM_GID, A2HLAB_VM_HOME).
if [ -n "${A2HLAB_VM_USER:-}" ] && [ -n "${A2HLAB_VM_UID:-}" ] && [ -n "${A2HLAB_VM_GID:-}" ] && [ -n "${A2HLAB_VM_HOME:-}" ]; then
  VM_USER=$A2HLAB_VM_USER VM_UID=$A2HLAB_VM_UID VM_GID=$A2HLAB_VM_GID VM_HOME=$A2HLAB_VM_HOME
elif command -v orb >/dev/null 2>&1; then
  read -r VM_USER VM_UID VM_GID VM_HOME < <(orb -m a2hlab bash -c 'echo "$(id -un) $(id -u) $(id -g) $HOME"') || true
else  # inside the VM itself
  VM_USER=$(id -un) VM_UID=$(id -u) VM_GID=$(id -g) VM_HOME=$HOME
fi
[ -n "${VM_HOME:-}" ] || { echo "dockbuild: cannot read the a2hlab VM user; set A2HLAB_VM_USER/_UID/_GID/_HOME" >&2; exit 1; }
VMH=/mnt/machines/a2hlab$VM_HOME
BIND=/home/dspfac/a2hlab/source-closure/verify
INPUTS=$WORKSPACES/westlake-inputs
OH=$BIND/toolchains/ohos-sdk/native

mounts=(
  -v "$VMH/a2hlab:$VM_HOME/a2hlab"                  # manifest, logs, tools/libmap32bit.so, ws, board outputs
  -v "$VMH/a2hlab/ws:$BIND"                         # the author path (VM: sudo mount --bind ~/a2hlab/ws)
  -v "$VMH/.cache/ccache:$VM_HOME/.cache/ccache"    # shared with the VM
  -v "$INPUTS:$INPUTS"                              # the build scripts call $INPUTS/tools/*.sh
)
# Extra Mac directories at their own paths: DOCKBUILD_MOUNTS="$HOME/kit:$HOME/src" (e.g. an OH header kit).
IFS=: read -r -a extra_mounts <<< "${DOCKBUILD_MOUNTS:-}"
for m in "${extra_mounts[@]}"; do [ -n "$m" ] && mounts+=(-v "$m:$m"); done
# $PWD is mounted at its own path so relative arguments keep working (Mac paths only; VM paths are above).
case "$PWD" in /Users/*|/private/*|/tmp/*) mounts+=(-v "$PWD:$PWD") ;; esac

drun() {  # drun NAME CMD...
  local name=$1; shift
  docker run --rm --platform linux/amd64 --name "$name" "${mounts[@]}" -w "$PWD" \
    -e CCACHE_DIR="$VM_HOME/.cache/ccache" "$IMG" "$@"
}

cmd=${1:-}; shift || true
case "$cmd" in
  image)
    docker build --platform linux/amd64 -t "$IMG" --build-arg LAB_USER="$VM_USER" --build-arg LAB_UID="$VM_UID" \
      --build-arg LAB_GID="$VM_GID" --build-arg LAB_HOME="$VM_HOME" "$HERE/docker" ;;
  run)
    name="dockbuild-$$"
    if [ "${1:-}" = -n ]; then name=$2; shift 2; fi
    [ "${1:-}" = -- ] && shift
    [ $# -gt 0 ] || { echo "usage: dockbuild.sh run [-n NAME] -- CMD..." >&2; exit 2; }
    drun "$name" bash -lc "$*" ;;
  cc)
    # clang-15 directly: the workspace's `clang` is a wrapper that execs ccache with a VM-absolute path.
    drun "dockbuild-cc-$$" "$OH/llvm/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$OH/sysroot" "$@" ;;
  check)
    drun "dockbuild-check-$$" bash -c "
      set -e
      test -x $OH/llvm/bin/clang-15 && $OH/llvm/bin/clang-15 --version | head -1
      test \"\$(stat -c %i $BIND)\" = \"\$(stat -c %i $VM_HOME/a2hlab/ws)\" && echo 'author path = ~/a2hlab/ws'
      test -f $VM_HOME/a2hlab/tools/libmap32bit.so && echo 'libmap32bit.so present'
      mountpoint -q $BIND && echo 'author path is a mountpoint (build scripts skip their sudo mount)'
      id" ;;
  *)
    sed -n '2,15p' "$0"; exit 2 ;;
esac
