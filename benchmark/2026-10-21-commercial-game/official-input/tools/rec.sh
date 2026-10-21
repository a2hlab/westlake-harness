#!/bin/bash
# usage: rec.sh <id> <cmd...>; records argv, rc, stdout, stderr, start/end epoch under $COMMERCIAL_G01_PRIVATE/raw/<id>.*
# Reproducible copy of the original private recorder (sha256 05ce4640…); only the root is parameterized.
P=${COMMERCIAL_G01_PRIVATE:-$HOME/.local/share/westlake/commercial-game-20261021/intake}
mkdir -p "$P/raw"
id=$1; shift
python3 -I -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@" > "$P/raw/$id.argv.json"
date +%s > "$P/raw/$id.start"
"$@" > "$P/raw/$id.stdout" 2> "$P/raw/$id.stderr"
rc=$?; echo $rc > "$P/raw/$id.rc"; date +%s > "$P/raw/$id.end"
echo "[$id rc=$rc out=$(wc -c <"$P/raw/$id.stdout")B err=$(wc -c <"$P/raw/$id.stderr")B]"
