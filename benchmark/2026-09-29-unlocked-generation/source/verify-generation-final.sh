#!/usr/bin/env bash
set -euo pipefail
export WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/rebuilt-provider-base
python3 /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/verify_route_a_generation.py --host /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/host/appspawn-x-stock --second-host /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/host/appspawn-x-stock --provider /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/provider/libwestlake_android_runtime_provider.so --second-provider /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/provider/libwestlake_android_runtime_provider.so --registry /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/registry/libwestlake_thread_guard_registry.so --second-registry /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/registry/libwestlake_thread_guard_registry.so --pthread-bridge /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so --second-pthread-bridge /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/pthread-bridge/libwestlake_bionic_pthread_bridge.so --compat /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/compat/libbionic_compat.so --second-compat /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/compat/libbionic_compat.so --app-native-loader /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/app-loader/libapp_native_loader.so --second-app-native-loader /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/app-loader/libapp_native_loader.so --native-loader /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/native-loader/libnativeloader.so --second-native-loader /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/native-loader/libnativeloader.so --art-palette /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass1/palette/libartpalette-system.so --second-art-palette /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/pass2/palette/libartpalette-system.so --provider-set-manifest /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/providers.sha256 --plugin /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/target/pass1/libwestlake_android_child.z.so --second-plugin /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/target/pass2/libwestlake_android_child.z.so --inputs /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/ROUTE_A_INPUTS.json --readelf /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf --objdump /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/.work/product-tls-generation/frozen/toolchain/bin/llvm-objdump --report /Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/out/route-a-generation/verification.json

ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest
PLUGIN=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
OUT=$PLUGIN/out/route-a-generation
REGISTRY=$ROOT/adapter/framework/native-compat/thread-guard-registry
READELF=$ROOT/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf
OBJDUMP=$ROOT/.work/product-tls-generation/frozen/toolchain/bin/llvm-objdump
python3 "$REGISTRY/tests/verify_route_a_product_integration.py" \
    --project-root "$ROOT" \
    --host "$OUT/pass1/host/appspawn-x-stock" \
    --second-host "$OUT/pass2/host/appspawn-x-stock" \
    --provider "$OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
    --second-provider "$OUT/pass2/provider/libwestlake_android_runtime_provider.so" \
    --plugin "$PLUGIN/out/target/pass1/libwestlake_android_child.z.so" \
    --second-plugin "$PLUGIN/out/target/pass2/libwestlake_android_child.z.so" \
    --registry "$OUT/pass1/registry/libwestlake_thread_guard_registry.so" \
    --second-registry "$OUT/pass2/registry/libwestlake_thread_guard_registry.so" \
    --pthread-bridge "$OUT/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --second-pthread-bridge "$OUT/pass2/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --compat "$OUT/pass1/compat/libbionic_compat.so" \
    --second-compat "$OUT/pass2/compat/libbionic_compat.so" \
    --app-native-loader "$OUT/pass1/app-loader/libapp_native_loader.so" \
    --second-app-native-loader "$OUT/pass2/app-loader/libapp_native_loader.so" \
    --native-loader "$OUT/pass1/native-loader/libnativeloader.so" \
    --second-native-loader "$OUT/pass2/native-loader/libnativeloader.so" \
    --art-palette "$OUT/pass1/palette/libartpalette-system.so" \
    --second-art-palette "$OUT/pass2/palette/libartpalette-system.so" \
    --provider-set-manifest "$OUT/providers.sha256" \
    --owner-object "$OUT/pass1/host/native_compat_prepare_owner_aarch64.o" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/guard-product-verification.json"

sha256sum \
    "$OUT/appspawn-x-stock" \
    "$OUT/libwestlake_android_runtime_provider.so" \
    "$OUT/libwestlake_thread_guard_registry.so" \
    "$OUT/libwestlake_bionic_pthread_bridge.so" \
    "$OUT/libbionic_compat.so" \
    "$OUT/libapp_native_loader.so" \
    "$OUT/libnativeloader.so" \
    "$OUT/libartpalette-system.so" \
    "$OUT/providers.sha256" \
    "$PLUGIN/out/target/libwestlake_android_child.z.so" \
    "$OUT/verification.json" \
    "$OUT/guard-product-verification.json" >"$OUT/artifacts.sha256"

echo "PASS Route A provider + stock host deterministic=2"
