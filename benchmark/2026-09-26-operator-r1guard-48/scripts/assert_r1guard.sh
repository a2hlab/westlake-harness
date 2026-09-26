#!/usr/bin/env bash
# Assert libsscronet.so carries the #48 r1 null-vtable-detector guard (3 nops at the virtual call).
set -uo pipefail
OD=$(command -v llvm-objdump || echo /opt/homebrew/bin/llvm-objdump)
RE=$(command -v llvm-readelf || echo /opt/homebrew/bin/llvm-readelf)
S="${1:?usage: assert_r1guard.sh <libsscronet.so>}"; pass=1
ins=$("$OD" -d --start-address=0x28a218 --stop-address=0x28a224 "$S" 2>/dev/null | grep -c 'nop')
[ "$ins" = 3 ] && echo "PASS: 3 nops at 0x28a218-0x28a220 (detector virtual call skipped)" || { echo "FAIL: expected 3 nops, got $ins"; pass=0; }
# epilogue continuation intact
"$OD" -d --start-address=0x28a224 --stop-address=0x28a228 "$S" 2>/dev/null | grep -q 'add.*x0, sp, #0x200' && echo "PASS: epilogue at 0x28a224 intact" || { echo "FAIL: epilogue clobbered"; pass=0; }
"$RE" -h "$S" 2>/dev/null | grep -q AArch64 && echo "PASS: ELF AArch64 valid" || { echo "FAIL: ELF"; pass=0; }
echo "----"; [ "$pass" = 1 ] && echo "ALL PASS" || { echo "ASSERT FAILED"; exit 1; }
