#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/framework/app-native-loader"
OUT="${ANL_OUT_DIR:-$ROOT/out/adapter}"
FIXTURE_OUT="${ANL_FIXTURE_OUT_DIR:-$ROOT/out/app_native_loader_fixture}"
DUAL_APP="$FIXTURE_OUT/dual_app"
DUAL_BRIDGE="$FIXTURE_OUT/dual_bridge"
PROBE_CTOR_APP="$FIXTURE_OUT/probe_constructor_app"
PROBE_CTOR_DECOY="$FIXTURE_OUT/probe_constructor_decoy"
PROBE_NESTED_APP="$FIXTURE_OUT/probe_nested_app"
PROBE_NESTED_DECOY="$FIXTURE_OUT/probe_nested_decoy"
PROBE_DOMAIN_A="$FIXTURE_OUT/probe_domain_a"
PROBE_DOMAIN_B="$FIXTURE_OUT/probe_domain_b"
OH_NATIVE="${OH_SDK_NATIVE:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}"
SYSROOT="${OH_SYSROOT:-$OH_NATIVE/sysroot}"
CC="${OH_CC:-$OH_NATIVE/llvm/bin/clang}"
READELF="${OH_READELF:-$OH_NATIVE/llvm/bin/llvm-readelf}"
DLNS_PROVIDER="${OH_DLNS_PROVIDER:-$ROOT/out/d600_a_e_n0_20260711/ld-musl-aarch64.so.1}"
DLNS_PROVIDER_SHA256="${OH_DLNS_PROVIDER_SHA256:-316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98}"

test -x "$CC"
test -x "$READELF"
test -d "$SYSROOT/usr/include"
test -s "$DLNS_PROVIDER"
test "$(sha256sum "$DLNS_PROVIDER" | awk '{print $1}')" = "$DLNS_PROVIDER_SHA256"
rm -rf "$FIXTURE_OUT"
mkdir -p "$OUT" "$FIXTURE_OUT" "$DUAL_APP" "$DUAL_BRIDGE" \
  "$PROBE_CTOR_APP" "$PROBE_CTOR_DECOY" \
  "$PROBE_NESTED_APP" "$PROBE_NESTED_DECOY" \
  "$PROBE_DOMAIN_A" "$PROBE_DOMAIN_B"

assert_needed_exact() {
  local so="$1"
  shift
  local actual expected
  actual="$("$READELF" -d "$so" \
    | sed -n 's/.*Shared library: \[\([^]]*\)\].*/\1/p' \
    | LC_ALL=C sort)"
  if [ "$#" -eq 0 ]; then
    expected=""
  else
    expected="$(printf '%s\n' "$@" | LC_ALL=C sort)"
  fi
  if [ "$actual" != "$expected" ]; then
    printf 'unexpected DT_NEEDED set in %s\nexpected:\n%s\nactual:\n%s\n' \
      "$so" "$expected" "$actual" >&2
    return 1
  fi
}

assert_undefined_exact() {
  local so="$1"
  shift
  local actual expected
  actual="$("$READELF" --dyn-syms --wide "$so" \
    | awk '$7 == "UND" && $8 != "" { print $8 }' \
    | LC_ALL=C sort)"
  if [ "$#" -eq 0 ]; then
    expected=""
  else
    expected="$(printf '%s\n' "$@" | LC_ALL=C sort)"
  fi
  if [ "$actual" != "$expected" ]; then
    printf 'unexpected undefined symbol set in %s\nexpected:\n%s\nactual:\n%s\n' \
      "$so" "$expected" "$actual" >&2
    return 1
  fi
}

assert_dir_exact() {
  local dir="$1"
  shift
  local actual expected
  actual="$(find "$dir" -mindepth 1 -maxdepth 1 -print \
    | sed "s#^$dir/##" | LC_ALL=C sort)"
  expected="$(printf '%s\n' "$@" | LC_ALL=C sort)"
  if [ "$actual" != "$expected" ]; then
    printf 'unexpected staging entries in %s\nexpected:\n%s\nactual:\n%s\n' \
      "$dir" "$expected" "$actual" >&2
    return 1
  fi
}

COMMON=(
  --target=aarch64-linux-ohos
  --sysroot="$SYSROOT"
  -D_GNU_SOURCE
  -std=c11
  -fPIC
  -fvisibility=hidden
  -Wall
  -Wextra
  -Werror
  -I"$SRC/include"
  -I"$ROOT/framework/native-compat/bionic-pthread-bridge/include"
)

