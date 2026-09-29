#!/usr/bin/env bash
# Build the CommonEvent JNI provider (5 natives + OH backing client) for the
# runtime's native library, inside the OH 6.1 sysroot via dockbuild.
# Fails if ANY required source is missing (#91 contract).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
OHOS_SYSROOT="${OHOS_SYSROOT:-}"
[ -n "$OHOS_SYSROOT" ] || { echo "OHOS_SYSROOT not set (dockbuild env provides it)"; exit 1; }
CC="${CC:-aarch64-linux-ohos-clang}"
CXX="${CXX_BIN:-aarch64-linux-ohos-clang++}"

REQUIRED=(
  oh_common_event_client.cpp
  oh_common_event_client.h
  common_event_subscriber_adapter.cpp
  common_event_subscriber_adapter.h
  activity_manager_adapter.cpp        # the 5 CommonEvent natives + RegisterNatives table
)
for f in "${REQUIRED[@]}"; do
  [ -f "$HERE/$f" ] || { echo "MISSING required source: $f"; exit 1; }
done
echo "all ${#REQUIRED[@]} required sources present"
mkdir -p "$OUT"

# Java companions are data for the runtime jar build, not compiled here — but
# their absence still fails the contract:
for j in CommonEventReceiverBridge.java BroadcastEventConverter.java; do
  [ -f "$HERE/$j" ] || { echo "MISSING java companion: $j"; exit 1; }
done

# oh_common_event_client + subscriber adapter: object files to link INTO the
# runtime native library (they reference OH common_event headers from the
# sysroot: common_event_manager.h etc.)
"$CXX" -c -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -o "$OUT/oh_common_event_client.o" "$HERE/oh_common_event_client.cpp" \
  || { echo "NOTE: needs OH common_event headers in sysroot (common_event_manager.h / common_event_data.h / matching_skills.h); if absent, cx-t0 wires the cESDK include path"; exit 2; }

"$CXX" -c -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -o "$OUT/common_event_subscriber_adapter.o" "$HERE/common_event_subscriber_adapter.cpp" \
  || { echo "NOTE: same sysroot include requirement"; exit 2; }

# activity_manager_adapter.cpp registers ALL 10 natives (5 ability + 5
# CommonEvent). It is included verbatim so the registration table stays
# byte-identical with Westlake; ability impls already exist in the current
# bridge — cx-t0 either links this object only for the CommonEvent entries or
# resolves duplicate ability symbols at link time.
"$CXX" -c -fPIC -O2 -Wall --target=aarch64-linux-ohos --sysroot="$OHOS_SYSROOT" \
  -I"$HERE" \
  -o "$OUT/activity_manager_adapter.o" "$HERE/activity_manager_adapter.cpp" \
  || { echo "NOTE: needs jni.h + log headers; wire runtime includes if absent"; exit 2; }

echo "DONE objects: $(ls "$OUT" | tr '\n' ' ')"
echo "link these .o into the runtime native lib; call register_ActivityManagerAdapter(env) at startup (Westlake wiring: AndroidRuntime.cpp registration table)."
