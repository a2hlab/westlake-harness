#!/usr/bin/env bash
set -euo pipefail
W=$(cd "$(dirname "$0")" && pwd)
F=$W/../product-tls-generation/frozen/toolchain
Z=$W/oh/third_party/zlib
SR=$W/oh/out/wukong100/obj/third_party/musl/usr
O=$W/zip-build
mkdir -p "$O"
export LD_LIBRARY_PATH=$F/runtime
for n in adler32 compress crc32 deflate gzclose gzlib gzread gzwrite infback inffast inflate inftrees trees uncompr zutil; do
 "$F/bin/clang" --target=aarch64-linux-ohos --sysroot="$SR" -I"$SR/include/aarch64-linux-ohos" -I"$Z" -fPIC -O2 -DHAVE_UNISTD_H -c "$Z/$n.c" -o "$O/$n.o"
done
"$F/bin/llvm-ar" rcs "$O/libz.a" "$O"/adler32.o "$O"/compress.o "$O"/crc32.o "$O"/deflate.o "$O"/gzclose.o "$O"/gzlib.o "$O"/gzread.o "$O"/gzwrite.o "$O"/infback.o "$O"/inffast.o "$O"/inflate.o "$O"/inftrees.o "$O"/trees.o "$O"/uncompr.o "$O"/zutil.o
for n in unzip ioapi; do
 "$F/bin/clang" --target=aarch64-linux-ohos --sysroot="$SR" -I"$SR/include/aarch64-linux-ohos" -I"$Z" -I"$Z/contrib/minizip" -fPIC -O2 -c "$Z/contrib/minizip/$n.c" -o "$O/$n.o"
done
