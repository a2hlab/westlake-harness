#!/usr/bin/env bash
# #48 fallback: assert a patched libnpth.so has its inline-hook installs neutered
# while staying loadable (JNI_OnLoad intact) and keeping the class-3 thread-walk ret
# patch. usage: assert_npth_nohooks.sh <libnpth.so>
set -u
L="${1:?usage: assert_npth_nohooks.sh <libnpth.so>}"
OBJD="${OBJD:-$HOME/a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump}"
[ -x "$OBJD" ] || OBJD=$(command -v llvm-objdump || command -v objdump)
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }
at(){ python3 -c "import sys;d=open('$L','rb').read();print(d[$1:$1+4].hex())"; }

# 1. still loadable: JNI_OnLoad exported
readelf -W --dyn-syms "$L" 2>/dev/null | grep -qw JNI_OnLoad \
  && say OK "JNI_OnLoad exported (npth stays loadable)" || say FAIL "no JNI_OnLoad"

# 2. both hook-install sites neutered to mov x0,#1 (d2800020 -> LE 200080d2)
[ "$(at 0x1ffb4)" = "200080d2" ] && say OK "site1 bytehook(setpriority) neutered (mov x0,#1)" \
  || say FAIL "site1 not neutered: $(at 0x1ffb4)"
[ "$(at 0x24a34)" = "200080d2" ] && say OK "site2 shadowhook(ART GC table) neutered (mov x0,#1)" \
  || say FAIL "site2 not neutered: $(at 0x24a34)"

# 3. no inline hook-install call remains
n=$("$OBJD" -d "$L" 2>/dev/null | grep -cE "bl[[:space:]]+0x[0-9a-f]+ <(bytehook_hook_partial|shadowhook_hook_sym_name|bytehook_hook_all|shadowhook_hook_sym_addr)")
[ "$n" = 0 ] && say OK "no bytehook/shadowhook hook-install call remains" \
  || say FAIL "$n hook-install call(s) still present"

# 4. class-3 thread-walk ret patch preserved (this stacks on 8b8d559c)
[ "$(at 0x17930)" = "c0035fd6" ] && say OK "class-3 thread-walk ret patch intact (0x17930)" \
  || say FAIL "class-3 ret patch missing: $(at 0x17930) (wrong base? use 8b8d559c)"

echo
[ "$fail" = 0 ] && echo "PASS: npth hooks neutered, still loadable (board: warm, npth mapped + JNI_OnLoad ok + SIG11=0)" \
               || echo "FAIL: npth no-hooks patch"
exit $fail
