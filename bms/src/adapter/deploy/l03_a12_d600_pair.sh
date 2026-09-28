#!/usr/bin/env bash

set -euo pipefail

# L03.A12 bounded diagnostic: deploy the current-vintage ARM64 BMS/installs
# pair to the one canonical D600. This script never installs or modifies an APK.

SERIAL="5bb5b1ae00000000000000000823012c"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="$ROOT/out/l03_a12_p7885_v9_20260710/artifacts"
DEVICE_STAGE="/data/local/tmp/codex_l03_a12"
DEVICE_BACKUP="$DEVICE_STAGE/backup_predeploy"

BMS_NAME="libbms.z.so"
INSTALLS_NAME="libinstalls.z.so"
BMS_OLD_SHA="10293b46017bf7c560f23e69c04293e8828c740610aa22f7327c9cae318d13d5"
INSTALLS_OLD_SHA="bba91b5cfdf33baff821fc2f90a2824c4e3c0cf7d52c4cc6c2cfd9b443b949a6"
BMS_NEW_SHA="5e20f57b8d17fd3ce739eca54c02ad4f9269437e05a5dd16fcca9e73a7135fd9"
INSTALLS_NEW_SHA="de9ca6ec3550c5a00f000cc027ed3b973b875d788899de30cfb1326d2b170861"
INSTALLER_SHA="206b73f402edbd71fa82545406ef87560ac5a87406138373be33be966db55591"
SYSTEM_LABEL="u:object_r:system_lib_file:s0"

die()
{
    printf 'L03.A12 FAIL: %s\n' "$*" >&2
    exit 1
}

device_sh()
{
    "$HDC" -t "$SERIAL" shell "$1"
}

host_sha()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

assert_target()
{
    [[ -x "$HDC" ]] || die "hdc missing: $HDC"
    "$HDC" list targets | grep -Fxq "$SERIAL" || die "canonical D600 is offline"
}

assert_host_artifacts()
{
    [[ "$(host_sha "$ARTIFACT_DIR/$BMS_NAME")" == "$BMS_NEW_SHA" ]] || die "host BMS SHA drift"
    [[ "$(host_sha "$ARTIFACT_DIR/$INSTALLS_NAME")" == "$INSTALLS_NEW_SHA" ]] || die "host installs SHA drift"
    file "$ARTIFACT_DIR/$BMS_NAME" | grep -Eq 'ELF 64-bit.*ARM aarch64' || die "host BMS is not AArch64 ELF64"
    file "$ARTIFACT_DIR/$INSTALLS_NAME" | grep -Eq 'ELF 64-bit.*ARM aarch64' || die "host installs is not AArch64 ELF64"
}

assert_device_file()
{
    local path="$1"
    local sha="$2"
    device_sh "set -- \$(sha256sum '$path'); test \"\$1\" = '$sha'" >/dev/null || die "device SHA mismatch: $path"
}

assert_system_attrs()
{
    local path="$1"
    device_sh "test \"\$(stat -c '%u:%g:%a' '$path')\" = '0:0:644' && ls -lZ '$path' | grep -Fq '$SYSTEM_LABEL'" >/dev/null ||
        die "owner/mode/label mismatch: $path"
}

assert_installs_profile()
{
    device_sh "grep -Fq '\"process\": \"installs\"' /system/profile/installs.json && \
grep -Fq '\"name\": 511' /system/profile/installs.json && \
grep -Fq '\"libpath\": \"libinstalls.z.so\"' /system/profile/installs.json && \
grep -Fq '\"ondemand\" : true' /system/etc/init/installs.cfg" >/dev/null ||
        die "D600 installs SA/profile contract drift"
}

