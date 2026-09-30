#!/usr/bin/env python3
"""Restore only verified B91 object inputs into this experiment's build cache."""
import hashlib,json,shutil
from pathlib import Path
r=Path(__file__).resolve().parent;repo=r.parents[1]
source=repo/'bms/src/.work/b91-common-event/runtime-objects'
dest=repo/'bms/src/.work/asset-fd/runtime-objects'
expected=json.loads((r/'baseline-objects.json').read_text())
for name,digest in expected.items():
 p=source/name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('baseline object changed: '+name)
for name in expected:shutil.copy2(source/name,dest/name)
print('verified baseline cache restored:',len(expected))
