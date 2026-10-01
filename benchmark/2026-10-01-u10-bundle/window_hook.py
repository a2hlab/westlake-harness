"""Draft U10 board-run transaction hooks; always restore signed U9 before unlock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

H = Path(__file__).resolve().parent
R = H.parents[1]
sys.path.insert(0, str(R / 'scripts/lab'))
import lab_paths

W = lab_paths.workspaces()
M = lab_paths.harness()
BASE = W / 'westlake-generation-u9-j10g-238ffc14'
CANDIDATE = W / 'westlake-inputs/generations/u10-j37465d6d-c015aa3a6-p621caec4-v3/bundle'
VERIFY = R / 'benchmark/2026-10-01-u9-native/rollout/approved-j10g/native_window.py'


def vm(command):
    return subprocess.run(['orb', '-m', 'a2hlab', 'env',
                           'WORKSPACES=' + str(W), 'MAC_HOME=' + str(Path.home()),
                           'LAB_HOME=' + os.environ['LAB_HOME'], *command], check=True)


def executor(serial, root, rollback=False):
    command = ['bash', str(R / 'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh'),
               '--rollback' if rollback else '--apply', '--serial', serial, '--lane', 'cx-t0',
               '--journal', str(root / 'transaction/journal.json'),
               '--out', str(root / ('rollback-' + uuid.uuid4().hex + '.json' if rollback else 'apply.json'))]
    if not rollback:
        command += ['--package', str(CANDIDATE), '--baseline-native', str(BASE / 'native'),
                    '--oatdump', str(M / 'scripts/lab/oatdump_remote.sh')]
    return vm(command)


def verify(serial, root):
    return vm(['python3', str(VERIFY), '--verify-final', '--serial', serial, '--out', str(root)])


def apply(serial, root):
    root.mkdir(parents=True, exist_ok=True)
    assert not (root / 'transaction/journal.json').exists(), 'fresh transaction output required'
    composition = json.loads((H / 'composition.json').read_text())
    actual = hashlib.sha256((CANDIDATE / 'bundle.json').read_bytes()).hexdigest()
    assert actual == composition['bundle_sha256'], 'candidate bundle drift'
    assert json.loads((CANDIDATE / 'bundle.json').read_text())['rollout_ready'], 'outer rollout approval pending'
    verify(serial, root / 'baseline')
    executor(serial, root)


def finish(serial, root, restored_spec):
    journal = root / 'transaction/journal.json'
    if journal.exists():
        state = json.loads(journal.read_text())
        if state.get('status') != 'rolled_back':
            executor(serial, root, rollback=True)
    verify(serial, root / ('restored-' + uuid.uuid4().hex))
    subprocess.run([sys.executable, str(M / 'scripts/lab/activation_smoke.py'),
                    '--serial', serial, '--lane', 'cx-t0', '--spec', str(restored_spec),
                    '--out', str(root / ('recovery-smoke-' + uuid.uuid4().hex))], check=True)
    # Do not unlock merely because screenshots exist; recheck byte identities after smoke.
    verify(serial, root / ('final-' + uuid.uuid4().hex))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--serial', required=True, choices=sorted(lab_paths.boards('oh')))
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--restored-spec', type=Path)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--apply', action='store_true')
    g.add_argument('--finish', action='store_true')
    a = p.parse_args()
    if a.apply:
        apply(a.serial, a.root)
    else:
        assert a.restored_spec is not None
        finish(a.serial, a.root, a.restored_spec)
