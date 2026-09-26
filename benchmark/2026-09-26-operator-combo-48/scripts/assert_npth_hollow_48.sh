#!/usr/bin/env bash
# #48 hollow npth stub: assert it covers the app ABI and spawns nothing.
# usage: assert_npth_hollow_48.sh <libnpth.so> <npth-app-abi-48.txt>
set -u
L="${1:?usage: assert_npth_hollow_48.sh <libnpth.so> <abi.txt>}"
ABI="${2:?need the ABI list}"
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }

readelf -W -d "$L" 2>/dev/null | grep -q "Library soname: \[libnpth.so\]" \
  && say OK "SONAME=libnpth.so" || say FAIL "SONAME not libnpth.so"
readelf -W --dyn-syms "$L" 2>/dev/null | awk '$4=="FUNC"&&$5=="GLOBAL"&&$7!="UND"{print $8}' \
  | grep -qx JNI_OnLoad && say OK "exports JNI_OnLoad" || say FAIL "no JNI_OnLoad"

# every app native name is registered (present as a string) -> no UnsatisfiedLinkError
miss=""; tot=0
while IFS='|' read -r nm sig; do
  case "$nm" in \#*|"") continue;; esac
  tot=$((tot+1))
  strings "$L" 2>/dev/null | grep -qxF "$nm" || miss="$miss $nm"
done < "$ABI"
[ -z "$miss" ] && say OK "all $tot app npth natives registered (no ULE)" \
  || say FAIL "missing natives (would ULE):$miss"

# both FindClass targets present
for c in "com/bytedance/crash/jni/NativeBridge" "com/bytedance/apm/profiler/Profiler"; do
  strings "$L" 2>/dev/null | grep -qxF "$c" && say OK "registers class $c" \
    || say FAIL "class string missing: $c"
done

# hollow: NEEDED only libc, and NO worker-spawn / hook / sigaction imports
bad=$(readelf -W -d "$L" 2>/dev/null | grep NEEDED | grep -oE "lib[a-z0-9_]+\.so" | grep -vxE "libc.so" | tr '\n' ' ')
[ -z "$bad" ] && say OK "hollow: NEEDED ⊆ {libc.so}" || say FAIL "extra NEEDED: $bad"
spawn=$(readelf -W --dyn-syms "$L" 2>/dev/null | awk '$7=="UND"{print $8}' \
  | grep -iE "pthread_create|bytehook|shadowhook|sigaction|^signal$" | tr '\n' ' ')
[ -z "$spawn" ] && say OK "no worker-spawn / hook / sigaction imports (does nothing)" \
  || say FAIL "imports that would run code: $spawn"
readelf -h "$L" 2>/dev/null | grep -q "Shared object" && say OK "valid ELF shared object" || say FAIL "not a shared object"

echo
[ "$fail" = 0 ] && echo "PASS: hollow npth covers the app ABI and spawns nothing" \
               || echo "FAIL: hollow npth stub"
exit $fail
