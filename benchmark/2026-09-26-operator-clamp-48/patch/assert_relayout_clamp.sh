#!/usr/bin/env bash
# Assert a built oh-adapter jar carries the #48 relayout width-clamp.
# Usage: assert_relayout_clamp.sh <adapter jar>
set -uo pipefail
JAR="${1:?usage: assert_relayout_clamp.sh <jar>}"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
unzip -o -q "$JAR" -d "$tmp" 'classes*.dex' 2>/dev/null || true
# one strings dump of all dex to a file (avoid piping a huge shell var)
: > "$tmp/allstr"
for d in "$tmp"/classes*.dex; do [ -f "$d" ] && strings "$d" >> "$tmp/allstr"; done
pass=1
check(){ if grep -qF -- "$1" "$tmp/allstr"; then echo "PASS: $2"; else echo "FAIL: $2"; pass=0; fi; }
check 'OH_WSA-relayout'                 'adapter emits OH_WSA-relayout (deployed-matching build)'
check '-> useWH='                       'relayout useWH computation present'
check 'clampWidth48'                    'clampWidth48 helper present'
check 'clampHeight48'                   'clampHeight48 helper present'
check 'sLastGoodWidth'                  'sLastGoodWidth cache field present'
check 'sLastGoodHeight'                 'sLastGoodHeight cache field present'
check 'DEGENERATE session rect'         '#48 degenerate-width clamp marker present'
check 'Layout:-79 guard'                '#48 guard tag present'
check 'getMaxBounds'                    'display max-bounds fallback linked'
echo "----"; [ "$pass" = 1 ] && echo "ALL PASS ($JAR)" || { echo "ASSERT FAILED"; exit 1; }