preflight_old()
{
    assert_target
    assert_host_artifacts
    assert_installs_profile
    device_sh "test \"\$(uname -m)\" = aarch64" >/dev/null || die "device is not aarch64"
    assert_device_file "/system/lib64/$BMS_NAME" "$BMS_OLD_SHA"
    assert_device_file "/system/lib64/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"
    assert_device_file "/system/lib64/libapk_installer.so" "$INSTALLER_SHA"
    assert_system_attrs "/system/lib64/$BMS_NAME"
    assert_system_attrs "/system/lib64/$INSTALLS_NAME"
    assert_system_attrs "/system/lib64/libapk_installer.so"
    device_sh "set -- \$(df -k / | tail -n 1); test \"\$4\" -ge 16384" >/dev/null ||
        die "root filesystem has less than 16 MiB free"
    printf 'L03.A12 preflight PASS: old pair, installer, attrs, ARM64 and free-space gates match.\n'
}

preflight_new()
{
    assert_target
    assert_host_artifacts
    assert_installs_profile
    assert_device_file "/system/lib64/$BMS_NAME" "$BMS_NEW_SHA"
    assert_device_file "/system/lib64/$INSTALLS_NAME" "$INSTALLS_NEW_SHA"
    assert_device_file "/system/lib64/libapk_installer.so" "$INSTALLER_SHA"
    assert_system_attrs "/system/lib64/$BMS_NAME"
    assert_system_attrs "/system/lib64/$INSTALLS_NAME"
}

wait_reboot()
{
    local old_boot_id="$1"
    local i
    local saw_offline=0
    local new_boot_id=""
    for i in $(seq 1 120); do
        if ! "$HDC" list targets 2>/dev/null | grep -Fxq "$SERIAL"; then
            saw_offline=1
        elif new_boot_id="$("$HDC" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null)" &&
             [[ -n "$new_boot_id" && "$new_boot_id" != "$old_boot_id" ]]; then
            printf 'L03.A12 reboot PASS: boot_id changed (hdc_offline_observed=%s).\n' "$saw_offline"
            return 0
        fi
        sleep 1
    done
    die "D600 did not return with a changed boot_id"
}

reboot_and_wait()
{
    local old_boot_id
    old_boot_id="$(device_sh 'cat /proc/sys/kernel/random/boot_id')"
    [[ -n "$old_boot_id" ]] || die "could not capture pre-reboot boot_id"
    "$HDC" -t "$SERIAL" shell reboot >/dev/null 2>&1 || true
    wait_reboot "$old_boot_id"
}

verify_new_consumers()
{
    preflight_new
    device_sh 'i=0; while test $i -lt 60; do pidof foundation >/dev/null && exit 0; i=$((i+1)); sleep 1; done; exit 1' >/dev/null ||
        die "foundation did not start"
    device_sh 'p=$(pidof foundation); test -n "$p"; grep -Fq /system/lib64/libbms.z.so "/proc/$p/maps"' >/dev/null ||
        die "foundation does not map the new BMS path"

    device_sh 'begetctl start_service installs; i=0; while test $i -lt 20; do pidof installs >/dev/null && exit 0; i=$((i+1)); sleep 1; done; exit 1' >/dev/null ||
        die "installs service did not start"
    device_sh 'p=$(pidof installs); test -n "$p"; grep -Fq /system/lib64/libinstalls.z.so "/proc/$p/maps"' >/dev/null ||
        die "installs does not map the new installs path"
    printf 'L03.A12 device pair PASS: disk identity, attrs and fresh consumer maps match.\n'
}

