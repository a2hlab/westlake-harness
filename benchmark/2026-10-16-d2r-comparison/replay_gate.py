#!/usr/bin/env python3
"""Replay the bounded D2R gate experiment using an existing pinned source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    evidence = json.loads((here / 'gate-experiment/results.json').read_text())
    sources = []
    for item in evidence['sources']:
        path = args.source_dir.resolve() / item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('upstream source hash mismatch: ' + item['path'])
        sources.append(path)
    original = sources[2].read_text()
    anchor = '    ldp x10, x11, [sp, #80]'
    if original.count(anchor) != 1:
        raise ValueError('mutation anchor must occur exactly once')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out / 'synthetic-gates.tsv'
    fixture.write_bytes((here / 'gate-experiment/synthetic-gates.tsv').read_bytes())
    mutated = out / 'entry-missing-x10-x11.S'
    mutated.write_text(original.replace(anchor, '    nop // omit x10/x11 restoration'))
    results = []
    for name, entry, expected in [('original', sources[2], 0),
                                  ('missing-register-restore', mutated, 1)]:
        binary = out / name
        commands = [('build', ['cc', '-O1', '-o', str(binary), str(sources[0]),
                               str(sources[1]), str(entry)]),
                    ('run', [str(binary), str(fixture)])]
        for phase, argv in commands:
            with (out / f'{name}-{phase}.stdout.txt').open('xb') as stdout, \
                    (out / f'{name}-{phase}.stderr.txt').open('xb') as stderr:
                proc = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=60)
            results.append({'case': name, 'phase': phase, 'argv': argv,
                            'returncode': proc.returncode})
            (out / 'commands.json').write_text(json.dumps(results, indent=2) + '\n')
            if proc.returncode != (0 if phase == 'build' else expected):
                raise RuntimeError('unexpected result: ' + name + '/' + phase)
        summary = (out / f'{name}-run.stdout.txt').read_text().splitlines()[-1]
        required = 'GATEFN OK 门=60' if expected == 0 else 'GATEFN FAIL 门=60'
        failures = '失败=0' if expected == 0 else '失败=60'
        if not summary.startswith(required) or not summary.endswith(failures):
            raise RuntimeError('unexpected coverage: ' + summary)
        print(summary)
    print('Synthetic gate experiment only; no Android/OH or full-game verdict.')


if __name__ == '__main__':
    main()
