#!/usr/bin/env python3
"""Rebuild the two original installer targets in a fresh, SHA-pinned Linux kit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    lock = json.loads((HERE / 'source.lock.json').read_text())
    for entry in lock['files']:
        if sha(HERE / entry['path']) != entry['sha256']:
            raise SystemExit('source pin mismatch: ' + entry['path'])
    if sha(args.archive) != lock['archive']['sha256']:
        raise SystemExit('archive SHA mismatch')
    if args.check_only:
        print('PASS source and original full-kit archive SHA; no build performed')
        return
    if args.out is None or args.out.exists():
        raise SystemExit('--out must name a fresh directory')
    args.out.mkdir(parents=True)
    # The exact trusted archive includes original toolchain symlinks. Refuse path traversal;
    # preserve its known links only inside this explicitly new scratch kit.
    with tarfile.open(args.archive, 'r:gz') as archive:
        for entry in archive.getmembers():
            path = Path(entry.name)
            if path.is_absolute() or '..' in path.parts:
                raise SystemExit('unsafe archive member')
        archive.extractall(args.out, filter='fully_trusted')
    kit = args.out.resolve() / 'oh61-bms-kit-b79'
    compiler = kit / 'prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang-15'
    if sha(compiler) != lock['compiler_sha256']:
        raise SystemExit('compiler SHA mismatch')
    for entry in lock['files']:
        if entry['path'].startswith('source/'):
            target = kit / entry['path'][len('source/'):]
            if sha(target) != entry['sha256']:
                raise SystemExit('archive production input drift')
            target.touch()  # require real recompilation rather than accepting archived outputs
    targets = ['bundlemanager/bundle_framework/libbms.z.so',
               'bundlemanager/bundle_framework/libinstalls.z.so']
    argv = [str(kit / 'tool-bin/ninja'), '-d', 'keeprsp', '-v', '-j2', *targets]
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(compiler.parent.parent / 'lib') + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    with (args.out / 'build.stdout.txt').open('wb') as stdout, (args.out / 'build.stderr.txt').open('wb') as stderr:
        result = subprocess.run(argv, cwd=kit / 'out/wukong100', env=env, stdout=stdout, stderr=stderr)
    outputs = {name: sha(kit / 'out/wukong100' / name) for name in targets if (kit / 'out/wukong100' / name).is_file()}
    (args.out / 'receipt.json').write_text(json.dumps({'exit_code': result.returncode, 'argv': argv,
        'archive_sha256': lock['archive']['sha256'], 'outputs': outputs,
        'historical_equivalence_asserted': False}, indent=2) + '\n')
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
