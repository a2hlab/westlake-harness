#!/usr/bin/env python3
"""Bounded offline checks of the actual builder and its exact outputs."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import build

def logged(argv, out):
    out.mkdir(parents=True, exist_ok=False)
    (out / 'argv.json').write_text(json.dumps(argv) + '\n')
    (out / 'start.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n')
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        rc = subprocess.run(argv, stdout=stdout, stderr=stderr).returncode
    (out / 'rc.txt').write_text(str(rc) + '\n')
    (out / 'end.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n')
    return rc

def tree(path):
    return {str(p.relative_to(path)): build.sha(p.read_bytes()) for p in path.rglob('*') if p.is_file()}

def verify(package):
    c = build.CARD
    receipt = json.loads((package / 'receipt.json').read_text())
    build.need(receipt['rollout_ready'] is False, 'rollout ready unexpectedly')
    for sub in ['candidate', 'rollback']:
        build.need({p.name for p in (package / sub).iterdir()} == set(build.MODIFIED), 'output file set')
    old = {n: (c / 'baseline' / n).read_bytes() for n in build.MODIFIED}
    new = {n: (package / 'candidate' / n).read_bytes() for n in build.MODIFIED}
    for n in build.MODIFIED:
        build.need((package / 'rollback' / n).read_bytes() == old[n], 'rollback not exact')
        build.need(build.sha(new[n]) == receipt['files'][n]['candidate_sha256'], 'receipt mismatch')
    for n in ['watchdog.sh', 'route-b-owner.sh']:
        build.need(new[n] == (c / 'sources' / n).read_bytes(), 'T46 source changed')
    expected_entry = old['entry.sh']
    for n in ['watchdog.sh', 'route-b-owner.sh']:
        expected_entry = expected_entry.replace(build.sha(old[n]).encode(), build.sha(new[n]).encode())
    build.need(new['entry.sh'] == expected_entry, 'entry changes beyond two pins')
    unchanged = 0
    for a, b in zip(old['members.tsv'].splitlines(True), new['members.tsv'].splitlines(True)):
        name = a.split()[1].decode()
        if name in ['watchdog.sh', 'route-b-owner.sh', 'entry.sh']:
            build.need(b.split()[0].decode() == build.sha(new[name]) and a.split()[1:] == b.split()[1:], 'member pin mismatch')
        else:
            build.need(a == b, 'unchanged member changed'); unchanged += 1
    build.need(unchanged == 10, 'ten unmodified members required')
    expected_env = old['startup.env'].replace(b"STARTUP_ENABLED='1'", b"STARTUP_ENABLED='0'")
    expected_env = expected_env.replace(build.sha(old['members.tsv']).encode(), build.sha(new['members.tsv']).encode())
    build.need(new['startup.env'] == expected_env, 'startup changes beyond disable/member pin')
    build.need(new['startup.expected.sha256'] == (build.sha(new['startup.env']) + '\n').encode(), 'expected pin mismatch')
    build.need(receipt['historical_member_records'] == 13 and receipt['member_bytes_not_in_public_snapshot'] == 9, 'historical member scope mismatch')

def main():
    build.need(sys.flags.optimize == 0 and not os.environ.get('PYTHONOPTIMIZE'), 'Python optimization prohibited')
    p = argparse.ArgumentParser();p.add_argument('--out', type=Path)
    a = p.parse_args();c = build.CARD
    out = a.out or c / '.private' / ('check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    out.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, str(c / 'build.py'), '--inputs', str(c / 'inputs/preimage-inputs.json'), '--bytes', str(c / 'baseline')]
    package = out / 'package'
    build.need(logged(argv + ['--out', str(package)], out / 'positive') == 0, 'real builder failed')
    verify(package)
    package2 = out / 'package-repeat'
    build.need(logged(argv + ['--out', str(package2)], out / 'repeat') == 0, 'second real build failed')
    build.need(tree(package / 'candidate') == tree(package2 / 'candidate'), 'candidate builds differ')
    build.need(tree(package / 'rollback') == tree(package2 / 'rollback'), 'rollback builds differ')
    before = tree(package)
    build.need(logged(argv + ['--out', str(package)], out / 'existing-output') != 0, 'existing output accepted')
    build.need(before == tree(package), 'existing output modified')
    bad = out / 'bad-bytes';shutil.copytree(c / 'baseline', bad)
    (bad / 'startup.env').write_bytes((bad / 'startup.env').read_bytes() + b"EVIL=$(touch forbidden)\n")
    bad_argv = argv.copy();bad_argv[bad_argv.index('--bytes') + 1] = str(bad)
    build.need(logged(bad_argv + ['--out', str(out / 'bad-package')], out / 'wrong-pin') != 0, 'wrong pin accepted')
    build.need(not (out / 'bad-package').exists(), 'wrong pin produced output')
    rejected = False
    try:
        build.parse_startup((bad / 'startup.env').read_bytes())
    except build.Refuse:
        rejected = True
    build.need(rejected, 'actual parser accepted executable syntax')
    (out / 'parser-check.json').write_text(json.dumps({'production_parser_rejected_executable_syntax': True}) + '\n')
    bad_sources = out / 'bad-sources'; shutil.copytree(c / 'sources', bad_sources)
    target = bad_sources / 'watchdog.sh'; target.write_bytes(target.read_bytes() + b'\n# drift\n')
    build.need(logged(argv + ['--sources', str(bad_sources), '--out', str(out / 'bad-source-package')], out / 'wrong-source') != 0, 'wrong source accepted')
    build.need(not (out / 'bad-source-package').exists(), 'wrong source produced package')
    mixed = out / 'mixed-card'; (mixed / 'inputs').mkdir(parents=True)
    shutil.copyfile(c / 'build.py', mixed / 'build.py')
    shutil.copyfile(c / 'inputs/t47-source-lock.reference.json', mixed / 'inputs/source-lock.json')
    mixed_argv = argv.copy(); mixed_argv[1] = str(mixed / 'build.py')
    build.need(logged(mixed_argv + ['--out', str(out / 'mixed-package')], out / 'mixed-lock') != 0, 'old lock accepted')
    build.need(not (out / 'mixed-package').exists(), 'old lock produced package')
    # Deliberate negative test: optimized execution must refuse, never bypass pins.
    build.need(logged([sys.executable, '-O'] + argv[1:] + ['--out', str(out / 'optimized-package')], out / 'optimization-refusal') != 0, 'optimization accepted')
    build.need(not (out / 'optimized-package').exists(), 'optimized run produced output')
    result = {'passed': True, 'checks': ['two_actual_builds_exact_six_file_chain', 'existing_output_refusal_and_preservation', 'wrong_pin_refusal_without_output', 'wrong_source_refusal', 'mixed_T47_lock_refusal', 'production_parser_rejects_executable_syntax', 'optimization_refusal_without_output'], 'device_commands': 0}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n');print(json.dumps(result))

if __name__ == '__main__':
    main()
