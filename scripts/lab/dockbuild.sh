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
VMH=/mnt/machines/a2hlab/home/zhaoyue
BIND=/home/dspfac/a2hlab/source-closure/verify
INPUTS=/Users/zhaoyue/orca/workspaces/westlake-inputs
OH=$BIND/toolchains/ohos-sdk/native
HERE=$(cd "$(dirname "$0")" && pwd)

mounts=(
  -v "$VMH/a2hlab:/home/zhaoyue/a2hlab"            # manifest, logs, tools/libmap32bit.so, ws, board outputs
  -v "$VMH/a2hlab/ws:$BIND"                         # the author path (VM: sudo mount --bind ~/a2hlab/ws)
  -v "$VMH/.cache/ccache:/home/zhaoyue/.cache/ccache"  # shared with the VM
  -v "$INPUTS:$INPUTS"                              # the build scripts call $INPUTS/tools/*.sh
)
# $PWD is mounted at its own path so relative arguments keep working (Mac paths only; VM paths are above).
case "$PWD" in /Users/*|/private/*|/tmp/*) mounts+=(-v "$PWD:$PWD") ;; esac

drun() {  # drun NAME CMD...
  local name=$1; shift
  docker run --rm --platform linux/amd64 --name "$name" "${mounts[@]}" -w "$PWD" \
    -e CCACHE_DIR=/home/zhaoyue/.cache/ccache "$IMG" "$@"
}

cmd=${1:-}; shift || true
case "$cmd" in
  image)
    docker build --platform linux/amd64 -t "$IMG" "$HERE/docker" ;;
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
      test \"\$(stat -c %i $BIND)\" = \"\$(stat -c %i /home/zhaoyue/a2hlab/ws)\" && echo 'author path = ~/a2hlab/ws'
      test -f /home/zhaoyue/a2hlab/tools/libmap32bit.so && echo 'libmap32bit.so present'
      mountpoint -q $BIND && echo 'author path is a mountpoint (build scripts skip their sudo mount)'
      id" ;;
  *)
    sed -n '2,15p' "$0"; exit 2 ;;
esac
