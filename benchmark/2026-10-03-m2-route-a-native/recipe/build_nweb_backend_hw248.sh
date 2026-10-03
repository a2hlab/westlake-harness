#!/bin/bash
# Runs ON hw248. Builds the route-a NWeb backend worker (libwl_nweb_backend.so, C++) and shim
# (libwl_nweb_backend_shim.so, C, JNI). Recipe mirrors cc-t3's build_a0_hw248.sh verbatim: frozen OH clang-15
# feef13a3, libcxx-ohos (ABI ns __h), -fno-rtti, -Wl,--no-undefined (every symbol resolves against the board libs in
# $A0/lib), include dirs from the A0 resolve_includes output (+ A0's jni.h). Reuses cc-t3's A0 build area (include
# dirs + board libs) read-only; writes only into $OUT.
#   A0=<cc-t3 a0probe build dir> SRC=<this src/native> OUT=<iso out dir> OH=<oh610 tree> SYSROOT=<sysroot> bash $0 <tag>
set -euo pipefail
A0=${A0:?}; SRC=${SRC:?}; OUT=${OUT:?}; OH=${OH:?}; SYSROOT=${SYSROOT:?}; TAG=${1:?tag}
LLVM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm; O=$OUT/$TAG; mkdir -p "$O"
CXX=$LLVM/bin/clang++; CC=$LLVM/bin/clang
COMMON="--target=aarch64-linux-ohos --sysroot=$SYSROOT -fPIC -O2 -g -fstack-protector-strong -D__MUSL__ -Wno-c++11-narrowing -ffile-prefix-map=$SRC=. -ffile-prefix-map=$A0=A0 -ffile-prefix-map=$OH=OH -ffile-prefix-map=$SYSROOT=SYSROOT"
INC="$(sed 's/^/-I/' $A0/out/include-dirs.txt | tr '\n' ' ') -I$A0/src/genstub -I$A0/src/native/include"
$CXX --version | head -1
sha256sum $CXX $A0/lib/*.so > "$O/inputs-sha256.txt"
# worker (C++)
$CXX $COMMON -std=c++17 -fno-rtti -nostdinc++ -isystem $LLVM/include/libcxx-ohos/include/c++/v1 -fvisibility=hidden $INC \
  -c "$SRC/native/nweb_backend.cpp" -o "$O/nweb_backend.o"
$CXX $COMMON -shared -nostdlib++ -fuse-ld=lld -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,libwl_nweb_backend.so \
  -o "$O/libwl_nweb_backend.so" "$O/nweb_backend.o" -L"$A0/lib" \
  -l:libarkweb_core_loader.z.so -l:libsurface.z.so -l:libutils.z.so -l:libhilog.so -l:libc++.so
# shim (C, JNI)
$CC $COMMON -std=c11 -c "$SRC/native/nweb_backend_shim.c" -o "$O/nweb_backend_shim.o"
$CC $COMMON -shared -fuse-ld=lld -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,libwl_nweb_backend_shim.so \
  -o "$O/libwl_nweb_backend_shim.so" "$O/nweb_backend_shim.o" -L"$A0/lib" -l:libhilog.so
sha256sum "$O/libwl_nweb_backend.so" "$O/libwl_nweb_backend_shim.so" | tee "$O/SHA256SUMS"
