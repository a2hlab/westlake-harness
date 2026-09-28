#!/usr/bin/env bash
set -euo pipefail
A=/home/dspfac/a2hlab/source-closure/verify
W=/home/zhaoyue/a2hlab/ws/westlake-touchfix
O=/home/zhaoyue/a2hlab/ws/out-touchfix
BASE=/home/zhaoyue/a2hlab/ws/out
LOG=/home/zhaoyue/a2hlab/logs/touchfix-8
REV=$1
mkdir -p "$O/$REV"
for name in bridge15 native-imports native-platform media-jni appspawn native-runtime; do
  if [ -e "$O/$name" ]; then mv "$O/$name" "$O/$REV/$name"; fi
done
if [ -e "$O/native-object-map.json" ]; then mv "$O/native-object-map.json" "$O/$REV/native-object-map.json"; fi
python3 "$W/tools/compile_native_inventory.py" --workspace "$A" --westlake-source "$W" --inventory "$W/native/bridge15-sources.json" --header-build "$BASE/oh61-headers" --out "$O/bridge15" --jobs 5 > "$LOG/bridge15-$REV.log" 2>&1
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
o=Path(sys.argv[1]); m=json.loads(Path('/home/zhaoyue/a2hlab/ws/native-object-map.json').read_text());m['liboh_adapter_bridge.so']['build']=str(o/'bridge15');(o/'native-object-map.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
PY
python3 "$W/tools/build_native_imports.py" --workspace "$A" --firmware-abi "$W/native/oh61-firmware-abi.json" --object-map "$O/native-object-map.json" --out "$O/native-imports" > "$LOG/native-imports-$REV.log" 2>&1
python3 "$W/tools/link_native_platform.py" --workspace "$A" --object-map "$O/native-object-map.json" --imports "$O/native-imports" --core-runtime "$BASE/art/runtime" --out "$O/native-platform" > "$LOG/native-platform-$REV.log" 2>&1
(cd /home/zhaoyue/a2hlab/manifest && python3 tools/build_media_jni_compat.py --workspace "$A" --westlake-source "$W" --bridge-build "$O/native-platform" --out "$O/media-jni") > "$LOG/media-jni-$REV.log" 2>&1
python3 "$W/tools/link_appspawn.py" --workspace "$A" --objects "$BASE/appspawn-objects" --runtime "$O/native-platform" --core-runtime "$BASE/art/runtime" --imports "$O/native-imports" --out "$O/appspawn" > "$LOG/appspawn-$REV.log" 2>&1
(cd /home/zhaoyue/a2hlab/manifest && python3 tools/compose_native_runtime.py --build "$BASE/art/runtime" --build "$O/native-platform" --build "$BASE/connectivity-native" --build "$O/media-jni" --build "$BASE/runtime-extras" --build "$BASE/runtime-helpers" --replace libminikin.so --out "$O/native-runtime") > "$LOG/native-runtime-$REV.log" 2>&1
printf 'PASS %s bridge15->native-imports->native-platform->media-jni/appspawn->native-runtime\n' "$REV"
