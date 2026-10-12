#!/usr/bin/env python3
"""Offline, SHA-pinned original-image checks; never builds or contacts a device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
from lab_paths import workspaces

BASELINE_SOURCE_SHA = '94a4a099241e62114f69e77d03473a182103acda889294fcace8d810f05cd6b7'
BASELINE_ARM_SHA = 'a0f5f55472e93338b490b89226aaf0436ee65b45191ce6f9f54be869781867fb'
STB_SHA = 'e4b91dc70192b9d998b0103c5e7e2abf531329a27309d239bee9057c519c4b24'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def png(width, height, truncated=False, login=False):
    header = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    if truncated:
        # Dimensions and IHDR are valid, but there are no compressed pixels.
        return header + chunk(b'IDAT', b'')
    pixels = bytearray((b'\0' + b'\xff\xff\xff' * width) * height)
    if login:
        for x, y in ((25, 100), (85, 100), (55, 125)):
            offset = y * (width * 3 + 1) + 1 + x * 3
            pixels[offset:offset + 3] = bytes((250, 60, 60))
    return header + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


def invoke(binary, path):
    p = subprocess.run([str(binary), str(path)], capture_output=True, text=True, timeout=20)
    return {'actual': p.stdout.strip(), 'rc': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def run_samples(catalog, group):
    binaries = {'candidate': HERE / 'payload/screen-gate-host', 'baseline': HERE / 'payload/baseline-host'}
    binary_pins = {k: sha(v) for k, v in binaries.items()}
    results = []
    with tempfile.TemporaryDirectory(prefix='westlake-feed-negative-') as temp:
        samples = []
        for row in catalog['samples']:
            if group == 'positive' and row['expected'] != 'feed':
                continue
            if group == 'negative' and row['expected'] == 'feed':
                continue
            path = Path(row['source'].replace('$WORKSPACES', str(workspaces())))
            samples.append((row, path))
        if group != 'positive':
            for item in catalog['generated_cases']:
                row = dict(item, kind='generated', source='generated:' + item['generator'], baseline_expected=item['expected'], baseline_rc=item['expected_rc'])
                path = Path(temp) / (item['id'] + '.png')
                if item['id'] == 'blank':
                    path.write_bytes(png(1200, 1920))
                elif item['id'] == 'unsupported-size':
                    path.write_bytes(png(16, 16))
                elif item['id'] == 'truncated':
                    path.write_bytes(png(1200, 1920, truncated=True))
                elif item['id'] == 'login-predicate':
                    path.write_bytes(png(1200, 1920, login=True))
                elif item['id'] != 'missing':
                    raise ValueError('unknown generator: ' + item['id'])
                samples.append((row, path))
        for row, path in samples:
            actual_sha = sha(path) if path.exists() else None
            result = {k: row[k] for k in ('id', 'source', 'kind', 'expected', 'expected_rc')}
            result.update(source_sha256=actual_sha, source_exists=path.exists(), source_pin_matches=(actual_sha == row['sha256']) if row['kind'] == 'captured' else True)
            if not result['source_pin_matches']:
                result.update(passed=False, error='source SHA mismatch; classifiers not invoked')
            else:
                result['candidate'] = invoke(binaries['candidate'], path)
                result['baseline'] = invoke(binaries['baseline'], path)
                result['baseline'].update(expected=row['baseline_expected'], expected_rc=row['baseline_rc'])
                result['passed'] = all((result['candidate']['actual'] == row['expected'], result['candidate']['rc'] == row['expected_rc'], result['baseline']['actual'] == row['baseline_expected'], result['baseline']['rc'] == row['baseline_rc']))
            results.append(result)
            print(('PASS' if result['passed'] else 'FAIL'), row['id'], json.dumps(result.get('candidate', {})))
    return {'binary_sha256': binary_pins, 'samples': results, 'passed': all(r['passed'] for r in results)}


def reproducible():
    """Check two existing logged builds. This selector never launches a compiler."""
    records = []
    builds = [HERE / 'evidence/build-03', HERE / 'evidence/build-04']
    outputs = []
    for directory in builds:
        inputs = json.loads((directory / 'inputs.json').read_text())
        commands = json.loads((directory / 'commands.json').read_text())
        out = json.loads((directory / 'outputs.json').read_text())
        assert set(out) == {'screen-gate-feed', 'screen-gate-host', 'baseline-host'}, 'missing build output'
        assert {r['name'] for r in commands} == {'arm', 'host', 'baseline-host'}, 'missing build command'
        for row in inputs:
            recorded = Path(row['path'])
            # Build receipts retain original locations; landed source bytes are
            # verified here without reading a producer's private checkout.
            local = HERE / 'src' / recorded.name if recorded.parent.name == 'src' else recorded
            assert sha(local) == row['sha256'], 'build input drift: ' + row['path']
        for row in commands:
            assert row['rc'] == 0 and (directory / (row['name'] + '.exit')).read_text().strip() == '0', 'build failure'
            for suffix in ('.stdout', '.stderr'):
                assert (directory / (row['name'] + suffix)).is_file(), 'missing raw build log'
        for name, expected in out.items():
            assert sha(directory / name) == expected, 'built binary drift: ' + name
            assert sha(HERE / 'payload' / name) == expected, 'published binary drift: ' + name
        outputs.append(out)
        records.append({'directory': str(directory.relative_to(HERE)), 'inputs_sha256': sha(directory / 'inputs.json'), 'outputs': out, 'raw_logs': {p.name: sha(p) for p in directory.iterdir() if p.suffix in ('.stdout', '.stderr', '.exit')}})
    assert outputs[0] == outputs[1], 'rebuild differs'
    assert sha(HERE / 'src/baseline_feed.c') == BASELINE_SOURCE_SHA, 'baseline source changed'
    current = (HERE / 'src/screen_gate_feed.c').read_text()
    start = current.index('/* t11:'); end = current.index('int main(', start)
    stripped = (current[:start] + current[end:]).replace(' if(!strcmp(label,"unknown") && observed_feed_regions())label="feed";\n', '')
    assert stripped == (HERE / 'src/baseline_feed.c').read_text(), 'historical branch or colour predicate changed'
    assert sha(HERE / 'src/stb_image.h') == STB_SHA, 'decoder source changed'
    original = workspaces() / 'westlake-harness/benchmark/2026-10-12-recovery-executor'
    assert sha(original / 'src/screen_gate_feed.c') == BASELINE_SOURCE_SHA, 'original source changed'
    assert sha(original / 'payload/screen-gate-feed') == BASELINE_ARM_SHA, 'original frozen binary changed'
    return {'passed': True, 'builds': records, 'original_source_sha256': BASELINE_SOURCE_SHA, 'original_arm_sha256': BASELINE_ARM_SHA, 'scope': 'Offline host execution and ARM compile only; no candidate ARM execution or board acceptance.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--group', choices=('all', 'positive', 'negative', 'reproducible'), default='all')
    args = ap.parse_args()
    catalog = json.loads((HERE / 'samples.json').read_text())
    report = {'schema': 'westlake.feed-classifier-results.v1', 'group': args.group, 'samples_sha256': sha(HERE / 'samples.json'), 'coverage_gaps': catalog['coverage_gaps'], 'scope': catalog['scope']}
    try:
        if args.group != 'reproducible':
            report.update(run_samples(catalog, args.group))
        if args.group in ('all', 'reproducible'):
            report['reproducible'] = reproducible()
        report['passed'] = report.get('passed', True)
    except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as exc:
        report.update(passed=False, error=str(exc))
    evidence = HERE / 'evidence'
    evidence.mkdir(exist_ok=True)
    # Rust selectors may run in parallel; their reports must not overwrite one another.
    name = 'local-results.json' if args.group == 'all' else 'local-results-' + args.group + '.json'
    (evidence / name).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'group': args.group, 'passed': report['passed'], 'report': name, 'error': report.get('error')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
