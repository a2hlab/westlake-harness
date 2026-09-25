"""Build Toutiao AOT against the frozen #38 idle-a1 framework; VM only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

COMPILER_SHA = '8f9592174aa9d3f8b8f7e0d2879d15c6407e3c2f9f839346b8a8523c4434c7e3'
APK_SHA = 'a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395'
MAP32_SHA = 'cda75da6a331c7a6d2574b5235ffce1b3d063acb0351b5941a2e7e207396e69f'
BCP_NAMES = ['core-oj', 'core-libart', 'core-icu4j', 'conscrypt', 'okhttp',
             'bouncycastle', 'apache-xml', 'framework', 'adapter-runtime-bcp']


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def check(path, expected):
    if sha(path) != expected:
        raise ValueError(f'Input hash mismatch: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--filter', choices=['verify', 'speed', 'speed-profile'], required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', args.name):
        parser.error('--name must be one directory basename')
    root = args.root.resolve()
    output = root / args.name
    if output.exists():
        parser.error(f'Output must be new: {output}')
    inputs = root / 'inputs'
    manifest = json.loads((root / 'input-files.json').read_text())
    for name, info in manifest.items():
        path = (inputs / name).resolve()
        if not path.is_relative_to(inputs):
            raise ValueError(f'Input outside frozen root: {name}')
        check(path, info['sha256'])
    compiler = root / 'tools/dex2oat'
    apk = inputs / 'toutiao.apk'
    shim = root / 'tools/libmap32bit.so'
    check(compiler, COMPILER_SHA)
    check(apk, APK_SHA)
    check(shim, MAP32_SHA)
    physical = [str(inputs / 'fw' / (name + '.jar')) for name in BCP_NAMES]
    logical = ['/system/framework/' + name + '.jar' for name in BCP_NAMES]
    cmd = [str(compiler), '--dex-file=' + str(apk),
           '--dex-location=/data/local/tmp/asx/toutiao.apk',
           '--oat-file=' + str(output / 'toutiao.odex'),
           '--oat-location=/data/local/tmp/asx/oat/arm64/toutiao.odex',
           '--output-vdex=' + str(output / 'toutiao.vdex'),
           '--app-image-file=' + str(output / 'toutiao.art'),
           '--instruction-set=arm64', '--compiler-filter=' + args.filter,
           '--boot-image=' + str(inputs / 'boot/boot.art'),
           '--runtime-arg', '-Xbootclasspath:' + ':'.join(physical),
           '--runtime-arg', '-Xbootclasspath-locations:' + ':'.join(logical),
           '--class-loader-context=PCL[]', '--compilation-reason=install',
           '--android-root=' + str(inputs), '--runtime-arg', '-Xms64m',
           '--runtime-arg', '-Xmx1024m', '-j4']
    if args.filter == 'speed-profile':
        cmd += ['--profile-file=' + str(inputs / 'baseline.prof')]
    env = dict(os.environ, LD_PRELOAD=str(shim), WESTLAKE_EXPLICIT_NULL_CHECKS='1',
               SOURCE_DATE_EPOCH='1772755200', TZ='UTC', LC_ALL='C')
    record = dict(command=cmd, compiler_sha256=sha(compiler), map32_sha256=sha(shim),
                  apk_sha256=sha(apk), framework_manifest_sha256=sha(root / 'input-files.json'),
                  explicit_null_suspend_checks=True, filter=args.filter,
                  started=time.time(), device_accepted=False)
    output.mkdir()
    record_file = output / 'build.json'
    record_file.write_text(json.dumps(record, indent=2) + '\n')
    with (output / 'build.log').open('wb') as log:
        process = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    record.update(returncode=process.returncode, elapsed_s=time.time() - record['started'],
                  artifacts={path.name: dict(bytes=path.stat().st_size, sha256=sha(path))
                             for path in output.iterdir()
                             if path.suffix in ['.odex', '.vdex', '.art']})
    record_file.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
