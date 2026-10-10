#!/usr/bin/env python3
"""Fresh container compile/link of the patched runtime, not a text-only gate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', HERE.parents[2])).resolve()
IMAGE = 'sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63'
PREPARE_SHA = '5631a7f543d59edf1ea8e859731c726ae0b97f029be022e304a098162d8ea459'
CLANG_SHA = 'b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913'
BASE_SHA = '18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae'
REGISTRARS = ['_ZN7android42register_android_database_SQLiteConnectionEP7_JNIEnv',
              '_ZN7android38register_android_database_SQLiteGlobalEP7_JNIEnv',
              '_ZN7android37register_android_database_SQLiteDebugEP7_JNIEnv',
              '_ZN7android38register_android_database_CursorWindowEP7_JNIEnv']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(path):
    return str(path).replace(str(WS) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def symbols(path):
    port = module(HERE / 'collect.py', 'port_elf')
    elf = port.Elf(Path(path))
    rows = {}
    for section in elf.sections:
        if section['type'] != 11:
            continue
        strings = elf.sections[section['link']]
        for offset in range(0, section['size'], section['entsize']):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', elf.data, section['offset'] + offset)
            start = strings['offset'] + name
            end = elf.data.find(b'\0', start)
            symbol = elf.data[start:end].decode()
            if symbol:
                rows[symbol] = dict(bind=info >> 4, type=info & 15, index=index, visibility=other & 3, size=size)
    return rows


def verify(candidate, baseline):
    before, after = symbols(baseline), symbols(candidate)
    old_exports = {name for name, row in before.items() if row['index'] and row['bind'] in [1, 2]}
    exports = {name for name, row in after.items() if row['index'] and row['bind'] in [1, 2]}
    old_undefined = {name for name, row in before.items() if not row['index']}
    undefined = {name for name, row in after.items() if not row['index']}
    new_undefined = sorted(undefined - old_undefined)
    removed = sorted(old_exports - exports)
    if new_undefined or removed or any('nwfs_apply_window_geometry' in name for name in undefined):
        raise ValueError('ELF unresolved/helper or export regression: ' + repr((new_undefined, removed)))
    checked = {}
    for name in REGISTRARS:
        row = after.get(name, {})
        if row.get('bind') != 1 or row.get('type') != 2 or not row.get('index') or row.get('visibility') != 0 or row.get('size', 0) <= 8:
            raise ValueError('registrar not GLOBAL DEFAULT real function: ' + name + ' ' + repr(row))
        checked[name] = row
    return dict(exports_before=len(old_exports), exports_after=len(exports), removed=removed,
                added=sorted(exports - old_exports), new_undefined=new_undefined,
                existing_dynamic_imports=len(undefined), registrars=checked,
                meaning='No unresolved link references under -z defs/--no-undefined; normal dynamic imports remain.')


def run():
    artifact_root = HERE / '.artifacts'
    artifact_root.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='fresh-link-', dir=artifact_root))
    receipt = dict(schema='boat-runtime-fresh-build-link/v1', status='pending', board_access=False,
                   container_image=IMAGE, attempt=portable(attempt),
                   patch_sha256=sha(HERE / 'u13-geometry-draft.patch'), steps=[])
    receipt_path = attempt / 'receipt.json'

    def step(argv, name, env=None):
        process = subprocess.run(argv, capture_output=True, env=env)
        stdout, stderr = attempt / (name + '.stdout.txt'), attempt / (name + '.stderr.txt')
        stdout.write_bytes(process.stdout)
        stderr.write_bytes(process.stderr)
        receipt['steps'].append(dict(argv=[portable(arg) for arg in argv], exit=process.returncode,
            stdout=portable(stdout), stdout_sha256=sha(stdout), stderr=portable(stderr), stderr_sha256=sha(stderr)))
        if process.returncode:
            raise RuntimeError(name + ' rc=' + str(process.returncode) + ': ' + process.stderr.decode(errors='replace')[-1500:] + '\nraw=' + portable(stdout))
        return process.stdout

    try:
        inspection = step(['docker', 'image', 'inspect', 'a2hlab-build:24.04', '--format', '{{.Id}}'], 'image')
        if inspection.decode().strip() != IMAGE:
            raise ValueError('container image identity drift')
        prepare = WS / 'westlake-harness/benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py'
        if sha(prepare) != PREPARE_SHA:
            raise ValueError('cold preparation tool SHA drift')
        cold = attempt / 'cold'
        module(prepare, 'cold_prepare').prepare(WS, cold)
        receipt['preparation'] = dict(path=portable(prepare), sha256=sha(prepare))
        port = module(HERE / 'collect.py', 'geometry_transform')
        source = HERE / 'source/android_graphics_compat_shim.cpp'
        patched = attempt / 'android_graphics_compat_shim.cpp'
        transformed = port.transform(source.read_text())
        if port.patch_text(source.read_text()) != (HERE / 'u13-geometry-draft.patch').read_text():
            raise ValueError('draft does not match the tested transform')
        patched.write_text(transformed)
        receipt['compiled_source_sha256'] = sha(patched)
        recipe = cold / 'recipe.sh'
        text = recipe.read_text()
        original = str(WS / port.SOURCE)
        if text.count(original) != 1:
            raise ValueError('geometry compile source anchor not unique')
        recipe.write_text(text.replace(original, str(patched)))
        toolchain = WS / 'westlake-harness-bms-deploy/bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain'
        compiler = toolchain / 'bin/clang-15'
        if sha(compiler) != CLANG_SHA:
            raise ValueError('frozen clang identity drift')
        receipt['clang'] = dict(path=portable(compiler), sha256=sha(compiler))
        log = attempt / 'build.log'
        argv = [str(WS / 'westlake-inputs/tools/dockbuild.sh'), 'run', '--', 'bash', str(cold / 'run.sh')]
        env = os.environ.copy()
        env['WORKSPACES'] = str(WS)
        env['DOCKBUILD_IMAGE'] = IMAGE
        env['DOCKBUILD_MOUNTS'] = ':'.join(str(WS / name) for name in ['westlake-harness-bms-deploy', 'westlake-harness-t3', HERE.parents[1].name])
        command = 'set -o pipefail; ' + shlex.join(argv) + ' 2>&1 | tee ' + shlex.quote(str(log))
        step(['/bin/bash', '-c', command], 'container-build', env)
        receipt['build_log'] = dict(path=portable(log), sha256=sha(log))
        candidate = cold / 'runtime-out/liboh_android_runtime.so'
        baseline = WS / port.ARTIFACTS['187'][0]
        if sha(baseline) != BASE_SHA:
            raise ValueError('baseline ELF identity drift')
        receipt['candidate'] = dict(path=portable(candidate), sha256=sha(candidate))
        receipt['baseline'] = dict(path=portable(baseline), sha256=sha(baseline))
        receipt['elf_checks'] = verify(candidate, baseline)
        receipt['link_flags'] = ['-Wl,-z,defs', '-Wl,--no-allow-shlib-undefined', '-Wl,--no-undefined']
        for flag in receipt['link_flags']:
            if flag not in recipe.read_text():
                raise ValueError('strict link flag missing: ' + flag)
        receipt['status'] = 'pass'
        return receipt
    except Exception as error:
        receipt['status'] = 'fail'
        receipt['error'] = portable(str(error))
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print('BUILD-LINK receipt=' + portable(receipt_path) + ' status=' + receipt['status'])


if __name__ == '__main__':
    run()
