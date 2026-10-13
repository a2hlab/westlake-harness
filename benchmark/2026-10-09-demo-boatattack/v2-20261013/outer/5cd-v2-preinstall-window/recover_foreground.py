"""Restore the actual desktop host foreground, then rerun the unchanged original R5."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SERIAL = '5cd1e3dd00000000000000000923012c'
BOOT = '8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
OUT = HERE / 'foreground-recovery-r2'
OUT.mkdir(exist_ok=False)
os.environ['WORKSPACES'] = str(ROOT.parent)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

source = ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
assert sha(source) == 'f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c'
spec = importlib.util.spec_from_file_location('original_bms', source)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
board = b.Board(SERIAL, HDC, 'bash ' + str(ROOT / 'scripts/lab/board_note.sh'),
                'outer(codex)', OUT / 'commands')
board.ready()
assert board.boot.strip() == BOOT
record = dict(serial=SERIAL, boot_id=BOOT, reason='Original HW/ZZ smoke hid imehost0; restore desktop foreground before original R5',
              reviewer='outer(codex)', package='org.westlake.imehost', consent_interaction=False)
remote = '/data/local/tmp/boat-v2-5cd-preinstall-foreground-r2'
board.shell('test ! -e ' + remote + ' && mkdir ' + remote)
b.desktop_launch(board, {'package': 'org.westlake.imehost', 'launch_activity': 'EntryAbility'}, remote, OUT, record)
b.save(OUT / 'record.json', record)
b.capture(board, remote + '/host.jpeg', OUT / 'host.jpeg')
binding = ROOT / 'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/activation-binding.5cd.json'
assert sha(binding) == 'c151abb82d8ca127010e0ad93fd9cbb79b1b71ac31465d46bc1667a481df7869'
argv = [sys.executable, str(ROOT / 'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'),
        '--checker', 'activation', '--activation-binding', str(binding), '--binding-sha256', sha(binding),
        '--serial', SERIAL, '--boot-id', BOOT, '--hdc', HDC, '--out', str(OUT / 'selfcheck.json')]
started = time.time()
with (OUT / 'selfcheck.stdout.txt').open('xb') as stdout, (OUT / 'selfcheck.stderr.txt').open('xb') as stderr:
    result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
b.save(OUT / 'selfcheck.invocation.json', dict(argv=argv, rc=result.returncode, started=started, finished=time.time()))
assert result.returncode == 0, 'Original R5 rejected; retained lock and evidence'
checked = json.loads((OUT / 'selfcheck.json').read_text())
assert checked['status'] == 'PASS' and checked['passed'] and checked['file_count'] == 940
assert checked['boot_before'] == checked['boot_after'] == BOOT and not checked['synthetic']
print('ORIGINAL_R5_POSTINSTALL_940_PASS', flush=True)
