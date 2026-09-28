"""Prepare explicit B6 input changes; never edit hw248 or disable loader checks."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
SRC = ROOT / 'bms/src'
PLUGIN = SRC / 'adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bridge = SRC / 'adapter/out/aosp_lib_arm64/libsigchain.so'
expected = sys.argv[1]
assert len(expected) == 64
assert sha(bridge) == expected
ledger = PLUGIN / 'ROUTE_A_INPUTS.json'
old = REPORT / 'route-inputs-before.json'
if not old.exists():
    shutil.copy2(ledger, old)
shutil.copy2(bridge, PLUGIN/'out/route-a-generation/providers/libsigchain.so')
# Recompute the input ledger using its existing generator; --verify stays enabled.
subprocess.run(['python3',str(PLUGIN/'generate_route_a_inputs.py')],check=True)
a = {x['path']:x for x in json.loads(old.read_text())['files']}
b = {x['path']:x for x in json.loads(ledger.read_text())['files']}
changes = [{'path':p,'before':a.get(p),'after':b.get(p)} for p in sorted(a.keys()|b.keys()) if a.get(p)!=b.get(p)]
(REPORT/'input-drift.json').write_text(json.dumps(changes,indent=2)+'\n')
print('recorded input changes:',len(changes))
