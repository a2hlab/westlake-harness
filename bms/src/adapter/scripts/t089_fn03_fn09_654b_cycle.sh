#!/usr/bin/env bash
set -Eeuo pipefail

readonly HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
readonly SERIAL="654b3a6b00000000000000000824012c"
readonly PACKAGE="com.a2hlab.bridge.fn0103.gamma"
readonly ACTIVITY="com.a2hlab.bridge.fn0103.gamma.GammaHomeActivity"
readonly REMOTE_STAGE="/data/local/tmp/t089-fn03-fn09-654b"
readonly OLD_CANDIDATE_BRIDGE="0bd13c9a2496525c070c8f64ccfa127a2ee183ea9cbe09a8a9b156ba8254a623"
readonly OLD_CANDIDATE_RUNTIME="9ee061e949a2ee3736106dbf38bb89751d7c1b9a1d4213e4d5924e057e1315ab"
readonly PRESERVED_BASE_BRIDGE="cbade338980644232dae75b17d5e40e9bf14af6331a0de8b65ff70dff442b414"
readonly PRESERVED_BASE_RUNTIME="06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d"

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
readonly CANDIDATE_BRIDGE="${REPO_ROOT}/src/adapter/sources/oh61-v7-b2133b5b/out/adapter/liboh_adapter_bridge.so"
readonly PROBE_APK="${REPO_ROOT}/APKS/Fn01F03-ProbeGamma/dist/fn0103-probe-gamma.apk"
readonly PRESERVED_DIR="/opt/Bridge/evidence/atoms/Fn03/A09/runs/physical-20260729T001232Z-654b-bind-ingress/baseline"
readonly PRESERVED_BRIDGE="${PRESERVED_DIR}/liboh_adapter_bridge.so"
readonly PRESERVED_RUNTIME="${PRESERVED_DIR}/oh-adapter-runtime.jar"
readonly WORK_ROOT="${REPO_ROOT}/out/t089-fn03-fn09-654b"

ACTIVE_BACKUP=""
MUTATED=0

dev() {
    "${HDC}" -t "${SERIAL}" shell "$1"
}

host_sha() {
    shasum -a 256 "$1" | awk '{print $1}'
}

device_sha() {
    dev "sha256sum '$1'" 2>/dev/null | tr -d '\r' | awk 'NR == 1 {print $1}'
}

require_serial() {
    local reply
    reply="$(dev 'printf T089_SERIAL_OK' 2>&1 | tr -d '\r')"
    if [[ "${reply}" != *T089_SERIAL_OK* ]]; then
        printf 'blocked|physical USB enumeration|serial=%s|reply=%s\n' \
            "${SERIAL}" "${reply}" >&2
        return 69
    fi
}

wait_serial() {
    local attempt reply
    for attempt in $(seq 1 90); do
        reply="$(dev 'printf T089_SERIAL_OK' 2>&1 | tr -d '\r')" || true
        if [[ "${reply}" == *T089_SERIAL_OK* ]]; then
            return 0
        fi
        sleep 1
    done
    printf 'blocked|physical USB enumeration|serial=%s|reply=%s\n' \
        "${SERIAL}" "${reply:-no reply}" >&2
    return 69
}

preflight() {
    require_serial
    dev "set -e
        printf 'SERIAL=%s\n' '${SERIAL}'
        printf 'BOOT_ID='; cat /proc/sys/kernel/random/boot_id
        printf 'BRIDGE_RUNTIME_HASHES\n'
        sha256sum /system/android/lib64/liboh_adapter_bridge.so \
            /system/android/framework/oh-adapter-runtime.jar
        printf 'APPSPAWN_PID='; pidof appspawn-x || true
        printf 'ANDROID_MOUNT='
        mount | grep ' /system/android ' || true
        printf 'PACKAGE_STATE='
        if bm dump -n '${PACKAGE}' 2>/dev/null | grep -q bundleName; then
            printf 'PRESENT\n'
        else
            printf 'ABSENT\n'
        fi"
}

