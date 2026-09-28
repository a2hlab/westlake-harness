#!/usr/bin/env bash
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd -P)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/unity-identity.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
GEN_ID=identity-selftest-r1
GEN=$WORK/$GEN_ID
CARD=$WORK/cardwords
LLVM=${OH_LLVM_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin}
CC=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${OH_CC:-$LLVM/clang}")
READELF=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${OH_READELF:-$LLVM/llvm-readelf}")
OBJCOPY=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${OH_OBJCOPY:-$LLVM/llvm-objcopy}")
for tool in "$CC" "$READELF" "$OBJCOPY"; do test -x "$tool"; done
mkdir -p "$GEN/meta" "$GEN/payload/adapter" "$CARD/lib/arm64-v8a"

build_so()
{
    local output=$1 soname=$2 symbol=$3
    printf 'void %s(void) {}\n' "$symbol" >"$WORK/$symbol.c"
    "$CC" --target=aarch64-linux-ohos -nostdlib -shared -fPIC \
        -Wl,--build-id=sha1 -Wl,-soname,"$soname" \
        "$WORK/$symbol.c" -o "$output"
}

build_so "$GEN/payload/adapter/libruntime.so" libruntime.so runtime_entry
build_so "$CARD/lib/arm64-v8a/libmain.so" libmain.so main_entry
build_so "$CARD/lib/arm64-v8a/libunity.so" libunity.so unity_entry
build_so "$CARD/lib/arm64-v8a/libil2cpp.so" libil2cpp.so il2cpp_entry
build_so "$CARD/lib/arm64-v8a/lib_burst_generated.so" \
    lib_burst_generated.so burst_entry

python3 - "$GEN" "$CARD" <<'PY'
import hashlib, json, sys
from pathlib import Path
gen, card = map(Path, sys.argv[1:])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest = gen / "meta/generation.json"
manifest.write_text(json.dumps({
  "schema": "westlake.l03_a12.provider_closure.v3",
  "generation_id": gen.name,
  "artifacts": [{"role": "runtime", "path": "adapter/libruntime.so",
                 "sha256": sha(gen / "payload/adapter/libruntime.so")}]
}, sort_keys=True))
manifest_sha = sha(manifest)
(card / "native-bundle.json").write_text(json.dumps({
  "schema": "westlake.cardwords.native_bundle.v1",
  "generation_id": gen.name,
  "generation_manifest_sha256": manifest_sha,
  "generation_token": f"wlgen-{gen.name}-{manifest_sha}",
  "artifacts": [
    {"role": "libmain", "path": "lib/arm64-v8a/libmain.so",
     "sha256": sha(card / "lib/arm64-v8a/libmain.so")},
    {"role": "libunity", "path": "lib/arm64-v8a/libunity.so",
     "sha256": sha(card / "lib/arm64-v8a/libunity.so")},
    {"role": "libil2cpp", "path": "lib/arm64-v8a/libil2cpp.so",
     "sha256": sha(card / "lib/arm64-v8a/libil2cpp.so")},
    {"role": "lib_burst_generated",
     "path": "lib/arm64-v8a/lib_burst_generated.so",
     "sha256": sha(card / "lib/arm64-v8a/lib_burst_generated.so")}
  ]
}, sort_keys=True))
PY

run_gate()
{
    python3 "$HERE/write_identity_receipt.py" \
        --generation-root "$GEN" \
        --generation-manifest "$GEN/meta/generation.json" \
        --cardwords-root "$CARD" \
        --cardwords-receipt "$CARD/native-bundle.json" \
        --readelf "$READELF" --output "$1"
}

run_gate "$WORK/positive.json" | grep -q '^UNITY_IDENTITY_PASS '
echo PASS positive

cp "$CARD/native-bundle.json" "$WORK/card.receipt.good"
python3 - "$CARD/native-bundle.json" <<'PY'
import json, sys
p=sys.argv[1]; v=json.load(open(p)); v["generation_id"]="other-generation"
open(p,"w").write(json.dumps(v))
PY
if run_gate "$WORK/mixed.json" 2>"$WORK/mixed.err"; then exit 1; fi
grep -q 'mixed generation' "$WORK/mixed.err"
echo PASS mixed_generation_rejected
cp "$WORK/card.receipt.good" "$CARD/native-bundle.json"

python3 - "$CARD/native-bundle.json" <<'PY'
import json, sys
p=sys.argv[1]; v=json.load(open(p)); v["artifacts"][0]["sha256"]="0"*64
open(p,"w").write(json.dumps(v))
PY
if run_gate "$WORK/sha.json" 2>"$WORK/sha.err"; then exit 1; fi
grep -q 'SHA256 mismatch' "$WORK/sha.err"
echo PASS sha_rejected
cp "$WORK/card.receipt.good" "$CARD/native-bundle.json"

"$OBJCOPY" --remove-section .note.gnu.build-id "$CARD/lib/arm64-v8a/libunity.so"
if run_gate "$WORK/buildid.json" 2>"$WORK/buildid.err"; then exit 1; fi
grep -q 'one exact 8-64-byte Build-ID' "$WORK/buildid.err"
echo PASS build_id_rejected

echo UNITY_IDENTITY_SELFTEST_PASS
