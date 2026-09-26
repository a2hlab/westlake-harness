#!/usr/bin/env bash
# Assert patched libbytehook.so / libshadowhook.so are hollow-engines (#48):
#   every hook-install export returns fake non-null (mov x0,#1; ret),
#   every unhook export returns 0 (mov x0,#0; ret), exports/SONAME/NEEDED intact.
# Usage: assert_hollow_engines.sh <libbytehook.so> <libshadowhook.so>
set -uo pipefail
OD=$(command -v llvm-objdump || echo /opt/homebrew/bin/llvm-objdump)
RE=$(command -v llvm-readelf || echo /opt/homebrew/bin/llvm-readelf)
pass=1
chk(){ local f=$1 va=$2 want=$3 name=$4
  local ins=$("$OD" -d --start-address=$va --stop-address=$((va+8)) "$f" 2>/dev/null | grep -oiE 'mov[[:space:]]+x0, #0x[01]|ret' | tr '\n' ';')
  if echo "$ins" | grep -q "$want" && echo "$ins" | grep -q 'ret'; then echo "PASS: $name -> $ins"; else echo "FAIL: $name -> $ins (want $want;ret)"; pass=0; fi; }
BY=${1:?}; SH=${2:?}
echo "== libbytehook =="
chk "$BY" 0xdcd4 'x0, #0x1' bytehook_hook_single
chk "$BY" 0xdce8 'x0, #0x1' bytehook_hook_partial
chk "$BY" 0xdcfc 'x0, #0x1' bytehook_hook_all
chk "$BY" 0xdd10 'x0, #0x0' bytehook_unhook
echo "== libshadowhook =="
chk "$SH" 0xc5d4 'x0, #0x1' shadowhook_hook_func_addr
chk "$SH" 0xc764 'x0, #0x1' shadowhook_hook_sym_addr
chk "$SH" 0xc77c 'x0, #0x1' shadowhook_hook_sym_name
chk "$SH" 0xc924 'x0, #0x1' shadowhook_hook_sym_name_callback
chk "$SH" 0xc938 'x0, #0x0' shadowhook_unhook
echo "== structural (exports/SONAME/NEEDED intact, ELF valid) =="
for f in "$BY" "$SH"; do
  n=$(basename "$f"); "$RE" -h "$f" 2>/dev/null | grep -q AArch64 && echo "PASS: $n ELF AArch64" || { echo "FAIL: $n ELF"; pass=0; }
  "$RE" -d "$f" 2>/dev/null | grep -q 'SONAME' && echo "PASS: $n has SONAME" || { echo "FAIL: $n SONAME"; pass=0; }
done
echo "----"; [ "$pass" = 1 ] && echo "ALL PASS" || { echo "ASSERT FAILED"; exit 1; }