stop_appspawn() {
    dev "aa force-stop '${PACKAGE}' >/dev/null 2>&1 || true
        begetctl stop_service appspawn-x >/dev/null 2>&1 || true
        for p in \$(pidof appspawn-x 2>/dev/null); do
            kill -TERM \"\$p\" 2>/dev/null || true
        done
        i=0
        while test \$i -lt 20; do
            test -z \"\$(pidof appspawn-x 2>/dev/null)\" && exit 0
            i=\$((i + 1)); sleep 1
        done
        exit 1"
}

start_appspawn_no_jit() {
    dev "begetctl start_service appspawn-x >/dev/null 2>&1 || true
        sleep 2
        if test -z \"\$(pidof appspawn-x 2>/dev/null)\"; then
            mkdir -p /data/service/el1/public/appspawnx \
                /data/misc/appspawnx/dalvik-cache/arm64 \
                /dev/memcg/perf_sensitive /dev/unix/socket
            rm -f /dev/unix/socket/AppSpawnX
            APPSPAWNX_NO_JIT=1 \
            ANDROID_ROOT=/system/android \
            ANDROID_DATA=/data \
            ANDROID_BOOT_IMAGE=/system/android/framework/arm64/boot.art \
            ANDROID_I18N_ROOT=/system/android \
            ANDROID_TZDATA_ROOT=/system/android \
            ICU_DATA=/system/android/etc/icu \
            LD_LIBRARY_PATH=/system/android/lib64:/system/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk-sp \
            LD_PRELOAD=/system/android/lib64/liblzma.so \
            nohup /system/bin/appspawn-x --socket-name AppSpawnX \
                >'${REMOTE_STAGE}/appspawn.out' \
                2>'${REMOTE_STAGE}/appspawn.err' </dev/null &
        fi
        i=0
        while test \$i -lt 30; do
            p=\$(pidof appspawn-x 2>/dev/null)
            test -n \"\$p\" && { printf 'APPSPAWN_PID=%s\n' \"\$p\"; exit 0; }
            i=\$((i + 1)); sleep 1
        done
        cat '${REMOTE_STAGE}/appspawn.err' 2>/dev/null || true
        exit 1"
}

copy_pair() {
    local bridge="$1"
    local runtime="$2"
    local expected_bridge="$3"
    local expected_runtime="$4"
    local label="$5"

    "${HDC}" -t "${SERIAL}" target mount
    wait_serial
    dev "mkdir -p '${REMOTE_STAGE}'"
    "${HDC}" -t "${SERIAL}" file send "${bridge}" \
        "${REMOTE_STAGE}/${label}-bridge.so"
    "${HDC}" -t "${SERIAL}" file send "${runtime}" \
        "${REMOTE_STAGE}/${label}-runtime.jar"
    stop_appspawn
    dev "set -e
        cp '${REMOTE_STAGE}/${label}-bridge.so' \
            /system/android/lib64/liboh_adapter_bridge.so
        cp '${REMOTE_STAGE}/${label}-runtime.jar' \
            /system/android/framework/oh-adapter-runtime.jar
        chown 0:0 /system/android/lib64/liboh_adapter_bridge.so \
            /system/android/framework/oh-adapter-runtime.jar
        chmod 0755 /system/android/lib64/liboh_adapter_bridge.so
        chmod 0644 /system/android/framework/oh-adapter-runtime.jar
        chcon u:object_r:system_lib_file:s0 \
            /system/android/lib64/liboh_adapter_bridge.so
        chcon u:object_r:system_file:s0 \
            /system/android/framework/oh-adapter-runtime.jar
        sync
        sha256sum /system/android/lib64/liboh_adapter_bridge.so \
            /system/android/framework/oh-adapter-runtime.jar"
    test "$(device_sha /system/android/lib64/liboh_adapter_bridge.so)" = \
        "${expected_bridge}"
    test "$(device_sha /system/android/framework/oh-adapter-runtime.jar)" = \
        "${expected_runtime}"
    start_appspawn_no_jit
}

