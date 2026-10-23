#!/usr/bin/env python3
"""Offline G38 reference/boundary check; never invokes a producer."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CARD = Path(__file__).resolve().parent
EXPECTED = '775c8ae837306c06a24fc0e2562291f63ee3854bdb5154d82c48a2ee37a6b93a'
SIGCHAIN = '6d5d5538ff45c057208186f5cb74b9b5c2402d693aa2756a99327fd4b9f8c400'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def validate(r):
    pins = json.loads((CARD / 'input-pins.json').read_text())
    paths = set()
    for pin in pins:
        p = CARD / pin['path']
        need(p.resolve().is_relative_to(CARD), 'path escape')
        b = p.read_bytes()
        need(len(b) == pin['size'] and hashlib.sha256(b).hexdigest() == pin['sha256'], 'input SHA drift')
        need(pin['path'] not in paths, 'duplicate pin')
        paths.add(pin['path'])

    def refs(v):
        if isinstance(v, dict):
            if {'file', 'line', 'text'} <= v.keys():
                need(v['file'] in paths, 'missing reference')
                lines = (CARD / v['file']).read_text().splitlines()
                need(isinstance(v['line'], int) and 1 <= v['line'] <= len(lines), 'invalid line')
                need(lines[v['line'] - 1] == v['text'], 'reference text drift')
            for x in v.values():
                refs(x)
        elif isinstance(v, list):
            for x in v:
                refs(x)

    refs(r)
    need(r['schema'] == 'G38-provider-archive-map-v1', 'schema')
    need(r['max_reference_depth'] == 2, 'depth limit')
    for edge in r['reference_chain']:
        need(edge['depth'] in [1, 2] and edge['from'] in paths, 'unbound hop')
        if edge['depth'] == 1:
            need(edge['to'] in paths, 'missing destination')
    need(r['source_script_expected_sha256'] == EXPECTED, 'wrong expected script')
    need(r['source_script_actual_sha256'] is None and r['source_script_verified'] is False, 'missing/mismatching script promoted')
    need(r['sigchain_target_sha256'] == SIGCHAIN, 'sigchain substitution')
    need(r['build_chain_complete'] is False and r['game_first_frame'] == 'unknown', 'unsupported build/frame claim')
    f = r['separate_findings']
    need(f['archive']['status'] == 'unknown' and f['archive']['path'] is None, 'invented archive binding')
    need(f['input_mount']['status'] == 'recipe_declared_only', 'recipe promoted to actual mount')
    need(f['exact_script']['analysis_performed'] is False, 'unverified inner analysis')
    logs = f['original_build_logs']
    need(logs['status'] == 'not_recovered' and all(logs[k] is None for k in ['stdout', 'stderr', 'rc']), 'missing build logs promoted')
    need(r['outer_probe']['rc'] == 1 and r['outer_parent_root_probe']['rc'] == 2, 'failed probe lost')
    need(r['next_input_request']['remote_paths_to_read_now'] == [], 'unsupported new remote request')
    need(all(x == 0 for x in r['operations'].values()), 'forbidden operation')
    # The main manifest binds the exact mapping scripts we read, not775c8ae8.
    manifest = dict((n, h) for h, n in (line.split(None, 1) for line in (CARD / 'evidence/recipe-SHA256SUMS').read_text().splitlines()))
    for local, origin in [('build_generation.sh.txt', 'build_generation.sh'), ('provider-report.md', 'REPORT.md'), ('provider-readme.md', 'README.md')]:
        need(hashlib.sha256((CARD / 'evidence' / local).read_bytes()).hexdigest() == manifest['adapter/build/provider_generation/' + origin], 'mapping source manifest mismatch')
    return len(pins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=CARD / 'results.json')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--private', action='store_true')
    args = ap.parse_args()
    try:
        r = json.loads(args.results.read_text())
        count = validate(r)
        if args.private:
            for pin in json.loads((CARD / 'outer-raw-index.json').read_text()):
                b = Path(pin['path'].replace('$HOME', str(Path.home()))).read_bytes()
                need(len(b) == pin['size'] and hashlib.sha256(b).hexdigest() == pin['sha256'], 'outer raw drift')
        cases = []
        if args.self_test:
            for name, change in [
                ('missing_reference', lambda x: x['reference_chain'][0]['basis'].update(file='missing')),
                ('wrong_script_accepted', lambda x: x.update(source_script_actual_sha256='fd306585ee18220dee9b0c653b256b70d4ced845199ac4fb7b45cf021809cc1f', source_script_verified=True)),
                ('missing_log_build_complete', lambda x: x.update(build_chain_complete=True)),
                ('sigchain_substitution', lambda x: x.update(sigchain_target_sha256='ea7becd0203fdcb03cc0d61a493ef8e4a12ef3ca3b4ca9b61be3f02103865ba2')),
            ]:
                bad = copy.deepcopy(r)
                change(bad)
                with tempfile.TemporaryDirectory(prefix='g38-negative-') as d:
                    p = Path(d) / 'results.json'
                    p.write_text(json.dumps(bad))
                    run = subprocess.run([sys.executable, str(CARD / 'check.py'), '--results', str(p)], capture_output=True, text=True)
                    need(run.returncode == 2 and run.stdout.startswith('REFUSE '), 'negative passed: ' + name)
                    cases.append({'case': name, 'rc': run.returncode, 'stdout': run.stdout.strip(), 'stderr': run.stderr})
        print(json.dumps({'status': 'OFFLINE_REFERENCES_VALID', 'pins': count, 'negatives': cases, 'mapping_entity_found': False, 'build_complete': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('REFUSE ' + str(exc))
        return 2


if __name__ == '__main__':
    sys.exit(main())
