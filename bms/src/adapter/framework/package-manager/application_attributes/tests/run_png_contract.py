#!/usr/bin/env python3
"""Compile and exercise the pinned production PNG/resource implementation."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mode', required=True, choices=['valid', 'rejected'])
p.add_argument('--pm-root', type=pathlib.Path, required=True)
p.add_argument('--build-dir', type=pathlib.Path, required=True)
p.add_argument('--zlib-root', type=pathlib.Path, required=True)
p.add_argument('--cc', required=True)
p.add_argument('--cxx', required=True)
p.add_argument('--g1-apk', required=True)
a = p.parse_args()
a.pm_root = a.pm_root.resolve()
a.build_dir = a.build_dir.resolve()
a.zlib_root = a.zlib_root.resolve()
codec = a.pm_root.parent.parent / 'third_party/lodepng'
pins = {
    'lodepng.cpp': 'd98e1f40d303c1038a096ebf93b413a565a91cf2c72b9d2fa5c625c4279c3cb6',
    'lodepng.h': '23c27abb06883ed98184d16d0b20771b526dca1e8e13236c2397316769c0dc8b',
    'README.md': '28e1c2cd8c013f8fc35dcb25ab6f90dc50b1646f59ce5c8aecc801eed3876791',
}
for name, expected in pins.items():
    path = codec / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f'SPC49_PINNED_CODEC_NOT_RESTORED: {name}')
out = a.build_dir / ('png-' + a.mode)
out.mkdir(parents=True, exist_ok=True)
tests = pathlib.Path(__file__).resolve().parent
includes = [a.pm_root / 'test/host_shims', a.pm_root / 'jni', codec,
            a.zlib_root / 'contrib/minizip', a.zlib_root]
sanitize = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
commands = []
def run(command, name):
    command = [str(x) for x in command]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '.log')).write_bytes(result.stdout)
    commands.append({'argv': command, 'exit_code': result.returncode,
                     'log_sha256': hashlib.sha256(result.stdout).hexdigest()})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(result.stdout.decode(errors='replace'), end='', flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
common = [a.cxx, '-std=c++17', '-Wall', '-Wextra', *sanitize,
          *['-I' + str(x) for x in includes],
          codec / 'lodepng.cpp', a.pm_root / 'jni/icon_normalize.cpp']
run([*common, tests / 'png_codec_probe.cpp', '-o', out / 'codec-probe'], 'compile-codec')
run([out / 'codec-probe', a.mode], 'codec')
if a.mode == 'valid':
    g1 = pathlib.Path(a.g1_apk)
    if not a.g1_apk or not g1.is_file() or hashlib.sha256(g1.read_bytes()).hexdigest() != '2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd':
        raise SystemExit('SPC49_ORIGINAL_G1_FIXTURE_REQUIRED')
    run([a.cc, '-std=c11', *sanitize, '-I' + str(a.zlib_root),
         '-I' + str(a.zlib_root / 'contrib/minizip'), '-c', a.zlib_root / 'contrib/minizip/zip.c',
         '-o', out / 'zip.o'], 'compile-zip')
    run([*common, a.pm_root / 'jni/apk_installer.cpp', a.pm_root / 'jni/apk_label_resolver.cpp',
         a.pm_root / 'jni/arsc_resolver.cpp', a.pm_root / 'test/test_resources_hap.cpp',
         a.build_dir / 'libapplication_attributes_manifest.a', a.build_dir / 'libapplication_attributes_core.a',
         a.build_dir / 'libparser_minizip.a', out / 'zip.o', '-lz', '-o', out / 'original-resource-test'], 'compile-resource')
    # Isolated fresh run dirs retain original generator/test argv and assertions.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='original-', dir=out) as temp:
        work = pathlib.Path(temp); fixtures = work / 'fixtures'; scratch = work / 'scratch'
        fixtures.mkdir(); scratch.mkdir()
        run(['python3', a.pm_root / 'test/make_resources_hap_fixtures.py', g1, fixtures], 'fixtures')
        run([out / 'original-resource-test', fixtures, scratch], 'original-resource')
        log = (out / 'original-resource.log').read_text()
        assert log.count('ICONLESS_APK_TEMPLATE_PLACEHOLDER') == 1, 'SPC49_ORIGINAL_PLACEHOLDER_ALARM'
        assert re.search(r'ICONLESS_APK_TEMPLATE_PLACEHOLDER.*class=(NOT_DECLARED|DECLARED_MISSING_ALL_BUCKETS)', log), 'SPC49_ORIGINAL_PLACEHOLDER_CLASS'
        assert log.count('refusing template placeholder') == 2, 'SPC49_ORIGINAL_TAMPER_ALARMS'
print('SPC49_REAL_CODEC_AND_RESOURCE_CONTRACT_PASS', a.mode)
