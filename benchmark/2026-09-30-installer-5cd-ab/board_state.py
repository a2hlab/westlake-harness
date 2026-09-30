#!/usr/bin/env python3
"""Capture current receipt, pin the authorized r17q variable, verify native invariance."""
import argparse, hashlib, json, shlex, sys, time
from pathlib import Path
R = Path(__file__).resolve().parent
sys.path.insert(0, '/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
SERIAL = '5cd1e3dd00000000000000000923012c'
TARGET = '/system/android/framework/oh-adapter-runtime.jar'
JAR = Path('/Users/zhaoyue/orca/workspaces/vm-copies/r17q-94424d60/oh-adapter-runtime.jar')
SHA = '94424d60b64468b494a9c1f7e0be0fb2bb763585d13cdcb795659089a044bac1'
q = shlex.quote
p = argparse.ArgumentParser()
p.add_argument('action', choices=['capture', 'pin-jar', 'verify-final'])
p.add_argument('--final', action='store_true')
a = p.parse_args()
if a.final:
    JAR=Path('/Users/zhaoyue/orca/workspaces/vm-copies/r17r-dd4f0eae/oh-adapter-runtime.jar')
    SHA=hashlib.sha256(JAR.read_bytes()).hexdigest()
    assert SHA.startswith('dd4f0eae')
out = R / 'board' / (a.action + '-' + str(time.time_ns()))
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', 'cx-t0', out/'commands')
board.ready()
expected = {x.split()[1]: x.split()[0] for x in (R/'baseline/runtime-fingerprint.txt').read_text().splitlines()}
if a.final:
    expected={k:('9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f' if v.startswith('32dfac83') else v) for k,v in expected.items()}
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
    if diff: raise RuntimeError('native differs from r17q A baseline: '+str(diff))
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
    if hashlib.sha256(JAR.read_bytes()).hexdigest() != SHA: raise RuntimeError('r17q input changed')
    if actual[TARGET] != SHA:
        rows = b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1])
        if any(x['name']=='appspawn-x' and x['uid']!=0 for x in rows):
            raise RuntimeError('Android child remains live; stop its known package before changing JAR')
        remote = '/data/local/tmp/installer-ab90-5cd-'+SHA[:8]+'/oh-adapter-runtime.jar'
        board.shell('mkdir -p '+q(str(Path(remote).parent)))
        board.send(JAR, remote)
        if hashes([remote])[remote] != SHA: raise RuntimeError('staged JAR changed')
        board.shell('mount --bind '+q(remote)+' '+q(TARGET))
        board.shell('begetctl stop_service appspawn-x && begetctl start_service appspawn-x')
        time.sleep(2)
        board.shell('chown 0:6005 /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX')
    actual = hashes(expected)
    if actual[TARGET] != SHA: raise RuntimeError('r17q not visible')
    assert_native(actual)
    rows = [x for x in b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1]) if x['name']=='appspawn-x' and x['uid']==0]
    if len(rows)!=1: raise RuntimeError('parent identity ambiguous')
    parent = rows[0]['pid']
    parent_paths = [f'/proc/{parent}/root'+TARGET, f'/proc/{parent}/exe']
    got = hashes(parent_paths)
    if got[parent_paths[0]] != SHA or got[parent_paths[1]] != expected['/system/bin/appspawn-x']:
        raise RuntimeError('parent JAR/host differs')
elif a.action == 'verify-final':
    if actual[TARGET] != SHA: raise RuntimeError('r17q drift')
    for path in installer_paths:
        if actual[path] != services['candidate'][Path(path).name]: raise RuntimeError('candidate installer drift')
b.save(out/'receipt.json', dict(action=a.action, boot_id=board.boot, hashes=actual, native_unchanged=True))
print(json.dumps(dict(action=a.action, boot_id=board.boot, evidence=str(out), jar_sha256=actual[TARGET])))
