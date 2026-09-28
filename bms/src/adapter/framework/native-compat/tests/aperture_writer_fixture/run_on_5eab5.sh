#!/usr/bin/env bash
# Execute only the company-owned, product-disabled aperture fixture on D600-B.
# This does not start CardWords or install a product library.  All host evidence
# stays under this project and the remote directory is owned by this run.

set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)
HDC=${HDC:-$PROJECT_ROOT/adapter/frozen/tools/hdc/hdc}
SERIAL=${SERIAL:-5eab586000000000000000001123012c}
RUN_ID=${RUN_ID:-$(date -u '+%Y%m%dT%H%M%SZ')}
OUT=${WLAF_DEVICE_OUT:-$SCRIPT_DIR/evidence/device-runs/$RUN_ID}
BACKEND=$SCRIPT_DIR/out/target/libwestlake_aperture_fixture_backend.so
MAIN=$SCRIPT_DIR/out/target/wlaf_aperture_owner_fixture
EXPECTED_BACKEND_SHA=c0055d9e9be4559263279aaec5c8103b196f7e0541ea48423de5660837e55805
EXPECTED_MAIN_SHA=d9559ae1c9e4497d427a247ea52cd13be05181281fa69bd0b7b72fd6c36d0144
EXPECTED_LOADER_SHA=316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98
REMOTE=/data/local/tmp/westlake-wlaf-${EXPECTED_MAIN_SHA:0:12}
LOCK=/data/local/tmp/westlake-codex-5eab5.lock
LOCK_ACQUIRED=0

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: evidence output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -e "$OUT" ]]; then
    echo "ERROR: immutable evidence directory already exists: $OUT" >&2
    exit 2
fi
test -x "$HDC"
test -f "$BACKEND"
test -f "$MAIN"

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

if [[ $(sha256_file "$BACKEND") != "$EXPECTED_BACKEND_SHA" ]]; then
    echo "ERROR: backend identity drift" >&2
    exit 2
fi
if [[ $(sha256_file "$MAIN") != "$EXPECTED_MAIN_SHA" ]]; then
    echo "ERROR: main fixture identity drift" >&2
    exit 2
fi

mkdir -p "$OUT/raw"
COMMANDS=$OUT/commands.log
touch "$COMMANDS"

record()
{
    printf '%s\n' "$*" >>"$COMMANDS"
}

remote_capture()
{
    local name=$1
    shift
    record "hdc -t $SERIAL shell $*"
    "$HDC" -t "$SERIAL" shell "$*" >"$OUT/raw/$name" 2>&1
}

cleanup()
{
    set +e
    if [[ $LOCK_ACQUIRED -eq 1 ]]; then
        record "hdc -t $SERIAL shell rm owned remote fixture and lock"
        "$HDC" -t "$SERIAL" shell "rm -rf '$REMOTE'; rmdir '$LOCK'" \
            >>"$OUT/raw/cleanup.txt" 2>&1
        LOCK_ACQUIRED=0
    fi
}
trap cleanup EXIT INT TERM

record "hdc list targets"
"$HDC" list targets >"$OUT/raw/targets.txt" 2>&1
if ! tr -d '\r' <"$OUT/raw/targets.txt" | grep -Fxq "$SERIAL"; then
    echo "ERROR: exact target is not connected" >&2
    exit 3
fi

{
    printf 'schema=westlake-wlaf-device-run-v1\n'
    printf 'serial=%s\n' "$SERIAL"
    printf 'hdc_path=%s\n' "$HDC"
    printf 'hdc_sha256=%s\n' "$(sha256_file "$HDC")"
    printf 'backend_sha256=%s\n' "$EXPECTED_BACKEND_SHA"
    printf 'main_sha256=%s\n' "$EXPECTED_MAIN_SHA"
    printf 'target_loader_sha256=%s\n' "$EXPECTED_LOADER_SHA"
    printf 'third_party_dso_mapped=false\n'
    printf 'product_activation=false\n'
} >"$OUT/inputs.env"

remote_capture before.txt \
    "date; cat /proc/sys/kernel/random/boot_id; getenforce; ps -A -o PID,NAME,ARGS"

record "hdc -t $SERIAL shell mkdir $LOCK"
if ! "$HDC" -t "$SERIAL" shell "mkdir '$LOCK'" >"$OUT/raw/lock.txt" 2>&1; then
    echo "ERROR: target coordination lock is held; no device change made" >&2
    exit 4
