#!/usr/bin/env bash
set -euo pipefail

MODULE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
PROJECT=$(cd "$MODULE/../../.." && pwd -P)
GEN=${WL_PALETTE_PROVIDER_INPUTS:-$PROJECT/.work/bionic-musl-provider/provider-inputs-v12-nobroadstub}
OUT=${WL_PALETTE_TARGET_OUT:-$PROJECT/.work/art-palette-oh/target}
case "$GEN" in "$PROJECT"/*) ;; *) echo "inputs escaped project" >&2; exit 2;; esac
case "$OUT" in "$PROJECT"/*) ;; *) echo "output escaped project" >&2; exit 2;; esac
for required in "$GEN/frozen" "$GEN/artifacts/providers/liblog.so"; do
    test -e "$required" && test ! -L "$required"
done
mkdir -p "$OUT/pass1" "$OUT/pass2"

for pass in pass1 pass2; do
    docker run --rm \
        --platform linux/amd64 \
        --network none \
        --read-only \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        -v "$GEN/frozen:/inputs:ro" \
        -v "$GEN/artifacts/providers:/providers:ro" \
        -v "$MODULE:/module:ro" \
        -v "$OUT/$pass:/out:rw" \
        westlake-oharm64build:local-tools \
        bash -lc '
          set -eu
          TC=/inputs/oh/toolchain
          SR=/inputs/oh/out/wukong100/obj/third_party/musl
          export LD_LIBRARY_PATH=$TC/runtime
          $TC/bin/clang-15 --target=aarch64-linux-ohos --sysroot=$SR \
            -I$SR/include/aarch64-linux-ohos -fPIC -O2 -D__OHOS__ \
            -D_GNU_SOURCE -D_POSIX_SOURCE -std=c11 \
            -c /module/src/palette_oh.c -o /out/palette_oh.o
          $TC/bin/clang++ --target=aarch64-linux-ohos --sysroot=$SR \
            -B$SR/lib/aarch64-linux-ohos -fuse-ld=lld -shared -fPIC \
            -nostdlib++ -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
            -Wl,--build-id=sha1 -Wl,-soname,libartpalette-system.so \
            -L/providers -L$SR/lib/aarch64-linux-ohos \
            -o /out/libartpalette-system.so /out/palette_oh.o \
            -lc -llog -ldl -lpthread \
            $TC/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
        '
done

cmp "$OUT/pass1/libartpalette-system.so" \
    "$OUT/pass2/libartpalette-system.so"

docker run --rm \
    --platform linux/amd64 \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$GEN/frozen:/inputs:ro" \
    -v "$OUT/pass1:/out:ro" \
    westlake-oharm64build:local-tools \
    bash -lc '
      set -eu
      R=/inputs/oh/toolchain/bin/llvm-readelf
      D=$($R --dynamic-table /out/libartpalette-system.so)
      H=$($R --file-header /out/libartpalette-system.so)
      S=$($R --dyn-syms --wide /out/libartpalette-system.so)
      printf "%s" "$H" | grep -q "Class:.*ELF64"
      printf "%s" "$H" | grep -q "Machine:.*AArch64"
      printf "%s" "$D" | grep -q "SONAME.*libartpalette-system.so"
      test "$(printf "%s" "$D" | grep -c "NEEDED")" = 2
      printf "%s" "$D" | grep -q "NEEDED.*libc.so"
      printf "%s" "$D" | grep -q "NEEDED.*liblog.so"
      ! printf "%s" "$D" | grep -Eq "RPATH|RUNPATH|TEXTREL"
      printf "%s" "$S" | grep -q "UND setpriority"
      printf "%s" "$S" | grep -q "UND getpriority"
      printf "%s" "$S" | grep -q "PaletteSchedSetPriority"
      printf "%s" "$S" | grep -q "PaletteSchedGetPriority"
    '

sha=$(shasum -a 256 "$OUT/pass1/libartpalette-system.so" | awk '{print $1}')

# Integration fixture: replace only the dormant v12 fake Palette provider in
# both deterministic base sets. The v2 provider policy must accept the real
# scheduler artifact while rejecting the untouched v12 fake under that policy.
FIXTURE="$OUT/provider-fixture"
rm -rf -- "$FIXTURE"
mkdir -p "$FIXTURE/primary/providers" "$FIXTURE/repro/providers" \
    "$FIXTURE/evidence"
cp "$GEN/artifacts/providers/"*.so "$FIXTURE/primary/providers/"
cp "$GEN/artifacts-repro/providers/"*.so "$FIXTURE/repro/providers/"
cp "$OUT/pass1/libartpalette-system.so" \
    "$FIXTURE/primary/providers/libartpalette-system.so"
cp "$OUT/pass2/libartpalette-system.so" \
    "$FIXTURE/repro/providers/libartpalette-system.so"
docker run --rm \
    --platform linux/amd64 \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$GEN/frozen:/inputs:ro" \
    -v "$FIXTURE/primary:/primary:ro" \
    -v "$FIXTURE/repro:/repro:ro" \
    -v "$PROJECT/adapter/build/provider_generation/verify_generation.py:/verify.py:ro" \
    -v "$FIXTURE/evidence:/evidence:rw" \
    westlake-oharm64build:local-tools \
    /usr/bin/python3 /verify.py \
      --readelf /inputs/oh/toolchain/bin/llvm-readelf \
      --primary /primary --repro /repro \
      --policy no-broad-art-stub-real-palette-v2 \
      --output /evidence/verification.json
python3 - "$FIXTURE/evidence/verification.json" <<'PY'
import json
import sys
from pathlib import Path
result = json.loads(Path(sys.argv[1]).read_text())
assert result["provider_count"] == 23
assert result["broad_art_runtime_stub_absent"] is True
assert result["real_palette_scheduler"] is True
assert result["product_activation"] is False
PY

set +e
docker run --rm \
    --platform linux/amd64 \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$GEN/frozen:/inputs:ro" \
    -v "$GEN/artifacts:/primary:ro" \
    -v "$GEN/artifacts-repro:/repro:ro" \
    -v "$PROJECT/adapter/build/provider_generation/verify_generation.py:/verify.py:ro" \
    westlake-oharm64build:local-tools \
    /usr/bin/python3 /verify.py \
      --readelf /inputs/oh/toolchain/bin/llvm-readelf \
      --primary /primary --repro /repro \
      --policy no-broad-art-stub-real-palette-v2 \
      --output /tmp/forbidden.json \
      >"$FIXTURE/v12-fake.stdout" 2>"$FIXTURE/v12-fake.stderr"
fake_rc=$?
set -e
test "$fake_rc" -ne 0
grep -q 'real OH Palette provider must need exactly' \
    "$FIXTURE/v12-fake.stderr"

echo "PASS art_palette_oh_target deterministic=2 real_sched_imports=2 provider_policy_v2=pass old_fake_rejected=1 sha256=$sha"
