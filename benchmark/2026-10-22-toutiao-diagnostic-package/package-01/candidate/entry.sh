#!/system/bin/sh
# Immutable durable authority; no short-lived install ticket sourced at runtime.
set -eu
HERE=$(dirname "$0")
. "$HERE/config-common.sh"
[ "$HERE" = "$AUTH_STATE_ROOT" ] || fail WRONG_KERNEL_BOOT_ATTEMPT
[ ! -e "$HERE/lock" ] && [ ! -e "$HERE/stop" ] || fail ATTEMPT_ALREADY_LOCKED_OR_STOPPED
# Read/decode a pinned synthetic JPEG through the same binary BEFORE any launch.
[ "$(sha256sum "$HERE/screen-gate" | cut -d' ' -f1)" = "$STARTUP_DECODER_SHA" ] || fail DECODER_CHANGED
[ "$(sha256sum "$HERE/decoder-probe.jpeg" | cut -d' ' -f1)" = "$STARTUP_PROBE_SHA" ] || fail DECODER_PROBE_CHANGED
[ -x "$HERE/screen-gate" ] || fail DECODER_NOT_EXECUTABLE
label=$(timeout 2 "$HERE/screen-gate" "$HERE/decoder-probe.jpeg") || fail DECODER_PRELAUNCH_FAILED
[ "$label" = feed ] || fail DECODER_PRELAUNCH_RESULT
. "$HERE/launch-common.sh"
# Human foreground tap only; persistent read-only wait. Never aa start/uinput.
[ "$STARTUP_TAP_WAIT_POLICY" = until-human-or-stop-or-boot-change ] || fail TAP_WAIT_POLICY
while ! foreground_window_id >/dev/null; do
 [ ! -e "$ROOT/stop" ] && [ ! -e "$HERE/stop" ] || fail STOP_DURING_TAP_WAIT
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$AUTH_BOOT" ] || fail BOOT_CHANGED
 sleep 1
done
[ ! -e "$AUTH_SOCKET" ] || fail EXISTING_SOCKET_NO_TAKEOVER
[ "$(sha256sum "$HERE/watchdog.sh" | cut -d' ' -f1)" = bcae2c697ae5ee6e31c836cd38d322d5120a87ffa74f1d35d2c88acca7be818e ] || fail WATCHDOG_CHANGED
[ "$(sha256sum "$HERE/route-b-owner.sh" | cut -d' ' -f1)" = fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58 ] || fail HELPER_CHANGED
unset TT_PARENT_PID TT_PARENT_BIRTH TT_CHILD_PID TT_CHILD_BIRTH TT_OPERATOR_ROOT TT_INTEGRATION_AUTH TT_INTEGRATION_HERE
export TT_PROC=/proc TT_MAX_ATTEMPTS=3 TT_MAX_POLLS=0
export TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT="$AUTH_BOOT" TT_OWNER_UID="$AUTH_UID"
export TT_STATE_ROOT="$AUTH_STATE_ROOT" TT_RUNTIME="$AUTH_RUNTIME" TT_STAGE="$AUTH_STAGE" TT_SOCKET="$AUTH_SOCKET"
printf '[TT-EXECUTOR] launching immutable guardian boot=%s\n' "$AUTH_BOOT"
exec /system/bin/sh "$HERE/watchdog.sh"
