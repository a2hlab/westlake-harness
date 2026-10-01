#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?usage: build-facade.sh output-directory (set OH_CLANG to pinned OH clang)}"
CLANG="${OH_CLANG:?set OH_CLANG to the pinned OpenHarmony clang executable}"
mkdir -p "$OUT"
test ! -e "$OUT/libOpenSLES.so"
"$CLANG" --target=aarch64-linux-ohos -std=c11 -O2 -fPIC -ffreestanding \
  -fno-stack-protector -mno-outline-atomics -fvisibility=hidden -nostdlib -shared \
  -fuse-ld=lld -Wl,-soname,libOpenSLES.so -Wl,--no-undefined -Wl,-Bsymbolic -Wl,-z,now -Wl,-z,relro \
  -Wl,--build-id=sha1 -I"$HERE" "$HERE/opensles-owner.c" -o "$OUT/libOpenSLES.so"
"$CLANG" --version > "$OUT/compiler-version.txt"
python3 - "$HERE" "$OUT" "$CLANG" <<'PY'
import hashlib,json,pathlib,sys,subprocess
here,out,compiler=map(pathlib.Path,sys.argv[1:])
digest=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
receipt=dict(status='facade-built-only-not-host-or-package',compiler_sha256=digest(compiler.resolve()),
    compiler_version=(out/'compiler-version.txt').read_text(),
    artifact_sha256=digest(out/'libOpenSLES.so'),
    sources={name:digest(here/name) for name in ['opensles-owner.c','opensles-owner.h','build-facade.sh']})
resource=pathlib.Path(subprocess.check_output([str(compiler),'-print-resource-dir'],text=True).strip())
receipt['resource_headers']={name:digest(resource/'include'/name) for name in ['stdint.h','stdatomic.h','stddef.h']}
receipt['linker_sha256']=digest((compiler.parent/'ld.lld').resolve())
(out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
