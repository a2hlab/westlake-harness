#!/usr/bin/env python3
"""Test the patched deployer against the current master's frozen-policy fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.out.mkdir(parents=True, exist_ok=False)
    overlay = args.out / 'root'
    scripts = overlay / 'scripts/lab'
    scripts.mkdir(parents=True)
    patched = root / 'scripts/lab/deploy_generation.py'
    shutil.copyfile(patched, scripts / patched.name)
    original_test = args.master / 'scripts/lab/test_deploy_frozen.py'
    shutil.copyfile(original_test, scripts / original_test.name)
    for source in sorted((args.master / 'scripts/lab').glob('*.py')):
        if source.name == 'selinux_label_audit.py':
            continue
        target = scripts / source.name
        if not target.exists():
            target.symlink_to(source.resolve())
    (scripts / 'selinux_label_audit.py').symlink_to(root / 'scripts/lab/selinux_label_audit.py')
    (overlay / 'knowledge').symlink_to(args.master.resolve() / 'knowledge')
    command = [sys.executable, str(scripts / original_test.name), '-v']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='backslashreplace')
    (args.out / 'stdout.txt').write_text(result.stdout)
    (args.out / 'stderr.txt').write_text(result.stderr)
    receipt = dict(exit_code=result.returncode, test_sha256=hashlib.sha256(original_test.read_bytes()).hexdigest(),
                   patched_deployer_sha256=hashlib.sha256(patched.read_bytes()).hexdigest(),
                   device_access=False, note='Only current-master dependencies/registry are symlinked; deployer is patched.')
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    print('regression_exit=' + str(result.returncode))
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
