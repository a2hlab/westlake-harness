#!/bin/bash
# board_run before_unlock for the 5ea Genshin window: uninstall com.miHoYo.Yuanshen (absent is fine), then
# read back. hdc shell does not propagate the remote rc, so the verdict is computed here: rc 0 only when
# the package is absent afterwards; otherwise rc 1 and board_run keeps the lock for recovery.
set -u
S=${1:?serial}; HDC=${HDC:-hdc}
echo "== boot_id"; "$HDC" -t "$S" shell "cat /proc/sys/kernel/random/boot_id"
echo "== uninstall"; "$HDC" -t "$S" shell "bm uninstall -n com.miHoYo.Yuanshen"
n=$("$HDC" -t "$S" shell "bm dump -a" | tr -d '\r' | grep -c -x -F $'\tcom.miHoYo.Yuanshen')
echo "== remaining=$n"
[ "$n" = 0 ]
