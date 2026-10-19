#!/system/bin/sh
# Installed as NEW_STATE_ROOT/start-parent.sh. R1 acquires/verifies its lock
# before calling this wrapper. Do not prelaunch a parent outside that lock.
set -eu
HERE=$(dirname "$0")
fail(){ printf '[TT-INTEGRATION] REFUSE %s\n' "$*" >&2; exit 2; }
. "$HERE/config-common.sh"
[ "${TT_RECOVERY_EXECUTE:-0}" = 1 ] && [ "$TT_PROC" = /proc ] || fail UNSIGNED_ENTRY
[ ! -e "$AUTH_SOCKET" ] || fail EXISTING_SOCKET_NO_TAKEOVER
[ "$(sha256sum "$AUTH_STAGE/source_app_namespace" | cut -d' ' -f1)" = "$AUTH_NAMESPACE_SHA" ] || fail NAMESPACE_SHA_CHANGED
[ "$(sha256sum "$HERE/real-start-parent-bounded.sh" | cut -d' ' -f1)" = "$AUTH_START_PARENT_SHA" ] || fail START_PARENT_SHA_CHANGED
. "$HERE/launch-common.sh"
wid=$(foreground_window_id) || fail FOREGROUND_HOST_NOT_READY
# No unbounded old WMS loop: the real helper receives the verified WID.
# Budget: foreground read <=2s + birth <=1s + socket <=2s.
# No nested timeout can signal a spawned parent. Outer R1 envelope remains15s.
# Execute the captured real window-ID update + source_app_namespace entry.
p=$(/system/bin/sh "$HERE/real-start-parent-bounded.sh" "$wid") || fail PARENT_COMMAND_FAILED
case "$p" in ''|*[!0-9]*) fail PARENT_PID_INVALID;; esac
b=''; n=0
while [ -z "$b" ] && [ "$n" -lt 10 ]; do
 b=$(rb_birth "$p") || b=''
 [ -n "$b" ] || sleep .1
 n=$((n+1))
done
[ -n "$b" ] || fail PARENT_NOT_LIVE
n=0
while [ ! -S "$AUTH_SOCKET" ] && [ "$n" -lt 8 ]; do sleep .25; n=$((n+1)); done
[ -S "$AUTH_SOCKET" ] || fail SOCKET_NOT_READY
parent_owned "$p" "$b" || fail PARENT_CHANGED_DURING_WAIT
verify_parent_window "$p" "$b"
file="$HERE/parent-identity"
[ ! -L "$file" ] && { [ ! -e "$file" ] || [ -f "$file" ]; } || fail PARENT_IDENTITY_BAD_PATH
printf '%s %s\n' "$p" "$b" > "$file" || fail PARENT_IDENTITY_WRITE_FAILED
[ "$(cat "$file")" = "$p $b" ] || fail PARENT_IDENTITY_READBACK_FAILED
[ "$(wc -c < "$file")" -eq "$(printf '%s %s\n' "$p" "$b" | wc -c)" ] || fail PARENT_IDENTITY_SIZE_MISMATCH
printf '%s\n' "$p"
