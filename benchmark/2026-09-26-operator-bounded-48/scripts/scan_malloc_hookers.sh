#!/usr/bin/env bash
# #48 warm-crash: find the ByteDance libs that inline-hook the malloc family via
# bytehook/shadowhook — the musl mallocng heap-corruption vector on warm start.
# usage: scan_malloc_hookers.sh <apk arm64-v8a lib dir>
set -u
APK="${1:?usage: scan_malloc_hookers.sh <lib/arm64-v8a>}"
echo "== libs that DT_NEED a hook engine AND reference malloc-family names =="
for f in "$APK"/*.so; do
  b=$(basename "$f")
  readelf -W -d "$f" 2>/dev/null | grep -qiE "libbytehook|libshadowhook" || continue
  hits=$(strings -a "$f" | grep -xE "malloc|free|calloc|realloc|posix_memalign|memalign|aligned_alloc|mallinfo|malloc_usable_size" | sort -u | tr '\n' ' ')
  [ -n "$hits" ] && printf "  %-28s [%s]\n" "$b" "$hits"
done
echo "== hook-engine export surfaces (stub must cover) =="
for eng in libbytehook.so libshadowhook.so; do
  [ -f "$APK/$eng" ] || continue
  echo "  $eng: $(readelf -W --dyn-syms "$APK/$eng" 2>/dev/null | awk '$4~/FUNC|OBJECT/&&$5=="GLOBAL"&&$7!="UND"{print $8}' | wc -l) exports"
done