stage_candidates_and_backup()
{
    device_sh "mkdir -p '$DEVICE_STAGE/candidate' '$DEVICE_BACKUP' && chmod 700 '$DEVICE_STAGE' '$DEVICE_STAGE/candidate' '$DEVICE_BACKUP'"
    device_sh "cp -p '/system/lib64/$BMS_NAME' '$DEVICE_BACKUP/$BMS_NAME' && cp -p '/system/lib64/$INSTALLS_NAME' '$DEVICE_BACKUP/$INSTALLS_NAME'"
    device_sh 'sync'
    assert_device_file "$DEVICE_BACKUP/$BMS_NAME" "$BMS_OLD_SHA"
    assert_device_file "$DEVICE_BACKUP/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"

    "$HDC" -t "$SERIAL" file send "$ARTIFACT_DIR/$BMS_NAME" "$DEVICE_STAGE/candidate/$BMS_NAME"
    "$HDC" -t "$SERIAL" file send "$ARTIFACT_DIR/$INSTALLS_NAME" "$DEVICE_STAGE/candidate/$INSTALLS_NAME"
    assert_device_file "$DEVICE_STAGE/candidate/$BMS_NAME" "$BMS_NEW_SHA"
    assert_device_file "$DEVICE_STAGE/candidate/$INSTALLS_NAME" "$INSTALLS_NEW_SHA"
}

quiesce_consumers()
{
    device_sh 'aa force-stop com.CardWordsStudio.CardWords >/dev/null 2>&1 || true; pkill -x appspawn-x >/dev/null 2>&1 || true; begetctl stop_service installs >/dev/null 2>&1 || true; begetctl stop_service foundation >/dev/null 2>&1 || true'
    device_sh 'i=0; while test $i -lt 20; do if test -z "$(pidof installs)$(pidof foundation)$(pidof appspawn-x)"; then exit 0; fi; i=$((i+1)); sleep 1; done; exit 1' >/dev/null ||
        die "BMS/installs/appspawn consumers did not quiesce"
    device_sh 'for f in /proc/[0-9]*/maps; do grep -Eq "/(libbms|libinstalls)[.]z[.]so" "$f" 2>/dev/null && { echo "active map: $f"; exit 1; }; done; exit 0' ||
        die "a process still maps the BMS/installs pair"
}

probe_and_quiesce_consumers()
{
    # Prove the current lazy service control and library path before replacement.
    device_sh 'begetctl start_service installs; i=0; while test $i -lt 20; do pidof installs >/dev/null && exit 0; i=$((i+1)); sleep 1; done; exit 1' >/dev/null ||
        die "old installs service could not be probed"
    device_sh 'p=$(pidof installs); grep -Fq /system/lib64/libinstalls.z.so "/proc/$p/maps"' >/dev/null ||
        die "old installs consumer maps an unexpected path"

    quiesce_consumers
}

install_pair_and_reboot()
{
    device_sh 'mount -o remount,rw /'
    device_sh "cp '$DEVICE_STAGE/candidate/$BMS_NAME' '/system/lib64/.l03a12.$BMS_NAME.new' && \
cp '$DEVICE_STAGE/candidate/$INSTALLS_NAME' '/system/lib64/.l03a12.$INSTALLS_NAME.new' && \
chown 0:0 '/system/lib64/.l03a12.$BMS_NAME.new' '/system/lib64/.l03a12.$INSTALLS_NAME.new' && \
chmod 0644 '/system/lib64/.l03a12.$BMS_NAME.new' '/system/lib64/.l03a12.$INSTALLS_NAME.new' && \
chcon '$SYSTEM_LABEL' '/system/lib64/.l03a12.$BMS_NAME.new' '/system/lib64/.l03a12.$INSTALLS_NAME.new'"
    assert_device_file "/system/lib64/.l03a12.$BMS_NAME.new" "$BMS_NEW_SHA"
    assert_device_file "/system/lib64/.l03a12.$INSTALLS_NAME.new" "$INSTALLS_NEW_SHA"
    assert_system_attrs "/system/lib64/.l03a12.$BMS_NAME.new"
    assert_system_attrs "/system/lib64/.l03a12.$INSTALLS_NAME.new"

    if ! device_sh "mv '/system/lib64/.l03a12.$BMS_NAME.new' '/system/lib64/$BMS_NAME' && \
mv '/system/lib64/.l03a12.$INSTALLS_NAME.new' '/system/lib64/$INSTALLS_NAME'"; then
        rollback_no_preflight
        die "pair rename failed; old pair restored"
    fi
    if ! device_sh "set -- \$(sha256sum '/system/lib64/$BMS_NAME'); test \"\$1\" = '$BMS_NEW_SHA' && \
set -- \$(sha256sum '/system/lib64/$INSTALLS_NAME'); test \"\$1\" = '$INSTALLS_NEW_SHA' && \
set -- \$(sha256sum /system/lib64/libapk_installer.so); test \"\$1\" = '$INSTALLER_SHA'" >/dev/null; then
        rollback_no_preflight
        die "post-rename identity failed; old pair restored"
    fi
    assert_system_attrs "/system/lib64/$BMS_NAME"
    assert_system_attrs "/system/lib64/$INSTALLS_NAME"
    device_sh 'sync'
    reboot_and_wait
    if ! (verify_new_consumers); then
        printf 'L03.A12 post-reboot verification failed; restoring the old pair.\n' >&2
        rollback_no_preflight
        reboot_and_wait
        assert_device_file "/system/lib64/$BMS_NAME" "$BMS_OLD_SHA"
        assert_device_file "/system/lib64/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"
        die "new pair rejected after reboot; old pair restored"
    fi
}

