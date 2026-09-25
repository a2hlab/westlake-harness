#!/usr/bin/env bash
# #48 hollow metasec: assert the stub libmetasec_ml.so satisfies the app's whole
# native ABI and is genuinely hollow (no heavy deps / init surface).
# usage: assert_metasec_stub.sh <libmetasec_ml.so>
set -u
L="${1:?usage: assert_metasec_stub.sh <libmetasec_ml.so>}"
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = MISS ] && fail=1; return 0; }

dyn(){ readelf -W --dyn-syms "$L" 2>/dev/null; }

# 1. SONAME must be libmetasec_ml.so so it drops in over the app copy.
if readelf -W -d "$L" 2>/dev/null | grep -q "Library soname: \[libmetasec_ml.so\]"; then
  say OK "SONAME=libmetasec_ml.so"; else say MISS "SONAME not libmetasec_ml.so"; fi

# 2. JNI runtime entry point.
dyn | awk '$4=="FUNC"&&$5=="GLOBAL"&&$7!="UND"{print $8}' | grep -qx JNI_OnLoad \
  && say OK "exports JNI_OnLoad" || say MISS "no JNI_OnLoad"

# 3. The app's SOLE metasec native: ms.bd.c.m.a (public static native
#    Object a(int,int,long,String,Object)). Short mangled name (one native in
#    the class) -> Java_ms_bd_c_m_a. Covered by the stub's default-resolution export.
dyn | awk '$4=="FUNC"&&$5=="GLOBAL"&&$7!="UND"{print $8}' | grep -qx Java_ms_bd_c_m_a \
  && say OK "exports Java_ms_bd_c_m_a (app native ms.bd.c.m.a)" \
  || say MISS "no Java_ms_bd_c_m_a — app native would UnsatisfiedLinkError"

# 4. Hollow: must NOT drag metasec's heavy deps. The real lib NEEDs
#    liblog/libandroid/libm/libdl/libc; a hollow stub needs at most libc.
bad=$(readelf -W -d "$L" 2>/dev/null | grep NEEDED | grep -oE "lib[a-z0-9_]+\.so" \
      | grep -vE "^libc\.so$" | sort -u | tr '\n' ' ')
[ -z "$bad" ] && say OK "hollow: NEEDED ⊆ {libc.so}" \
  || say MISS "not hollow: extra NEEDED: $bad"

# 5. No undefined symbols at all (a hollow stub resolves entirely on its own).
un=$(dyn | awk '$4~/FUNC|OBJECT/ && $5=="GLOBAL" && $7=="UND"{print $8}' | sort -u)
uc=$(printf '%s\n' "$un" | grep -c . )
[ "$uc" = 0 ] && say OK "no undefined global symbols (fully self-contained)" \
  || say WARN "$uc undefined symbols (real lib, not hollow): $(printf '%s ' $un | cut -c1-80)…"

echo
[ "$fail" = 0 ] && echo "PASS: hollow metasec stub covers the app native ABI" \
               || echo "FAIL: stub does not cover the app native ABI"
exit $fail
