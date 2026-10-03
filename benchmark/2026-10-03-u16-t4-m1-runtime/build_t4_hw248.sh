#!/usr/bin/env bash
# Runs ON hw248. U16 t4 = U15 runtime M3 (94c31177) with cc-wiki's M1 split applied:
#   - the android_graphics_compat_shim.o argv item -> shim_split.o (baseline + one call;
#     object A′-proven vs the deployed 612236be in benchmark/2026-10-03-m1-split)
#   - m1_copy.o appended right after it (the TU carrying the m1_* payload)
#   - EGLImpl.o keeps the m3-a object (M3's EGL fix stays in)
# Two passes (a, b) must be byte-identical. Mirrors build_m3_hw248.sh's link mechanics.
set -euo pipefail
# The hw248 mirror root is injected by the caller (keeps host paths out of the repo file):
: "${T4_ROOT:?set T4_ROOT=<hw248 mirror root (the cc-t3-u15rt-m3 tree)>}"
R=$T4_ROOT
cd "$R"

# argv sanity on the pristine list (before any rewrite)
grep -c . "$R/link-argv.txt" | grep -qx 112 || { echo "link-argv.txt is not 112 items"; exit 8; }

for TAG in a b; do
  D=$R/t4-$TAG
  rm -rf "$D"; mkdir -p "$D/out"
  cp "$R/shim_split.o" "$R/m1_copy.o" "$D/"
  sha256sum "$D/shim_split.o" "$D/m1_copy.o" | cut -c1-16

  python3 - "$R/link-argv.txt" "$D/argv.txt" "$R" "$D" << 'PY'
import sys
src, dst, R, D = sys.argv[1:5]
items = [l.rstrip('\n') for l in open(src) if l.strip('\n') != '']
out, n_shim, n_egl, n_out = [], 0, 0, 0
for it in items:
    if it.endswith('/n4-native/gl/EGLImpl.o'):
        out.append(R + '/m3-a/EGLImpl.o'); n_egl += 1          # keep M3's EGL object
    elif it.endswith('/rt/runtime-objects/android_graphics_compat_shim.o'):
        out.append(D + '/shim_split.o'); n_shim += 1            # the split shim
        out.append(D + '/m1_copy.o')                            # ... and its new TU right after
    elif it == R + '/rt/out/liboh_android_runtime.so':
        out.append(D + '/out/liboh_android_runtime.so'); n_out += 1
    else:
        out.append(it)
assert n_shim == 1 and n_egl == 1 and n_out == 1, (n_shim, n_egl, n_out)
open(dst, 'w').write('\n'.join(out) + '\n')
print('argv items:', len(out), '(112 + m1_copy.o)')
PY

  cp "$R/rt/out/libwestlake_thread_guard_registry.so" "$D/out/"
  mapfile -t A < "$D/argv.txt"
  (cd "$R/rt" && "${A[@]}") > "$D/link.log" 2>&1
  echo "t4-$TAG built:"; sha256sum "$D/out/liboh_android_runtime.so" | cut -c1-16
done

cmp "$R/t4-a/out/liboh_android_runtime.so" "$R/t4-b/out/liboh_android_runtime.so" \
  && echo "TWO PASSES BYTE-IDENTICAL" || { echo "PASSES DIFFER"; exit 9; }
sha256sum "$R/t4-a/out/liboh_android_runtime.so"