fi
LOCK_ACQUIRED=1

record "hdc -t $SERIAL shell prepare $REMOTE"
"$HDC" -t "$SERIAL" shell "rm -rf '$REMOTE'; mkdir '$REMOTE'" \
    >"$OUT/raw/prepare.txt" 2>&1
record "hdc -t $SERIAL file send backend"
"$HDC" -t "$SERIAL" file send "$BACKEND" \
    "$REMOTE/libwestlake_aperture_fixture_backend.so" \
    >"$OUT/raw/send-backend.txt" 2>&1
record "hdc -t $SERIAL file send main"
"$HDC" -t "$SERIAL" file send "$MAIN" \
    "$REMOTE/wlaf_aperture_owner_fixture" \
    >"$OUT/raw/send-main.txt" 2>&1
remote_capture remote-identity.txt \
    "sha256sum /lib/ld-musl-aarch64.so.1 '$REMOTE/libwestlake_aperture_fixture_backend.so' '$REMOTE/wlaf_aperture_owner_fixture'; chmod 0500 '$REMOTE/wlaf_aperture_owner_fixture'; chmod 0400 '$REMOTE/libwestlake_aperture_fixture_backend.so'"

grep -Fq "$EXPECTED_LOADER_SHA" "$OUT/raw/remote-identity.txt"
grep -Fq "$EXPECTED_BACKEND_SHA" "$OUT/raw/remote-identity.txt"
grep -Fq "$EXPECTED_MAIN_SHA" "$OUT/raw/remote-identity.txt"

record "hdc -t $SERIAL shell execute company-owned fixture"
set +e
"$HDC" -t "$SERIAL" shell \
    "LD_LIBRARY_PATH='$REMOTE' '$REMOTE/wlaf_aperture_owner_fixture'; rc=\$?; echo __WLAF_REMOTE_RC=\$rc; exit \$rc" \
    >"$OUT/raw/execute.txt" 2>&1
HDC_RC=$?
set -e
REMOTE_RC=$(sed -n 's/.*__WLAF_REMOTE_RC=\([0-9][0-9]*\).*/\1/p' \
    "$OUT/raw/execute.txt" | tail -1 | tr -d '\r')
if [[ $HDC_RC -ne 0 || "$REMOTE_RC" != 0 ]]; then
    printf 'status=FAIL\nhdc_exit_code=%s\nremote_exit_code=%s\n' \
        "$HDC_RC" "${REMOTE_RC:-missing}" >"$OUT/result.env"
    echo "ERROR: target fixture rejected; see $OUT/raw/execute.txt" >&2
    exit 5
fi

remote_capture after.txt \
    "date; cat /proc/sys/kernel/random/boot_id; getenforce; ps -A -o PID,NAME,ARGS"

BEFORE_BOOT=$(sed -n '2p' "$OUT/raw/before.txt" | tr -d '\r')
AFTER_BOOT=$(sed -n '2p' "$OUT/raw/after.txt" | tr -d '\r')
BEFORE_ENFORCE=$(sed -n '3p' "$OUT/raw/before.txt" | tr -d '\r')
AFTER_ENFORCE=$(sed -n '3p' "$OUT/raw/after.txt" | tr -d '\r')
if [[ -z "$BEFORE_BOOT" || "$BEFORE_BOOT" != "$AFTER_BOOT" ||
      "$BEFORE_ENFORCE" != "Enforcing" || "$AFTER_ENFORCE" != "Enforcing" ]]; then
    echo "ERROR: device bracket changed or SELinux was not Enforcing" >&2
    exit 6
fi

{
    printf 'status=PASS\n'
    printf 'classification=company_owned_target_fixture\n'
    printf 'target_executed=true\n'
    printf 'device_verified_aperture_fixture=true\n'
    printf 'device_verified_product=false\n'
    printf 'product_activation=false\n'
    printf 'third_party_dso_mapped=false\n'
    printf 'boot_id=%s\n' "$BEFORE_BOOT"
    printf 'selinux=Enforcing\n'
    printf 'hdc_exit_code=0\nremote_exit_code=0\n'
} >"$OUT/result.env"

trap - EXIT INT TERM
cleanup
shasum -a 256 "$OUT/inputs.env" "$OUT/result.env" "$OUT/commands.log" \
    "$OUT"/raw/* >"$OUT/MANIFEST.sha256"
echo "PASS company-owned aperture target fixture; product_activation=false third_party_dso_mapped=false"