restore_preserved_if_required() {
    local bridge_sha runtime_sha
    require_serial
    bridge_sha="$(device_sha /system/android/lib64/liboh_adapter_bridge.so)"
    runtime_sha="$(device_sha /system/android/framework/oh-adapter-runtime.jar)"
    if [[ "${bridge_sha}/${runtime_sha}" == \
        "${PRESERVED_BASE_BRIDGE}/${PRESERVED_BASE_RUNTIME}" ]]; then
        printf 'preserved rollback not required; baseline pair already active\n'
        return
    fi
    if [[ "${bridge_sha}/${runtime_sha}" != \
        "${OLD_CANDIDATE_BRIDGE}/${OLD_CANDIDATE_RUNTIME}" ]]; then
        printf 'refusing mutation: unknown device pair %s/%s\n' \
            "${bridge_sha}" "${runtime_sha}" >&2
        return 65
    fi
    test "$(host_sha "${PRESERVED_BRIDGE}")" = "${PRESERVED_BASE_BRIDGE}"
    test "$(host_sha "${PRESERVED_RUNTIME}")" = "${PRESERVED_BASE_RUNTIME}"
    copy_pair "${PRESERVED_BRIDGE}" "${PRESERVED_RUNTIME}" \
        "${PRESERVED_BASE_BRIDGE}" "${PRESERVED_BASE_RUNTIME}" preserved
    printf 'restored preserved baseline pair\n'
}

backup_current() {
    mkdir -p "${WORK_ROOT}"
    ACTIVE_BACKUP="$(mktemp -d "${WORK_ROOT}/rollback.XXXXXX")"
    "${HDC}" -t "${SERIAL}" file recv \
        /system/android/lib64/liboh_adapter_bridge.so \
        "${ACTIVE_BACKUP}/liboh_adapter_bridge.so"
    "${HDC}" -t "${SERIAL}" file recv \
        /system/android/framework/oh-adapter-runtime.jar \
        "${ACTIVE_BACKUP}/oh-adapter-runtime.jar"
    dev "if bm dump -n '${PACKAGE}' 2>/dev/null | grep -q bundleName; then
            printf PRESENT
        else
            printf ABSENT
        fi" | tr -d '\r' >"${ACTIVE_BACKUP}/package-state"
    if grep -qx PRESENT "${ACTIVE_BACKUP}/package-state"; then
        "${HDC}" -t "${SERIAL}" file recv \
            "/data/app/el1/bundle/public/${PACKAGE}/android/base.apk" \
            "${ACTIVE_BACKUP}/previous-gamma.apk"
    fi
    {
        printf 'bridge_sha=%s\n' \
            "$(host_sha "${ACTIVE_BACKUP}/liboh_adapter_bridge.so")"
        printf 'runtime_sha=%s\n' \
            "$(host_sha "${ACTIVE_BACKUP}/oh-adapter-runtime.jar")"
        printf 'package_state=%s\n' \
            "$(cat "${ACTIVE_BACKUP}/package-state")"
    } >"${ACTIVE_BACKUP}/manifest"
    printf 'ROLLBACK_DIR=%s\n' "${ACTIVE_BACKUP}"
}

rollback() {
    local backup="${1:-${ACTIVE_BACKUP}}"
    test -n "${backup}"
    test -f "${backup}/liboh_adapter_bridge.so"
    test -f "${backup}/oh-adapter-runtime.jar"
    copy_pair \
        "${backup}/liboh_adapter_bridge.so" \
        "${backup}/oh-adapter-runtime.jar" \
        "$(host_sha "${backup}/liboh_adapter_bridge.so")" \
        "$(host_sha "${backup}/oh-adapter-runtime.jar")" rollback
    if grep -qx PRESENT "${backup}/package-state"; then
        test -f "${backup}/previous-gamma.apk"
        "${HDC}" -t "${SERIAL}" file send \
            "${backup}/previous-gamma.apk" "${REMOTE_STAGE}/previous-gamma.apk"
        dev "bm install -p '${REMOTE_STAGE}/previous-gamma.apk'"
    else
        dev "bm uninstall -n '${PACKAGE}' >/dev/null 2>&1 || true"
    fi
    MUTATED=0
    printf 'rollback complete from %s\n' "${backup}"
}

