"""Preflight offline while samples run; enter the same executor only after verified U5 recovery."""
import fcntl,json,os,sys,time
from pathlib import Path
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'scripts/lab'));import u7_executor as u
out=Path(__file__).resolve().parent;serial='61b0657200000000000000000324012c'
ws=u.lab_paths.workspaces()
plan=u.preflight(ws/'westlake-generation-u7-executor-example',ws/'westlake-generation-n4-order-216b68fb',str(repo/'scripts/lab/oatdump_remote.sh'))
assert plan['deployable']
u.native.save(out/'afterboot-preflight.json',plan)
# Deadline is the explicitly assigned local board window; no work starts after it.
deadline=float(os.environ['U7_WINDOW_DEADLINE_EPOCH'])
while time.time()<deadline:
    receipt=out/'baseline-replay.json'
    if receipt.exists():
        restored=json.loads(receipt.read_text())
        if restored.get('status')=='baseline_restored':break
        if restored.get('status') in ['rejected','recovery_required']:raise SystemExit('baseline recovery failed; no U7 write')
    time.sleep(1)
else:raise SystemExit('board window expired before verified baseline replay')
u.unchanged(plan)
lock_path=ws/'westlake-generation-state'/serial/'u7-executor.lock'
with lock_path.open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    io=u.DeviceIO(serial,'cx-t0',out/'apply3-device')
    if io.boot!=restored['boot_id']:raise RuntimeError('boot changed after baseline recovery')
    tx=u.Transaction(io,out/'apply3-journal.json',plan)
    result=tx.apply()
    u.native.save(out/'apply3.json',result)
print(result['status'])