"$CC" "${COMMON[@]}" -shared \
  -Wl,-soname,libapp_native_loader.so \
  -Wl,--build-id=sha1 \
  -Wl,-z,defs \
  -Wl,--version-script,"$SRC/app_native_loader.map" \
  "$SRC/src/app_native_loader.c" \
  -L"$(dirname "$DLNS_PROVIDER")" -l:"$(basename "$DLNS_PROVIDER")" \
  -o "$OUT/libapp_native_loader.so"

"$CC" "${COMMON[@]}" -shared \
  -Wl,-soname,libanl_peer.so \
  -nostdlib \
  -Wl,-z,defs \
  "$SRC/tests/peer.c" \
  -o "$FIXTURE_OUT/libanl_peer.so"

"$CC" "${COMMON[@]}" -shared \
  -Wl,-soname,libanl_root.so \
  -nostdlib \
  -Wl,-z,defs \
  -Wl,--no-as-needed \
  "$SRC/tests/root.c" \
  -L"$FIXTURE_OUT" -l:libanl_peer.so \
  -o "$FIXTURE_OUT/libanl_root.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_SHADOW_BASE=0x1000 \
  -Wl,-soname,libanl_shadow.so \
  "$SRC/tests/dual_shadow.c" \
  -o "$DUAL_APP/libanl_shadow.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_SHADOW_BASE=0x2000 \
  -Wl,-soname,libanl_shadow.so \
  "$SRC/tests/dual_shadow.c" \
  -o "$DUAL_BRIDGE/libanl_shadow.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -Wl,-soname,libanl_bridge_only.so \
  "$SRC/tests/bridge_only.c" \
  -o "$DUAL_BRIDGE/libanl_bridge_only.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -Wl,-soname,libanl_bridge_denied.so \
  "$SRC/tests/bridge_denied.c" \
  -o "$DUAL_BRIDGE/libanl_bridge_denied.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs -Wl,--no-as-needed \
  -Wl,-soname,libanl_dual_root.so \
  "$SRC/tests/dual_root.c" \
  -L"$DUAL_APP" -l:libanl_shadow.so \
  -L"$DUAL_BRIDGE" -l:libanl_bridge_only.so \
  -o "$DUAL_APP/libanl_dual_root.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs -Wl,--no-as-needed \
  -Wl,-soname,libanl_denied_root.so \
  "$SRC/tests/denied_root.c" \
  -L"$DUAL_BRIDGE" -l:libanl_bridge_denied.so \
  -o "$DUAL_APP/libanl_denied_root.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_CONSTRUCTOR_MARKER=0xc7 \
  -Wl,-soname,libanl_probe_constructor.so \
  "$SRC/tests/probe_constructor.c" \
  -o "$PROBE_CTOR_APP/libanl_probe_constructor.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_CONSTRUCTOR_MARKER=0xb0 \
  -Wl,-soname,libanl_probe_constructor.so \
  "$SRC/tests/probe_constructor.c" \
  -o "$PROBE_CTOR_DECOY/libanl_probe_constructor.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_NESTED_MARKER=0x2e \
  -Wl,-soname,libanl_probe_nested_leaf.so \
  "$SRC/tests/probe_nested_leaf.c" \
  -o "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_NESTED_MARKER=0xbd \
  -Wl,-soname,libanl_probe_nested_leaf.so \
  "$SRC/tests/probe_nested_leaf.c" \
  -o "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -Wl,-soname,libanl_probe_nested_root.so \
  "$SRC/tests/probe_nested_root.c" -lc \
  -o "$PROBE_NESTED_APP/libanl_probe_nested_root.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_SAME_MARKER=0xa1 \
  -Wl,-soname,libanl_probe_same.so \
  "$SRC/tests/probe_same_soname.c" \
  -o "$PROBE_DOMAIN_A/libanl_probe_same.so"

"$CC" "${COMMON[@]}" -shared -nostdlib -Wl,-z,defs \
  -DANL_PROBE_SAME_MARKER=0xb2 \
  -Wl,-soname,libanl_probe_same.so \
  "$SRC/tests/probe_same_soname.c" \
  -o "$PROBE_DOMAIN_B/libanl_probe_same.so"

"$CC" "${COMMON[@]}" \
  -Wl,-z,defs \
  -Wl,--version-script,"$SRC/app_native_loader.map" \
  "$SRC/src/app_native_loader.c" \
  "$SRC/tests/target/anl_target_fixture.c" \
  -L"$(dirname "$DLNS_PROVIDER")" -l:"$(basename "$DLNS_PROVIDER")" \
  -o "$FIXTURE_OUT/anl_target_fixture"

