"""Post-run checks: waits for the writer lock, then verifies one-app invalidation."""
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path
import shutil

P=Path('/Users/zhaoyue/orca/workspaces/westlake-inputs')
D=Path.home()/'a2hlab/static'
OUT=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-static-100/benchmark/2026-09-24-static-100')
LOGS=Path.home()/'a2hlab/logs'
sys.path.insert(0,str(P/'tools'))
import static_pipeline as pipeline

with (D/'.pipeline.lock').open('a') as guard:
    fcntl.flock(guard,fcntl.LOCK_EX)
    log=(LOGS/'static-100-v2.log').read_text()
    assert log.count('ok (')==100 and 'failed' not in log,log[-500:]
    corpus=json.loads((P/'corpus100.json').read_text())['apps']
    paths={k:[D/'scans'/f'{k}.json',D/'oh'/f'{k}.json',D/'maps'/k/'gap-map.json'] for k in corpus}
    before={k:[p.stat().st_mtime_ns for p in ps] for k,ps in paths.items()}
    receipt=D/'maps/markor/pipeline-state.json'
    original=json.loads(receipt.read_text())
    pipeline.write_json(OUT/'evidence/markor-receipt-before-cache-check.json',original)
    changed=json.loads(receipt.read_text())
    changed['fingerprint']['runtime_lock_id']='cache-invalidation-probe:stale-lock'
    pipeline.write_json(receipt,changed)
    print('Original 100-app run passed; invalidated markor cached runtime identity only',flush=True)

with (LOGS/'static-100-v2-cache-check.log').open('w') as log:
    subprocess.run([sys.executable,str(P/'tools/static_pipeline.py'),str(P/'corpus100.json'),str(D),'--jobs','4'],stdout=log,stderr=subprocess.STDOUT,check=True)
log=(LOGS/'static-100-v2-cache-check.log').read_text()
after={k:[p.stat().st_mtime_ns for p in ps] for k,ps in paths.items()}
rebuilt=[k for k in corpus if before[k]!=after[k]]
assert rebuilt==['markor'],rebuilt
assert log.count('; rebuilt)')==1 and log.count('; cached)')==99
final=json.loads(receipt.read_text())
assert final['fingerprint']==original['fingerprint']
pipeline.write_json(OUT/'cache-verification.json',{'scope':'real 100-app corpus; only markor cached runtime_lock_id deliberately corrupted; runtime index and APK unchanged','rebuilt_apps':rebuilt,'cached_apps':99,'all_ok':log.count('ok (')==100,'only_markor_output_mtimes_changed':rebuilt==['markor'],'runtime_fingerprint_restored':final['fingerprint']==original['fingerprint'],'before_mtimes':before,'after_mtimes':after})
print('PASS: markor rebuilt; 99 cached; output timestamps independently agree',flush=True)
subprocess.run([sys.executable,str(P/'tools/aggregate_gaps.py'),str(D),str(P/'corpus100.json')],check=True)
with (LOGS/'static-100-v2-audit.log').open('w') as log:
    subprocess.run([sys.executable,str(P/'tools/audit_static100.py'),str(OUT)],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([sys.executable,str(P/'tools/provenance_static100.py')],check=True)
with (LOGS/'static-100-v2-verify.log').open('w') as log:
    subprocess.run([sys.executable,str(P/'tools/verify_static100.py'),str(OUT)],stdout=log,stderr=subprocess.STDOUT,check=True)
for name in ['LEADERBOARD.md','leaderboard.json']:shutil.copy(D/name,OUT/name)
shutil.copy(P/'static100-provenance.json',OUT/'provenance.json')
for name in ['static-100-v2.log','static-100-v2-cache-check.log','static-100-v2-audit.log','static-100-v2-verify.log']:shutil.copy(LOGS/name,OUT/'evidence'/name)
pipeline.write_json(OUT/'pipeline-receipts.json',{k:json.loads((D/'maps'/k/'pipeline-state.json').read_text()) for k in corpus})
print('PASS: aggregation, audit, provenance and independent verification completed',flush=True)
