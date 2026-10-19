#!/bin/sh
# OUTER ONLY: read-only and serial/lock enforcement belongs to the invoking outer.
set -eu
root=$1
case "$root" in /data/local/tmp/wl-debug-compat-????????-*) ;; *) exit 2;; esac
printf 'R12_BOOT\n'; cat /proc/sys/kernel/random/boot_id
printf 'R12_KERNEL\n'; uname -srvm
printf 'R12_SELINUX\n'; getenforce
printf 'R12_ROOT\n'; if [ -e "$root" ]; then printf 'PRESENT\n'; else printf 'ABSENT\n'; fi
printf 'R12_PIDS\n'; printf '%s\n' /proc/[0-9]*
printf 'R12_TCP\n'; cat /proc/net/tcp
printf 'R12_TCP6\n'; cat /proc/net/tcp6
printf 'R12_BOOT_END\n'; cat /proc/sys/kernel/random/boot_id
printf 'R12_RC=0\n'
