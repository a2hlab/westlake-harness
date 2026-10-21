# Synthetic OS adapter for the recorded-epoch interface. No production function replaced here.
# Production rc_epoch_binding, rc_wait_exit, record parsing and signal guards stay real.
RB_PROC=$PROC; RB_RUNTIME=$RUNTIME
fixture_stat() { printf '%s (fixture) S %s 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 %s\n' "$1" "$2" "$3"; }
fixture_process() {
 mkdir -p "$PROC/$1/ns" "$PROC/$1/net" "$PROC/$1/fd"
 fixture_stat "$1" 1 "$2" > "$PROC/$1/stat"
 ln -s 'mnt:[100]' "$PROC/$1/ns/mnt"
}
fixture_process "$$" 1
fixture_process 5177 5834
ln -s 'socket:[333]' "$PROC/5177/fd/4"
printf 'Num RefCount Protocol Flags Type St Inode Path\nx: 00000002 00000000 00010000 0001 01 333 %s\n' "$SOCKET" > "$PROC/$$/net/unix"
cp "$PROC/$$/net/unix" "$PROC/5177/net/unix"
printf 'phase=bound parent=5177:5834 mntns=mnt:[100] sock=333 sockfile=1:20\n' > "$F/parent-epoch"
rc_owned_pids_strict() { return "$enum_rc"; }
rb_birth() {
 if [ "$1" = "$$" ]; then [ -r "$PROC/$$/stat" ] || return 1; echo 1; return 0; fi
 if [ "$1" = 5177 ]; then
  if [ "$terms" = 0 ] || [ "$stop_mode" = alive ]; then echo 5834; return 0; fi
  if [ "$stop_mode" = reused ]; then echo 9999; return 0; fi
  return 1
 fi
 echo 222
}
rc_send_term() {
 terms=$((terms+1)); echo ACTION_TERM
 case "$stop_mode" in
 exited) command rm -rf "$PROC/5177"; holders=; : > "$PROC/$$/net/unix";;
 unreadable) command rm -f "$PROC/5177/stat"; holders=;;
 reused) fixture_stat 5177 1 9999 > "$PROC/5177/stat"; holders=;;
 alive) :;;
 esac
}
fixture_start() {
 starts=$((starts+1)); bound_wid=$pe_wid; holders=$1
 echo ACTION_START; fixture_process "$1" 222
 printf 'Num RefCount Protocol Flags Type St Inode Path\nx: 00000002 00000000 00010000 0001 01 333 %s\n' "$SOCKET" > "$PROC/$$/net/unix"
 cp "$PROC/$$/net/unix" "$PROC/$1/net/unix"
 echo "$1" > "$2"
}
rc_run_start_parent() { fixture_start 8080 "$1"; }
# Let the candidate write its actual epoch schema; do not manufacture newer fields.
rc_record_bootstrap_epoch
