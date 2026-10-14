#!/usr/bin/env python3
"""Offline fixed-input Boat transforms and original signal-box compile/link recipe.
No imports from device scripts, no device commands, no download or deployment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent
PATCHES = [(0x761ed8, 'f40f1ef8', '11000014'),
           (0x690ac0, '808900d0', 'c0035fd6'),
           (0x67a554, 'f37bbfa9338a00d0', 'e0031f2ac0035fd6')]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(path, expected):
    if digest(path) != expected:
        raise ValueError('SHA mismatch: ' + str(path))


def sources():
    lock = json.loads((ROOT / 'source.lock.json').read_text())
    for row in lock['files']:
        require(ROOT / row['path'], row['sha256'])


def check_sdk(sdk, lock):
    for row in lock['sdk_files']:
        require(sdk / row['path'], row['sha256'])


def patch_exact(path, offset, before, after):
    old, new = bytes.fromhex(before), bytes.fromhex(after)
    if len(old) != len(new):
        raise ValueError('patch length differs')
    with Path(path).open('r+b') as stream:
        stream.seek(offset)
        if stream.read(len(old)) != old:
            raise ValueError('patch preimage mismatch at ' + hex(offset))
        stream.seek(offset)
        stream.write(new)


class Execution:
    def __init__(self, args):
        self.out = args.out.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.rows = []
        self.aliases = [(str(ROOT), '$SOURCE'), (str(self.out), '$OUT')]
        for field, token in [('sdk', '$OH_SDK'), ('apk', '$BOAT_APK'), ('patchelf', '$PATCHELF')]:
            value = getattr(args, field, None)
            if value:
                self.aliases.append((str(value.resolve()), token))

    def portable(self, value):
        text = str(value)
        for actual, token in sorted(self.aliases, key=lambda x: -len(x[0])):
            text = text.replace(actual, token)
        return text

    def run(self, argv, label):
        argv = [str(v) for v in argv]
        stem = '%02d-%s' % (len(self.rows) + 1, label)
        started = time.time()
        stdout, stderr = self.out / (stem + '.stdout.txt'), self.out / (stem + '.stderr.txt')
        with stdout.open('wb') as so, stderr.open('wb') as se:
            proc = subprocess.run(argv, cwd=self.out, stdout=so, stderr=se, check=False,
                                  env={**os.environ, 'LC_ALL': 'C', 'LANG': 'C'})
        row = {'argv': [self.portable(v) for v in argv], 'cwd': '$OUT',
               'started_at_epoch': started, 'finished_at_epoch': time.time(), 'rc': proc.returncode,
               'stdout': {'path': stdout.name, 'sha256': digest(stdout)},
               'stderr': {'path': stderr.name, 'sha256': digest(stderr)}}
        self.rows.append(row)
        (self.out / 'commands.json').write_text(json.dumps(self.rows, indent=2) + '\n')
        print(json.dumps({'command': label, 'rc': proc.returncode}), flush=True)
        if proc.returncode:
            raise RuntimeError(label + ' returned ' + str(proc.returncode))


def transform(args, lock, ex):
    require(args.apk, lock['apk']['sha256'])
    require(args.patchelf, lock['patchelf']['sha256'])
    with zipfile.ZipFile(args.apk) as archive:
        for name, expected in lock['raw_members'].items():
            if archive.namelist().count(name) != 1:
                raise ValueError('missing/duplicate APK member: ' + name)
            target = ex.out / Path(name).name
            with archive.open(name) as source, target.open('xb') as dest:
                shutil.copyfileobj(source, dest)
            require(target, expected)
    table = ROOT / 'signal/tuanjie_signal_symbols.map'
    for name in ['libunity.so', 'libil2cpp.so']:
        target = ex.out / name
        ex.run([args.patchelf, '--rename-dynamic-symbols', table, target], name + '-rename')
        for needed in ['libwestlake_bionic_signal_box.so', 'libwestlake_bionic_pthread_bridge.so']:
            ex.run([args.patchelf, '--add-needed', needed, target], name + '-needed')
        if name == 'libunity.so':
            for offset, before, after in PATCHES:
                patch_exact(target, offset, before, after)
                print(json.dumps({'patch_offset': hex(offset), 'before': before, 'after': after}), flush=True)
    return ['libunity.so', 'libil2cpp.so']


def signal(args, lock, ex):
    check_sdk(args.sdk, lock)
    cc = args.sdk / 'llvm/bin/clang'
    common = [cc, '--target=aarch64-linux-ohos', '--sysroot=' + str(args.sdk / 'sysroot'),
              '-fPIC', '-O2', '-g', '-D__OHOS__', '-D_GNU_SOURCE']
    warning = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-stack-protector',
               '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-mno-outline-atomics',
               '-I' + str(ROOT / 'signal/include')]
    for stem, defines in [('unity_signal_box', ['-DWESTLAKE_SIGNAL_BOX_NAMESPACE=1']),
                          ('oh_musl_signal_backend', [])]:
        ex.run(common + defines + warning + ['-c', ROOT / ('signal/src/' + stem + '.c'),
               '-o', ex.out / (stem + '.o')], stem)
    unstripped = ex.out / 'libwestlake_bionic_signal_box.so.unstripped'
    ex.run([cc, '--target=aarch64-linux-ohos', '--sysroot=' + str(args.sdk / 'sysroot'),
            '-B' + str(args.sdk / 'llvm/bin'), '-fuse-ld=lld', '-shared',
            '-Wl,-z,defs', '-Wl,-z,now', '-Wl,-z,relro', '-Wl,--no-undefined',
            '-Wl,--fatal-warnings', '-Wl,--build-id=sha1', '-Wl,--hash-style=both',
            '-Wl,-soname,libwestlake_bionic_signal_box.so',
            '-Wl,--version-script=' + str(ROOT / 'signal/westlake_bionic_signal_box.map'),
            ex.out / 'unity_signal_box.o', ex.out / 'oh_musl_signal_backend.o', '-lc',
            '-o', unstripped], 'link')
    output = ex.out / 'libwestlake_bionic_signal_box.so'
    shutil.copyfile(unstripped, output)
    ex.run([args.sdk / 'llvm/bin/llvm-strip', '--strip-unneeded', output], 'strip')
    ex.run([args.sdk / 'llvm/bin/llvm-readelf', '-h', '-d', '-n', output], 'elf')
    ex.run([args.sdk / 'llvm/bin/llvm-nm', '-D', '--defined-only', output], 'exports')
    return [output.name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'transform', 'signal'])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--apk', type=Path)
    parser.add_argument('--patchelf', type=Path)
    parser.add_argument('--sdk', type=Path)
    args = parser.parse_args()
    sources()
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    if args.action == 'check':
        print('SOURCE_PINS_OK'); return 0
    if not args.out or (args.action == 'transform' and (not args.apk or not args.patchelf)) or (args.action == 'signal' and not args.sdk):
        parser.error('fresh --out and action-specific dependency paths are required')
    for field in ['apk', 'sdk', 'patchelf']:
        if getattr(args, field, None):
            setattr(args, field, getattr(args, field).absolute())
    ex = Execution(args)
    receipt = {'schema': 'boat-offline-execution/v1', 'action': args.action,
               'source_lock_sha256': digest(ROOT / 'source.lock.json'),
               'dependencies_lock_sha256': digest(ROOT / 'dependencies.lock.json'),
               'recipe_sha256': digest(Path(__file__)), 'historical_logs': 'unknown',
               'new_execution': True, 'device_calls': 0, 'outputs': []}
    rc = 1
    try:
        names = (transform if args.action == 'transform' else signal)(args, lock, ex)
        for name in names:
            actual, expected = digest(ex.out / name), lock['expected_outputs'][name]
            receipt['outputs'].append({'path': name, 'sha256': actual, 'expected_sha256': expected,
                                       'equal': actual == expected})
        rc = 0 if all(x['equal'] for x in receipt['outputs']) else 2
        receipt['status'] = 'EXACT_OUTPUT_MATCH_NEW_EXECUTION' if rc == 0 else 'BUILD_SUCCEEDED_OUTPUT_DIFFERS'
    except Exception as error:
        receipt['status'] = 'FAILED_EVIDENCE_RETAINED'
        receipt['error'] = ex.portable(error)
    finally:
        receipt.update({'rc': rc, 'commands': ex.rows})
        (ex.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt, indent=2))
    return rc


if __name__ == '__main__':
    sys.exit(main())
