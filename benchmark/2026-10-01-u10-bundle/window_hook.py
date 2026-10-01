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
import u7_executor as u

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


def retain_candidate(serial, root):
    data = json.loads((H / 'expected-run.json').read_text())['boards'][serial]
    wanted = data['expected']
    plan = u.prepare(CANDIDATE, BASE / 'native')
    io = u.DeviceIO(serial, 'cx-t0', root / ('retained-device-' + uuid.uuid4().hex))
    actual, absent = io.snapshot(sorted(wanted))
    diff = {p: {'expected': v, 'actual': actual.get(p)} for p, v in wanted.items() if actual.get(p) != v}
    assert not diff and not absent, 'U10 final 318-assertion identity mismatch'
    refs = {k: list(v) for k, v in plan['reference_paths'].items()}
    services = json.loads((R / 'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text())['boards'][serial]['services']
    refs['runtime'] = sorted(set(refs['runtime']) | set(services))
    fp = u.fingerprints(actual, refs)
    assert fp == data['fingerprints'], 'U10 final fingerprint mismatch'
    parents = [r for r in io.ps() if r['name'] == 'appspawn-x' and r['uid'] == 0 and r['ppid'] == 1]
    assert len(parents) == 1, 'U10 parent count mismatch'
    parent = parents[0]['pid']
    paths = {f'/proc/{parent}/root' + p: v for p, v in wanted.items()}
    assert io.hashes(sorted(paths)) == paths, 'U10 parent view mismatch'
    result = {'state': 'U10 retained pending outer full-sweep review', 'identity_assertions': 318,
              'identities': len(actual), 'diff': diff, 'absent': absent, 'fingerprints': fp,
              'parent': parent, 'boot_id': io.boot, 'confirmed_regression': False}
    (root / 'retained-u10.json').write_text(json.dumps(result, indent=2) + '\n')


def finish(serial, root, restored_spec):
    smoke = root / 'runner/smoke/smoke-result.json'
    regression = root / 'confirmed-regression.json'
    confirmed = regression.exists() and json.loads(regression.read_text()).get('confirmed') is True
    passed = smoke.exists() and json.loads(smoke.read_text()).get('passed') is True
    if passed and not confirmed:
        try:
            if sys.platform == 'darwin':
                vm(['python3', str(Path(__file__).resolve()), '--retain', '--serial', serial, '--root', str(root)])
            else:
                retain_candidate(serial, root)
            return
        except (subprocess.CalledProcessError, AssertionError) as exc:
            (root / 'retention-error.txt').write_text(str(exc) + '\n')
            # Failed final identity/parent check is a gate failure, not a retained success.

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
    g.add_argument('--retain', action='store_true')
    a = p.parse_args()
    if a.apply:
        apply(a.serial, a.root)
    elif a.retain:
        retain_candidate(a.serial, a.root)
    else:
        assert a.restored_spec is not None
        finish(a.serial, a.root, a.restored_spec)
