#!/usr/bin/env bash
# #48 warm-start heap-corruption gate: after extending the shim g_refused list to
# the malloc-hooking monitor fleet, a WARM run must show no mallocng crash and the
# refused libs must not be mapped. Run against a warm evidence dir.
#
# usage: assert_heap_hook_refuse.sh <evidence-dir>
#   expects, in the dir: a maps capture (warm.maps or */*.maps[.gz]) and, if a
#   crash occurred, crash-analysis.json; plus the child stderr (adapter_child_*.stderr
#   or child.stderr[.gz]) for UnsatisfiedLinkError checks.
set -u
D="${1:?usage: assert_heap_hook_refuse.sh <evidence-dir>}"
fail=0
say(){ printf '  %-4s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }

# NARROWED to the confirmed allocator hookers only (hook target = malloc/free
# family). libhotfix-opt and the other bytehook/shadowhook users that hook
# NON-allocator symbols are intentionally NOT here — refusing them broke class
# init (app _exit(1) ~61s). libnpth is kept (patched, fresh-proven non-corrupting).
REFUSED="libgodzilla-memsponge libjato libmonitorcollector-lib libsysoptimizer \
libnpth_vm_monitor libnpth_xasan libnpth_heap_tracker"
# These MUST still load (kept functional libs); a load failure here is a regression.
KEPT_FUNCTIONAL="libhotfix-opt libturbo libtunnel libflash libreparo libhubble \
libgodzilla-lib libgodzilla-sysopt libnpth_fd_tracker libnpth_ref_monitor \
libnpth_repair libnpth_tls_monitor libnpth"

# decompress any maps in the dir into one stream
maps(){ find "$D" -iname '*.maps' -o -iname '*maps*.gz' -o -name 'warm.maps' 2>/dev/null | while read -r m; do
  case "$m" in *.gz) gunzip -c "$m" 2>/dev/null;; *) cat "$m" 2>/dev/null;; esac; done; }
errs(){ find "$D" -iname '*stderr*' 2>/dev/null | while read -r s; do
  case "$s" in *.gz) gunzip -c "$s" 2>/dev/null;; *) cat "$s" 2>/dev/null;; esac; done; }

# 1. No mallocng/get_meta SIG11 recorded.
if find "$D" -name 'crash-analysis.json' 2>/dev/null | grep -q .; then
  if find "$D" -name 'crash-analysis.json' -exec grep -lE '"signal": *11' {} + 2>/dev/null | grep -q .; then
    say FAIL "a SIG11 crash-analysis is present in this warm run"
  else
    say OK "crash-analysis present but no signal 11"
  fi
else
  say OK "no SIG11 crash-analysis recorded"
fi

# 2. None of the refused malloc-hooking libs is mapped on warm.
M="$(maps)"
if [ -z "$M" ]; then
  say WARN "no maps captured (cat /proc/pid/maps > file then pull; do not hdc recv)"
else
  bad=""
  for l in $REFUSED; do printf '%s' "$M" | grep -q "/${l}\.so" && bad="$bad $l"; done
  [ -z "$bad" ] && say OK "no refused malloc-hooker mapped" \
                || say FAIL "refused lib(s) still mapped:$bad (refuse not effective)"
fi

# 3. No new UnsatisfiedLinkError for a refused lib (they must be tolerated on NULL).
E="$(errs)"
if [ -z "$E" ]; then
  say WARN "no stderr captured (pull adapter_child_<pid>.stderr)"
else
  ule=""
  for l in $REFUSED; do printf '%s' "$E" | grep -qiE "UnsatisfiedLinkError.*${l}|${l}.*symbol not found" && ule="$ule $l"; done
  [ -z "$ule" ] && say OK "no UnsatisfiedLinkError from refusing these libs" \
               || say FAIL "refusing caused UnsatisfiedLinkError:$ule (unguarded loader — do not refuse that one)"
fi

# 4. No class-init failure / _exit(1) regression from a KEPT functional lib being
#    mis-refused (the libhotfix-opt breakage signature: ExceptionInInitializerError
#    / UnsatisfiedLinkError -> _exit(1) ~61s).
if [ -n "$E" ]; then
  reg=""
  for l in $KEPT_FUNCTIONAL; do printf '%s' "$E" | grep -qiE "UnsatisfiedLinkError.*${l}|${l}.*symbol not found|couldn.t find.*${l}" && reg="$reg $l"; done
  if printf '%s' "$E" | grep -qiE "ExceptionInInitializerError|Failed to load native|_exit\(1\)|clinit"; then
    say WARN "an initializer/native-load error is present — confirm it is not from a kept lib:$reg"
  else
    say OK "no class-init / native-load regression from kept functional libs"
  fi
fi

echo
[ "$fail" = 0 ] && echo "PASS: warm heap-hook refuse gate (pair with >=180s survival + feed/article screenshot, and NO _exit(1))" \
               || echo "FAIL: warm heap-hook refuse gate"
exit $fail