deploy() {
    test -f "${CANDIDATE_BRIDGE}"
    test -f "${PROBE_APK}"
    backup_current
    MUTATED=1
    copy_pair \
        "${CANDIDATE_BRIDGE}" \
        "${ACTIVE_BACKUP}/oh-adapter-runtime.jar" \
        "$(host_sha "${CANDIDATE_BRIDGE}")" \
        "$(host_sha "${ACTIVE_BACKUP}/oh-adapter-runtime.jar")" candidate
    "${HDC}" -t "${SERIAL}" file send \
        "${PROBE_APK}" "${REMOTE_STAGE}/fn0103-probe-gamma.apk"
    dev "bm install -p '${REMOTE_STAGE}/fn0103-probe-gamma.apk'"
}

cold_cycle() {
    local log_file="${ACTIVE_BACKUP}/cold-cycle.hilog"
    dev "aa force-stop '${PACKAGE}' >/dev/null 2>&1 || true
        test -z \"\$(pidof '${PACKAGE}' 2>/dev/null)\""
    dev "hilog -r >/dev/null 2>&1 || true"
    dev "aa start -a '${ACTIVITY}' -b '${PACKAGE}' -m entry -W"
    dev "sleep 5; uinput -K -d 1 -u 1; sleep 3"
    dev "aa start -a '${ACTIVITY}' -b '${PACKAGE}' -m entry -W"
    dev "sleep 4; uinput -K -d 2 -u 2; sleep 4"
    dev "aa force-stop '${PACKAGE}' >/dev/null 2>&1 || true
        test -z \"\$(pidof '${PACKAGE}' 2>/dev/null)\""
    dev "aa start -a '${ACTIVITY}' -b '${PACKAGE}' -m entry -W"
    dev "sleep 5; hilog -x" >"${log_file}"
    grep -q 'FN0103_GAMMA_LIFECYCLE.*onCreate state=cold' "${log_file}"
    grep -q 'FN0103_GAMMA_LIFECYCLE.*onRestart' "${log_file}"
    grep -q 'FN0103_GAMMA_LIFECYCLE.*onDestroy' "${log_file}"
    grep -q 'FN0103_GAMMA_PATH.*resource=PASS.*provider=PASS.*value=42' \
        "${log_file}"
    grep -q 'FN0103_GAMMA_PROVIDER.*query' "${log_file}"
    printf 'cold lifecycle/exit/restart trace matched required oracles\n'
}

cycle() {
    preflight
    restore_preserved_if_required
    trap 'rc=$?; trap - EXIT INT TERM; if test "${MUTATED}" -eq 1; then rollback "${ACTIVE_BACKUP}" || true; fi; exit "${rc}"' EXIT INT TERM
    deploy
    cold_cycle
    rollback "${ACTIVE_BACKUP}"
    trap - EXIT INT TERM
}

self_check() {
    test -x "${HDC}"
    test -f "${PRESERVED_BRIDGE}"
    test -f "${PRESERVED_RUNTIME}"
    test "$(host_sha "${PRESERVED_BRIDGE}")" = "${PRESERVED_BASE_BRIDGE}"
    test "$(host_sha "${PRESERVED_RUNTIME}")" = "${PRESERVED_BASE_RUNTIME}"
    test -f "${CANDIDATE_BRIDGE}"
    test -f "${PROBE_APK}"
    printf 'SERIAL=%s\n' "${SERIAL}"
    printf 'NEXT_COMMAND=%s/src/adapter/scripts/t089_fn03_fn09_654b_cycle.sh cycle\n' \
        "${REPO_ROOT}"
    printf 'MANUAL_ROLLBACK=%s/src/adapter/scripts/t089_fn03_fn09_654b_cycle.sh rollback <ROLLBACK_DIR>\n' \
        "${REPO_ROOT}"
}

usage() {
    printf 'usage: %s {preflight|restore-preserved|cycle|rollback DIR|self-check}\n' "$0"
}

case "${1:-}" in
    preflight)
        preflight
        ;;
    restore-preserved)
        preflight
        restore_preserved_if_required
        ;;
    cycle)
        cycle
        ;;
    rollback)
        test "$#" -eq 2
        require_serial
        rollback "$2"
        ;;
    self-check)
        self_check
        ;;
    *)
        usage >&2
        exit 64
        ;;
esac
