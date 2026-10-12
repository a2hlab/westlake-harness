#!/usr/bin/env python3
"""Package already recorded targeted revision results; no candidate rerun."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
ATTEMPT = HERE / '.artifacts/t5-b093d859-independent2'
PREFIX = HERE.relative_to(REPOSITORY).as_posix()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads((ATTEMPT / 'first-results.json').read_text())
    data.update(schema='t5-targeted-revision-review/v1', deployment_accepted=False,
                ui_accepted=False, seal_signed=False, logic_new_blockers=[],
                release_blockers=['checkpoint manifest has 11 stale hashes and excludes new files'],
                author_selected_tests=dict(tests=4, exit=0, seconds=5.280,
                                           host_fixture_compilations=1, real_elapsed_601_proved=False),
                boundary=dict(board=False, vm=False, remote=False, deployment=False, push=False))
    (HERE / 't5-b093d859-results.json').write_text(json.dumps(data, indent=2) + '\n')
    copies = {'t5-b093d859-cli-original.txt': '.artifacts/t5-b093d859-run2.stdout.txt',
              't5-b093d859-cli-errors.txt': '.artifacts/t5-b093d859-run2.stderr.txt',
              't5-b093d859-export-rejection.txt': '.artifacts/t5-b093d859.stderr.txt',
              't5-b093d859-cfg-tap-original.txt': 't5-b093d859-cfg-tap.stderr.txt'}
    for target, source in copies.items():
        (HERE / 'evidence' / target).write_bytes((HERE / source).read_bytes())
    paths = [path for directory in [HERE / '.artifacts/t5-b093d859-independent', ATTEMPT]
             for path in directory.rglob('*') if path.is_file() and '__pycache__' not in path.parts]
    paths.extend(HERE / source for source in copies.values())
    raw = [{'path': '$WORKSPACES/westlake-harness-bms/' + path.relative_to(REPOSITORY).as_posix(),
            'sha256': sha(path), 'bytes': path.stat().st_size} for path in sorted(set(paths))]
    original = json.loads((HERE / 'evidence/t4-handoff-inputs.json').read_text())['original_r2_file_hashes']
    drift = [path for path, expected in original.items() if sha(REPOSITORY / path) != expected]
    assert not drift, drift
    index = dict(commit=data['receipt']['commit'], raw_files=raw, original_r2_drift=drift,
                 original_r2_files=52, sources={name: sha(HERE / name) for name in
                                               ['review_t5_70b6.py', 'record_t5_hdc.py']})
    (HERE / 'evidence/t5-b093d859-artifact-index.json').write_text(json.dumps(index, indent=2) + '\n')
    files = ['T5-B093D859-REVISION.md', 't5-b093d859-results.json',
             'review_t5_70b6.py', 'record_t5_hdc.py', 'finalize_t5_b093d859.py',
             'evidence/t5-b093d859-artifact-index.json', *['evidence/' + name for name in copies],
             't5-b093d859-landing-paths.txt', 'evidence/t5-b093d859-preflight.txt']
    (HERE / 't5-b093d859-landing-paths.txt').write_text(''.join(PREFIX + '/' + name + '\n' for name in files))
    print(json.dumps({'files': len(files), 'raw_files': len(raw), 'original52_drift': drift}))


if __name__ == '__main__':
    main()