for so in "$OUT/libapp_native_loader.so" \
          "$FIXTURE_OUT/libanl_peer.so" \
          "$FIXTURE_OUT/libanl_root.so" \
          "$DUAL_APP/libanl_shadow.so" \
          "$DUAL_APP/libanl_dual_root.so" \
          "$DUAL_APP/libanl_denied_root.so" \
          "$DUAL_BRIDGE/libanl_shadow.so" \
          "$DUAL_BRIDGE/libanl_bridge_only.so" \
          "$DUAL_BRIDGE/libanl_bridge_denied.so" \
          "$PROBE_CTOR_APP/libanl_probe_constructor.so" \
          "$PROBE_CTOR_DECOY/libanl_probe_constructor.so" \
          "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so" \
          "$PROBE_NESTED_APP/libanl_probe_nested_root.so" \
          "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so" \
          "$PROBE_DOMAIN_A/libanl_probe_same.so" \
          "$PROBE_DOMAIN_B/libanl_probe_same.so" \
          "$FIXTURE_OUT/anl_target_fixture"; do
  "$READELF" -h "$so" | grep -E 'Class:[[:space:]]+ELF64' >/dev/null
  "$READELF" -h "$so" | grep -E 'Machine:[[:space:]]+AArch64' >/dev/null
  ! "$READELF" -d "$so" | grep -Eq 'RPATH|RUNPATH|TEXTREL'
done

"$READELF" --dyn-syms --wide "$OUT/libapp_native_loader.so" \
  | grep 'ANL_CreateDomain' >/dev/null
if "$READELF" --dyn-syms --wide "$OUT/libapp_native_loader.so" \
    | awk '$1 ~ /^[0-9]+:$/ && $7 != "UND" && $8 !~ /^ANL_/ && $8 !~ /^WESTLAKE_ANL_1/ { bad = 1 } END { exit bad ? 0 : 1 }'; then
  echo "unexpected exported symbol in libapp_native_loader.so" >&2
  exit 1
fi
"$READELF" -d "$FIXTURE_OUT/libanl_root.so" \
  | grep 'Shared library: \[libanl_peer.so\]' >/dev/null
assert_needed_exact "$FIXTURE_OUT/libanl_peer.so"
assert_needed_exact "$FIXTURE_OUT/libanl_root.so" libanl_peer.so
assert_needed_exact "$DUAL_APP/libanl_shadow.so"
assert_needed_exact "$DUAL_APP/libanl_dual_root.so" \
  libanl_shadow.so libanl_bridge_only.so
assert_needed_exact "$DUAL_APP/libanl_denied_root.so" libanl_bridge_denied.so
assert_needed_exact "$DUAL_BRIDGE/libanl_shadow.so"
assert_needed_exact "$DUAL_BRIDGE/libanl_bridge_only.so"
assert_needed_exact "$DUAL_BRIDGE/libanl_bridge_denied.so"

assert_undefined_exact "$DUAL_APP/libanl_dual_root.so" \
  anl_shadow_value anl_bridge_only_value
assert_undefined_exact "$DUAL_APP/libanl_denied_root.so" \
  anl_bridge_denied_value

assert_needed_exact "$PROBE_CTOR_APP/libanl_probe_constructor.so"
assert_needed_exact "$PROBE_CTOR_DECOY/libanl_probe_constructor.so"
assert_needed_exact "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so"
assert_needed_exact "$PROBE_NESTED_APP/libanl_probe_nested_root.so" libc.so
assert_needed_exact "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so"
assert_needed_exact "$PROBE_DOMAIN_A/libanl_probe_same.so"
assert_needed_exact "$PROBE_DOMAIN_B/libanl_probe_same.so"

assert_undefined_exact "$PROBE_CTOR_APP/libanl_probe_constructor.so"
assert_undefined_exact "$PROBE_CTOR_DECOY/libanl_probe_constructor.so"
assert_undefined_exact "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so"
assert_undefined_exact "$PROBE_NESTED_APP/libanl_probe_nested_root.so" \
  dlclose dlopen dlsym
assert_undefined_exact "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so"
assert_undefined_exact "$PROBE_DOMAIN_A/libanl_probe_same.so"
assert_undefined_exact "$PROBE_DOMAIN_B/libanl_probe_same.so"

