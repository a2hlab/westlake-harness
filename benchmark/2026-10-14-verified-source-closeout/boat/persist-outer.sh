#!/usr/bin/env bash
# Outer executes this explicit persistence handoff; no devices or builds.
set -euo pipefail
: "${WORKSPACES:?Set WORKSPACES}"
: "${PERSIST_OUT:?Set a new directory for raw upload receipts}"
archive="$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-verified-source-closeout/boat/.artifacts/boat-production-closeout.tar.gz"
expected=29e883638f23c9d13ca49b95535d02e29f3956970efe9f8ed0a283eea735e403
mkdir "$PERSIST_OUT"
python3 - "$archive" "$expected" <<'PY'
import hashlib,sys
h=hashlib.sha256()
with open(sys.argv[1],'rb') as f:
    for b in iter(lambda:f.read(1048576),b''): h.update(b)
if h.hexdigest()!=sys.argv[2]: raise SystemExit('local archive SHA mismatch')
PY
ssh -o BatchMode=yes hw248 'mkdir -p "$HOME/westlake-boat-source-closeout-20261014-29e883638f23"' >"$PERSIST_OUT/mkdir.stdout.txt" 2>"$PERSIST_OUT/mkdir.stderr.txt"
scp "$archive" hw248:westlake-boat-source-closeout-20261014-29e883638f23/boat-production-closeout.tar.gz >"$PERSIST_OUT/upload.stdout.txt" 2>"$PERSIST_OUT/upload.stderr.txt"
ssh -o BatchMode=yes hw248 'sha256sum "$HOME/westlake-boat-source-closeout-20261014-29e883638f23/boat-production-closeout.tar.gz"' >"$PERSIST_OUT/remote-sha.stdout.txt" 2>"$PERSIST_OUT/remote-sha.stderr.txt"
python3 - "$PERSIST_OUT" "$expected" <<'PY'
from pathlib import Path
import json,sys,hashlib
p=Path(sys.argv[1]); actual=(p/'remote-sha.stdout.txt').read_text().split()[0]
if actual!=sys.argv[2]: raise SystemExit('remote SHA mismatch')
r={'status':'REMOTE_SHA_VERIFIED','sha256':actual,'archive':'hw248:~/westlake-boat-source-closeout-20261014-29e883638f23/boat-production-closeout.tar.gz','rc':0,'raw':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.txt')}}
(p/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
PY
