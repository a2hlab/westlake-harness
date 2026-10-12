#!/usr/bin/env python3
"""Package existing original receipts, without executing the candidate again."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
ATTEMPT = HERE / '.artifacts/t5-70b6-independent-attempt4'
PREFIX = HERE.relative_to(REPOSITORY).as_posix()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n')


def main():
    data = json.loads((ATTEMPT / 'first-results.json').read_text())
    blockers = {'partial_send': 'direct partial transfer cannot restore prior alias',
                'null_after_label': 'unknown metadata accepted before control write',
                'mkdir_first_failure': 'zero-write missing ROOT cannot close safely as no-op'}
    for row in data['cases']:
        row['review_verdict'] = 'BLOCKER' if row['case'] in blockers else (
            'OBSERVATION' if row['case'] == 'old_stop_drift' else 'EXPECTED_OUTCOME')
        if row['case'] in blockers:
            row['finding'] = blockers[row['case']]
    data.update(schema='t5-independent-frozen-review/v1', deployment_accepted=False,
                ui_accepted=False, seal_signed=False, candidate_was_modified=False,
                boundary=dict(board=False, vm=False, remote=False, builds=0, push=False),
                cli_projection=dict(members=4, production_members=22, prerequisites_excluded=True),
                counts=dict(cli_cases=26, expected_outcomes=22, blockers=3, observations=1),
                autoboot=json.loads((ATTEMPT / 'autoboot-review.json').read_text()),
                known_answers=dict(tests=10, exit=0, candidate_acceptance=False),
                new_boot_auth_note='Initial apply SHA is recorded; final auth file is rollback phase. Restore its boot field to plan boot to reproduce initial bytes.',
                pending=['real mount/remount and permissions', 'full placement prerequisites',
                         'real current WID/parent/namespace', 'fresh screenshot and interactive UI',
                         'board reboot/seal and Plan-2 regression'])
    write_json(HERE / 't5-70b6-results.json', data)
    evidence = HERE / 'evidence'
    copies = {'t5-70b6-cli-original.txt': '.artifacts/t5-70b6-attempt4.stdout.txt',
              't5-70b6-cli-original-errors.txt': '.artifacts/t5-70b6-attempt4.stderr.txt',
              't5-70b6-autoboot-original.txt': '.artifacts/t5-70b6-autoboot.stderr.txt',
              't5-70b6-known-answers-original.txt': '.artifacts/t5-70b6-known-answers-final.stderr.txt'}
    for target, source in copies.items():
        (evidence / target).write_bytes((HERE / source).read_bytes())
    raw_paths = sorted({path for candidate in (HERE / '.artifacts').glob('t5-70b6*')
                        for path in (candidate.rglob('*') if candidate.is_dir() else [candidate])
                        if path.is_file() and '__pycache__' not in path.parts})
    raw_index = [{'path': '$WORKSPACES/westlake-harness-bms/' + path.relative_to(REPOSITORY).as_posix(),
                  'sha256': sha(path), 'bytes': path.stat().st_size} for path in raw_paths]
    original = json.loads((evidence / 't4-handoff-inputs.json').read_text())['original_r2_file_hashes']
    drift = [path for path, expected in original.items() if sha(REPOSITORY / path) != expected]
    assert not drift, drift
    package = ATTEMPT / 'workspaces/westlake-harness-t0/benchmark/2026-10-12-recovery-executor'
    manifest = json.loads((package / 'checkpoint-manifest.json').read_text())
    write_json(evidence / 't5-70b6-artifact-index.json',
               dict(commit=data['receipt']['commit'], raw_files=raw_index,
                    frozen_git_members=manifest['files'], original_r2_files=52, original_r2_drift=drift,
                    original_r2_listing_sha256=sha(HERE / 'landing-paths.txt'),
                    reviewer_sources={name: sha(HERE / name) for name in
                                      ['review_t5_70b6.py', 'record_t5_hdc.py',
                                       'review_t5_70b6_autoboot.py', 'test_t5_70b6_review.py']}))
    files = ['T5-70B6-FINAL.md', 't5-70b6-results.json', 'review_t5_70b6.py',
             'record_t5_hdc.py', 'review_t5_70b6_autoboot.py', 'test_t5_70b6_review.py',
             'finalize_t5_70b6_review.py', 'evidence/t5-70b6-artifact-index.json',
             *['evidence/' + name for name in copies], 't5-70b6-landing-paths.txt',
             'evidence/t5-70b6-preflight.txt']
    (HERE / 't5-70b6-landing-paths.txt').write_text(''.join(PREFIX + '/' + name + '\n' for name in files))
    print(json.dumps({'files': len(files), 'raw_files': len(raw_index), 'counts': data['counts'],
                      'original_r2_drift': drift}))


if __name__ == '__main__':
    main()
