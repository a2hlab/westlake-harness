#!/usr/bin/env bash
# Assert a built oh-adapter jar carries the #48 relayout width-clamp.
# Usage: assert_relayout_clamp.sh <oh-adapter-*.jar>
set -euo pipefail
JAR="${1:?usage: assert_relayout_clamp.sh <jar>}"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
n=0; unzip -o -q "$JAR" -d "$tmp" 'classes*.dex' 2>/dev/null || true
str=""; for d in "$tmp"/classes*.dex; do [ -f "$d" ] && str+=$(strings "$d"); done
pass=1
check(){ if printf '%s' "$str" | grep -q -- "$1"; then echo "PASS: $2"; else echo "FAIL: $2"; pass=0; fi; }
# 1) it IS the relayout-logging (deployed-matching) adapter
check 'OH_WSA-relayout'            'adapter emits OH_WSA-relayout (deployed-matching build)'
check '\-> useWH='                 'relayout useWH computation present'
# 2) the clamp is compiled in
check 'DEGENERATE session rect'    '#48 degenerate-width clamp marker present'
check 'Layout:-79 guard'           '#48 guard tag present'
# 3) fallback API linked
check 'getMaxBounds'               'display max-bounds fallback linked'
echo "----"; [ "$pass" = 1 ] && echo "ALL PASS ($JAR)" || { echo "ASSERT FAILED"; exit 1; }
