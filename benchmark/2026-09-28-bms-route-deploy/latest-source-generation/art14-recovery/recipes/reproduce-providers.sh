#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?Set B6_REPO_ROOT to the harness checkout}
W=$ROOT/bms/src/.work/b6-art14-recovery
bash "$ROOT/benchmark/2026-09-28-bms-route-deploy/latest-source-generation/art14-recovery/build-providers.sh"
OHOS_CLANGXX=bms/src/.work/product-tls-generation/frozen/toolchain/bin/clang++ OHOS_SYSROOT=bms/src/.work/product-tls-generation/frozen/sysroot bash bms/src/adapter/build/inner/compile_sigchain_muslcompat.sh
cp bms/src/adapter/out/aosp_lib_arm64/libsigchain.so "$W/build/providers/libsigchain.so"
sed 's/--only=libandroidfw/--only=libicuuc,libandroidfw/' "$W/build-graphics.sh" > "$W/build-graphics-repro.sh"
bash "$W/build-graphics-repro.sh"
bash "$W/relink-zlib.sh"
python3 - "$W" <<'PY'
from pathlib import Path
import sys,hashlib,json
w=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[{'name':f.name,'first':sha(w/'providers-pass1'/f.name),'second':sha(f)} for f in sorted((w/'build/providers').glob('*.so'))]
x={'passed':all(r['first']==r['second'] for r in rows),'providers':rows};(w/'provider-repro.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x));assert x['passed']
PY
