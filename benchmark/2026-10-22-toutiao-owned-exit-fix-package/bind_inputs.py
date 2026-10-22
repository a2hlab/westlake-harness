#!/usr/bin/env python3
"""Read committed accepted T50 inputs; no runtime or device commands."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import build

COMMIT = '53749c0ded3c320fc3b66c7d9a2efc140ceefe64'
PREFIX = 'benchmark/2026-10-22-toutiao-owned-exit-fix/'
ACCEPTED = {
    'candidate/watchdog.sh': 'd45a8d36794d3927c0c03f19d71fa632a0b9cec18944d9d9f92a3406b49f64f0',
    'candidate/route-b-owner.sh': 'fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58',
    'outer-review.json': '0e7321f5fd61990f91373126cf53a007d548fd6579a8be77645c85984e5a2985',
    'raw-index.json': '452d5dc473881f4d5c9affb7fb3ae1f7a43c709d2baac395b7bd58230e7b323d',
}

def main():
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True)
    a = p.parse_args(); c = build.CARD
    lock_path = c / 'inputs/source-lock.json'; lock = json.loads(lock_path.read_text())
    build.need(lock['status'] == 'PENDING_OUTER_ACCEPTANCE', 'lock already bound')
    build.need(not any((c / 'sources').iterdir()), 'sources already populated')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(a.repo), *args])
    files = git('ls-tree', '-r', '--name-only', COMMIT, '--', PREFIX).decode().splitlines()
    payload, index = {}, []
    for path in files:
        rel = path.removeprefix(PREFIX); data = git('show', COMMIT + ':' + path)
        digest = build.sha(data)
        if rel in ACCEPTED:
            build.need(digest == ACCEPTED[rel], 'outer pin mismatch: ' + rel)
        blob = git('rev-parse', COMMIT + ':' + path).decode().strip()
        build.need(blob == hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), 'git blob mismatch')
        payload[rel] = data
        index.append({'path': path, 'local': 'sources/t50/' + rel, 'sha256': digest, 'bytes': len(data), 'git_blob': blob})
    build.need(set(ACCEPTED) <= set(payload), 'accepted artifact missing')
    pending = c / 'inputs/source-lock.pending.json'
    build.need(not pending.exists(), 'pending history already exists')
    pending.write_bytes(lock_path.read_bytes())
    for rel, data in payload.items():
        target = c / 'sources/t50' / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    for name in ('watchdog.sh', 'route-b-owner.sh'):
        data = payload['candidate/' + name]; (c / 'sources' / name).write_bytes(data)
        row = next(x for x in index if x['path'] == PREFIX + 'candidate/' + name)
        lock['sources'][name] = {k: row[k] for k in ['sha256', 'bytes', 'git_blob']}
        lock['sources'][name]['repo_path'] = row['path']
    lock['status'] = 'ACCEPTED_FOR_OFFLINE_PACKAGING'; lock['t50_commit'] = COMMIT
    roles = {'source_git': 'sources.json', 'recipe': 'prepare.py', 'raw_execution_index': 'raw-index.json',
             'outer_acceptance': 'outer-review.json', 'patch': 'candidate.patch', 'pins': 'pins.json',
             'checker': 'check.py', 'replay': 'replay.py', 'fixture': 'fixture.sh',
             'baseline_watchdog': 'baseline/watchdog.sh', 'baseline_owner': 'baseline/route-b-owner.sh'}
    lock['provenance'] = {role: {'path': 't50/' + rel, 'sha256': build.sha(payload[rel])} for role, rel in roles.items()}
    lock['outer_acceptance'] = lock['provenance']['outer_acceptance']; lock['pending_fields'] = []
    lock_path.write_text(json.dumps(lock, indent=2) + '\n')
    (c / 'inputs/accepted-source-index.json').write_text(json.dumps({'commit': COMMIT, 'files': index}, indent=2) + '\n')
    print(json.dumps({'status': 'BOUND_ACCEPTED_OFFLINE_SOURCES', 'commit': COMMIT, 'files_from_git': len(index), 'candidate_sources': 2}))

if __name__ == '__main__':
    main()
