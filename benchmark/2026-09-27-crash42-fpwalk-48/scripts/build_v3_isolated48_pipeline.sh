#!/usr/bin/env bash
set -e
WS="$HOME/a2hlab/ws"; SDK="$WS/toolchains/ohos-sdk/native"
REC="$WS/out-crash42/recorder"; ISO="$WS/out-isolated48-recorder"; FIX="$WS/out-crash42/fixture/native"
WORKING="$WS/out-speed-delivery50/inputs/libart.so"   # 78e34445 working recorder
BK=/tmp/iso48-backup; ISOSCR=/tmp/iso48/scripts; ISONAT=/tmp/iso48/native

echo "=== 0. back up isolated48 working artifacts (restore at end) ==="
rm -rf "$BK"; mkdir -p "$BK"
for f in libart-initialized.so libart.so relink.json initialized-relink.json sigchain-initialized.o sigchain-initialized.cc baseline-relinked.so; do
  [ -f "$ISO/$f" ] && cp -a "$ISO/$f" "$BK/$f" || true
done
cp -a "$REC/crash_snapshot.o" "$BK/crash_snapshot.o.pre" 2>/dev/null || true
echo "backed up: $(ls "$BK")"

echo "=== 0b. scripts + native already staged at /tmp/iso48 by caller; native has crash_snapshot.h ==="
ls "$ISOSCR"/*.py "$ISONAT/crash_snapshot.h"

run_pipeline() {  # $1 = label, uses whatever crash_snapshot.o is at $REC
  echo ">>> relink_recorder.py ($1)"; python3 "$ISOSCR/relink_recorder.py" | grep -E 'candidate|baseline|reproduced|recorder' || true
  echo ">>> initialize_recorder.py ($1)"; local sha; sha=$(python3 "$ISOSCR/initialize_recorder.py"); echo "candidate libart-initialized.so sha=$sha"
  echo "$sha"
}
stripsha() { cp "$1" /tmp/ss.so; "$SDK/llvm/bin/llvm-strip" --strip-all /tmp/ss.so 2>/dev/null; sha256sum /tmp/ss.so | cut -c1-16; }

echo "=== 1. VERIFY: pipeline with UNPATCHED recorder must reproduce 78e34445 (functionally) ==="
"$SDK/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -std=c11 -O2 -g -fPIC -Wall -Wextra -Werror -I"$FIX" -c "$FIX/crash_snapshot.c" -o "$REC/crash_snapshot.o"
run_pipeline unpatched >/tmp/v3_unpatched.log 2>&1 || { echo UNPATCHED_FAIL; tail -20 /tmp/v3_unpatched.log; exit 1; }
UNPATCHED_CAND=$(sha256sum "$ISO/libart-initialized.so" | cut -c1-16)
echo "unpatched pipeline candidate: $UNPATCHED_CAND  (78e34445 full=78e344455ec300f7)"
echo "stripped: mine=$(stripsha "$ISO/libart-initialized.so")  78e34445=$(stripsha "$WORKING")"

echo "=== 2. PATCHED: pipeline with v2 fp-walk recorder ==="
"$SDK/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -std=c11 -O2 -g -fPIC -Wall -Wextra -Werror -I"$FIX" -c "$WS/out-crash42-fpwalk48/art-v2/crash_snapshot.c" -o "$REC/crash_snapshot.o"
echo "v2 recorder .o UND dl_iterate_phdr (want 0): $("$SDK/llvm/bin/llvm-nm" -u "$REC/crash_snapshot.o" | grep -c dl_iterate_phdr || true)"
run_pipeline patched >/tmp/v3_patched.log 2>&1 || { echo PATCHED_FAIL; tail -20 /tmp/v3_patched.log; exit 1; }
V3=$ISO/libart-initialized.so
echo "v3 candidate libart-initialized.so: $(sha256sum "$V3" | cut -d' ' -f1)"
echo "size v3=$(stat -c%s "$V3")  78e34445=$(stat -c%s "$WORKING")"
echo "fp-walk in v3? $("$SDK/llvm/bin/llvm-strings" "$V3" | grep -E 'base_capture_complete|fp_frame_return' | head -2 | tr '\n' ' ')"
echo "wl_crash_snapshot defined? $("$SDK/llvm/bin/llvm-nm" "$V3" 2>/dev/null | grep -c 'T wl_crash_snapshot$')"
echo "sigchain init fix in v3? $("$SDK/llvm/bin/llvm-strings" "$V3" | grep -c 'directory ready before fork')"

echo "=== 3. stage v3 delivery ==="
DEL="$WS/out-crash42-fpwalk48/art-v3"; rm -rf "$DEL"; mkdir -p "$DEL"
cp "$V3" "$DEL/libart-initialized.so"
cp "$ISO/initialized-relink.json" "$DEL/initialized-relink.json" 2>/dev/null || true
cp "$WS/out-crash42-fpwalk48/art-v2/crash_snapshot.c" "$DEL/crash_snapshot.c"
sha256sum "$DEL/libart-initialized.so" > "$DEL/SHA256SUMS"
echo "staged $DEL/libart-initialized.so sha=$(sha256sum "$DEL/libart-initialized.so"|cut -c1-16)"

echo "=== 4. RESTORE isolated48 working artifacts ==="
for f in libart-initialized.so libart.so relink.json initialized-relink.json sigchain-initialized.o sigchain-initialized.cc baseline-relinked.so; do
  [ -f "$BK/$f" ] && cp -a "$BK/$f" "$ISO/$f" || true
done
echo "restored 78e34445: $(sha256sum "$ISO/libart-initialized.so"|cut -c1-16) (must be 78e344455ec300f7)"
echo "V3_DONE"
