"""Original pinned desktop/selfcheck sequence; final collection only, no deployment."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
os.environ.setdefault('WORKSPACES', str(ROOT.parent))

def read(path):
    return json.loads(Path(path).read_text())

def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

auth = read(OUT / 'window-authorization.json')
assert auth['serial'] == '5cd1e3dd00000000000000000923012c'
assert time.time() < auth['rollback_expires_epoch']
assert read(OUT / 'final-controls/smoke-result.json')['passed'] is True
prior = read(OUT / 'postboot-selfcheck954.json')
assert prior['passed'] and prior['file_count'] == 954
request = read(BASE / 'outer/r5-experiment-main-r4/request.json')
refs = {}
for key in ('batch', 'lock'):
    ref = request['programs'][key]
    path = Path(os.path.expandvars(ref['path']))
    assert digest(path) == ref['sha256'], key
    refs[key] = path
spec = importlib.util.spec_from_file_location('final_bms', refs['batch'])
B = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = B
spec.loader.exec_module(B)
dest = OUT / 'final-host'
dest.mkdir(exist_ok=False)
board = B.Board(auth['serial'], request['hdc'], str(refs['lock']), 'outer(codex)', dest / 'commands')
board.ready()
assert board.boot.strip() == prior['current_boot']
record = {'serial': auth['serial'], 'boot_id': board.boot.strip(), 'package': 'org.westlake.imehost', 'reason': 'final host foreground before lock release', 'consent_interaction': False}
remote = '/data/local/tmp/boat-final-host-' + str(time.time_ns())
board.shell('test ! -e ' + remote + ' && mkdir ' + remote)
B.desktop_launch(board, {'package': 'org.westlake.imehost', 'launch_activity': 'EntryAbility'}, remote, dest, record)
record['capture'] = B.capture(board, remote + '/host.jpeg', dest / 'host.jpeg')
B.save(dest / 'record.json', record)
argv = read(OUT / 'postboot-selfcheck954.process.json')['argv']
argv[-1] = str(OUT / 'final-selfcheck954.json')
started = time.time()
with (OUT / 'final-selfcheck954.stdout.txt').open('xb') as stdout, (OUT / 'final-selfcheck954.stderr.txt').open('xb') as stderr:
    proc = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=max(1, auth['rollback_expires_epoch'] - time.time()))
save(OUT / 'final-selfcheck954.process.json', {'argv': argv, 'rc': proc.returncode, 'started': started, 'finished': time.time()})
assert proc.returncode == 0
result = read(OUT / 'final-selfcheck954.json')
assert result['passed'] and result['status'] == 'PASS' and result['file_count'] == 954
save(OUT / 'ready-to-unlock.json', {'serial': auth['serial'], 'boot_id': board.boot.strip(), 'full954_passed': True, 'controls_passed': True, 'host_capture': record['capture'], 'finished': time.time(), 'visual_review': 'pending', 'candidate_retained': True, 'boat_playability_this_board': 'not_tested'})
print('FINAL_954_PASS_READY_FOR_VISUAL_AND_UNLOCK', flush=True)
