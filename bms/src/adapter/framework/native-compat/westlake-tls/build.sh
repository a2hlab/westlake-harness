#!/usr/bin/env bash
# #93-native: build liboh_tls_boundary.so — the Westlake §441 TLS boundary as a
# single shared library, inside the OH 6.1 sysroot via dockbuild.
# dlopen()s the board's own libssl_openssl.z.so / libcrypto_openssl.z.so at
# runtime (no OpenSSL linked in), verifies against /etc/ssl/certs/cacert.pem.
# Fails if ANY required source is missing (contract).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
# PROVEN recipe (2026-09-29): VM-pinned clang-15 + OH sysroot + westlake's
# third_party jni.h (the sysroot ships no jni.h). Paths are VM-side; run this
# script INSIDE the a2hlab VM (or via dockbuild run with these mounts).
VMROOT="${VMROOT:-/home/zhaoyue/a2hlab/ws}"
CXX="$VMROOT/toolchains/ohos-sdk/native/llvm/bin/clang-15"
SYSROOT="$VMROOT/toolchains/ohos-sdk/native/sysroot"
JNI_INC="${JNI_INC:-/home/zhaoyue/a2hlab/westlake-current/third_party/jni}"
[ -x "$CXX" ] || { echo "clang-15 not found at $CXX"; exit 1; }
[ -f "$SYSROOT/usr/include/stdlib.h" ] || { echo "sysroot invalid: $SYSROOT"; exit 1; }
[ -f "$JNI_INC/jni.h" ] || { echo "jni.h not found (set JNI_INC)"; exit 1; }

REQUIRED=(
  wl_tls_block.cpp        # §441 verbatim block (WlSslApi + wl_tls_* + 7 JNI impls)
  register_tls.h          # registration entry (wl_register_tls_natives standalone)
)
for f in "${REQUIRED[@]}"; do
  [ -f "$HERE/$f" ] || { echo "MISSING required source: $f"; exit 1; }
done
echo "all ${#REQUIRED[@]} required sources present"
mkdir -p "$OUT"

"$CXX" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
  -shared -fPIC -O2 -std=c++17 -Wall \
  -I"$HERE" -I"$JNI_INC" \
  -o "$OUT/liboh_tls_boundary.so" \
  "$HERE/wl_tls_block.cpp" \
  -ldl -lpthread \
  || { echo "build failed"; exit 2; }
file "$OUT/liboh_tls_boundary.so" | head -1
nm -D "$OUT/liboh_tls_boundary.so" | grep -q westlake_tls_child_register \
  || { echo "westlake_tls_child_register missing from output"; exit 3; }
# pipefail-safe: grep -c exits 1 on zero matches, so capture with || true
N_SSL=$(nm -D "$OUT/liboh_tls_boundary.so" | grep -cE " U (SSL_|OPENSSL_)" || true)
[ "$N_SSL" = "0" ] || { echo "static OpenSSL linkage detected ($N_SSL undefined) — must be dlopen-only"; exit 4; }
echo "gate: dlopen-only OK (0 undefined OpenSSL symbols)"

echo "built $OUT/liboh_tls_boundary.so"
echo "symbols:"; nm -D "$OUT/liboh_tls_boundary.so" | grep -E "westlake_tls_child_register|wl_register_tls_natives" || true
echo "wiring: call westlake_tls_child_register(env) (or wl_register_tls_natives) once per child after FindClass(adapter/compat/WestlakeSSLSocket) is resolvable — cx-t0 hooks it in child init."
