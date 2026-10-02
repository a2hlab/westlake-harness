#!/usr/bin/env bash
# Runs ON hw248. U15 runtime M3 = U13 runtime 18763dd4 with ONE object replaced: EGLImpl.o.
#   build_m3_hw248.sh <mirror-root> <link-root> <tag>
# 1. EGLImpl.o: the compile line of westlake-harness-bms-deploy benchmark/2026-09-30-n4-native/build-egl.sh verbatim
#    (frozen clang feef13a3, same flags, same -I list, output dir n4-native/gl so the DWARF include paths keep their
#    form), inside the 58-char mirror root; only the source path changes to this round's src/oh_egl_impl.cpp.
# 2. Link: the U13 recipe's exact link argv (printed by the recipe itself, 112 items incl. webview_publication.o),
#    with every input mirrored under <link-root>; only the EGLImpl.o item points at the new object.
set -euo pipefail
REPO=${1:?mirror root}; LR=${2:?link root}; TAG=${3:?tag}
[ -n "$REPO" ] && [ -n "$LR" ] && [ -d "$REPO/benchmark/2026-10-03-u15-runtime-m3/src" ] || exit 9
cd "$REPO"
BASE=$REPO/bms/src/.work/b68-generation
FROZEN=$BASE/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
AOSP=$REPO/bms/src/.work/b6-art14-recovery/aosp-restoration
OUT=$REPO/bms/src/.work/n4-native/gl
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$OUT/include"
ln -sfn "$AOSP/frameworks/native/opengl/include/GLES" "$OUT/include/GLES"
FLAGS=(--target=aarch64-linux-ohos --sysroot=$SYS -B$TC/bin -fPIC -O2 -g -ffunction-sections -fdata-sections -D_GNU_SOURCE -D__OHOS__ -DGL_GLEXT_PROTOTYPES -DEGL_EGLEXT_PROTOTYPES -include limits.h -include sys/types.h -I$REPO/benchmark/2026-09-30-n2-native/westlake-gl/compat -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/include_jni -I$AOSP/system/logging/liblog/include -I$OUT/include)
echo "[hw248] $(date -Iseconds) root=$REPO ($(printf %s "$REPO" | wc -c) chars) tag=$TAG clang: $($TC/bin/clang-15 --version | head -1)"
rm -f "$OUT/EGLImpl.o"
"$TC/bin/clang++" "${FLAGS[@]}" -std=c++17 -isystem "$TC/include/c++/v1" -Wno-unused-parameter -Wno-unused-function -c "$REPO/benchmark/2026-10-03-u15-runtime-m3/src/oh_egl_impl.cpp" -o "$OUT/EGLImpl.o"
mkdir -p "$LR/m3-$TAG/out"
cp "$OUT/EGLImpl.o" "$LR/m3-$TAG/EGLImpl.o"
sha256sum "$LR/m3-$TAG/EGLImpl.o"
mapfile -t A < "$LR/link-argv.txt"
n=0
for i in "${!A[@]}"; do
  case "${A[$i]}" in */n4-native/gl/EGLImpl.o) A[$i]="$LR/m3-$TAG/EGLImpl.o"; n=$((n+1));; esac
  [ "${A[$i]}" = "$LR/rt/out/liboh_android_runtime.so" ] && A[$i]="$LR/m3-$TAG/out/liboh_android_runtime.so"
done
[ "$n" -eq 1 ] || { echo "EGLImpl.o argv items: $n"; exit 7; }
cp "$LR/rt/out/libwestlake_thread_guard_registry.so" "$LR/m3-$TAG/out/"
# -L <link-root>/rt/out stays: it holds the registry the recipe copies there; the output goes to m3-<tag>/out.
(cd "$LR/rt" && "${A[@]}")
sha256sum "$LR/m3-$TAG/out/liboh_android_runtime.so"
