#!/usr/bin/env python3
"""Read-only producer for adapter.py; explicit groups, complete demo packages."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

import adapter

SERIALS = {'61b0657200000000000000000324012c',
           '5cd1e3dd00000000000000000923012c',
           '5ea34a4500000000000000001123012c'}


def collect(serial, groups, names, out, hdc='hdc', runner=subprocess.run):
    adapter.require(serial in SERIALS, 'serial outside whitelist')
    adapter.require(set(groups) == {'runtime', 'boot', 'overlays', 'installation'}, 'four groups required')
    paths = sorted({p for members in groups.values() for p in members})
    adapter.require(paths and all(adapter.PATH.fullmatch(p) and '..' not in p.split('/') for p in paths), 'unsafe/empty file inventory')
    adapter.require(names and len(set(names)) == len(names) and all(adapter.NAME.fullmatch(n) for n in names), 'invalid package inventory')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    capture = dict(serial=serial, captured_at=datetime.now().astimezone().isoformat(),
                   groups=groups, package_names=names, receipts={}, hash_receipts=[],
                   param_names=['const.ohos.fullname'], synthetic=False)

    def read(key, command):
        stem = '%03d' % len(capture['receipts'])
        wrapped = command + '; seal_read_rc=$?; printf "\\nSEAL_READ_RC=%s\\n" "$seal_read_rc"'
        result = runner([hdc, '-t', serial, 'shell', wrapped], capture_output=True, timeout=90)
        stdout, stderr = result.stdout, result.stderr
        (out/(stem+'.stdout.txt')).write_bytes(stdout)
        (out/(stem+'.stderr.txt')).write_bytes(stderr)
        capture['receipts'][key] = dict(command=command, stdout=stem+'.stdout.txt',
            stderr=stem+'.stderr.txt', host_rc=result.returncode,
            sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest())
        (out/'capture.json').write_text(json.dumps(capture, indent=2)+'\n')
        text = stdout.decode().replace('\r', '')
        match = re.search(r'\nSEAL_READ_RC=(\d+)\s*\Z', text)
        adapter.require(result.returncode == 0 and match is not None and match[1] == '0', 'read failed: '+key)
        return text[:match.start()].strip()

    before = read('boot-before', 'cat /proc/sys/kernel/random/boot_id')
    for name in names:
        observed = adapter.bundle_identity(read('bundle:'+name, 'bm dump -n '+name), name)
        paths.append(observed['apk_path'])
    paths = sorted(set(paths))
    for offset in range(0, len(paths), 20):
        key = 'hashes-%03d' % offset
        capture['hash_receipts'].append(key)
        read(key, 'sha256sum '+' '.join(paths[offset:offset+20]))
    for name in capture['param_names']:
        read('param:'+name, 'param get '+name)
    after = read('boot-after', 'cat /proc/sys/kernel/random/boot_id')
    adapter.require(before == after, 'boot changed during capture')
    snapshot = adapter.convert(out)
    (out/'snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n')
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', choices=sorted(SERIALS), required=True)
    parser.add_argument('--groups', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--extra-package', action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--hdc', default='hdc')
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        names = [a['package'] for a in manifest['apps'] if a.get('install') is not False]
        names += args.extra_package
        snapshot = collect(args.serial, json.loads(args.groups.read_text()), names, args.out, args.hdc)
        print(json.dumps(dict(packages=len(snapshot['packages']), boot=snapshot['boot_after'], ui_accepted=False)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print('REJECT '+str(error))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
