#!/usr/bin/env python3
"""Only compile the accepted module into an OH AArch64 ET_REL object, never link."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
STATUS = 'OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE'
SOURCE_PINS = {
    'window_module.c': '1f42a3936449b75db6c08163c21cf68882d664065705c2d2f9afd7e2c1af4707',
    'window_module.h': '28a88796febf5063e374fbc3d1d007a53f1004eafb24f46d6f925783724cbe32',
}
TOOL_PINS = {
    'llvm/bin/clang': '6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1',
    'llvm/bin/llvm-readelf': '2e8ccf494ea3ef05f10f54b3299a69253815f99f8aac8d54d32f3445725b35da',
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)

def dependencies(text):
    # clang's Make dependency format; shlex preserves backslash-escaped spaces.
    flat = text.replace('\\\n', ' ')
    require(': ' in flat, 'missing dependency target')
    names = shlex.split(flat.split(': ', 1)[1])
    paths = sorted({str(Path(x).resolve()) for x in names})
    require(bool(paths) and all(Path(x).is_file() for x in paths), 'missing dependency')
    return {x: sha(x) for x in paths}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk', default=os.environ.get('OH_SDK_NATIVE', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native'))
    parser.add_argument('--source-repo', default=str(next(p for p in HERE.parents if (p / 'scripts/lab/check_frozen.py').is_file())))
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    sdk = Path(args.sdk).expanduser().resolve()
    repo = Path(args.source_repo).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    require(not str(out).startswith(('/tmp/', '/private/tmp/')), 'persistent output required')
    out.mkdir(parents=True, exist_ok=False)
    raw = out / 'raw'
    raw.mkdir()
    receipt = {'schema': 'r14-oh-object-v1', 'status': STATUS, 'complete': False,
               'device_calls': 0, 'linked': False, 'executed_object': False,
               'production_provider_binding': False, 'recipe_sha256': sha(__file__),
               'source_pins': SOURCE_PINS, 'commands': [], 'tools': {}}
    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(name, argv):
        (raw / (name + '.command.json')).write_text(json.dumps(argv, indent=2) + '\n')
        started = time.time()
        with (raw / (name + '.stdout.txt')).open('wb') as stdout, (raw / (name + '.stderr')).open('wb') as stderr:
            try:
                process = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=120)
                rc = process.returncode
            except subprocess.TimeoutExpired:
                rc = 124
            except OSError as exc:
                stderr.write((str(exc) + '\n').encode())
                rc = 127
        (raw / (name + '.rc')).write_text(str(rc) + '\n')
        receipt['commands'].append({'name': name, 'rc': rc, 'elapsed_seconds': time.time() - started,
            'raw': {str(p.relative_to(out)): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(raw.glob(name + '.*'))}})
        save()
        require(rc == 0, name + ' failed rc=' + str(rc))
        return (raw / (name + '.stdout.txt')).read_text()
    try:
        for name, digest in SOURCE_PINS.items():
            require(sha(HERE / name) == digest, 'accepted source drift: ' + name)
        run('00-frozen', [sys.executable, str(repo / 'scripts/lab/check_frozen.py'), '--git', str(repo), '--registry', str(repo / 'knowledge/frozen/frozen.json')])
        for name, digest in TOOL_PINS.items():
            require((sdk / name).is_file(), 'SDK tool missing: ' + name)
            require(sha(sdk / name) == digest, 'SDK tool drift: ' + name)
            receipt['tools'][name] = {'path': str(sdk / name), 'sha256': digest}
        require((sdk / 'sysroot/usr/include/pthread.h').is_file(), 'SDK sysroot incomplete')
        cc = str(sdk / 'llvm/bin/clang')
        run('01-version', [cc, '--version'])
        run('02-resource-dir', [cc, '-print-resource-dir'])
        flags = ['--target=aarch64-linux-ohos', '--sysroot=' + str(sdk / 'sysroot'),
                 '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-pthread']
        source = str(HERE / 'window_module.c')
        before = dependencies(run('03-dependencies', [cc, *flags, '-M', '-MT', 'window_module.o', source]))
        require(all(str((HERE / n).resolve()) in before for n in SOURCE_PINS), 'source dependency omitted')
        receipt['dependencies_before'] = before
        save()
        obj = out / 'window_module.o'
        run('04-compile', [cc, *flags, '-MD', '-MF', str(out / 'window_module.d'), '-MT', 'window_module.o', '-c', source, '-o', str(obj)])
        after = dependencies((out / 'window_module.d').read_text())
        require(before == after, 'used header/source set or bytes changed during compile')
        for name, digest in SOURCE_PINS.items():
            require(sha(HERE / name) == digest, 'source changed during compile')
        for name, digest in TOOL_PINS.items():
            require(sha(sdk / name) == digest, 'tool changed during compile')
        run('05-readelf', [str(sdk / 'llvm/bin/llvm-readelf'), '--file-header', '--sections', '--symbols', '--relocs', str(obj)])
        elf = obj.read_bytes()
        require(len(elf) >= 64 and elf[:6] == b'\x7fELF\x02\x01', 'not little-endian ELF64')
        typ, machine = struct.unpack_from('<HH', elf, 16)
        require((typ, machine) == (1, 183), 'not AArch64 ET_REL')
        require(struct.unpack_from('<H', elf, 56)[0] == 0, 'unexpected program headers')
        receipt['elf'] = {'class': 'ELF64', 'endianness': 'little', 'type': 'ET_REL', 'type_number': typ,
                          'machine': 'AArch64', 'machine_number': machine, 'program_headers': 0}
        receipt['object'] = {'path': 'window_module.o', 'sha256': sha(obj), 'bytes': obj.stat().st_size}
        receipt['dependencies_unchanged'] = True
        receipt['layout_static_asserts'] = 'compiled successfully for target aarch64-linux-ohos'
        receipt['provider_abi'] = 'UNKNOWN_NOT_BOUND'
        receipt['complete'] = True
        save()
        print(json.dumps({'status': STATUS, 'object': receipt['object'], 'elf': receipt['elf'], 'receipt_sha256': sha(out / 'receipt.json')}))
    except Exception as exc:
        receipt['error'] = str(exc)
        save()
        print(str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
