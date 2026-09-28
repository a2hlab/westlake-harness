#!/bin/bash
# Runtime libraries westlake main loads by name that no manifest build produces:
#   libwl_opengl_jni.so     tools/build_opengl_jni.sh (d77e993)
#   libwl_missing_natives.so framework/javacore-shim/missing_natives.c (e6e67ae, 7d5a349)
# Output: $O/runtime-extras/{lib...so, artifacts.json}
set -eu
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out; SDK=$A/toolchains/ohos-sdk/native; WL=$A/westlake; AS=$A/android-source
OUT=$O/runtime-extras; [ -e $OUT ] && { echo "exists: $OUT"; exit 1; }
mkdir -p $OUT/opengl/lib
for l in libnativehelper.so liblog.so; do
  src=$(find $O/native-runtime $O/art/runtime -maxdepth 2 -name $l | head -1); [ -n "$src" ] || { echo "missing runtime $l"; exit 1; }
  ln -s "$src" $OUT/opengl/lib/$l
done
bash $WL/tools/build_opengl_jni.sh $AS $SDK $OUT/opengl
mv $OUT/opengl/libwl_opengl_jni.so $OUT/; rm -rf $OUT/opengl
$SDK/llvm/bin/clang --target=aarch64-linux-ohos --sysroot=$SDK/sysroot -fPIC -O2 -Wall -Wextra -shared -fuse-ld=lld \
  -Wl,-z,defs -Wl,--build-id=sha1 -Wl,-soname,libwl_missing_natives.so -I$AS/libnativehelper/include_jni \
  $WL/framework/javacore-shim/missing_natives.c -lm -o $OUT/libwl_missing_natives.so
python3 - $OUT <<'PY'
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
arts = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in sorted(out.glob("*.so"))}
(out / "artifacts.json").write_text(json.dumps({"artifacts": arts, "errors": []}, indent=2) + "\n")
print(json.dumps(arts, indent=1))
PY
