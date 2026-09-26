#!/usr/bin/env bash
# Assert libmonitorcollector-lib.so sigaction install+clear are neutered to mov x0,#0.
set -uo pipefail
OD=$(command -v llvm-objdump || echo /opt/homebrew/bin/llvm-objdump)
RE=$(command -v llvm-readelf || echo /opt/homebrew/bin/llvm-readelf)
M="${1:?usage: assert_r5neuter.sh <libmonitorcollector-lib.so>}"; pass=1
chk(){ local va=$1 n=$2; "$OD" -d --start-address=$va --stop-address=$((va+4)) "$M" 2>/dev/null | grep -q 'mov[[:space:]]*x0, #0x0' && echo "PASS: $n @$(printf 0x%x $va) = mov x0,#0" || { echo "FAIL: $n not neutered"; pass=0; }; }
chk 0x1d214 'xh install sigaction'
chk 0x1df78 'xh_core_clear sigaction'
# no remaining reachable bl sigaction (site2 0x1d318 is a b-tail in the dead handler)
bl=$("$OD" -d "$M" 2>/dev/null | grep -cE 'bl.*<sigaction@plt>')
[ "$bl" = 0 ] && echo "PASS: 0 remaining 'bl sigaction' (both neutered)" || echo "NOTE: $bl bl-sigaction remain (expected 0)"
"$RE" -h "$M" 2>/dev/null | grep -q AArch64 && echo "PASS: ELF AArch64 valid" || { echo "FAIL ELF"; pass=0; }
echo "----"; [ "$pass" = 1 ] && echo "ALL PASS" || { echo "ASSERT FAILED"; exit 1; }
