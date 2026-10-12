#!/system/bin/sh
# Future reviewed attempt only. NONE in authorization.expected.sha256 disarms it.
set -eu
HERE=$(dirname "$0")
fail(){ printf '[TT-INTEGRATION] REFUSE %s\n' "$*" >&2; exit 2; }
expected=$(cat "$HERE/authorization.expected.sha256") || fail AUTH_BINDING_MISSING
case "$expected" in ''|NONE|*[!0-9a-f]*) fail UNSIGNED_NEW_ATTEMPT;; esac
[ "${#expected}" = 64 ] || fail AUTH_BINDING_INVALID
[ $# = 1 ] && [ -f "$1" ] && [ ! -L "$1" ] || fail AUTH_FILE_REQUIRED
[ "$(sha256sum "$1" | cut -d' ' -f1)" = "$expected" ] || fail AUTH_SHA_MISMATCH
# Source only the exact outer-reviewed file pinned into this package, never a
# caller-supplied hash/env flag. Default package has no such approval.
. "$1"
[ "${AUTH_APPROVED_BY:-}" = 'outer(codex)' ] || fail AUTH_NOT_OUTER
[ "${AUTH_NEW_ATTEMPT:-}" = yes ] || fail AUTH_NOT_NEW_ATTEMPT
[ "${AUTH_RETAIN_OLD_STOP:-}" = yes ] || fail OLD_STOP_POLICY_PENDING
[ "${AUTH_SERIAL:-}" = 61b0657200000000000000000324012c ] || fail WRONG_SERIAL
[ "$(date +%s)" -lt "${AUTH_EXPIRES_EPOCH:-0}" ] || fail AUTH_EXPIRED
boot=$(cat /proc/sys/kernel/random/boot_id)
[ "$boot" = "${AUTH_BOOT:-}" ] || fail WRONG_BOOT
case "${AUTH_UID:-}" in ''|0|*[!0-9]*) fail UID_INVALID;; esac
[ "$AUTH_UID" = 20011206 ] || fail EFFECTIVE_UID_REBIND_REQUIRED
[ "$(stat -c %u /data/app/el2/100/base/org.westlake.imehost)" = "$AUTH_UID" ] || fail INSTALLED_HOST_UID_CHANGED
case "${AUTH_STATE_ROOT:-}" in /data/westlake-demo/toutiao/recovery-attempts/*) :;; *) fail NEW_STATE_ROOT_REQUIRED;; esac
[ "${AUTH_STATE_ROOT}" != /data/local/tmp/operator45/selfheal48 ] || fail OLD_STATE_ROOT
old=/data/local/tmp/operator45/selfheal48/stop
[ -f "$old" ] && [ ! -L "$old" ] || fail OLD_STOP_CHANGED
[ "$(sha256sum "$old" | cut -d' ' -f1)" = "${AUTH_OLD_STOP_SHA:-}" ] || fail OLD_STOP_SHA_CHANGED
[ "${AUTH_CAPTURE_FORMAT_VERIFIED:-}" = yes ] || fail CAPTURE_FORMAT_PENDING
[ "${AUTH_RUNTIME_BINDINGS_VERIFIED:-}" = yes ] || fail RUNTIME_BINDINGS_PENDING
[ "${AUTH_CANDIDATE_SHA:-}" = 9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072 ] || fail WRONG_CANDIDATE
[ -f "$HERE/route-b-owner.sh" ] || fail MISSING_HELPER
[ "$(sha256sum "$HERE/route-b-owner.sh" | cut -d' ' -f1)" = "${AUTH_HELPER_SHA:-}" ] || fail HELPER_SHA_CHANGED
[ "$(sha256sum "$HERE/watchdog.sh" | cut -d' ' -f1)" = "${AUTH_WATCHDOG_FILE_SHA:-}" ] || fail WATCHDOG_FILE_SHA_CHANGED
[ -d "$AUTH_STATE_ROOT" ] && [ ! -e "$AUTH_STATE_ROOT/lock" ] && [ ! -e "$AUTH_STATE_ROOT/stop" ] || fail NEW_STATE_NOT_READY
. "$HERE/launch-common.sh"
case "${AUTH_WAIT_FOR_TAP_SECONDS:-}" in ''|0|*[!0-9]*) fail TAP_WAIT_POLICY_PENDING;; esac
n=0
while ! foreground_window_id >/dev/null; do
 [ "$n" -lt "$AUTH_WAIT_FOR_TAP_SECONDS" ] || fail FOREGROUND_HOST_NOT_READY
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$AUTH_BOOT" ] || fail BOOT_CHANGED_DURING_TAP_WAIT
 [ "$(date +%s)" -lt "$AUTH_EXPIRES_EPOCH" ] || fail AUTH_EXPIRED
 [ ! -e "$AUTH_STATE_ROOT/stop" ] || fail NEW_ATTEMPT_STOPPED
 sleep 1; n=$((n+1))
done
# Candidate verifies these again. No lookup/adoption by process name.
export TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT="$boot" TT_OWNER_UID="$AUTH_UID"
export TT_STATE_ROOT="$AUTH_STATE_ROOT"
export TT_RUNTIME="$AUTH_RUNTIME" TT_STAGE="$AUTH_STAGE" TT_SOCKET="$AUTH_SOCKET"
case "${AUTH_PARENT_MODE:-}" in
 existing)
  [ -n "${AUTH_PARENT_PID:-}" ] && [ -n "${AUTH_PARENT_BIRTH:-}" ] || fail PARENT_IDENTITY_PENDING
  export TT_PARENT_PID="$AUTH_PARENT_PID" TT_PARENT_BIRTH="$AUTH_PARENT_BIRTH";;
 new) unset TT_PARENT_PID TT_PARENT_BIRTH;;
 *) fail PARENT_MODE_PENDING;;
esac
export TT_INTEGRATION_AUTH="$1" TT_INTEGRATION_HERE="$HERE"
printf '[TT-INTEGRATION] starting reviewed new attempt; old stop/data retained\n'
exec /system/bin/sh "$HERE/watchdog.sh"
