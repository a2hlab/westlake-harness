#!/bin/bash
# Runs ON hw248: builds liba0probe.so (C++, OH 6.1.0.31 headers, linked against the boards' libraries in $B/lib, whose
# hashes are recorded in out/lib-sha256.txt) and liba0shim.so (C, JNI). Compiler = the OH tree's prebuilt clang
# (llvm-project feef13a3, libcxx-ohos ABI namespace __h, the frozen compiler of every route-A native build).
# Include dirs: out/include-dirs.txt from resolve_includes_hw248.sh (+ src/genstub). --no-undefined: every symbol must
# resolve against the board libraries at link time. -fno-rtti: OH system C++ is built without RTTI (no typeinfo exported). Usage: A0_BUILD=<dir> OH610=<tree> OH_SYSROOT=<sysroot> bash $0 <tag>
set -euo pipefail
B=${A0_BUILD:?}; OH=${OH610:?}; SYSROOT=${OH_SYSROOT:?}; TAG=${1:?tag}
LLVM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm; O=$B/out/$TAG; mkdir -p $O
CXX=$LLVM/bin/clang++; CC=$LLVM/bin/clang
COMMON="--target=aarch64-linux-ohos --sysroot=$SYSROOT -fPIC -O2 -g -fstack-protector-strong -D__MUSL__ -Wno-c++11-narrowing -ffile-prefix-map=$B=. -ffile-prefix-map=$OH=OH -ffile-prefix-map=$SYSROOT=SYSROOT"
INC="$(sed 's/^/-I/' $B/out/include-dirs.txt | tr '\n' ' ') -I$B/src/genstub"
$CXX --version | head -1
sha256sum $CXX $B/lib/*.so > $O/inputs-sha256.txt
$CXX $COMMON -std=c++17 -fno-rtti -nostdinc++ -isystem $LLVM/include/libcxx-ohos/include/c++/v1 -fvisibility=hidden $INC \
  -c $B/src/native/a0probe.cpp -o $O/a0probe.o
$CXX $COMMON -shared -nostdlib++ -fuse-ld=lld -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,liba0probe.so \
  -o $O/liba0probe.so $O/a0probe.o -L$B/lib \
  -l:libarkweb_core_loader.z.so -l:libapp_context.z.so -l:libappexecfwk_base.z.so -l:libeventhandler.z.so \
  -l:libsurface.z.so -l:libsync_fence.z.so -l:libbegetutil.z.so -l:libutils.z.so -l:libhilog.so -l:libc++.so
$CC $COMMON -std=c11 -I$B/src/native/include -c $B/src/native/a0shim.c -o $O/a0shim.o
$CC $COMMON -shared -fuse-ld=lld -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,liba0shim.so -o $O/liba0shim.so $O/a0shim.o
sha256sum $O/liba0probe.so $O/liba0shim.so | tee $O/SHA256SUMS
