#!/usr/bin/env python3
"""Verify delivered Java inputs and run the retained source compiler in a fresh output."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--core-build', type=Path)
    parser.add_argument('--framework-build', type=Path)
    parser.add_argument('--core-extension-build', type=Path, action='append')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    lock = json.loads((HERE / 'java-source.lock.json').read_text())
    for entry in lock['files']:
        p = HERE / entry['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('Source pin differs: ' + entry['path'])
    if args.check_only:
        subprocess.run([sys.executable, str(HERE / 'manifest-tools/tools/build_westlake_java.py'), '--help'], check=True, stdout=subprocess.DEVNULL)
        print(json.dumps({'source_pins': len(lock['files']), 'import_closure': 'PASS', 'compiled': False}))
        return
    for name in ['workspace', 'core_build', 'framework_build', 'core_extension_build', 'out']:
        if getattr(args, name) is None:
            parser.error('--' + name.replace('_', '-') + ' is required for compilation')
    if args.out.exists():
        parser.error('--out must be new')
    out = args.out.absolute()
    out.mkdir(parents=True)
    command = [sys.executable, str(HERE / 'manifest-tools/tools/build_westlake_java.py'),
               '--workspace', str(args.workspace.resolve()), '--westlake-source', str(HERE / 'westlake-java'),
               '--core-build', str(args.core_build.resolve()), '--framework-build', str(args.framework_build.resolve()),
               '--out', str(out / 'classes-build')]
    for p in args.core_extension_build:
        command += ['--core-extension-build', str(p.resolve())]
    with (out / 'stdout.log').open('xb') as stdout, (out / 'stderr.log').open('xb') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr)
    receipt = {'scope': 'new Java class compilation, not historical production DEX or device acceptance',
               'source_lock_sha256': hashlib.sha256((HERE / 'java-source.lock.json').read_bytes()).hexdigest(),
               'exit_code': result.returncode, 'historical_build': False, 'device_calls': 0}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
