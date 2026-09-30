#!/usr/bin/env bash
# Fast fail-closed guard for the fixed R45 OH6.1 LTS full-product graph.
# It prevents HanBing's OH7/rk3568 module-only loader/ETS cuts from being
# replayed into a wukong100 images build.

set -euo pipefail

OH_ROOT="${OH_ROOT:-/opt/build-trees/oh610_lts_source}"
OH_PRODUCT_NAME="${OH_PRODUCT_NAME:-wukong100}"
SOURCE_ONLY=0

if [ "${1:-}" = "--source-only" ]; then
    SOURCE_ONLY=1
elif [ "$#" -ne 0 ]; then
    printf 'usage: %s [--source-only]\n' "$0" >&2
    exit 2
fi

if [ "$OH_PRODUCT_NAME" != "wukong100" ]; then
    printf 'FAIL product: expected=wukong100 actual=%s\n' "$OH_PRODUCT_NAME" >&2
    exit 3
fi

app="$OH_ROOT/build/ohos/app/app_internal.gni"
ets="$OH_ROOT/build/config/components/ets_frontend/ets2abc_config.gni"
product="$OH_ROOT/vendor/revoview/wukong100/config.json"
updater="$OH_ROOT/foundation/arkui/ui_lite/ext/updater/BUILD.gn"
app_expected="595c739b0741f9fbc1e32990cb1d95bee37bd2fd68daae17e65b726ff44edd1c"
ets_expected="28fc4cdcd620fda21c3cb6728d5cfc6a40f0162b93247f2ab86c2c5d4d763867"
product_expected="45a94f39a529b81577542b02900bbea82dca74d9d8368dd30eb994c9a8b951bd"
updater_expected="2a59138648ef7e8771836ea532c7effde7c1fb7387f45bdd74f1bf1cfcc81e13"

for file in "$app" "$ets" "$product" "$updater"; do
    if [ ! -f "$file" ] || [ -L "$file" ]; then
        printf 'FAIL source input: %s\n' "$file" >&2
        exit 4
    fi
done

app_actual=$(sha256sum "$app" | awk '{print $1}')
ets_actual=$(sha256sum "$ets" | awk '{print $1}')
product_actual=$(sha256sum "$product" | awk '{print $1}')
updater_actual=$(sha256sum "$updater" | awk '{print $1}')
if [ "$app_actual" != "$app_expected" ]; then
    printf 'FAIL app_internal SHA: expected=%s actual=%s\n' "$app_expected" "$app_actual" >&2
    exit 5
fi
if [ "$ets_actual" != "$ets_expected" ]; then
    printf 'FAIL ets2abc SHA: expected=%s actual=%s\n' "$ets_expected" "$ets_actual" >&2
    exit 6
fi
if [ "$product_actual" != "$product_expected" ]; then
    printf 'FAIL product config SHA: expected=%s actual=%s\n' "$product_expected" "$product_actual" >&2
    exit 10
fi
if [ "$updater_actual" != "$updater_expected" ]; then
    printf 'FAIL updater BUILD.gn SHA: expected=%s actual=%s\n' "$updater_expected" "$updater_actual" >&2
    exit 11
fi
grep -Fq '"//developtools/ace_js2bundle:ace_loader_ark_hap",' "$app"
grep -Fq 'external_deps = [ "ace_ets2bundle:ets_loader_ark_hap" ]' "$app"
if grep -Fq '_ace_loader_home = "/developtools/' "$app"; then
    printf 'FAIL forbidden static loader root in app_internal.gni\n' >&2
    exit 7
fi

printf 'SOURCE_GATE_PASS app=%s ets=%s product=%s updater=%s\n' \
    "$app_actual" "$ets_actual" "$product_actual" "$updater_actual"
[ "$SOURCE_ONLY" = "0" ] || exit 0

