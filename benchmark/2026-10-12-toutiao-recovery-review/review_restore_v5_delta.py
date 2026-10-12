#!/usr/bin/env python3
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


FREEZE = '756c57e899ff89855f12bc174fdcd35c1e10fdd01ffb5d11b01501e193087ed8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def review(root, previous, workspace):
    assert sha(root / 'freeze.json') == FREEZE
    frozen = read(root / 'freeze.json')
    repository = root.parents[2]
    for row in frozen['files']:
        assert sha(repository / row['path']) == row['sha256'], row['path']
    package = root / 'package-r3-disabled'
    oldpackage = previous / 'package-r2b-disabled'
    binding = read(root / 'binding.5cd.r3.disabled.json')
    oldbinding = read(previous / 'binding.5cd.r2b.disabled.json')
    assert set(binding) == set(oldbinding)
    binding_changes = [key for key in binding if binding[key] != oldbinding[key]]
    assert set(binding_changes) == {'guardian_update', 'observation_provenance'}
    assert not binding['startup_enabled'] and binding['host_uid'] == 20011300
    pin = binding['guardian_update']
    checkpoint_path = Path(pin['path'].replace('$WORKSPACES', str(workspace)))
    assert sha(checkpoint_path) == pin['sha256']
    gitprefix = 'benchmark/2026-10-12-child-readiness/r3-lowfork-audit/'
    commit = '69e15c4ae058d1fe17ba5f4355883e460ac9859b'
    blob = subprocess.check_output(['git', '-C', str(workspace / 'westlake-harness-t0'), 'show', commit + ':' + gitprefix + 'checkpoint-manifest.json'])
    assert checkpoint_path.read_bytes() == blob
    for row in json.loads(blob)['files']:
        data = subprocess.check_output(['git', '-C', str(workspace / 'westlake-harness-t0'), 'show', commit + ':' + gitprefix + row['path']])
        assert data == (checkpoint_path.parent / row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes']
    manifest = read(package / 'manifest.json')
    for row in manifest['files']:
        source = package / row['path']
        assert sha(source) == row['sha256'] and source.stat().st_size == row['bytes']
    plan = read(package / 'plan.json')
    oldplan = read(oldpackage / 'plan.json')
    assert manifest['plan_sha256'] == sha(package / 'plan.json')
    assert len(plan['members']) == 487 and not plan['execution_enabled']
    oldmap = {row['target']: row for row in oldplan['members']}
    changed = []
    for row in plan['members']:
        oldrow = oldmap[row['target']]
        assert {key: value for key, value in row.items() if key != 'sha256'} == {key: value for key, value in oldrow.items() if key != 'sha256'}, row['target']
        assert sha(package / row['source'].removeprefix('$PACKAGE/')) == row['sha256']
        if row['sha256'] != oldrow['sha256']:
            changed.append({'target': row['target'], 'old': oldrow['sha256'], 'new': row['sha256']})
    assert len(changed) == 8
    payload = package / 'payload'
    for name in ('route-b-owner.sh', 'readiness-probe.sh'):
        assert (payload / name).read_bytes() == (checkpoint_path.parent / 'candidate' / name).read_bytes()
    for name in ('watchdog.sh', 'launch-common.sh'):
        assert (payload / name).read_bytes() == (oldpackage / 'payload' / name).read_bytes()
    aliases = {'start-parent.sh': 'start-parent-prepared.sh', 'spawn.sh': 'spawn-prepared.sh', 'screen-gate': 'screen-gate-feed'}
    members = (payload / 'members.tsv').read_text().splitlines()
    assert len(members) == 13
    for line in members:
        digest, name, mode = line.split()
        assert sha(payload / aliases.get(name, name)) == digest
    assert sha(payload / 'members.tsv') in (payload / 'startup.env').read_text()
    assert sha(payload / 'startup.env') == (payload / 'startup.expected.sha256').read_text().strip()
    assert "STARTUP_ENABLED='0'" in (payload / 'startup.env').read_text()
    def functions(path):
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}
    oldfunctions = functions(previous / 'toutiao_provider.py')
    newfunctions = functions(root / 'toutiao_provider.py')
    function_changes = [name for name in oldfunctions if oldfunctions[name] != newfunctions[name]]
    assert set(function_changes) == {'guardian_update', 'compile_package', 'main'}
    assert sha(package / 'executor.py') == sha(oldpackage / 'executor.py')
    with tempfile.TemporaryDirectory() as temporary:
        counter = Path(temporary) / 'counter'
        script = 'RB_OWNER_UID=20011300; RB_AUDIT_QUIET=1; . "$1"; COUNT=$2; od(){ echo od >> "$COUNT"; command od "$@"; }; RB_AUDIT_PHASE=strict; RB_AUDIT_PID=101; RB_AUDIT_BIRTH=500; rb_deny uid 20011206:20011206:20011206:20011206 20011300:20011300:20011300:20011300'
        result = subprocess.run(['bash', '-c', script, 'fixture', str(payload / 'route-b-owner.sh'), str(counter)], capture_output=True, text=True)
        assert result.returncode == 1 and counter.read_text().splitlines() == ['od']
        diagnostic = json.loads(result.stderr)
        assert diagnostic['field'] == 'uid' and diagnostic['actual'] != diagnostic['expected']
    assert not frozen['execution_enabled'] and not frozen['seal_signed'] and not frozen['authorization_created']
    return {'freeze': FREEZE, 'freeze_rows': len(frozen['files']), 'manifest_files_verified': len(manifest['files']), 'target_rows': len(plan['members']), 'binding_changes': binding_changes, 'target_sha_changes': changed, 'provider_function_changes': function_changes, 'executor_unchanged': True, 'all_5cd_before_and_metadata_unchanged': True, 'boot_members': len(members), 'wrong_61b_uid_rejected': diagnostic, 'logic_matrix_reruns': 0, 'decision': 'EXACT_OFFLINE_DELTA_ACCEPT_DISABLED_NOT_ORIGIN_SEAL_NOT_WRITE_AUTHORITY', 'board_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review(args.root.resolve(), args.previous.resolve(), args.workspace.resolve()), indent=2))
