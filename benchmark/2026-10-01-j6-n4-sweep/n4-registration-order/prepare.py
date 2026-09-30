#!/usr/bin/env python3
"""Make a new immutable package; the published N4 package remains unchanged."""
from pathlib import Path
import hashlib,json,subprocess,sys
P=Path(__file__).resolve().parent;R=P.parents[2]
sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
base=lab_paths.workspaces()/'westlake-generation-n4-1617080a'
replacement=R/'bms/src/.work/n4-registration-order/runtime-out/liboh_android_runtime.so'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'package.json')=='1617080a6a42651016937816ee3c9900554c5326379e5cf635b08227a00744d8'
digest=sha(replacement)
assert digest=='216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df'
out=lab_paths.workspaces()/('westlake-generation-n4-order-'+digest[:8])
subprocess.run([sys.executable,str(R/'scripts/lab/prepare_generation_replacement.py'),str(base),'/system/android/lib64/liboh_android_runtime.so',str(replacement),'--sha256',digest,'--out',str(out)],check=True)
old=json.loads((base/'package.json').read_text());new=json.loads((out/'package.json').read_text())
assert set(old['files'])==set(new['files'])
assert [p for p in old['files'] if old['files'][p]!=new['files'][p]]==['payload/android/lib64/liboh_android_runtime.so']
print(sha(out/'package.json'))
