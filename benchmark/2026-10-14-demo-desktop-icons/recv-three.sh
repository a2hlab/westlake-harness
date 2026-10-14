#!/bin/sh
set -eu
: "${HDC:?root supplies existing HDC transport}"
: "${OUT:?fresh local evidence output directory}"
serial=61b0657200000000000000000324012c
test ! -e "$OUT"
mkdir -p "$OUT"
for package in app.varlorg.unote com.alxgnon.postwriter org.tasks; do
    mkdir "$OUT/$package"
    "$HDC" -t "$serial" file recv "/data/app/el1/bundle/public/$package/android/icon.png" "$OUT/$package/icon.png"
    "$HDC" -t "$serial" file recv "/data/app/el1/bundle/public/$package/entry.hap" "$OUT/$package/entry.hap"
done
printf '%s\n' 'READONLY_RECEIVE_ONLY: verify both remote/local SHA before relying on bytes; no launcher refresh executed.'
