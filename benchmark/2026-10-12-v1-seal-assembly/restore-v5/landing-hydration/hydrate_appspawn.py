#!/usr/bin/env python3
"""Hydrate one local untracked test input, never a device or Git index."""
import argparse
import hashlib
import json
import os
from pathlib import Path

V5 = Path(__file__).resolve().parent.parent
SHA = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
SIZE = 257792
MANIFEST_SHA = '0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5'
BINDING_SHA = 'a1739d72758ef55e213469a9361e2abf53a66c6c4e5b3806d5f66ca1dbaa5c2a'
SOURCE = 'westlake-inputs/seal-artifacts-20261012/sha256/' + SHA

def digest(raw): return hashlib.sha256(raw).hexdigest()
def pinned_json(path, expected):
    raw = path.read_bytes()
    if digest(raw) != expected: raise ValueError('evidence SHA drift: ' + str(path))
    return json.loads(raw)

def hydrate(workspaces, target_package):
    manifest = pinned_json(V5/'package-r3-disabled/manifest.json', MANIFEST_SHA)
    binding = pinned_json(V5/'binding.5cd.r3.disabled.json', BINDING_SHA)
    row = next(r for r in manifest['files'] if r['path'] == 'runtime/appspawn-x')
    assert row['sha256'] == SHA and row['bytes'] == SIZE
    source_row = next(r for r in binding['extra_runtime_files'] if r['target'].endswith('/appspawn-x'))
    assert source_row['source'] == {'path': '$WORKSPACES/'+SOURCE, 'sha256': SHA}
    source = workspaces.resolve()/SOURCE
    if not source.is_file() or source.is_symlink(): raise ValueError('CAS is not a regular file')
    raw = source.read_bytes()
    if len(raw) != SIZE or digest(raw) != SHA: raise ValueError('CAS size/SHA drift')
    target = target_package.absolute()/'runtime/appspawn-x'
    if target.parent.is_symlink() or target.is_symlink(): raise ValueError('refuse symlink target')
    if target.exists():
        if not target.is_file() or target.read_bytes() != raw: raise ValueError('existing target drift; not overwritten')
        status = 'ALREADY_EQUAL'
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f: f.write(raw)
        status = 'HYDRATED_LOCAL_UNTRACKED_INPUT'
    assert target.stat().st_size == SIZE and digest(target.read_bytes()) == SHA
    runtime = [r for r in manifest['files'] if r['path'].startswith('runtime/')]
    missing = [r['path'] for r in runtime if not (target_package/r['path']).is_file()]
    return {'status': status, 'target': str(target), 'bytes': SIZE, 'sha256': SHA,
            'source': str(source), 'source_manifest_sha256': MANIFEST_SHA,
            'source_binding_sha256': BINDING_SHA, 'runtime_required_by_original_test': len(runtime),
            'runtime_missing_after': len(missing), 'first_missing_runtime': missing[:8],
            'all_runtime_verified': False, 'git_index_operations': 0, 'device_calls': 0}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspaces', type=Path, required=True)
    ap.add_argument('--target-package', type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(hydrate(args.workspaces, args.target_package), indent=2))

if __name__ == '__main__': main()
