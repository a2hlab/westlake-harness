#!/bin/bash
# Repro for the Flutter U16 slot check. APP=dir holding <key>/lib/arm64-v8a/libflutter.so; EB90=the eb90 libandroid.so.
# 1) eb90 covered GL procs:  (llvm-nm -D $EB90 | grep ' T gl'); (llvm-strings $EB90 | grep '^gl[A-Z]')
# 2) crash-slot offset per key: disasm the crash PC; the `ldr x8,[x9,#OFF]; blr x8` OFF/8 = ProcTable slot index.
#    localsend +0x4b655c -> OFF 0xea0 -> slot 468 (glDepthRange). fluffychat/kitchenowl +0x4c367c -> OFF 0x8d0 -> slot 282.
APPS=${1:?app-inputs dir}
EB90=${2:?eb90 libandroid.so}
echo "== eb90 covered procs =="; (llvm-strings "$EB90" 2>/dev/null||strings "$EB90") | grep -E '^gl[A-Z]' | sort -u
for row in "localsend:0x4b6540:0x4b6568" "fd-fluffychat:0x4c3660:0x4c3688" "fd-kitchenowl:0x4c3660:0x4c3688"; do
  k=${row%%:*}; rest=${row#*:}; a=${rest%%:*}; b=${rest#*:}
  f="$APPS/$k/lib/arm64-v8a/libflutter.so"; [ -f "$f" ] || continue
  echo "== $k crash slot =="
  llvm-objdump -d --start-address=$a --stop-address=$b "$f" 2>/dev/null | grep -E 'ldr x8, \[x9|blr'
done
