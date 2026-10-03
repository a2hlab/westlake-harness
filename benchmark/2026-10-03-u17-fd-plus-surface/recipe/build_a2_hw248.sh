#!/usr/bin/env bash
# =============================================================================
# U17 ① fd-plus — build the A2 software-lockCanvas candidate. RUNS ON hw248.
#
# Base = U16 runtime liboh_android_runtime 1d42dbfb (cc-t3 t4). Change = ONLY
# S_nativeLockCanvas / S_nativeUnlockCanvasAndPost in the shim object
# (shim_split.o = n2-native shim + m1 split.patch). Method = the A' byte-identical
# lock: reproduce shim_split.o from the frozen recipe (must match 003a4edb...),
# THEN apply the A2 patch and recompile with the IDENTICAL cxxc command, so only
# the two functions (+ their internal helpers) vary. Then relink via the t4
# mechanics (×2 byte-identical) into a FRESH out dir (cc-t3's t4-a/t4-b untouched).
#
# Replicates split_a_prime.{run,inner}.sh env verbatim (so the baseline reproduces
# byte-for-byte). Does NOT run the full runtime compile — only the single shim TU.
# =============================================================================
set -uo pipefail
# Paths are parameterized (land.py user-path gate: no hardcoded per-machine paths).
# WORKSPACES defaults to the repo-root derived from this script's location.
# The build-host (hw248) trees are env vars; the values used for the landed candidate are
# recorded in deploy/generation.json:
#   WORKSPACES=<...>/orca/workspaces
#   CCT3_T4_TREE=/home/<build-user>/cc-t3-u15rt-m3     (cc-t3's t4 tree: link-argv.txt + 112 objects + m1_copy.o + m3-a)
#   U17_FDPLUS_OUT=/home/<build-user>/cc-wiki-u17-fdplus (our isolated output; cc-t3's t4-a/t4-b untouched)
W="${WORKSPACES:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
BMS=$W/westlake-harness-bms-deploy
WIKI=$W/westlake-harness-wiki
SPLIT=$WIKI/benchmark/2026-10-03-m1-split
DELIV=$WIKI/benchmark/2026-10-03-u17-fd-plus-surface
R="${CCT3_T4_TREE:?set CCT3_T4_TREE to cc-t3's t4 tree on the build host}"   # read inputs; NOT t4-a/b
OUT="${U17_FDPLUS_OUT:?set U17_FDPLUS_OUT to an isolated output dir on the build host}"
LOG=$DELIV/evidence
mkdir -p "$OUT" "$LOG"

# ---- env exactly as split_a_prime.run.sh exports ----------------------------
export L03_A12_STRICT_BUILD=1
export ADAPTER_ROOT=$BMS/bms/src/.work/b87-native/adapter
export OH_ROOT=$BMS/bms/src/.work/b6-latest/oh
export AOSP_ROOT=$BMS/bms/src/.work/b6-art14-recovery/aosp-restoration
export L03_A12_CXX=$BMS/bms/src/.work/b6-art14-recovery/build/cxx-sdk15
export L03_A12_NM=$BMS/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-nm
export L03_A12_READELF=$BMS/bms/src/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
export L03_A12_LIBCXX_INCLUDE=$BMS/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1

# ---- cxxc env exactly as split_a_prime.inner.sh (lines 143-202,518) ---------
OH="$OH_ROOT"; A="$AOSP_ROOT"
SRC="$ADAPTER_ROOT/framework/android-runtime"
BC="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"
OH_PRODUCT=wukong100
OH_OUT="$OH/out/$OH_PRODUCT"
SR="$OH_OUT/obj/third_party/musl/usr"
CXX="$L03_A12_CXX"
COMMON="--target=aarch64-linux-ohos -march=armv8-a --sysroot=$SR -I$SR/include/aarch64-linux-ohos -fPIC -O2 -std=gnu++17 -fno-rtti"
COMMON="$COMMON -nostdinc++ -isystem $L03_A12_LIBCXX_INCLUDE -MMD -MP"
COMMON="$COMMON -ffile-prefix-map=$ADAPTER_ROOT=. -fdebug-prefix-map=$ADAPTER_ROOT=."
INC="-I$ADAPTER_ROOT/framework/native-loader-oh/include -I$SRC/include -I$SRC/src -I$ADAPTER_ROOT/framework/surface/jni -I$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/include -I$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/include -I$BC -I$A/system/logging/liblog/include -I$A/libnativehelper/include_jni -I$A/libnativehelper/include -I$A/system/libbase/include -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
DEFS="-D__OHOS__ -D_GNU_SOURCE"
cxxc(){ echo "+ $(basename "$1") -> $(basename "$2")"; "$CXX" $COMMON -include "$BC/libcxx_compat.h" $INC $DEFS -c "$1" -o "$2" || { echo "COMPILE FAIL $1"; exit 1; }; }

