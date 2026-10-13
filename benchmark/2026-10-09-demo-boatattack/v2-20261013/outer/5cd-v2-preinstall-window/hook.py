"""Exact original v1 checks around the reviewed missing-only Boat preinstallation."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REL = Path('benchmark/2026-10-09-demo-boatattack/v2-20261013')
SERIAL = '5cd1e3dd00000000000000000923012c'
BOOT = '8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(name, argv):
    started = time.time()
    with (HERE / (name + '.stdout.txt')).open('xb') as stdout, (HERE / (name + '.stderr.txt')).open('xb') as stderr:
        result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
    (HERE / (name + '.invocation.json')).write_text(json.dumps(dict(argv=argv, rc=result.returncode,
        started=started, finished=time.time()), indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(name + ' failed; original output retained')


phase = sys.argv[1]
assert phase in ('before', 'after')
os.environ['WORKSPACES'] = str(ROOT.parent)
auth = read(HERE / 'authorization.json')
assert auth['serial'] == SERIAL and auth['boot_id'] == BOOT
assert auth['approved_by'] == 'outer(codex)'
assert datetime.datetime.now().astimezone() < datetime.datetime.fromisoformat(auth['expires_at'])
for path, digest in auth['pins'].items():
    assert sha(ROOT / path) == digest, path
freeze = ROOT / REL / 'integration/final-v2-rehearsal-5cd/freeze.json'
assert sha(freeze) == auth['source_freeze']
for item in read(freeze)['files']:
    assert sha(ROOT / item['path']) == item['sha256'], item['path']
held = subprocess.run(['bash', str(ROOT / 'scripts/lab/board_note.sh'), 'held', SERIAL],
                      capture_output=True, text=True, check=True)
assert held.stdout.split()[0] == 'outer(codex)'
binding = ROOT / 'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/activation-binding.5cd.json'
result = HERE / ('identity-' + phase + '.json')
run('identity-' + phase, [sys.executable,
    str(ROOT / 'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'),
    '--checker', 'activation', '--activation-binding', str(binding), '--binding-sha256', sha(binding),
    '--serial', SERIAL, '--boot-id', BOOT, '--hdc', HDC, '--out', str(result)])
checked = read(result)
assert checked['status'] == 'PASS' and checked['passed'] is True and checked['mode'] == 'live-readonly'
assert checked['serial'] == SERIAL and checked['boot_before'] == checked['boot_after'] == BOOT
assert checked['file_count'] == 940 and checked['synthetic'] is False
if phase == 'before':
    recipe = ROOT / REL / 'outer/5cd-v2-main-request/preinstall-disabled/recipe.enabled.json'
    run('preinstall', [sys.executable,
        str(ROOT / REL / 'integration/final-v2-rehearsal-5cd/entry/restore_entry.py'),
        '--v2-recipe', str(recipe), '--recipe-sha256', sha(recipe), '--out', str(HERE / 'staged'), '--execute'])
    receipt = read(HERE / 'staged/preinstall/preinstall-receipt.json')
    assert receipt['status'] == 'PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE'
    assert receipt['serial'] == SERIAL and receipt['boot_id'] == BOOT
    assert receipt['stock_libraries_preserved'] is True and receipt['provider_compiled'] is False
    assert receipt['reboots'] == 0 and receipt['restored'] is False
print('5CD_PREINSTALL_' + phase.upper() + '_COMPLETE')
