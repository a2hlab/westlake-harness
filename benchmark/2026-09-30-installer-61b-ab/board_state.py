#!/usr/bin/env python3
"""Capture current receipt, pin the authorized r17p variable, verify native invariance."""
import argparse, hashlib, json, shlex, sys, time
from pathlib import Path
R = Path(__file__).resolve().parent
sys.path.insert(0, '/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
SERIAL = '61b0657200000000000000000324012c'
TARGET = '/system/android/framework/oh-adapter-runtime.jar'
JAR = Path('/Users/zhaoyue/orca/workspaces/vm-copies/r17p-a0ed5c4f/oh-adapter-runtime.jar')
SHA = 'a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173'
q = shlex.quote
p = argparse.ArgumentParser()
p.add_argument('action', choices=['capture', 'pin-jar', 'verify-final'])
a = p.parse_args()
out = R / 'board' / (a.action + '-' + str(time.time_ns()))
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', 'cx-t0', out/'commands')
board.ready()
expected = {x.split()[1]: x.split()[0] for x in (R/'baseline/runtime-fingerprint.txt').read_text().splitlines()}
services = json.loads((R/'manifest.json').read_text())
installer_paths = ['/system/lib64/'+n for n in services['candidate']]
receipt = R/'original.json'
def hashes(paths):
    raw = board.shell('sha256sum ' + ' '.join(map(q, paths)))[1]
    result = {parts[1]: parts[0] for l in raw.splitlines() if len(parts := l.split()) == 2 and len(parts[0]) == 64}
    if set(result) != set(paths): raise RuntimeError('incomplete SHA readback')
    return result
def assert_native(actual):
    diff = [k for k in expected if k not in installer_paths+[TARGET] and actual[k] != expected[k]]
    if diff: raise RuntimeError('native differs from r17p A baseline: '+str(diff))
actual = hashes(expected)
assert_native(actual)
if a.action == 'capture':
    if receipt.exists(): raise RuntimeError('original receipt already exists')
    mounts = board.shell('cat /proc/self/mountinfo')[1]
    (out/'mountinfo.txt').write_text(mounts)
    jar_mounts = [l for l in mounts.splitlines() if l.split()[4] == TARGET]
    ledger = Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')/SERIAL/(board.boot+'-74d1d6d48210.json')
    state = json.loads(ledger.read_text())
    if state['status'] != 'active_verified': raise RuntimeError('ledger not active_verified')
    if any(actual[k] != expected[k] for k in installer_paths): raise RuntimeError('installer baseline changed')
    b.save(receipt, dict(serial=SERIAL, boot_id=board.boot, hashes=actual, jar_mounts=jar_mounts,
                        package_path=state['package_path'], package_sha256=state['package_sha256'], ledger=str(ledger)))
elif a.action == 'pin-jar':
    original = json.loads(receipt.read_text())
    if hashlib.sha256(JAR.read_bytes()).hexdigest() != SHA: raise RuntimeError('r17p input changed')
    if actual[TARGET] != SHA:
        rows = b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1])
        if any(x['name']=='appspawn-x' and x['uid']!=0 for x in rows):
            raise RuntimeError('Android child remains live; stop its known package before changing JAR')
        remote = '/data/local/tmp/installer-ab90-r17p/oh-adapter-runtime.jar'
        board.shell('mkdir -p '+q(str(Path(remote).parent)))
        board.send(JAR, remote)
        if hashes([remote])[remote] != SHA: raise RuntimeError('staged JAR changed')
        board.shell('mount --bind '+q(remote)+' '+q(TARGET))
        board.shell('begetctl stop_service appspawn-x && begetctl start_service appspawn-x')
        time.sleep(2)
        board.shell('chown 0:6005 /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX')
    actual = hashes(expected)
    if actual[TARGET] != SHA: raise RuntimeError('r17p not visible')
    assert_native(actual)
    rows = [x for x in b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1]) if x['name']=='appspawn-x' and x['uid']==0]
    if len(rows)!=1: raise RuntimeError('parent identity ambiguous')
    parent = rows[0]['pid']
    parent_paths = [f'/proc/{parent}/root'+TARGET, f'/proc/{parent}/exe']
    got = hashes(parent_paths)
    if got[parent_paths[0]] != SHA or got[parent_paths[1]] != expected['/system/bin/appspawn-x']:
        raise RuntimeError('parent JAR/host differs')
elif a.action == 'verify-final':
    if actual[TARGET] != SHA: raise RuntimeError('r17p drift')
    for path in installer_paths:
        if actual[path] != services['candidate'][Path(path).name]: raise RuntimeError('candidate installer drift')
b.save(out/'receipt.json', dict(action=a.action, boot_id=board.boot, hashes=actual, native_unchanged=True))
print(json.dumps(dict(action=a.action, boot_id=board.boot, evidence=str(out), jar_sha256=actual[TARGET])))
