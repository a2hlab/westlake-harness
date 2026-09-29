#!/usr/bin/env bash
# Build the westlake-bionic provider libs (libc.so + liblog.so) and the
# VelocityTracker registration object, inside the OH 6.1 sysroot toolchain
# via dockbuild. Fails if ANY expected source is missing (per #86 contract).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
OHOS_SYSROOT="${OHOS_SYSROOT:-}"
[ -n "$OHOS_SYSROOT" ] || { echo "OHOS_SYSROOT not set (dockbuild env provides it)"; exit 1; }

CC="${CC:-aarch64-linux-ohos-clang}"
CXX="${CXX_BIN:-aarch64-linux-ohos-clang++}"

# ---- mandatory files (missing any = hard fail, per contract) ----
REQUIRED=(
  bionic-abi.map
  bionic_assert_compat.c
  bionic_stdio_compat.c
  liblog_android_supplement.cpp
  malloc_compat.cpp
  fdsan_stubs.cpp
  libstdcxx_compat.c
  misc_compat.cpp
  system_properties.cpp
  android_native_network_compat.c
  opensles_android_compat.c
  android_view_VelocityTracker.cpp
  libstdcxx_shim.c
  include/bionic/malloc.h
  include/sys/system_properties.h
)
for f in "${REQUIRED[@]}"; do
  [ -f "$HERE/$f" ] || { echo "MISSING required source: $f"; exit 1; }
done
echo "all ${#REQUIRED[@]} required sources present"

mkdir -p "$OUT"

# libc.so — bionic ABI surface (versioned LIBC node from bionic-abi.map)
"$CC" -shared -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -Wl,-soname,libc.so \
  -I"$HERE/include" \
  -Wl,--version-script="$HERE/bionic-abi.map" \
  -o "$OUT/libc.so" \
  "$HERE/bionic_assert_compat.c" \
  "$HERE/bionic_stdio_compat.c" \
  "$HERE/malloc_compat.cpp" \
  "$HERE/android_native_network_compat.c"
echo "built $OUT/libc.so"

# liblog.so — the Android logging surface anki's librsdroid DT_NEEDEDs
"$CXX" -shared -fPIC -O2 -Wall -nostdinc++ --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -Wl,-soname,liblog.so \
  -o "$OUT/liblog.so" \
  "$HERE/liblog_android_supplement.cpp"
echo "built $OUT/liblog.so"

# libfdsan/libstdcxx tiny companions (single .so each; Westlake links them into
# appspawn-x; here they are standalone providers for the app namespace)
"$CC" -shared -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -I"$HERE/include" -Wl,-soname,libfdsan_shim.so -o "$OUT/libfdsan_shim.so" "$HERE/fdsan_stubs.cpp"
"$CXX" -shared -fPIC -O2 -Wall -nostdinc++ --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -Wl,-soname,libstdcxx_compat.so -o "$OUT/libstdcxx_compat.so" "$HERE/libstdcxx_compat.c"
echo "built companion shims"

# ---- #91-① shims ----
# libstdc++.so: satisfies legacy DT_NEEDED (fd-app libgdx.so et al.); the
# compat source's own header documents this exact purpose.
"$CC" -shared -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -I"$HERE/include" \
  -Wl,-soname,libstdc++.so \
  -o "$OUT/libstdc++.so" "$HERE/libstdcxx_shim.c"

# libOpenSLES.so: Westlake opensles_android_compat.c (verbatim) — provides
# SL_IID_ANDROIDCONFIGURATION / SL_IID_ANDROIDSIMPLEBUFFERQUEUE data symbols
# (mindustry libarc.so DT_NEEDED). Engine funcs resolve from OH's libOpenSL.
"$CC" -shared -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -I"$HERE/include" \
  -Wl,-soname,libOpenSLES.so \
  -o "$OUT/libOpenSLES.so" "$HERE/opensles_android_compat.c" -ldl
echo "built #91 shims: libstdc++.so libOpenSLES.so"

# android_view_VelocityTracker.cpp — registration OBJECT for the runtime jar's
# native library to link in (not a standalone .so; it needs AndroidRuntime/JNI env)
"$CXX" -c -fPIC -O2 -Wall -nostdinc++ --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -I"$HERE/../../jni" \
  -o "$OUT/android_view_VelocityTracker.o" \
  "$HERE/android_view_VelocityTracker.cpp" \
  || { echo "NOTE: VelocityTracker object needs the runtime's AndroidRuntime.h/jni includes; \
pass -I to the runtime tree if this fails (cx-t0 wires it during integration)"; exit 2; }
echo "built $OUT/android_view_VelocityTracker.o"

echo "DONE: $(ls "$OUT" | tr '\n' ' ')"
