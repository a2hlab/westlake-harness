#!/bin/bash
# Build + run the cluster-4 keystore probe on a desktop JVM. Self-contained (minimal android stubs).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/out"; rm -rf "$OUT"; mkdir -p "$OUT"
find "$HERE/src" -name '*.java' > "$OUT/sources.txt"
javac -d "$OUT" @"$OUT/sources.txt"
java -cp "$OUT" KeystoreProbe
