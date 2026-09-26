#!/usr/bin/env bash
# #48: verify whether a bytehook/shadowhook user actually HOOKS the malloc family
# (target) vs merely CALLS malloc (UND import). The refuse criterion is the former.
# usage: verify_hook_targets.sh <lib/arm64-v8a>
set -u
APK="${1:?usage: verify_hook_targets.sh <lib/arm64-v8a>}"
printf "%-26s %-22s %-12s %-8s %s\n" LIB rodata-alloc-target UND-malloc dispatch verdict
for f in "$APK"/*.so; do
  b=$(basename "$f" .so)
  # only libs that can hook
  readelf -W -d "$f" 2>/dev/null | grep -qiE "NEEDED.*(libbytehook|libshadowhook)" || continue
  # (b) malloc-family as a .rodata string (the hook target)
  rod=$(readelf -p .rodata "$f" 2>/dev/null | grep -oE "\b(malloc|free|calloc|realloc|posix_memalign|memalign|aligned_alloc)\b" | sort -u | tr '\n' ',')
  # (a) malloc as UND import (calls it)
  und=$(readelf -W --dyn-syms "$f" 2>/dev/null | awk '$7=="UND"{print $8}' | grep -oxE "malloc|free|calloc|realloc" | sort -u | tr '\n' ',')
  # hook-install imports
  inst=$(readelf -W --dyn-syms "$f" 2>/dev/null | awk '$7=="UND"{print $8}' | grep -cE "_hook_(all|single|partial|sym_name|sym_addr|func_addr)")
  disp=$(readelf -W --dyn-syms "$f" 2>/dev/null | grep -qE "__libc_malloc_dispatch|__libc_globals" && echo YES || echo no)
  if { [ -n "$rod" ] && [ "$inst" -gt 0 ]; } || [ "$disp" = YES ]; then v=REFUSE; else v=keep; fi
  printf "%-26s %-22s %-12s %-8s %s\n" "$b" "${rod:-none}" "${und:-none}" "$disp" "$v"
done
