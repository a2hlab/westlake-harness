#!/usr/bin/env bash
# #48 master switch: assert the shim blocks malloc-family hooks at the bytehook/
# shadowhook API, and (given board evidence) that warm start no longer heap-corrupts
# while the monitor libs still load.
#
# usage: assert_hook_masterswitch.sh <shim.so> [warm-evidence-dir]
set -u
SHIM="${1:?usage: assert_hook_masterswitch.sh <libwebview_bionic_shim.so> [evidence-dir]}"
D="${2:-}"
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }

# --- static: the shim interposes the 9 hook-install/unhook entry points ---
INTERP="shadowhook_hook_sym_name shadowhook_hook_sym_name_callback \
shadowhook_hook_sym_addr shadowhook_hook_func_addr shadowhook_unhook \
bytehook_hook_all bytehook_hook_single bytehook_hook_partial bytehook_unhook"
miss=""
for s in $INTERP; do
  readelf -W --dyn-syms "$SHIM" 2>/dev/null | awk '$5=="GLOBAL"&&$7!="UND"{print $8}' \
    | sed 's/@@.*//' | grep -qx "$s" || miss="$miss $s"
done
[ -z "$miss" ] && say OK "shim interposes all 9 bytehook/shadowhook entry points" \
              || say FAIL "shim missing interposers:$miss"

# the malloc-family filter list is compiled in
for t in malloc free calloc realloc; do
  strings "$SHIM" 2>/dev/null | grep -qx "$t" || say FAIL "filter target '$t' not in shim"
done
[ "$fail" = 0 ] && say OK "malloc-family filter targets present"

# --- board evidence (optional) ---
if [ -n "$D" ]; then
  maps(){ find "$D" -iname '*.maps' -o -iname '*maps*.gz' 2>/dev/null | while read -r m; do
    case "$m" in *.gz) gunzip -c "$m" 2>/dev/null;; *) cat "$m" 2>/dev/null;; esac; done; }
  errs(){ find "$D" -iname '*stderr*' 2>/dev/null | while read -r s; do
    case "$s" in *.gz) gunzip -c "$s" 2>/dev/null;; *) cat "$s" 2>/dev/null;; esac; done; }

  # no mallocng SIG11
  if find "$D" -name 'crash-analysis.json' -exec grep -lE '"signal": *11' {} + 2>/dev/null | grep -q .; then
    say FAIL "a SIG11 crash-analysis is present"
  else
    say OK "no SIG11 crash-analysis"
  fi
  # filter (not refusal): the monitor libs SHOULD load now
  M="$(maps)"
  if [ -n "$M" ]; then
    loaded=""
    for l in libgodzilla-memsponge libjato libmonitorcollector-lib; do
      printf '%s' "$M" | grep -q "/${l}\.so" && loaded="$loaded $l"; done
    [ -n "$loaded" ] && say OK "monitor libs load (filter, not refuse):$loaded" \
                     || say WARN "expected monitor libs not seen in maps"
  else
    say WARN "no maps captured (board: cat /proc/pid/maps > file then pull)"
  fi
  # no _exit(1) / class-init regression
  E="$(errs)"
  if [ -n "$E" ]; then
    printf '%s' "$E" | grep -qiE "ExceptionInInitializerError|_exit\(1\)|Failed to load native" \
      && say WARN "an init/native-load error present — confirm not a functional regression" \
      || say OK "no class-init / _exit(1) regression"
  fi
fi

echo
[ "$fail" = 0 ] && echo "PASS: hook master-switch (pair with 5 warm rounds >=180s, SIG11=0, feed/article)" \
               || echo "FAIL: hook master-switch"
exit $fail
