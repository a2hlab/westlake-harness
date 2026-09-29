#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0

ROOT=${ROUTE_A_PROJECT_ROOT:-/project}
PLUGIN=$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
ADAPTER=$ROOT/adapter/framework/appspawn-x
FROZEN=$ROOT/adapter/frozen/references/oh-appspawn-security-v7
LEDGER_DIR=${WESTLAKE_ROUTE_A_LEDGER_DIR:-$PLUGIN}
ROUTE_A_INPUTS=$LEDGER_DIR/ROUTE_A_INPUTS.json
SOURCE_CLOSURE=$LEDGER_DIR/SOURCE_CLOSURE.json
OUT=${WESTLAKE_ROUTE_A_TARGET_OUTPUT_ROOT:-$PLUGIN/out/target}
ROUTE_OUT=${WESTLAKE_ROUTE_A_OUTPUT_ROOT:-$PLUGIN/out/route-a-generation}
GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$ROOT/.work/product-tls-generation}
TOOLCHAIN=$GENERATION_ROOT/frozen/toolchain
SYSROOT=$GENERATION_ROOT/frozen/sysroot
TARGET_LIB=$SYSROOT/lib/aarch64-linux-ohos
RUNTIME_FROZEN=$PLUGIN/frozen/runtime_provider
STOCK_HOST_FROZEN=$PLUGIN/frozen/stock_host
TARGET_EXTERNAL=$PLUGIN/frozen/target_external/openharmony-6.1.0.31-d600
SYSTEMPARAM_ORIGIN=$TARGET_EXTERNAL/libsystemparam.z.so
UBSAN_ORIGIN=$TARGET_EXTERNAL/libclang_rt.ubsan_minimal.so
CC=$TOOLCHAIN/bin/clang-15
READELF=$TOOLCHAIN/bin/llvm-readelf
OBJDUMP=$TOOLCHAIN/bin/llvm-objdump

[[ ${WLASC_P0_TYPED_REJECT_CAPABILITIES:-} == 1 ]] || {
    echo "ERROR this P0 target requires typed-reject hook isolation" >&2
    exit 1
}

INCLUDES=(
    -include "$ROOT/adapter/framework/app-native-loader/include/oh_dlns_abi.h"
    -I"$PLUGIN/include"
    -I"$ROOT/adapter/framework/app-native-loader/include"
    -I"$ADAPTER/src"
    -I"$FROZEN/base/startup/appspawn/common"
    -I"$FROZEN/base/startup/appspawn/standard"
    -I"$FROZEN/base/startup/appspawn/modules/module_engine/include"
    -I"$FROZEN/base/startup/appspawn/modules/modulemgr"
    -I"$FROZEN/base/startup/appspawn/modules/common"
    -I"$FROZEN/base/startup/appspawn/util/include"
    -I"$FROZEN/base/startup/appspawn/interfaces/innerkits/include"
    -I"$FROZEN/base/startup/init/interfaces/innerkits/include"
    -I"$FROZEN/base/startup/init/interfaces/innerkits/include/syspara"
    -I"$FROZEN/third_party/cJSON"
    -I"$FROZEN/interface/sdk_c/hiviewdfx/hilog/include"
    -I"$FROZEN/third_party/bounds_checking_function/include"
)

