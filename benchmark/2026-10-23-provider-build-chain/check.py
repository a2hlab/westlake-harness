#!/usr/bin/env python3
"""Validate G37 evidence boundaries, without running a producer or a remote tool."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CARD = Path(__file__).resolve().parent
TARGETS = {
    'libunwindstack.so': 'd2c1cbc70d097855b9196ec87f80c09d6f24e674ee16a3c517629df999c66965',
    'libsigchain.so': '6d5d5538ff45c057208186f5cb74b9b5c2402d693aa2756a99327fd4b9f8c400',
}
OTHER_SIGCHAIN = 'ea7becd0203fdcb03cc0d61a493ef8e4a12ef3ca3b4ca9b61be3f02103865ba2'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def validate(report):
    pins = json.loads((CARD / 'input-pins.json').read_text())
    pinned = {}
    for row in pins:
        p = CARD / row['path']
        need(p.resolve().is_relative_to(CARD), 'input escapes card')
        b = p.read_bytes()
        need(len(b) == row['size'] and hashlib.sha256(b).hexdigest() == row['sha256'], 'input drift: ' + row['path'])
        need(row['path'] not in pinned, 'duplicate pin')
        pinned[row['path']] = row

    def refs(value):
        if isinstance(value, dict):
            if {'file', 'line', 'text'} <= value.keys():
                need(value['file'] in pinned, 'unbound evidence reference')
                lines = (CARD / value['file']).read_text().splitlines()
                n = value['line']
                need(isinstance(n, int) and 1 <= n <= len(lines), 'bad evidence line')
                need(lines[n - 1] == value['text'], 'evidence text mismatch')
            for item in value.values():
                refs(item)
        elif isinstance(value, list):
            for item in value:
                refs(item)

    refs(report)
    need(report['schema'] == 'G37-provider-chain-v1', 'schema')
    need(report['max_producer_hops'] == 2 and 0 <= report['completed_producer_hops'] <= 2, 'producer hop budget')
    need(len(report['producer_edges']) == report['completed_producer_hops'], 'producer edge count')
    for edge in report['producer_edges']:
        need({'from', 'to', 'evidence'} <= edge.keys(), 'missing producer edge reference')
        need(edge['evidence']['file'] in pinned, 'unbound producer')
    need(report['completed_producer_hops'] == 1, 'only exact entry is resolved')
    entry = CARD / 'sources/container_build.sh'
    need(hashlib.sha256(entry.read_bytes()).hexdigest() == '766edce071252c1506d575ecb22db6319f50436b98c4f450ec326531b02754cb', 'producer entry SHA')
    pending = report['pending_second_hop']
    need(pending['expected_sha256'] == '775c8ae837306c06a24fc0e2562291f63ee3854bdb5154d82c48a2ee37a6b93a', 'frozen inner pin changed')
    need(pending['status'] == 'REFUSED_HASH_MISMATCH_NOT_TRAVERSED', 'drifted inner script accepted')
    need(pending['remote_exact_path_actual_sha256'] == 'b358f08a7b75c98fac8c5ec3fe63dfe3a04c13c386dd307332e4f8358c94f88c', 'drift evidence changed')
    need(report['build_executed'] is False and report['artifact_rehashed'] is False, 'unsupported build/rehash claim')
    need(report['source_closure'] is False and report['game_first_frame'] == 'unknown', 'unsupported closure/frame claim')
    need(set(report['targets']) == set(TARGETS), 'target set')
    for name, target in TARGETS.items():
        item = report['targets'][name]
        need(item['target_sha256'] == target, 'target SHA substituted: ' + name)
        for field in ['source_snapshot', 'actual_compile_command', 'toolchain', 'link_inputs', 'original_rc0_logs', 'final_object']:
            need(isinstance(item[field], dict) and 'status' in item[field], 'missing component: ' + field)
        need(item['actual_compile_command']['status'] == 'unknown', 'compile command not evidenced')
        need(item['original_rc0_logs']['status'] == 'unknown', 'lookup rc0 is not compile rc0')
    sig = report['targets']['libsigchain.so']
    need(sig['final_object'] == {'status': 'unbound', 'sha256': None}, 'different sigchain cannot bind target')
    need(sig['non_target_manifest']['sha256'] == OTHER_SIGCHAIN, 'different sigchain evidence lost')
    unw = report['targets']['libunwindstack.so']
    need(unw['final_object']['status'] == 'manifest_declared' and unw['final_object']['sha256'] == TARGETS['libunwindstack.so'], 'manifest scope changed')
    audit = json.loads((CARD / 'evidence/independent-audit.json').read_text())
    row = next(x for x in audit['dual_build']['providers'] if x['provider'] == 'libunwindstack.so')
    need(row['build_a_sha256'] == row['build_b_sha256'] == TARGETS['libunwindstack.so'], 'audit object mismatch')
    need(all(x == 0 for x in report['operations'].values()), 'forbidden action claimed')
    need(all(x['executor'] == 'outer_only' and x['path'].startswith('/opt/build-runs/') for x in report['next_exact_reads']), 'read request scope')
    return len(pins)


def self_test(report):
    cases = []
    for label, change in [
        ('different_sigchain', lambda x: x['targets']['libsigchain.so'].update(final_object={'status': 'bound', 'sha256': OTHER_SIGCHAIN})),
        ('missing_reference', lambda x: x['bounded_findings'][0]['evidence'].update(file='evidence/missing.txt')),
        ('third_producer_hop', lambda x: x.update(completed_producer_hops=3)),
        ('lookup_rc_promoted', lambda x: x['targets']['libunwindstack.so']['original_rc0_logs'].update(status='verified_rc0')),
        ('drifted_inner_promoted', lambda x: x['pending_second_hop'].update(status='verified')),
    ]:
        mutated = copy.deepcopy(report)
        change(mutated)
        with tempfile.TemporaryDirectory(prefix='g37-negative-') as d:
            p = Path(d) / 'results.json'
            p.write_text(json.dumps(mutated))
            run = subprocess.run([sys.executable, str(CARD / 'check.py'), '--results', str(p)], capture_output=True, text=True)
            need(run.returncode == 2 and run.stdout.startswith('REFUSE '), 'negative not refused: ' + label)
            cases.append({'case': label, 'rc': run.returncode, 'stdout': run.stdout.strip(), 'stderr': run.stderr})
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=CARD / 'results.json')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--private', action='store_true', help='also verify outer persistent read receipts and full index excerpts')
    args = ap.parse_args()
    try:
        report = json.loads(args.results.read_text())
        count = validate(report)
        if args.private:
            for item in json.loads((CARD / 'exact-read-raw-index.json').read_text()):
                p = Path(item['path'].replace('$HOME', str(Path.home())))
                b = p.read_bytes()
                need(len(b) == item['size'] and hashlib.sha256(b).hexdigest() == item['sha256'], 'private raw drift')
            source = Path(report['full_input_manifest']['origin'].replace('$HOME', str(Path.home())))
            lines = source.read_text().splitlines()
            for line in (CARD / report['full_input_manifest']['excerpt']).read_text().splitlines():
                number, exact = line.split(':', 1)
                need(lines[int(number) - 1] == exact, 'manifest excerpt mismatch')
        negative = self_test(report) if args.self_test else []
        print(json.dumps({'status': 'OFFLINE_REFERENCES_VALID', 'input_pins': count, 'negative_cases': negative, 'build_chain_complete': False, 'game_first_frame': 'unknown'}))
    except (ValueError, KeyError, OSError, StopIteration, TypeError) as exc:
        print('REFUSE ' + str(exc))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