for so in "$DUAL_APP/libanl_shadow.so" \
          "$DUAL_BRIDGE/libanl_shadow.so" \
          "$DUAL_BRIDGE/libanl_bridge_only.so"; do
  "$READELF" -d "$so" | grep -E '\(INIT_ARRAYSZ\)[[:space:]]+8 \(bytes\)' >/dev/null
done
for so in "$PROBE_CTOR_APP/libanl_probe_constructor.so" \
          "$PROBE_CTOR_DECOY/libanl_probe_constructor.so"; do
  "$READELF" -d "$so" | grep -E '\(INIT_ARRAYSZ\)[[:space:]]+8 \(bytes\)' >/dev/null
done
"$READELF" -d "$DUAL_APP/libanl_shadow.so" \
  | grep 'Library soname: \[libanl_shadow.so\]' >/dev/null
"$READELF" -d "$DUAL_BRIDGE/libanl_shadow.so" \
  | grep 'Library soname: \[libanl_shadow.so\]' >/dev/null
test "$(sha256sum "$DUAL_APP/libanl_shadow.so" | awk '{print $1}')" != \
     "$(sha256sum "$DUAL_BRIDGE/libanl_shadow.so" | awk '{print $1}')"

for so in "$PROBE_CTOR_APP/libanl_probe_constructor.so" \
          "$PROBE_CTOR_DECOY/libanl_probe_constructor.so"; do
  "$READELF" -d "$so" \
    | grep 'Library soname: \[libanl_probe_constructor.so\]' >/dev/null
done
for so in "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so" \
          "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so"; do
  "$READELF" -d "$so" \
    | grep 'Library soname: \[libanl_probe_nested_leaf.so\]' >/dev/null
done
for so in "$PROBE_DOMAIN_A/libanl_probe_same.so" \
          "$PROBE_DOMAIN_B/libanl_probe_same.so"; do
  "$READELF" -d "$so" \
    | grep 'Library soname: \[libanl_probe_same.so\]' >/dev/null
done
"$READELF" -d "$PROBE_NESTED_APP/libanl_probe_nested_root.so" \
  | grep 'Library soname: \[libanl_probe_nested_root.so\]' >/dev/null

test "$(sha256sum "$PROBE_CTOR_APP/libanl_probe_constructor.so" | awk '{print $1}')" != \
     "$(sha256sum "$PROBE_CTOR_DECOY/libanl_probe_constructor.so" | awk '{print $1}')"
test "$(sha256sum "$PROBE_NESTED_APP/libanl_probe_nested_leaf.so" | awk '{print $1}')" != \
     "$(sha256sum "$PROBE_NESTED_DECOY/libanl_probe_nested_leaf.so" | awk '{print $1}')"
test "$(sha256sum "$PROBE_DOMAIN_A/libanl_probe_same.so" | awk '{print $1}')" != \
     "$(sha256sum "$PROBE_DOMAIN_B/libanl_probe_same.so" | awk '{print $1}')"

if grep -En '(^|[^_[:alnum:]])dlopen[[:space:]]*\(' \
    "$SRC/tests/target/anl_target_fixture.c"; then
  echo "plain dlopen is forbidden in the target fixture driver" >&2
  exit 1
fi
grep -q 'ANL_InstallRuntimeGate' \
  "$SRC/tests/target/anl_target_fixture.c"
grep -q -- '--probe-denied-gate' \
  "$SRC/tests/target/anl_target_fixture.c"
grep -q 'ANL_PROBE_DENIED_GATE_PASS constructor_reachable=0' \
  "$SRC/tests/target/anl_target_fixture.c"
test "$(grep -Ec 'dlopen\("libanl_probe_nested_leaf\.so"' \
  "$SRC/tests/probe_nested_root.c")" = 1
! grep -En 'dlopen\([^\"]|dlopen\("/' "$SRC/tests/probe_nested_root.c"

if "$READELF" --dyn-syms --wide "$FIXTURE_OUT/anl_target_fixture" \
    | awk '$7 == "UND" { print $8 }' | grep -Eq '(^|@)dlopen(@|$)'; then
  echo "target fixture driver unexpectedly imports plain dlopen" >&2
  exit 1
fi

assert_dir_exact "$DUAL_APP" \
  libanl_shadow.so libanl_dual_root.so libanl_denied_root.so
assert_dir_exact "$DUAL_BRIDGE" \
  libanl_shadow.so libanl_bridge_only.so libanl_bridge_denied.so
