#!/usr/bin/env python3
"""Offline append-only and exact-reference checks; never executes cited code."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_ref(root, item):
    path = Path(item['path'])
    require(not path.is_absolute() and '..' not in path.parts, f'unsafe reference: {path}')
    target = root / path
    require(target.is_file() and not target.is_symlink(), f'missing/nonregular reference: {path}')
    require(sha(target) == item['sha256'], f'SHA drift: {path}')
    if 'bytes' in item:
        require(target.stat().st_size == item['bytes'], f'size drift: {path}')


def check(data, source_root):
    pins = read(HERE / 'input-pins.json')
    original = read(HERE / 'original-50.json')
    original_pin = next(p for p in pins['preimages'] if p['path'].endswith('/observations.json'))
    require(sha(HERE / 'original-50.json') == original_pin['sha256'], 'original 50 snapshot changed')
    require(len(original['rows']) == 50 and data['rows'][:50] == original['rows'], 'original 50 row objects changed')
    require(len(data['rows']) >= 58, 'expected original 58-row prefix')
    require(data['rows'][50:58] == read(HERE / 'added-rows.json'), 'new observation snapshot changed')
    require(data['historical_rows'] == 315 and data['historical_semantics_changed'] is False, 'historical315 boundary changed')
    require(data['remote_publication_verified'] is False, 'local rendering is not remote publication')
    require(len({r['id'] for r in data['rows'][:58]}) == 58, 'duplicate observation ID')
    for item in pins['readonly_anchors']:
        check_ref(source_root, item)
    render_pin = next(p for p in pins['readonly_anchors'] if p['path'].endswith('/render.py'))
    require(sha(API / 'render.py') == render_pin['sha256'], 'local renderer changed')
    count = 0
    for row in data['rows'][:58]:
        for group in ('source', 'build', 'evidence'):
            for item in row[group]:
                check_ref(source_root, item)
                count += 1
    added = {r['id']: r for r in data['rows'][50:58]}
    for row in added.values():
        require(row['frozen'] is False and row['platform'] and row['limitations'], 'new row lacks bounded version/scope')
    g13 = added['OBS-20261021-G13-INSTALL']
    require(g13['status'] == 'INSTALL_ACCEPTED_GAME_NOT_STARTED', 'G13 scope upgrade')
    require(all('/accepted-install-01/' in r['path'] for r in g13['evidence']), 'G13 must use accepted evidence only')
    for key in ('OBS-20261021-T38-STOP', 'OBS-20261021-G14-STOP'):
        row = added[key]
        require(not row['source'] and not row['build'], f'{key}: execution references forbidden')
        require('SAFETY_STOP' in row['status'], f'{key}: stop omitted')
    return count


def negative_cases(data, source_root):
    cases = []
    changed = copy.deepcopy(data)
    changed['rows'][0]['status'] += ' changed'
    cases.append(('modified original row', lambda: check(changed, source_root), 'original 50'))
    cases.append(('missing reference', lambda: check_ref(source_root, {
        'path': 'benchmark/2026-10-21-current-api-observations/intentionally-missing.json',
        'sha256': '0' * 64}), 'missing/nonregular'))
    wrong = dict(data['rows'][57]['evidence'][0], sha256='0' * 64)
    cases.append(('reference SHA drift', lambda: check_ref(source_root, wrong), 'SHA drift'))
    results = []
    for name, call, expected in cases:
        try:
            call()
        except ValueError as exc:
            require(expected in str(exc), f'unexpected refusal: {exc}')
            results.append({'case': name, 'refused': True, 'reason': str(exc)})
        else:
            raise ValueError(f'negative case accepted: {name}')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--render', action='store_true', help='check first, then run the unchanged renderer')
    args = parser.parse_args()
    data = read(API / 'observations.json')
    count = check(data, args.source_root.resolve())
    negatives = negative_cases(data, args.source_root.resolve()) if args.self_test else []
    if args.render:
        subprocess.run([sys.executable, str(API / 'render.py'), '--source-root', str(args.source_root.resolve())], check=True)
    print(json.dumps({'status': 'PASS', 'original_rows_unchanged': 50,
        'added_rows': 8, 'rows': 58, 'exact_references': count,
        'historical_rows_unchanged': 315, 'negative_cases': negatives,
        'device_calls': 0, 'rea_calls': 0, 'builds_executed': 0,
        'remote_publication_verified': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
