#!/usr/bin/env python3
"""Check G17's one-row append and rendered evidence; no device or cited-code execution."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / 'benchmark/2026-10-19-api-progress-update'
G15 = ROOT / 'benchmark/2026-10-21-current-api-observations'
spec = importlib.util.spec_from_file_location('g15_checker', G15 / 'check_observations.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def check(data, source_root, rendered=True):
    pins = old.read(HERE / 'input-pins.json')['preimages']
    baseline = old.read(HERE / 'original-58.json')
    original_pin = next(p for p in pins if p['path'].endswith('/observations.json'))
    old.require(old.sha(HERE / 'original-58.json') == original_pin['sha256'], 'original58 snapshot drift')
    old.require(len(baseline['rows']) == 58 and data['rows'][:58] == baseline['rows'], 'original58 objects changed')
    old.require(len(data['rows']) == 59, 'G17 requires exactly59 rows')
    old.require(data['rows'][58] == old.read(HERE / 'added-row.json'), 'new observation changed')
    old.require(len({r['id'] for r in data['rows']}) == 59, 'duplicate observation ID')
    before_pin = next(p for p in pins if p['path'].endswith('/README.md'))
    old.require(old.sha(HERE / 'README.before.md') == before_pin['sha256'], 'README preimage drift')
    old.require((API / 'README.md').read_bytes().startswith((HERE / 'README.before.md').read_bytes()), 'prior README lines changed')
    result_pin = next(p for p in pins if p['path'].endswith('/results.json'))
    old.check_ref(ROOT, result_pin)
    count = old.check(data, source_root)
    row = data['rows'][58]
    old.require(row['frozen'] is False and row['status'] == 'LAUNCH_ATTEMPT_FAILED；无游戏帧', 'unsupported launch/API claim')
    for group in ('source', 'build', 'evidence'):
        for item in row[group]:
            path = item['path']
            allowed = path.startswith('benchmark/2026-10-21-commercial-game/normal-ui-01/') or path in (
                'benchmark/2026-10-21-commercial-game/exact-static/rea-method-findings.json',
                'benchmark/2026-10-21-commercial-game/exact-static/rea-ledger.json')
            old.require(allowed, f'unaccepted evidence source: {path}')
            old.check_ref(source_root, item)
            count += 1
    normal = old.read(source_root / 'benchmark/2026-10-21-commercial-game/normal-ui-01/results.json')
    old.require(normal['white_screen_t2'] and normal['desktop_t20'] and not normal['game_frame_observed'], 'normal UI scope drift')
    old.require(normal['exit_code_from_hilog'] == 1 and normal['causal_relation'] == 'unproven', 'exit/causal evidence drift')
    if rendered:
        with (API / 'observations.csv').open(encoding='utf-8-sig', newline='') as f:
            table = list(csv.DictReader(f))
        old.require(len(table) == 59, 'CSV row count')
        for expected, actual in zip(data['rows'], table):
            for key, value in expected.items():
                text = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
                old.require(actual[key] == text, f'CSV mismatch: {expected["id"]}/{key}')
        html = (API / 'index.html').read_text()
        old.require(html.count('<article>') == 59, 'HTML row count')
        old.require(re.findall(r'<code>(OBS-[^<]+)</code>', html) == [r['id'] for r in data['rows']], 'HTML row order')
        result = old.read(API / 'results.json')
        old.require(result['rows'] == 59 and result['references_verified'] == count, 'renderer result count')
        old.require(result['input_sha256'] == old.sha(API / 'observations.json'), 'renderer input drift')
        old.require(result['remote_publication_verified'] is False, 'render is not remote publication')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    data = old.read(API / 'observations.json')
    count = check(data, source_root)
    refusals = []
    changed = copy.deepcopy(data)
    changed['rows'][57]['status'] = 'changed'
    extra = copy.deepcopy(data)
    extra['rows'].append(dict(data['rows'][58], id='OBS-FUTURE'))
    item = data['rows'][58]['evidence'][0]
    cases = [
        ('original58 changed', lambda: check(changed, source_root, False), 'original58 objects changed'),
        ('missing reference', lambda: old.check_ref(source_root, dict(item, path='benchmark/2026-10-21-launch-observation-update/intentionally-missing.json')), 'missing/nonregular'),
        ('reference SHA drift', lambda: old.check_ref(source_root, dict(item, sha256='0' * 64)), 'SHA drift'),
        ('G17 rejects60', lambda: check(extra, source_root, False), 'exactly59'),
    ]
    for name, call, expected in cases:
        try:
            call()
        except ValueError as exc:
            old.require(expected in str(exc), f'unexpected refusal: {exc}')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else:
            raise ValueError(f'negative case accepted: {name}')
    old.require(old.check(extra, source_root) == 1339, 'G15 blocks later append')
    print(json.dumps({'status': 'PASS', 'original_rows_unchanged': 58,
        'added_rows': 1, 'rows': 59, 'exact_references': count,
        'html_csv_consistent': True, 'historical315_unchanged': True,
        'g15_prefix_check_pass': True, 'g15_allows_future_append': True,
        'g15_historical_result_unchanged': True, 'negative_cases': refusals,
        'device_calls': 0, 'rea_calls': 0, 'runtime_builds': 0,
        'remote_publication_verified': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