assert_dir_exact "$PROBE_CTOR_APP" libanl_probe_constructor.so
assert_dir_exact "$PROBE_CTOR_DECOY" libanl_probe_constructor.so
assert_dir_exact "$PROBE_NESTED_APP" \
  libanl_probe_nested_leaf.so libanl_probe_nested_root.so
assert_dir_exact "$PROBE_NESTED_DECOY" libanl_probe_nested_leaf.so
assert_dir_exact "$PROBE_DOMAIN_A" libanl_probe_same.so
assert_dir_exact "$PROBE_DOMAIN_B" libanl_probe_same.so

(
  cd "$FIXTURE_OUT"
  sha256sum anl_target_fixture \
    dual_app/libanl_shadow.so \
    dual_app/libanl_dual_root.so \
    dual_app/libanl_denied_root.so \
    dual_bridge/libanl_shadow.so \
    dual_bridge/libanl_bridge_only.so \
    dual_bridge/libanl_bridge_denied.so \
    > dual_target_manifest.sha256
)

(
  cd "$FIXTURE_OUT"
  sha256sum anl_target_fixture \
    probe_constructor_app/libanl_probe_constructor.so \
    probe_constructor_decoy/libanl_probe_constructor.so \
    probe_nested_app/libanl_probe_nested_leaf.so \
    probe_nested_app/libanl_probe_nested_root.so \
    probe_nested_decoy/libanl_probe_nested_leaf.so \
    probe_domain_a/libanl_probe_same.so \
    probe_domain_b/libanl_probe_same.so \
    > probe_target_manifest.sha256

  sha256sum anl_target_fixture \
    libanl_peer.so libanl_root.so \
    dual_app/libanl_shadow.so \
    dual_app/libanl_dual_root.so \
    dual_app/libanl_denied_root.so \
    dual_bridge/libanl_shadow.so \
    dual_bridge/libanl_bridge_only.so \
    dual_bridge/libanl_bridge_denied.so \
    probe_constructor_app/libanl_probe_constructor.so \
    probe_constructor_decoy/libanl_probe_constructor.so \
    probe_nested_app/libanl_probe_nested_leaf.so \
    probe_nested_app/libanl_probe_nested_root.so \
    probe_nested_decoy/libanl_probe_nested_leaf.so \
    probe_domain_a/libanl_probe_same.so \
    probe_domain_b/libanl_probe_same.so \
    > all_target_manifest.sha256
)

(
  cd "$ROOT"
  sha256sum \
    build/compile_app_native_loader_arm64.sh \
    framework/app-native-loader/include/app_native_loader.h \
    framework/app-native-loader/src/app_native_loader.c \
    framework/app-native-loader/app_native_loader.map \
    framework/app-native-loader/tests/peer.c \
    framework/app-native-loader/tests/root.c \
    framework/app-native-loader/tests/dual_shadow.c \
    framework/app-native-loader/tests/dual_root.c \
    framework/app-native-loader/tests/bridge_only.c \
    framework/app-native-loader/tests/bridge_denied.c \
    framework/app-native-loader/tests/denied_root.c \
    framework/app-native-loader/tests/probe_constructor.c \
    framework/app-native-loader/tests/probe_nested_leaf.c \
    framework/app-native-loader/tests/probe_nested_root.c \
    framework/app-native-loader/tests/probe_same_soname.c \
    framework/app-native-loader/tests/target/anl_target_fixture.c \
    > "$FIXTURE_OUT/target_source_manifest.sha256"
  printf '%s  %s\n' "$DLNS_PROVIDER_SHA256" "$DLNS_PROVIDER" \
    >> "$FIXTURE_OUT/target_source_manifest.sha256"
  sha256sum "$CC" >> "$FIXTURE_OUT/target_source_manifest.sha256"
)

assert_dir_exact "$FIXTURE_OUT" \
  all_target_manifest.sha256 anl_target_fixture \
  dual_app dual_bridge dual_target_manifest.sha256 \
  libanl_peer.so libanl_root.so \
  probe_constructor_app probe_constructor_decoy \
  probe_domain_a probe_domain_b probe_nested_app probe_nested_decoy \
  probe_target_manifest.sha256 target_source_manifest.sha256

(
  cd "$FIXTURE_OUT"
  sha256sum -c dual_target_manifest.sha256
  sha256sum -c probe_target_manifest.sha256
  sha256sum -c all_target_manifest.sha256
)
(
  cd "$ROOT"
  sha256sum -c "$FIXTURE_OUT/target_source_manifest.sha256"
)

sha256sum "$OUT/libapp_native_loader.so"
cat "$FIXTURE_OUT/all_target_manifest.sha256"
