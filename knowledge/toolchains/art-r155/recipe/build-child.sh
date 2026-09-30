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
OUT=$PLUGIN/out/target
ROUTE_OUT=$PLUGIN/out/route-a-generation
GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$ROOT/.work/product-tls-generation}
TOOLCHAIN=$GENERATION_ROOT/frozen/toolchain
SYSROOT=$GENERATION_ROOT/frozen/sysroot
TARGET_LIB=$SYSROOT/lib/aarch64-linux-ohos
RUNTIME_FROZEN=$PLUGIN/frozen/runtime_provider
CC=$TOOLCHAIN/bin/clang-15
READELF=$TOOLCHAIN/bin/llvm-readelf
OBJDUMP=$TOOLCHAIN/bin/llvm-objdump

INCLUDES=(
    -I"$PLUGIN/include"
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

GENERATION_SHA=74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d
PLUGIN_BUILD_ID_HEX=${GENERATION_SHA:0:40}
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
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -std=c11 -include /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-r155/build-declarations.h \
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
    if sonames != [path.name] or len(build_ids) != 1 or len(build_ids[0]) != 40:
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
    compile "$PLUGIN/src/sealed_child_provider_loader.c" \
        "$dir/sealed_child_provider_loader.o"
    compile "$PLUGIN/src/child_hook_table_v1.c" \
        "$dir/child_hook_table_v1.o"
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

}

build_pass pass1
build_pass pass2
cmp "$OUT/pass1/libwestlake_android_child.z.so" "$OUT/pass2/libwestlake_android_child.z.so"