# ---- inputs -----------------------------------------------------------------
N2=$BMS/benchmark/2026-09-30-n2-native/src/android_graphics_compat_shim.cpp
PATCHF=$SPLIT/patch/android_graphics_compat_shim.split.patch
A2INC=$DELIV/src/a2-lockcanvas.inc.cpp
APPLY=$DELIV/recipe/apply_a2.py
SC=$SPLIT/build; rm -rf "$SC"; mkdir -p "$SC/cmp"       # SAME stage path as the recipe
BASE_SHA=003a4edbcbbb8cc9a2f6d4da9c788bd1e1e040953042bd4c1cbd20664a0f115f
DEP_RT_SHA=1d42dbfb473f87e8    # deployed runtime (t4-b/out), first 16

echo "===== STEP A: reproduce shim_split.o baseline (lock the command) ====="
cp "$N2" "$SC/cmp/android_graphics_compat_shim.cpp"
patch -s "$SC/cmp/android_graphics_compat_shim.cpp" < "$PATCHF" || { echo "split.patch FAILED"; exit 3; }
cxxc "$SC/cmp/android_graphics_compat_shim.cpp" "$SC/shim_split_repro.o"
GOT=$(sha256sum "$SC/shim_split_repro.o" | cut -d' ' -f1)
echo "repro sha : $GOT"
echo "target sha: $BASE_SHA"
if [ "$GOT" != "$BASE_SHA" ]; then
  echo "!!! BASELINE NOT BYTE-IDENTICAL — env/command not locked; aborting before patch."
  exit 4
fi
echo "BASELINE LOCKED (byte-identical to deployed shim_split.o)."

echo "===== STEP B: apply A2 patch + recompile with the IDENTICAL command ====="
cp "$SC/cmp/android_graphics_compat_shim.cpp" "$SC/shim_a2.cpp"
python3 "$APPLY" "$SC/shim_a2.cpp" "$A2INC" "$SC/shim_a2_patched.cpp" || { echo "apply_a2 FAILED"; exit 5; }
cxxc "$SC/shim_a2_patched.cpp" "$SC/shim_split_a2.o"
echo "shim_split_a2.o sha: $(sha256sum "$SC/shim_split_a2.o" | cut -c1-16)"

echo "===== STEP C: relink ×2 (t4 mechanics; fresh out; shim_split_a2.o) ====="
grep -c . "$R/link-argv.txt" | grep -qx 112 || { echo "link-argv.txt not 112"; exit 8; }
for TAG in a b; do
  D=$OUT/t-$TAG; rm -rf "$D"; mkdir -p "$D/out"
  cp "$SC/shim_split_a2.o" "$D/shim_split_a2.o"
  cp "$R/m1_copy.o" "$D/m1_copy.o"
  python3 - "$R/link-argv.txt" "$D/argv.txt" "$R" "$D" <<'PY'
import sys
src, dst, R, D = sys.argv[1:5]
items=[l.rstrip('\n') for l in open(src) if l.strip('\n')!='']
out=[]; ns=ne=no=0
for it in items:
    if it.endswith('/n4-native/gl/EGLImpl.o'):
        out.append(R+'/m3-a/EGLImpl.o'); ne+=1
    elif it.endswith('/rt/runtime-objects/android_graphics_compat_shim.o'):
        out.append(D+'/shim_split_a2.o'); ns+=1
        out.append(D+'/m1_copy.o')
    elif it==R+'/rt/out/liboh_android_runtime.so':
        out.append(D+'/out/liboh_android_runtime.so'); no+=1
    else:
        out.append(it)
assert ns==1 and ne==1 and no==1,(ns,ne,no)
open(dst,'w').write('\n'.join(out)+'\n'); print('argv items:',len(out))
PY
  cp "$R/rt/out/libwestlake_thread_guard_registry.so" "$D/out/"
  mapfile -t ARGS < "$D/argv.txt"
  (cd "$R/rt" && "${ARGS[@]}") > "$D/link.log" 2>&1 || { echo "LINK FAIL t-$TAG (see $D/link.log)"; tail -20 "$D/link.log"; exit 6; }
  echo "t-$TAG: $(sha256sum "$D/out/liboh_android_runtime.so" | cut -c1-16)"
done
if cmp -s "$OUT/t-a/out/liboh_android_runtime.so" "$OUT/t-b/out/liboh_android_runtime.so"; then
  echo "TWO PASSES BYTE-IDENTICAL"
else
  echo "!!! PASSES DIFFER"; exit 9
fi
CAND=$OUT/t-a/out/liboh_android_runtime.so
echo "CANDIDATE sha256: $(sha256sum "$CAND")"
cp "$CAND" "$OUT/liboh_android_runtime.A2.so"
echo "build log tee -> $LOG/build-a2.log (copy this script's stdout there)"
echo "DONE: candidate at $CAND"
