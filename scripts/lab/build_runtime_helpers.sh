#!/bin/bash
# Runtime libraries westlake loads by name that the manifest flow never composes into native-runtime
# (found by westlake-harness deploy-check):
#   6 public-SDK helpers  westlake tools/build_native.py (ime_helper_capi, network_jni, tls/popen boundary,
#                         process_cpu_time, webview_startup_order); its flat artifacts.json is not composable
#   libwestlake_asset_bridge.so  framework/webview-shim/android_asset_manager_bridge.cpp: the wl_AAsset* ABI the
#                         WebView libandroid shim dlopens when the bridge lacks it; compiled with the exact
#                         android-runtime15 flags and linked against the runtime's own libraries
# Output: $O/runtime-helpers/{*.so, artifacts.json}
set -eu
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out; SDK=$A/toolchains/ohos-sdk/native; WL=$A/westlake
OUT=$O/runtime-helpers; [ -e $OUT ] && { echo "exists: $OUT"; exit 1; }
mkdir -p $OUT/asset
python3 $WL/tools/build_native.py --sdk $SDK --out $OUT/public-sdk
python3 - "$O" "$WL" "$OUT/asset/bridge.o" <<'PY'
import json, subprocess, sys
O, WL, obj = sys.argv[1:4]
cmds = json.load(open(f"{O}/android-runtime15/artifacts.json"))["commands"]
tmpl = next(c for c in cmds if "-c" in c and any("AssetManager" in t for t in c))
out_i = tmpl.index("-o")
src_i = next(i for i, t in enumerate(tmpl) if t.endswith((".cpp", ".cc")) and i != out_i + 1)
cmd = list(tmpl); cmd[src_i] = f"{WL}/framework/webview-shim/android_asset_manager_bridge.cpp"; cmd[out_i + 1] = obj
cmd = [t for t in cmd if not t.startswith(("-MD", "-MF")) and not (t.endswith(".d") and cmd[cmd.index(t) - 1] == "-MF")]
subprocess.run(cmd, check=True)
PY
R=$O/art/runtime; I=$O/native-imports
$SDK/llvm/bin/clang++ --target=aarch64-linux-ohos --sysroot=$SDK/sysroot -fuse-ld=lld -nostdlib -shared -Wl,-z,defs \
  -Wl,--build-id=sha1 -Wl,-soname,libwestlake_asset_bridge.so -Wl,--as-needed $OUT/asset/bridge.o \
  $R/libandroidfw.so $R/libutils.so $R/libcutils.so $R/libbase.so $R/liblog.so $R/libnativehelper.so \
  $O/native-platform/liboh_android_runtime.so $I/libc++.so $I/libc.so -o $OUT/libwestlake_asset_bridge.so
cp $OUT/public-sdk/*.so $OUT/
python3 - $OUT <<'PY'
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
arts = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in sorted(out.glob("*.so"))}
(out / "artifacts.json").write_text(json.dumps({"artifacts": arts, "errors": []}, indent=2) + "\n")
for n, a in arts.items(): print(f"{a['bytes']:>9} {n}")
PY
