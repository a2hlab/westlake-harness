#!/usr/bin/env bash
# #48: enumerate the malloc-hooking fleet in an APK lib dir and classify by load
# mechanism (dlopen-only = shim-refusable vs DT_NEEDED = not).
# usage: scan_heap_hook_fleet.sh <lib/arm64-v8a>
set -u
APK="${1:?usage: scan_heap_hook_fleet.sh <lib/arm64-v8a>}"

echo "TOTAL: $(ls "$APK"/*.so 2>/dev/null | wc -l) libs"
echo
echo "SET A — reference Bionic malloc-dispatch ABI:"
for f in "$APK"/*.so; do readelf -W --dyn-syms "$f" 2>/dev/null | grep -qE "__libc_malloc_dispatch|__libc_globals" && echo "  $(basename "$f")"; done
echo "  (empty = none)"
echo
echo "SET C — DT_NEED bytehook/shadowhook AND hook the malloc family:"
hookers=""
for f in "$APK"/*.so; do
  b=$(basename "$f")
  readelf -W -d "$f" 2>/dev/null | grep -qiE "NEEDED.*(libbytehook|libshadowhook)" || continue
  strings -a "$f" | grep -qxE "malloc|free|calloc|realloc|posix_memalign|memalign" || continue
  hookers="$hookers $b"
  hits=$(strings -a "$f" | grep -xE "malloc|free|calloc|realloc|posix_memalign|memalign" | sort -u | tr '\n' ' ')
  printf "  %-28s [%s]\n" "$b" "$hits"
done
echo
echo "Load mechanism (dlopen-only = shim-refusable):"
for h in $hookers; do
  base="${h%.so}"
  needed_by=$(for f in "$APK"/*.so; do readelf -W -d "$f" 2>/dev/null | grep -qE "NEEDED.*\b${base}\.so\b" && basename "$f"; done | tr '\n' ' ')
  [ -n "$needed_by" ] && echo "  DT_NEEDED  $h  <- $needed_by" || echo "  dlopen-only $h"
done