rollback_no_preflight()
{
    quiesce_consumers
    device_sh 'mount -o remount,rw /'
    assert_device_file "$DEVICE_BACKUP/$BMS_NAME" "$BMS_OLD_SHA"
    assert_device_file "$DEVICE_BACKUP/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"
    device_sh "cp '$DEVICE_BACKUP/$BMS_NAME' '/system/lib64/.l03a12.$BMS_NAME.rollback' && \
cp '$DEVICE_BACKUP/$INSTALLS_NAME' '/system/lib64/.l03a12.$INSTALLS_NAME.rollback' && \
chown 0:0 '/system/lib64/.l03a12.$BMS_NAME.rollback' '/system/lib64/.l03a12.$INSTALLS_NAME.rollback' && \
chmod 0644 '/system/lib64/.l03a12.$BMS_NAME.rollback' '/system/lib64/.l03a12.$INSTALLS_NAME.rollback' && \
chcon '$SYSTEM_LABEL' '/system/lib64/.l03a12.$BMS_NAME.rollback' '/system/lib64/.l03a12.$INSTALLS_NAME.rollback' && \
mv '/system/lib64/.l03a12.$BMS_NAME.rollback' '/system/lib64/$BMS_NAME' && \
mv '/system/lib64/.l03a12.$INSTALLS_NAME.rollback' '/system/lib64/$INSTALLS_NAME' && sync"
    assert_device_file "/system/lib64/$BMS_NAME" "$BMS_OLD_SHA"
    assert_device_file "/system/lib64/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"
    assert_device_file "/system/lib64/libapk_installer.so" "$INSTALLER_SHA"
    assert_system_attrs "/system/lib64/$BMS_NAME"
    assert_system_attrs "/system/lib64/$INSTALLS_NAME"
}

deploy()
{
    preflight_old
    stage_candidates_and_backup
    probe_and_quiesce_consumers
    install_pair_and_reboot
}

rollback()
{
    assert_target
    rollback_no_preflight
    reboot_and_wait
    assert_device_file "/system/lib64/$BMS_NAME" "$BMS_OLD_SHA"
    assert_device_file "/system/lib64/$INSTALLS_NAME" "$INSTALLS_OLD_SHA"
    printf 'L03.A12 rollback PASS: old pair restored after reboot.\n'
}

usage()
{
    printf 'Usage: %s preflight-old|deploy|verify-new|rollback\n' "$0" >&2
    exit 2
}

case "${1:-}" in
    preflight-old) preflight_old ;;
    deploy) deploy ;;
    verify-new) verify_new_consumers ;;
    rollback) rollback ;;
    *) usage ;;
esac
