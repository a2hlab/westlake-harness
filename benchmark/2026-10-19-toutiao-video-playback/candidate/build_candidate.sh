#!/bin/bash
# t2 offline build of libopensles_android_compat.so (Toutiao video P1).
# Recipe: westlake scripts/toutiao/native/build.sh 0d8e4f43 (build_link_only + build_shared, lines 89-93),
# executed through scripts/lab/dockbuild.sh with the pinned OHOS clang-15 + sysroot. Run from this directory.
# Every step's raw stdout/stderr/rc is written to LOGDIR (default: a private persistent dir under
# $HOME/.local/share/westlake/, never scrubbed); the repo keeps renamed *.sanitized.txt copies made by
# sanitize_logs.sh. Link-only outputs are never deployable.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"
REPO=$(cd "$HERE/../../.." && pwd)
DB="$REPO/scripts/lab/dockbuild.sh"
SEL="$REPO/benchmark/2026-10-19-toutiao-video-playback/static/selected-change"
OH=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native
LOGDIR=${LOGDIR:-$HOME/.local/share/westlake/toutiao-video-t2-build/$(date +%Y%m%dT%H%M%S)}
mkdir -p src "$LOGDIR" out/link-only.NOT-FOR-DEPLOY out/unstripped out/asx
echo "raw logs: $LOGDIR"
step() {  # step NAME CMD...
  local n=$1; shift
  echo "== $n: $*" > "$LOGDIR/$n.cmd.txt"
  "$@" > "$LOGDIR/$n.stdout.txt" 2> "$LOGDIR/$n.stderr.txt"; local rc=$?
  echo "$rc" > "$LOGDIR/$n.rc.txt"; echo "$n rc=$rc"
  [ "$rc" -eq 0 ] || { echo "FAILED $n" >&2; exit "$rc"; }
}
# 1. verbatim sources (SHA pinned by the t2 contract)
cp "$SEL/opensles_android_compat.c" "$SEL/link_only_stub.c" src/
step 00-source-sha shasum -a 256 -c /dev/stdin <<SHA
cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351  src/opensles_android_compat.c
fa47585b8fb702e8da05c52d732c9c964b5ec50a34edfa6815dea7f962898e13  src/link_only_stub.c
SHA
# 2. toolchain identity
step 01-dockbuild-check "$DB" check
step 02-toolchain-sha "$DB" run -- "sha256sum $OH/llvm/bin/clang-15 $OH/llvm/bin/lld $OH/llvm/bin/llvm-strip $OH/llvm/bin/llvm-readelf $OH/sysroot/usr/lib/aarch64-linux-ohos/libc.so $OH/sysroot/usr/lib/aarch64-linux-ohos/libdl.so 2>/dev/null; $OH/llvm/bin/clang-15 --version"
# 3. link-only libOpenSLES.so (SONAME only; never staged/deployed)
step 10-link-only "$DB" cc -fPIC -O2 -shared -fuse-ld=lld -Wl,-z,relro,-z,now \
  src/link_only_stub.c -Wl,-soname,libOpenSLES.so -o out/link-only.NOT-FOR-DEPLOY/libOpenSLES.so
# 4. compat DSO, exact build_shared flags
step 20-compat "$DB" cc -fPIC -O2 -g -Wall -Wextra -shared -fuse-ld=lld -Wl,-z,relro,-z,now \
  -Wl,-soname,libopensles_android_compat.so src/opensles_android_compat.c \
  -ldl -Lout/link-only.NOT-FOR-DEPLOY -Wl,--no-as-needed -lOpenSLES -Wl,--as-needed \
  -o out/unstripped/libopensles_android_compat.so
step 21-strip "$DB" run -- "cp out/unstripped/libopensles_android_compat.so out/asx/libopensles_android_compat.so && $OH/llvm/bin/llvm-strip --strip-unneeded out/asx/libopensles_android_compat.so"
step 30-sha shasum -a 256 out/asx/libopensles_android_compat.so out/unstripped/libopensles_android_compat.so out/link-only.NOT-FOR-DEPLOY/libOpenSLES.so
echo "build done"
