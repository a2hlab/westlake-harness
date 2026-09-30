#!/usr/bin/env python3
"""Assemble one N5 candidate; never mutate a published input package."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parent
REPO = REPORT.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
from deploy_generation import load_package, validate_upgrade


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('base', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--inputs', type=Path, required=True)
    args = parser.parse_args()
    manifest = load_package(args.base)
    assert sha(args.base / 'package.json') == '7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe'
    inputs = json.loads(args.inputs.read_text())
    assert set(inputs) == {'anl'}
    sources = {}
    for key, item in inputs.items():
        path = REPO / item['path']
        assert sha(path) == item['sha256'], key
        sources[key] = path
    assert not args.out.exists(), 'Output must be a new candidate directory'
    subprocess.run(['/bin/cp', '-Rc', str(args.base), str(args.out)], check=True)
    changes = []
    names = {'libapp_native_loader.so': 'anl'}
    counts = dict.fromkeys(inputs, 0)
    for rel, previous in list(manifest['files'].items()):
        key = names.get(Path(rel).name)
        if key is None:
            continue
        counts[key] += 1
        source = sources[key]
        digest = sha(source)
        target = args.out / rel
        assert not target.is_symlink()
        target.chmod(target.stat().st_mode | 0o200)
        target.write_bytes(source.read_bytes())
        manifest['files'][rel] = digest
        live = [p for p, h in manifest['live_hashes'].items()
                if h == previous and Path(p).name == Path(rel).name]
        for path in live:
            manifest['live_hashes'][path] = digest
        changes.append({'component': key, 'file': rel, 'before': previous,
                        'sha256': digest, 'source': str(source.relative_to(REPO))})
    assert counts == {'anl': 2}, counts
    manifest['rollout_ready'] = False
    manifest['rollout_blocker'] = 'N5 offline candidate; native gates and scheduled device review required'
    (args.out / 'package.json').write_text(json.dumps(manifest, indent=2) + '\n')
    validate_upgrade(load_package(args.base), load_package(args.out))
    result = {'package': str(args.out.resolve()), 'manifest_sha256': sha(args.out / 'package.json'),
              'base': str(args.base.resolve()), 'changes': changes,
              'device_status': 'unverified', 'board_writes': False}
    (REPORT / 'package.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    subprocess.run([sys.executable, str(REPO / 'scripts/lab/check_frozen.py'), '--package', str(args.out)], check=True)
    gate = subprocess.run([sys.executable, str(REPORT / 'emit_native_inputs.py'), str(args.out)])
    if gate.returncode:
        raise SystemExit(gate.returncode)


if __name__ == '__main__':
    main()
