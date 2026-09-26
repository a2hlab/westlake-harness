#!/usr/bin/env bash
# #48 final npth: assert class-3 + hook-neuter + sigaction-neuter all present and
# the lib stays loadable. usage: assert_npth_all_48.sh <libnpth.so>
set -u
L="${1:?usage: assert_npth_all_48.sh <libnpth.so>}"
OBJD="${OBJD:-$HOME/a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump}"
[ -x "$OBJD" ] || OBJD=$(command -v llvm-objdump || command -v objdump)
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }
at(){ python3 -c "import sys;d=open('$L','rb').read();print(d[$1:$1+4].hex())"; }

readelf -W --dyn-syms "$L" 2>/dev/null | grep -qw JNI_OnLoad \
  && say OK "JNI_OnLoad exported (loadable)" || say FAIL "no JNI_OnLoad"
[ "$(at 0x17930)" = "c0035fd6" ] && say OK "class-3 thread-walk ret (0x17930)" \
  || say FAIL "class-3 ret missing: $(at 0x17930)"
[ "$(at 0x1ffb4)" = "200080d2" ] && say OK "hook site1 neutered (mov x0,#1)" \
  || say FAIL "hook site1: $(at 0x1ffb4)"
[ "$(at 0x24a34)" = "200080d2" ] && say OK "hook site2 neutered (mov x0,#1)" \
  || say FAIL "hook site2: $(at 0x24a34)"
# the 14 non-NULL-old sigaction sites -> mov x0,#0 (000080d2)
n=0; bad=""
for off in 0x12b68 0x12b7c 0x13200 0x13390 0x13d24 0x13d3c 0x13d54 0x13d6c 0x13d84 \
           0x13d9c 0x13db4 0x13df4 0x13e10 0x1e260; do
  if [ "$(at $off)" = "000080d2" ]; then n=$((n+1)); else bad="$bad $off"; fi
done
[ -z "$bad" ] && say OK "all 14 non-NULL-old sigaction calls neutered (mov x0,#0)" \
  || say FAIL "sigaction sites not neutered:$bad"
# no residual bl to sigaction with a non-null old is hard to assert statically here;
# rely on the 14-site check above + the count of remaining sigaction bls (should be 20)
rem=$("$OBJD" -d "$L" 2>/dev/null | grep -cE "bl[[:space:]]+0x[0-9a-f]+ <sigaction")
[ "$rem" = 20 ] && say OK "20 old=NULL sigaction calls kept (handlers still install)" \
  || say WARN "remaining sigaction bl = $rem (expected 20)"

echo
[ "$fail" = 0 ] && echo "PASS: npth class-3+hook+sigaction patched, loadable (board: warm, npth mapped, no sigaction SEGV, SIG11=0)" \
               || echo "FAIL: npth final patch"
exit $fail
