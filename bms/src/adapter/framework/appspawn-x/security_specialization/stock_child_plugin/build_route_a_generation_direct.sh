#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=${ROUTE_A_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)}
GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$PROJECT_ROOT/.work/product-tls-generation}
TOOLCHAIN=$GENERATION_ROOT/frozen/toolchain
IDENTITY_CONTRACT=$SCRIPT_DIR/r45_adapter_identity.env
HOST_TEST_RECEIPT=${WESTLAKE_HOST_TEST_RECEIPT:-}

[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || {
    echo "ERROR direct Route-A target build requires Linux x86_64" >&2
    exit 1
}

[[ -x "$TOOLCHAIN/bin/clang-15" ]] || {
    echo "ERROR missing frozen direct toolchain: $TOOLCHAIN/bin/clang-15" >&2
    exit 1
}
[[ -f "$IDENTITY_CONTRACT" ]] || {
    echo "ERROR missing R45 adapter identity contract: $IDENTITY_CONTRACT" >&2
    exit 1
}
[[ -f "$HOST_TEST_RECEIPT" ]] || {
    echo "ERROR missing macOS-native host-test receipt: $HOST_TEST_RECEIPT" >&2
    exit 1
}
[[ -f "$GENERATION_ROOT/frozen.sha256" ]] || {
    echo "ERROR missing direct-host frozen input manifest" >&2
    exit 1
}

set -a
# shellcheck disable=SC1090
source "$IDENTITY_CONTRACT"
set +a

for identity_name in \
    WLAR_ADAPTER_BRIDGE_PATH \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    WLAR_ANDROID_RUNTIME_PATH \
    WLAR_ANDROID_RUNTIME_SHA256_HEX \
    WLAR_ANDROID_RUNTIME_BUILD_ID_HEX
do
    [[ -n ${!identity_name:-} ]] || {
        echo "ERROR incomplete R45 adapter identity contract: $identity_name" >&2
        exit 1
    }
done

(
    cd "$GENERATION_ROOT/frozen"
    sha256sum -c "$GENERATION_ROOT/frozen.sha256" >/dev/null
)

TOOL_RUNTIME_LOCK=$GENERATION_ROOT/tool_runtime.lock
{
    printf 'schema=westlake-direct-host-tool-runtime-v1\n'
    printf 'execution=direct-linux-host\n'
    printf 'container_used=false\n'
    printf 'host_kernel=%s\n' "$(uname -sr)"
    printf 'host_arch=%s\n' "$(uname -m)"
    printf 'host_os_release_sha256=%s\n' \
        "$(sha256sum /etc/os-release | awk '{print $1}')"
    printf 'clang_path=%s\n' "$TOOLCHAIN/bin/clang-15"
    printf 'clang_sha256=%s\n' \
        "$(sha256sum "$TOOLCHAIN/bin/clang-15" | awk '{print $1}')"
    printf 'clang_version=%s\n' \
        "$("$TOOLCHAIN/bin/clang-15" --version | head -n 1)"
    printf 'lld_sha256=%s\n' \
        "$(sha256sum "$TOOLCHAIN/bin/ld.lld" | awk '{print $1}')"
    printf 'direct_recipe_sha256=%s\n' \
        "$(sha256sum "$SCRIPT_DIR/build_route_a_generation_direct.sh" | awk '{print $1}')"
    printf 'compiler_recipe_sha256=%s\n' \
        "$(sha256sum "$SCRIPT_DIR/build_route_a_generation_in_container.sh" | awk '{print $1}')"
    printf 'host_test_receipt_sha256=%s\n' \
        "$(sha256sum "$HOST_TEST_RECEIPT" | awk '{print $1}')"
} >"$TOOL_RUNTIME_LOCK"

# These are candidate-local ledgers.  Regeneration binds the direct-host lock
# and this wrapper before the underlying recipe immediately verifies them.
export ROUTE_A_PROJECT_ROOT=$PROJECT_ROOT
export WESTLAKE_GENERATION_ROOT=$GENERATION_ROOT
python3 "$SCRIPT_DIR/generate_source_closure.py"
python3 "$SCRIPT_DIR/generate_route_a_inputs.py"

# The historical filename is misleading: this script contains only the
# underlying compiler/linker commands and invokes no container runtime.
export CC=$TOOLCHAIN/bin/clang-15
bash "$SCRIPT_DIR/build_route_a_generation_in_container.sh"

echo "PASS route-A direct final link; container_used=false product_activation=false device_verified=false"
