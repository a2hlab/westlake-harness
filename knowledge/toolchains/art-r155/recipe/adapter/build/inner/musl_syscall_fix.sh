#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# musl_syscall_fix.sh - Fix missing SYS_* aliases in generated syscall.h
#
# The OH musl build generates include/bits/syscall.h with only __NR_* defines.
# musl's src/internal/syscall.h expects SYS_* aliases (e.g., SYS_futex, SYS_mmap).
# Without them, compilation of dynlink.c, __init_tls.c etc. fails with
# "use of undeclared identifier 'SYS_futex_time64'" on aarch64.
#
# This script must run AFTER GN gen creates the intermediate files
# but BEFORE ninja compiles musl source files.
#
# Usage: musl_syscall_fix.sh <oh_output_dir>
#   e.g.: musl_syscall_fix.sh ~/oh/out/rk3568

set -e

OH_OUT="${1:?Usage: musl_syscall_fix.sh <oh_output_dir>}"

# Find the generated syscall.h
SYSCALL_H=$(find "$OH_OUT/obj/third_party/musl" -path "*/include/bits/syscall.h" 2>/dev/null | head -1)

if [ -z "$SYSCALL_H" ]; then
    echo "[musl_fix] WARNING: syscall.h not found in $OH_OUT - GN gen may not have run yet"
    exit 0
fi

# Check if SYS_ aliases already exist
if grep -q '^#define SYS_' "$SYSCALL_H"; then
    echo "[musl_fix] SYS_* aliases already present in $SYSCALL_H - skipping"
    exit 0
fi

# Count __NR_ defines
NR_COUNT=$(grep -c '^#define __NR_' "$SYSCALL_H")
echo "[musl_fix] Found $NR_COUNT __NR_* defines, adding SYS_* aliases..."

# Append SYS_* aliases from __NR_* defines
grep '^#define __NR_' "$SYSCALL_H" | sed 's/__NR_/SYS_/' >> "$SYSCALL_H"

SYS_COUNT=$(grep -c '^#define SYS_' "$SYSCALL_H")
echo "[musl_fix] Added $SYS_COUNT SYS_* aliases to $SYSCALL_H"
