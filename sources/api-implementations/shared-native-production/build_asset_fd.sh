#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  printf '%s\n' 'ADAPTER_ROOT/AOSP_ROOT/OH_ROOT/AOSP_LIB_DIR=<fresh restored original input trees> BUILD_OUT=<new dir> bash build_asset_fd.sh'
  printf '%s\n' 'Original FZ003 dependency-generation binding remains unresolved. This is not the U13/f28 reproduction entry.'
  exit 0
fi
: "${ADAPTER_ROOT:?fresh original source snapshot required}" "${AOSP_ROOT:?pinned original headers required}" "${OH_ROOT:?pinned OH input required}" "${AOSP_LIB_DIR:?original link inputs required}" "${BUILD_OUT:?new output required}"
[[ "$BUILD_OUT" == /* && ! -e "$BUILD_OUT" ]] || exit 2
mkdir -p "$BUILD_OUT"
export BUILD_INNER_INVOKED=1
export ASSET_FD_SOURCE="$HERE/FZ-003/src/android_util_AssetManager_aosp.cpp"
export ANDROID_RUNTIME_BUILD_DIR="$BUILD_OUT/objects" ADAPTER_OUT_DIR="$BUILD_OUT/runtime-out"
set +e
bash "$HERE/FZ-003/recipes/runtime-recipe.sh.original.txt.sh" >"$BUILD_OUT/build.stdout" 2>"$BUILD_OUT/build.stderr"
status=$?
set -e
printf '%s\n' "$status" >"$BUILD_OUT/producer.rc"
cat "$BUILD_OUT/build.stdout"
cat "$BUILD_OUT/build.stderr" >&2
[[ "$status" == 0 ]] || exit "$status"
python3 - "$BUILD_OUT" <<'PY'
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
artifact = out / 'runtime-out/liboh_android_runtime.so'
expected = '53f00423e0a6ddb310029554ee4db785a8f28c6c422abe4f0ba27f6f47dd4fe6'
actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
receipt = {'expected_sha256': expected, 'actual_sha256': actual, 'byte_equal': expected == actual, 'historical_production_proven': False}
(out / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if expected == actual else 3)
PY
