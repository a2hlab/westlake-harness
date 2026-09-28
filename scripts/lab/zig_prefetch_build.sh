#!/bin/bash
# Build herdr when Zig's own HTTP client fails through the proxy (HTTP 400): each dependency URL Zig
# reports is downloaded with curl and added to Zig's package cache with `zig fetch <file>` (content-hashed,
# so it is the same package build.zig.zon pins), then the build is retried. `zig fetch` runs where build.zig
# lives (vendor/libghostty-vt); Zig 0.16 refuses to run it elsewhere. Zig cannot reach the network here at all
# (HTTP 400 through the proxy, TlsInitializationFailed without it), so every dependency comes this way.
set -u
Z=$(mise where zig@0.16.0)/zig; cd ~/workspace/herdr || exit 1
T=$(mktemp -d)
for i in $(seq 1 12); do
  ZIG=$Z cargo install --path . --locked > /tmp/herdr-build.log 2>&1 && { echo "BUILT on attempt $i"; exit 0; }
  url=$(grep -o -E "\.url = \"[^\"]+\"" /tmp/herdr-build.log | head -1 | sed -E 's/.url = "(.*)"/\1/')
  [ -z "$url" ] && url=$(grep -B1 "bad HTTP response" /tmp/herdr-build.log | grep -o -E "https://[^\" ]+" | head -1)
  [ -z "$url" ] && { echo "build failed for another reason:"; grep -E "error" /tmp/herdr-build.log | head -5; exit 1; }
  f="$T/$(basename "$url")"
  for k in 1 2 3 4 5 6; do curl -fsSL -C - --retry 8 --retry-all-errors --max-time 600 -o "$f" "$url" && break; sleep 3; done; [ -s "$f" ] && h=$(cd vendor/libghostty-vt && $Z fetch "$f") && echo "prefetched $(basename "$url") -> $h" || { echo "could not prefetch $url"; exit 1; }
done
exit 1
