#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?}
RW=$ROOT/bms/src/.work/b6-real-work
W=$ROOT/bms/src/.work/b6-task47
BASE=$RW/.work/product-tls-generation/frozen
TC=$BASE/toolchain
SYSROOT=$BASE/sysroot
PLUGIN=$RW/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
LIVE=$ROOT/bms/src/.work/b6-r155/live/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d
EXT=$PLUGIN/frozen/target_external/openharmony-6.1.0.31-d600
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$W/bridge"
"$TC/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$SYSROOT" -B"$TC/bin" \
 -fPIC -O2 -g -fvisibility=hidden -std=c++17 -nostdinc++ -isystem "$TC/include/c++/v1" \
 -fdebug-prefix-map="$ROOT"=. -ffile-prefix-map="$ROOT"=. \
 -c "$RW/adapter/framework/appspawn-x/src/art_abort_message_bridge.cpp" -o "$W/bridge/bridge.o"
"$TC/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$SYSROOT" -B"$TC/bin" \
 -fuse-ld=lld -shared -nostdlib++ -Wl,-z,defs,--no-undefined,--no-allow-shlib-undefined \
 -Wl,-z,now,-z,relro,--build-id=sha1,-soname,libwestlake_art_abort_bridge.so \
 -L"$LIVE" -L"$EXT" -L"$PLUGIN/frozen/libraries/oh" \
 -Wl,-rpath-link,"$LIVE",-rpath-link,"$EXT",-rpath-link,"$PLUGIN/frozen/libraries/oh" \
 "$W/bridge/bridge.o" -Wl,--no-as-needed -lart -lc++ -Wl,--as-needed -lc \
 -o "$W/bridge/libwestlake_art_abort_bridge.so"
"$TC/bin/llvm-readelf" -dW "$W/bridge/libwestlake_art_abort_bridge.so"
"$TC/bin/llvm-objdump" -d "$W/bridge/libwestlake_art_abort_bridge.so" > "$W/bridge/disassembly.txt"
sha256sum "$W/bridge/libwestlake_art_abort_bridge.so" "$EXT/libc++.so"