out="$OH_ROOT/out/wukong100"
ninja="$OH_ROOT/prebuilts/build-tools/linux-x86/bin/ninja"
if [ ! -x "$ninja" ] || [ ! -f "$out/build.ninja" ]; then
    printf 'FAIL generated graph is absent; run GN first\n' >&2
    exit 8
fi

targets=(
    obj/base/inputmethod/imf/services/dialog/input_method_choose_hap/js_assets.zip
    obj/base/location/location/services/location_ui/location_dialog_hap/js_assets.zip
    obj/base/notification/distributed_notification_service/services/dialog_ui/enable_notification_dialog/enable_notification_dialog_hap/js_assets.zip
    obj/applications/standard/auth_widget/auth_widget/js_assets.zip
    obj/base/usb/usb_manager/frameworks/dialog/dialog_ui/usb_right_dialog/dialog_hap/js_assets.zip
)

commands=$(
    "$ninja" -w dupbuild=warn -C "$out" -t commands "${targets[@]}" 2>/dev/null \
        | grep 'build_js_assets.py'
)
action_count=$(printf '%s\n' "$commands" | grep -c 'build_js_assets.py' || true)
bad_count=$(printf '%s\n' "$commands" | grep -c '../../../../../developtools' || true)
js_count=$(printf '%s\n' "$commands" | grep -c -- '--webpack-js obj/developtools/ace_js2bundle/ace_loader_ark/node_modules/webpack/bin/webpack.js' || true)
ets_count=$(printf '%s\n' "$commands" | grep -c -- '--webpack-ets obj/developtools/ace_ets2bundle/ets_loader_ark/node_modules/webpack/bin/webpack.js' || true)

if [ "$action_count" != "5" ] || [ "$bad_count" != "0" ] \
    || [ "$js_count" != "5" ] || [ "$ets_count" != "5" ]; then
    printf 'FAIL generated loader paths: actions=%s bad=%s js=%s ets=%s\n' \
        "$action_count" "$bad_count" "$js_count" "$ets_count" >&2
    exit 9
fi

printf 'GRAPH_GATE_PASS actions=%s bad=%s js=%s ets=%s\n' \
    "$action_count" "$bad_count" "$js_count" "$ets_count"

# The five exact targets above are the historical regression set.  Also scan
# every JS-assets action reachable from the real images target so a new HAP
# cannot reintroduce the same loader-root drift outside that sample.
image_commands=$(
    "$ninja" -w dupbuild=warn -C "$out" -t commands images 2>/dev/null \
        | grep 'build_js_assets.py'
)
image_action_count=$(printf '%s\n' "$image_commands" | grep -c 'build_js_assets.py' || true)
image_bad_count=$(printf '%s\n' "$image_commands" \
    | grep -Ec '\.\./\.\./\.\./\.\./\.\./developtools|--webpack-(js|ets) /developtools' || true)
image_js_count=$(printf '%s\n' "$image_commands" \
    | grep -c -- '--webpack-js obj/developtools/ace_js2bundle/ace_loader_ark/node_modules/webpack/bin/webpack.js' || true)
image_ets_count=$(printf '%s\n' "$image_commands" \
    | grep -c -- '--webpack-ets obj/developtools/ace_ets2bundle/ets_loader_ark/node_modules/webpack/bin/webpack.js' || true)

if [ "$image_action_count" -lt "$action_count" ] \
    || [ "$image_bad_count" != "0" ] \
    || [ "$image_js_count" != "$image_action_count" ] \
    || [ "$image_ets_count" != "$image_action_count" ]; then
    printf 'FAIL images loader paths: actions=%s bad=%s js=%s ets=%s\n' \
        "$image_action_count" "$image_bad_count" "$image_js_count" "$image_ets_count" >&2
    exit 12
fi

printf 'IMAGE_GRAPH_GATE_PASS actions=%s bad=%s js=%s ets=%s\n' \
    "$image_action_count" "$image_bad_count" "$image_js_count" "$image_ets_count"