for input in \
    "$CC" \
    "$TOOLCHAIN/bin/ld.lld" \
    "$READELF" \
    "$OBJDUMP" \
	    "$ROUTE_A_INPUTS" \
    "$PLUGIN/generate_route_a_inputs.py" \
	    "$SOURCE_CLOSURE" \
    "$PLUGIN/include/westlake_android_child_plugin.h" \
    "$PLUGIN/include/sealed_child_provider_loader.h" \
    "$ROOT/adapter/framework/app-native-loader/include/oh_dlns_abi.h" \
    "$PLUGIN/include/westlake_child_hook_table_v1.h" \
    "$PLUGIN/include/westlake_stock_host_services.h" \
    "$PLUGIN/include/westlake_elf_identity.h" \
    "$PLUGIN/include/westlake_sha256.h" \
    "$PLUGIN/src/stage_receipt.c" \
    "$PLUGIN/src/sealed_child_provider_loader.c" \
    "$PLUGIN/src/child_hook_table_v1.c" \
    "$PLUGIN/src/westlake_android_child_plugin.c" \
    "$PLUGIN/src/westlake_elf_identity.c" \
    "$PLUGIN/src/westlake_sha256.c" \
    "$PLUGIN/src/westlake_stock_host_main.c" \
    "$PLUGIN/tests/test_child_hook_table_v1.c" \
    "$PLUGIN/tests/test_westlake_child_hook_table_v1_layout.c" \
    "$PLUGIN/tests/test_sealed_child_provider_loader.c" \
    "$PLUGIN/stock_host_patched/base/startup/appspawn/standard/appspawn_service.c" \
    "$PLUGIN/westlake_android_child_plugin.map" \
    "$PLUGIN/verify_target_artifacts.py" \
    "$ADAPTER/src/native_compat_prepare.h" \
    "$FROZEN/base/startup/appspawn/standard/appspawn_manager.h" \
    "$FROZEN/base/startup/appspawn/common/appspawn_server.h" \
    "$FROZEN/base/startup/appspawn/modules/module_engine/include/appspawn_hook.h" \
    "$FROZEN/base/startup/appspawn/modules/module_engine/include/appspawn_msg.h" \
    "$ROUTE_OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
    "$ROUTE_OUT/pass2/provider/libwestlake_android_runtime_provider.so" \
    "$TARGET_LIB/libc.so" \
    "$RUNTIME_FROZEN/libraries/oh/libc++.so" \
    "$GENERATION_ROOT/frozen/libraries/oh/libhilog.so" \
    "$STOCK_HOST_FROZEN/libraries/libbegetutil.z.so" \
    "$STOCK_HOST_FROZEN/libraries/libconfigpolicy_util.z.so" \
    "$STOCK_HOST_FROZEN/libraries/libsec_shared.z.so" \
    "$TARGET_EXTERNAL/SHA256SUMS" \
    "$TARGET_EXTERNAL/libbegetutil.z.so" \
    "$TARGET_EXTERNAL/libc++.so" \
    "$TARGET_EXTERNAL/libc.so" \
    "$TARGET_EXTERNAL/libconfigpolicy_util.z.so" \
    "$TARGET_EXTERNAL/libhilog.so" \
    "$TARGET_EXTERNAL/libsec_shared.z.so" \
    "$SYSTEMPARAM_ORIGIN" \
    "$TARGET_EXTERNAL/libutils.z.so" \
    "$UBSAN_ORIGIN"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing project-local target input: $input" >&2
        exit 1
    }
done

(
    cd "$TARGET_EXTERNAL"
    sha256sum -c SHA256SUMS >/dev/null
)

