#!/usr/bin/env python3
"""Bind frozen r3 content to the existing disabled 5cd observations; local only."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[3])))
COMMIT = '69e15c4ae058d1fe17ba5f4355883e460ac9859b'
REL = 'benchmark/2026-10-12-child-readiness/r3-lowfork-audit'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def ref(path): return {'path': '$WORKSPACES/' + str(path.relative_to(WS)), 'sha256': sha(path)}
def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')

def main():
    t0 = WS/'westlake-harness-t0'; source = t0/REL
    manifest = source/'checkpoint-manifest.json'
    blob = subprocess.check_output(['git', 'show', COMMIT+':'+REL+'/checkpoint-manifest.json'], cwd=t0)
    assert hashlib.sha256(blob).hexdigest() == sha(manifest), 'checkpoint differs from frozen Git snapshot'
    checkpoint = json.loads(blob)
    assert checkpoint['schema'] == 'lowfork-audit-checkpoint/v1'
    listed = set()
    for row in checkpoint['files']:
        name = row['path']
        assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in listed
        listed.add(name); path = source/name
        assert path.is_file() and not path.is_symlink()
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], name
    previous = HERE.parent/'restore-v4/binding.5cd.r2b.disabled.json'
    b = read(previous)
    assert b['startup_enabled'] is False and b['serial'].startswith('5cd') and b['host_uid'] == 20011300
    old_before = json.dumps(b['before'], sort_keys=True)
    b['guardian_update'] = ref(manifest)
    b['observation_provenance']['t9_r3'] = {
        'commit': COMMIT, 'checkpoint': ref(manifest),
        'helper_sha256': sha(source/'candidate/route-b-owner.sh'),
        'worker_sha256': sha(source/'candidate/readiness-probe.sh'),
        'scope': 'helper and worker content only; no61b before, startup template or authorization imported'}
    assert json.dumps(b['before'], sort_keys=True) == old_before
    write(HERE/'binding.5cd.r3.disabled.json', b)
    write(HERE/'source-r3-audit.json', {
        'schema': 'restore-r3-source-audit/v1', 'source_commit': COMMIT,
        'checkpoint': ref(manifest), 'verified_checkpoint_files': len(listed),
        'previous_binding': ref(previous), 'before_unchanged': True,
        'guardian': b['observation_provenance']['t9_r3'],
        'source_startup_policy': 'retain measured v4 control source and derive explicit 5cd fields; never copy r3 template',
        'device_calls': 0, 'execution_enabled': False})
    print(json.dumps({'status': 'R3_FROZEN_SOURCE_BOUND_DISABLED', 'source_commit': COMMIT,
        'checkpoint_sha256': sha(manifest), 'binding_sha256': sha(HERE/'binding.5cd.r3.disabled.json'), 'device_calls': 0}))
if __name__ == '__main__': main()
