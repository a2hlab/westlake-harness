#!/usr/bin/env python3
"""Preparation-only validation: no accepted source, no candidate generation."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import build
from check import logged

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    c = build.CARD
    for name in ['build.py', 'check.py', 'prepare_check.py']:
        compile((c / name).read_text(), name, 'exec')
    lock = json.loads((c / 'inputs/source-lock.json').read_text())
    build.need(lock['status'] == 'PENDING_OUTER_ACCEPTANCE' and not lock['sources'], 'not preparation state')
    manifest = (c / 'inputs/preimage-inputs.json').read_bytes()
    build.need(build.sha(manifest) == lock['preimage_manifest_sha256'], 'preimage index drift')
    records = json.loads(manifest)['files']
    build.need(len(records) == 9, 'nine preimages required')
    for row in records:
        data = (c / 'baseline' / Path(row['path']).name).read_bytes()
        build.need(len(data) == row['size'] and build.sha(data) == row['device_sha256'] == row['local_bytes_sha256'], 'preimage drift')
    members = (c / 'baseline/members.tsv').read_bytes()
    startup = (c / 'baseline/startup.env').read_bytes()
    build.need(build.parse_startup(startup)['STARTUP_MEMBERS_SHA'] == build.sha(members), 'baseline member pin')
    build.need((c / 'baseline/startup.expected.sha256').read_text() == build.sha(startup) + '\n', 'baseline expected pin')
    rows = []
    for line in members.decode().splitlines(True):
        h, name, mode = line.split()
        rows.append((h, name, mode, line))
    build.validate_members(lock, rows)
    argv = [sys.executable, str(c / 'build.py'), '--inputs', str(c / 'inputs/preimage-inputs.json'), '--bytes', str(c / 'baseline')]
    target = args.out / 'must-not-exist'
    build.need(logged(argv + ['--out', str(target)], args.out / 'pending-refusal') == 2, 'pending acceptance not refused')
    build.need(not target.exists(), 'pending candidate output exists')
    build.need('T50 outer acceptance pending' in (args.out / 'pending-refusal/stderr').read_text(), 'wrong refusal')
    mixed = args.out / 'mixed-card'; (mixed / 'inputs').mkdir(parents=True)
    shutil.copyfile(c / 'build.py', mixed / 'build.py')
    (mixed / 'inputs/source-lock.json').write_text(json.dumps({'t46_commit': '8e4c993077', 'sources': {}}))
    argv[1] = str(mixed / 'build.py')
    build.need(logged(argv + ['--out', str(target)], args.out / 'mixed-lock-refusal') == 2, 'mixed lock not refused')
    build.need(not target.exists(), 'mixed lock produced output')
    build.need('wrong card lock' in (args.out / 'mixed-lock-refusal/stderr').read_text(), 'wrong mixed-lock refusal')
    result = {'status': 'PREPARATION_CHECKED_PENDING_T50_ACCEPTANCE', 'baseline_files_verified': 9,
              'historical_member_records_verified': 13, 'pending_refusal_rc': 2,
              'mixed_lock_refusal_rc': 2, 'candidate_packages_generated': 0,
              'full_T51_scenarios_run': False, 'device_commands': 0}
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