python3 "$PLUGIN/generate_route_a_inputs.py" --verify
GENERATION_SHA=$(sha256sum "$ROUTE_A_INPUTS" | awk '{print $1}')
[[ $GENERATION_SHA =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR invalid Route-A generation identity" >&2
    exit 1
}
# The plugin note and its compiled contract use an input-derived identity,
# never a digest of the output that would create a self-reference.
PLUGIN_BUILD_ID_HEX=${GENERATION_SHA:0:40}
[[ $PLUGIN_BUILD_ID_HEX =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR invalid deterministic plugin Build-ID" >&2
    exit 1
}

mkdir -p "$OUT/pass1" "$OUT/pass2" "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

run()
{
    printf '%q ' "$@" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$@"
}

compile()
{
    local source=$1
    local output=$2
    shift 2
    # -ffreestanding clears __STDC_HOSTED__, which stops the compiler's own
    # <limits.h> from chaining on to the C library's copy.  The plugin sources
    # still ask <limits.h> for PATH_MAX, so name the libc include directory
    # explicitly instead of relying on that chain; musl's limits.h is
    # self-contained and supplies the freestanding subset as well.
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -std=c11 \
        -O2 \
        -Wall \
        -Wextra \
        -Werror \
        -Wno-zero-length-array \
        -Wno-gnu-zero-variadic-macro-arguments \
        -ffreestanding \
        -fPIC \
        -fvisibility=hidden \
        -fno-stack-protector \
        -fno-unwind-tables \
        -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -DSUPPORT_64BIT \
        -D__MUSL__ \
        -D__OHOS__ \
        -D_GNU_SOURCE \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -isystem "$SYSROOT/include/aarch64-linux-ohos" \
        -isystem "$SYSROOT/include" \
        "${INCLUDES[@]}" \
        "$@" \
        -c "$source" \
        -o "$output"
}

generate_sealed_manifest()
{
    local pass=$1
    local output=$2
    local root=$ROUTE_OUT/$pass/provider/libwestlake_android_runtime_provider.so
    local deploy_dir=/system/lib64/westlake/route-a/$GENERATION_SHA
    python3 - "$root" "$ROUTE_OUT/providers" "$READELF" \
        "$deploy_dir" "$GENERATION_SHA" "$output" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]).resolve(strict=True)
provider_dir = Path(sys.argv[2]).resolve(strict=True)
readelf = Path(sys.argv[3]).resolve(strict=True)
deploy_dir = sys.argv[4]
generation = sys.argv[5]
output = Path(sys.argv[6])

if not deploy_dir.startswith("/") or not re.fullmatch(r"[0-9a-f]{64}", generation):
    raise SystemExit("invalid sealed generation/deploy identity")

candidates = {root.name: root}
for path in sorted(provider_dir.glob("*.so")):
    if path.name in candidates:
        raise SystemExit(f"duplicate sealed SONAME candidate: {path.name}")
    candidates[path.name] = path.resolve(strict=True)

def inspect(path: Path) -> tuple[str, list[str], str]:
    dynamic = subprocess.run(
        [str(readelf), "-dW", str(path)], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout
    notes = subprocess.run(
        [str(readelf), "-nW", str(path)], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout
    sonames = re.findall(r"\(SONAME\).*?\[([^]]+)\]", dynamic)
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
    build_ids = re.findall(r"Build ID:\s*([0-9a-f]+)", notes)
    if sonames != [path.name] or len(build_ids) != 1 or len(build_ids[0]) not in (32, 40):
        raise SystemExit(f"unsealed ELF identity: {path}")
    return sonames[0], needed, build_ids[0]

metadata: dict[str, tuple[Path, list[str], str]] = {}
pending = [root.name]
while pending:
    name = pending.pop()
    if name in metadata:
        continue
    path = candidates.get(name)
    if path is None:
        raise SystemExit(f"sealed closure member missing: {name}")
    soname, needed, build_id = inspect(path)
    sealed_needed = [dependency for dependency in needed
                     if dependency in candidates]
    metadata[soname] = (path, sealed_needed, build_id)
    pending.extend(sealed_needed)

names = [root.name] + sorted(set(metadata) - {root.name})
if not 0 < len(names) <= 64:
    raise SystemExit(f"sealed closure size invalid: {len(names)}")
indices = {name: index for index, name in enumerate(names)}
lines = [
    '#include "sealed_child_provider_loader.h"',
    '',
    'static const WlscplArtifactV1 kWlscplArtifacts[] = {',
]
for name in names:
    path, needed, build_id = metadata[name]
    if len(needed) > 32:
        raise SystemExit(f"too many sealed dependencies: {name}")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact_path = f"{deploy_dir}/{name}"
    if name == "libwestlake_thread_guard_registry.so":
        artifact_path = "/system/lib64/libwestlake_thread_guard_registry.so"
    if name == "liblzma.so":
        artifact_path = "/system/android/lib64/liblzma.so"
    if name == "libbionic_compat.so":
        artifact_path = "/system/android/lib64/libbionic_compat.so"
    needed_values = ", ".join(f"UINT32_C({indices[item]})" for item in needed)
    needed_initializer = "{" + needed_values + "}" if needed_values else "{0}"
    lines.extend([
        '    {',
        f'        "{artifact_path}",',
        f'        "{sha}",',
        f'        "{build_id}",',
        f'        "{name}",',
        f'        UINT32_C({len(needed)}),',
        f'        {needed_initializer},',
        '    },',
    ])
lines.extend([
    '};',
    '',
    'static const WlscplManifestV1 kWlscplManifest = {',
    '    WLSCPL_ABI_VERSION,',
    '    (uint32_t)sizeof(WlscplManifestV1),',
    '    UINT16_C(183),',
    '    UINT16_C(0),',
    f'    UINT32_C({len(names)}),',
    '    UINT32_C(0),',
    f'    UINT64_C(0x{generation[:16]}),',
    '    kWlscplArtifacts,',
    '};',
    '',
    'const WlscplManifestV1 *WLSCPL_GetBuildGeneratedManifest(void)',
    '{',
    '    return &kWlscplManifest;',
    '}',
    '',
])
output.write_text("\n".join(lines), encoding="utf-8")
PY
}

build_pass()
{
    local pass=$1
    local dir=$OUT/$pass
    generate_sealed_manifest "$pass" "$dir/sealed_provider_manifest.c"
    compile "$PLUGIN/src/stage_receipt.c" "$dir/stage_receipt.o"
    compile "$PLUGIN/src/sealed_child_provider_loader.c" "$dir/sealed_child_provider_loader.o"
    compile "$PLUGIN/src/child_hook_table_v1.c" \
        "$dir/child_hook_table_v1.o" \
        "-DWLASC_P0_TYPED_REJECT_CAPABILITIES=$WLASC_P0_TYPED_REJECT_CAPABILITIES"
    compile "$PLUGIN/src/westlake_elf_identity.c" \
        "$dir/westlake_elf_identity.o"
    compile "$PLUGIN/src/westlake_sha256.c" \
        "$dir/westlake_sha256.o"
    compile "$dir/sealed_provider_manifest.c" \
        "$dir/sealed_provider_manifest.o"
    compile "$PLUGIN/src/westlake_android_child_plugin.c" \
        "$dir/westlake_android_child_plugin.o" \
        "-DWLASC_PLUGIN_GENERATION_SHA_HEX=\"$GENERATION_SHA\"" \
        "-DWLASC_PLUGIN_BUILD_ID_HEX=\"$PLUGIN_BUILD_ID_HEX\"" \
        "-DWLAR_GENERATION_SHA_HEX=\"$GENERATION_SHA\""
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fuse-ld=lld \
        -nostdlib \
        -shared \
        -Wl,-z,defs \
        -Wl,--no-allow-shlib-undefined \
        -Wl,--no-undefined \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--fatal-warnings \
        "-Wl,--build-id=0x$PLUGIN_BUILD_ID_HEX" \
        -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_android_child.z.so \
        -Wl,--version-script="$PLUGIN/westlake_android_child_plugin.map" \
        -L"$ROUTE_OUT/$pass/provider" \
        -L"$ROUTE_OUT/$pass/compat" \
        -L"$ROUTE_OUT/$pass/app-loader" \
        -L"$RUNTIME_FROZEN/provider-v12/providers" \
        -L"$RUNTIME_FROZEN/provider-v12/dependencies" \
        -L"$RUNTIME_FROZEN/libraries/oh" \
        -L"$TARGET_LIB" \
        "$dir/stage_receipt.o" \
        "$dir/sealed_child_provider_loader.o" \
        "$dir/child_hook_table_v1.o" \
        "$dir/westlake_android_child_plugin.o" \
        "$dir/westlake_elf_identity.o" \
        "$dir/westlake_sha256.o" \
        "$dir/sealed_provider_manifest.o" \
        -Wl,--no-as-needed -ldl -lc \
        -Wl,--as-needed \
        -o "$dir/libwestlake_android_child.z.so"

    local plugin_sha
    local plugin_build_id
    plugin_sha=$(sha256sum "$dir/libwestlake_android_child.z.so" | awk '{print $1}')
    plugin_build_id=$(
        "$READELF" -nW "$dir/libwestlake_android_child.z.so" |
            awk '/Build ID:/ {print $3; exit}'
    )
    [[ $plugin_sha =~ ^[0-9a-f]{64}$ &&
       $plugin_build_id == "$PLUGIN_BUILD_ID_HEX" ]] || {
        echo "ERROR plugin identity derivation failed for $pass" >&2
        exit 1
    }
    compile "$PLUGIN/src/westlake_stock_host_main.c" \
        "$dir/westlake_stock_host_main.o" \
        "-DWLASC_PLUGIN_GENERATION_SHA_HEX=\"$GENERATION_SHA\"" \
        "-DWLASC_PLUGIN_BUILD_ID_HEX=\"$PLUGIN_BUILD_ID_HEX\"" \
        "-DWLASC_PLUGIN_ELF_SHA256_HEX=\"$plugin_sha\"" \
        "-DWLAR_GENERATION_SHA_HEX=\"$GENERATION_SHA\""
    compile "$PLUGIN/stock_host_patched/base/startup/appspawn/standard/appspawn_service.c" \
        "$dir/appspawn_service_fail_closed.o" -Wno-everything
}

build_pass pass1
build_pass pass2
cmp "$OUT/pass1/libwestlake_android_child.z.so" \
    "$OUT/pass2/libwestlake_android_child.z.so"
cmp "$OUT/pass1/sealed_provider_manifest.c" \
    "$OUT/pass2/sealed_provider_manifest.c"
cmp "$OUT/pass1/westlake_stock_host_main.o" \
    "$OUT/pass2/westlake_stock_host_main.o"
cmp "$OUT/pass1/appspawn_service_fail_closed.o" \
    "$OUT/pass2/appspawn_service_fail_closed.o"

cp "$OUT/pass1/libwestlake_android_child.z.so" \
   "$OUT/libwestlake_android_child.z.so"
cp "$OUT/pass1/sealed_provider_manifest.c" \
   "$OUT/sealed_provider_manifest.c"
cp "$OUT/pass1/westlake_stock_host_main.o" \
   "$OUT/westlake_stock_host_main.o"
cp "$OUT/pass1/appspawn_service_fail_closed.o" \
   "$OUT/appspawn_service_fail_closed.o"

python3 "$PLUGIN/verify_target_artifacts.py" \
    --project-root "$ROOT" \
    --artifact-root "$OUT" \
    --tool-root "$TOOLCHAIN" \
    --plugin "$OUT/libwestlake_android_child.z.so" \
    --second-plugin "$OUT/pass2/libwestlake_android_child.z.so" \
    --host-object "$OUT/westlake_stock_host_main.o" \
    --second-host-object "$OUT/pass2/westlake_stock_host_main.o" \
    --service-object "$OUT/appspawn_service_fail_closed.o" \
    --second-service-object "$OUT/pass2/appspawn_service_fail_closed.o" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/verification.json"

sha256sum \
    "$PLUGIN/include/westlake_android_child_plugin.h" \
    "$PLUGIN/include/sealed_child_provider_loader.h" \
    "$PLUGIN/include/westlake_child_hook_table_v1.h" \
    "$PLUGIN/src/stage_receipt.c" \
    "$PLUGIN/src/sealed_child_provider_loader.c" \
    "$PLUGIN/src/child_hook_table_v1.c" \
    "$PLUGIN/src/westlake_android_child_plugin.c" \
    "$PLUGIN/src/westlake_elf_identity.c" \
    "$PLUGIN/src/westlake_sha256.c" \
    "$OUT/sealed_provider_manifest.c" \
    "$PLUGIN/src/westlake_stock_host_main.c" \
    "$OUT/libwestlake_android_child.z.so" \
    "$OUT/westlake_stock_host_main.o" \
    "$OUT/appspawn_service_fail_closed.o" \
    "$OUT/verification.json" >"$OUT/sha256.txt"

echo "PASS stock-host/plugin target ABI fixture deterministic=2 product_activation=false"
