#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?Set B6_REPO_ROOT to the harness checkout}
W=$ROOT/bms/src/.work/b6-art14-recovery
L=$ROOT/bms/src/.work/b6-latest
TC=$ROOT/bms/src/.work/product-tls-generation/frozen/toolchain
ML=$W/oh/out/wukong100/obj/third_party/musl/usr/lib/aarch64-linux-ohos
O=$W/build/providers
GEN=$L/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation
ZLIB=$GEN/libshared_libz.z.so
CXX=$W/build/cxx-sdk15
BUILTINS=$TC/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
for N in ziparchive dexfile profile; do
 case $N in
 ziparchive) EDGES=(-lbase -llog -lbionic_compat);;
 dexfile) EDGES=(-lartbase -lartpalette -lziparchive -lbase -llog -lbionic_compat);;
 profile) EDGES=(-lbase -llog -lartbase -lartpalette -ldexfile -lziparchive);;
 esac
 "$CXX" --target=aarch64-linux-ohos -B"$ML" -L"$ML" -L"$O" -shared -fPIC -Wl,-z,defs -Wl,--build-id=sha1 -Wl,-soname,lib$N.so -o "$O/lib$N.so" "$W/build/objects/$N"/*.o -lc "${EDGES[@]}" "$ZLIB" -ldl -lpthread "$BUILTINS"
done
"$CXX" --target=aarch64-linux-ohos -B"$ML" -L"$ML" -L"$O" -shared -fPIC -Wl,-z,defs -Wl,--no-allow-shlib-undefined -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,libandroidfw.so -o "$O/libandroidfw.so" "$W/build/graphics-objects/androidfw"/*.o -lbase -lutils -lcutils -llog -licuuc "$ZLIB" -lziparchive
