"""Fresh offline reports. Remote oatdump is accepted only with outer replay token."""
import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime

from prepare import HERE, MASTER, expand, load, portable, save, sha


def capture(folder, name, argv):
    raw = HERE / '.artifacts/raw' / folder / (name + '.txt')
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open('wb') as stream:
        result = subprocess.run([str(item) for item in argv], stdout=stream, stderr=subprocess.STDOUT)
    evidence = HERE / 'evidence' / folder / (name + '.txt')
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(raw.read_text(errors='backslashreplace')))
    print(f'{folder}/{name} exit={result.returncode}', flush=True)
    return {'command': portable(argv), 'exit_code': result.returncode, 'raw': portable(raw),
            'raw_sha256': sha(raw), 'evidence': portable(evidence), 'evidence_sha256': sha(evidence)}


def image_check(package, oatdump):
    sys.path.insert(0, str(MASTER / 'scripts/lab'))
    import generation_bundle
    result = generation_bundle.image_checks(package, oatdump)
    print(result['log'], end='')
    print(__import__('json').dumps(result))
    return 0 if result['G1'] and result['G2'] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-child')
    parser.add_argument('--oatdump')
    parser.add_argument('--variant', choices=['common', '61b', 'both'], default='both')
    parser.add_argument('--image-only', action='store_true')
    args = parser.parse_args()
    if args.oatdump and os.environ.get('U16_OUTER_REPLAY') != 'outer-approved':
        raise SystemExit('REFUSE: remote G2 requires outer replay token')
    if args.image_child:
        return image_check(expand(args.image_child), args.oatdump)
    surface = platform.system().lower()
    tag = surface + '-' + datetime.now().strftime('%Y%m%dT%H%M%S')
    records = []
    for variant in ['common', '61b'] if args.variant == 'both' else [args.variant]:
        composition = load(HERE / variant / 'composition.json')
        package, base = expand(composition['package']), expand(composition['content_base'])
        if sha(package / 'bundle.json') != composition['bundle_sha256'] or sha(base / 'bundle.json') != composition['content_base_sha256']:
            raise ValueError('candidate/base drift')
        folder = variant + '/' + tag
        image_command = [sys.executable, HERE / 'run_gates.py', '--image-child', str(package)]
        if args.oatdump:
            image_command += ['--oatdump', args.oatdump]
        if not args.image_only:
            records.append(capture(folder, 'rb', [sys.executable, MASTER / 'knowledge/toolchains/art-r155/check_boot_oat_rb.py',
                package / 'boot/arm64/boot.oat', '--image', package / 'boot/arm64/boot.art']))
            records.append(capture(folder, 't4b', [sys.executable, MASTER / 'knowledge/toolchains/art-r155/t4b_build_switch_gate.py',
                '--libart', package / 'native/payload/route/libart.so', '--oat', package / 'boot/arm64/boot.oat',
                '--build', HERE / 'receipts/U16-BUILD-snapshot.md',
                '--out', HERE / '.artifacts/raw' / folder / 't4b.json']))
            records.append(capture(folder, 'native', [sys.executable, MASTER / 'scripts/lab/native_predeploy.py',
                '--package', package / 'native', '--inputs', package / 'native/native-checks/native-gates.json',
                '--exceptions', MASTER / 'knowledge/gates/native-predeploy-exceptions.json', '--readelf', 'llvm-readelf']))
            records.append(capture(folder, 'static', [sys.executable, MASTER / 'scripts/lab/generation_static_checks.py',
                '--package', package, '--baseline', base, '--out', HERE / '.artifacts/raw' / folder / 'static.json']))
        records.append(capture(folder, 'image', image_command))
    save(HERE / 'gates' / (tag + '.json'), {'records': records, 'remote_executed': bool(args.oatdump),
          'execution_enabled': False, 'rollout_ready': False, 'not_production_pass': True})
    return 0 if all(row['exit_code'] == 0 for row in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
