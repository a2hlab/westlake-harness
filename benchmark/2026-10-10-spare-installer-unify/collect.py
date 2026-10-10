import argparse
import json
from pathlib import Path
import shlex
import subprocess

from prepare import HERE, SERIAL, fingerprint, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hdc', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    reference = json.loads((HERE / 'reference.json').read_text())
    counter = 0

    def read(command):
        nonlocal counter
        counter += 1
        result = subprocess.run([str(args.hdc), '-t', SERIAL, 'shell', command], capture_output=True,
                                text=True, encoding='utf-8', errors='backslashreplace', timeout=120)
        (args.out / f'{counter:03d}.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError('readonly command failed; do not repair board')
        return result.stdout.strip()

    boot_before = read('cat /proc/sys/kernel/random/boot_id')
    hashes = {}
    paths = sorted(reference['expected_paths'])
    for offset in range(0, len(paths), 24):
        output = read('sha256sum ' + ' '.join(map(shlex.quote, paths[offset:offset + 24])))
        for row in output.splitlines():
            digest, path = row.split(maxsplit=1)
            if path in hashes:
                raise ValueError('duplicate identity path')
            hashes[path] = digest
    for name, command in [('mounts', 'cat /proc/mounts'), ('mountinfo', 'cat /proc/self/mountinfo'),
                          ('processes', 'ps -A -o PID,PPID,UID,NAME'),
                          ('packages', 'bm dump -a'), ('ready', 'param get sys.westlake.demo.u13.ready'),
                          ('uptime', 'cat /proc/uptime'), ('init_domain', 'cat /proc/1/attr/current'),
                          ('dmesg', 'dmesg'),
                          ('selinux', 'getenforce')]:
        (args.out / (name + '.txt')).write_text(read(command) + '\n')
    boot_after = read('cat /proc/sys/kernel/random/boot_id')
    differences = {path: dict(expected=expected, actual=hashes.get(path))
                   for path, expected in reference['expected_paths'].items() if hashes.get(path) != expected}
    complete = set(hashes) == set(reference['expected_paths'])
    result = dict(serial=SERIAL, boot_read_before=boot_before, boot_read_after=boot_after, hashes=hashes,
                  identity_complete=complete, differences=differences,
                  fingerprints={kind: fingerprint(hashes, group) for kind, group in reference['reference_paths'].items()} if complete else {},
                  board_mutations=[], visual_verdict=None,
                  pending=['bind boot_before to original reboot receipt', '56 autonomous mounts and installed count',
                           'dmesg has no ServiceStart invalid:appspawn-x in this boot',
                           'actual installation-service maps/process-root aliases equal51e1 and not deleted',
                           'fresh daemon PID/PPID/UID plus parent/child single ART views', 'two exact t20 outer-signed screenshots'])
    save(args.out / 'readonly-collection.json', result)
    print(json.dumps(dict(readonly=True, serial=SERIAL, identity_complete=complete, differences=len(differences), visual_pending=True)))
    if boot_before != boot_after or not complete or differences:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
