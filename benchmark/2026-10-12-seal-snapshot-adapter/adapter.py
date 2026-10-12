#!/usr/bin/env python3
"""Offline, receipt-backed adapter to the existing seal compiler input."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SHA = re.compile(r'[0-9a-f]{64}\Z')
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*\Z')
PATH = re.compile(r'/[A-Za-z0-9_./:+@-]+\Z')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def bundle_identity(text, name):
    """BMS's nested applicationInfo has a zero placeholder version on Android."""
    value, end = json.JSONDecoder().raw_decode(text[text.index('{'):])
    require(value.get('name') == name, 'top-level bundle name mismatch')
    code, version = value.get('versionCode'), value.get('versionName')
    require(type(code) is int and code >= 0 and isinstance(version, str) and version,
            'top-level installed version missing')
    app = value.get('applicationInfo', {})
    apk = app.get('codePath', '')
    if not (isinstance(apk, str) and apk.endswith('.apk')):
        paths = {m.get('hapPath') for m in value.get('hapModuleInfos', [])
                 if m.get('moduleName') == 'entry' and m.get('hapPath')}
        require(len(paths) == 1, 'unique installed entry HAP required')
        apk = paths.pop()
    require(PATH.fullmatch(apk) and '..' not in apk.split('/'), 'invalid installed archive path')
    return dict(package=name, version_code=code, version_name=version, apk_path=apk)


def convert(folder):
    folder = Path(folder)
    capture = json.loads((folder / 'capture.json').read_text())
    receipts = capture['receipts']
    def raw(key):
        ref = receipts[key]
        expected = ('cat /proc/sys/kernel/random/boot_id' if key.startswith('boot-') else
                    'bm dump -n ' + key[7:] if key.startswith('bundle:') else
                    'param get ' + key[6:] if key.startswith('param:') else None)
        if expected is not None:
            require(ref['command'] == expected, 'receipt command mismatch: ' + key)
        else:
            tokens = ref['command'].split()
            require(tokens and tokens[0] == 'sha256sum' and len(tokens) > 1 and
                    all(PATH.fullmatch(p) and '..' not in p.split('/') for p in tokens[1:]),
                    'non-readonly hash command')
        path = (folder / ref['stdout']).resolve()
        require(path.is_relative_to(folder.resolve()), 'receipt path outside capture')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == ref['sha256'], 'receipt SHA drift: ' + key)
        require(ref['host_rc'] == 0, 'transport failed: ' + key)
        text = data.decode().replace('\r', '')
        marker = re.search(r'\nSEAL_READ_RC=(\d+)\s*\Z', text)
        require(marker is not None and marker.group(1) == '0', 'remote read failed: ' + key)
        return text[:marker.start()].strip()
    before, after = raw('boot-before'), raw('boot-after')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', before)
            and before == after, 'cross-boot or invalid boot')
    observed, raw_lines = {}, {}
    for key in capture['hash_receipts']:
        for line in raw(key).splitlines():
            match = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
            require(match is not None, 'malformed hash row')
            sha, path = match.groups()
            require(path not in observed, 'duplicate observed path')
            observed[path], raw_lines[path] = sha, line
    groups = capture['groups']
    require(set(groups) == {'runtime', 'boot', 'overlays', 'installation'}, 'four file groups required')
    files = {}
    for group, paths in groups.items():
        require(len(set(paths)) == len(paths), 'duplicate file group member')
        require(all(p in observed for p in paths), 'missing group file SHA')
        files[group] = {p: observed[p] for p in paths}
    names = capture['package_names']
    require(names and len(names) == len(set(names)), 'empty or duplicate package inventory')
    packages = []
    for name in names:
        require(NAME.fullmatch(name), 'invalid package name')
        package = bundle_identity(raw('bundle:' + name), name)
        path = package['apk_path']
        require(path in observed, 'installed archive not hashed: ' + name)
        package['apk_sha256'] = observed[path]
        packages.append(package)
    system = {key: raw('param:' + key) for key in capture['param_names']}
    require(system.get('const.ohos.fullname'), 'live system version required')
    return dict(schema='demo-seal-snapshot/v1', mode='live-readonly', serial=capture['serial'],
                synthetic=capture.get('synthetic', False),
                captured_at=capture['captured_at'], boot_before=before, boot_after=after,
                remote_write_operations=0, lock_operations=0, errors=[], files=files,
                fingerprint_lines={g: [raw_lines[p] for p in groups[g]] for g in ('runtime', 'boot')},
                system_params=system, packages=packages,
                apk_hashes={p['apk_path']: p['apk_sha256'] for p in packages},
                file_inventory_complete=True, package_inventory_complete=True,
                inventories=capture.get('inventories', []),
                collection_provenance={'capture_sha256': hashlib.sha256((folder/'capture.json').read_bytes()).hexdigest(),
                                       'scope': 'explicit full demo manifest plus active overlay hosts',
                                       'ui_accepted': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        snapshot = convert(args.capture)
        with args.out.open('x') as stream:
            json.dump(snapshot, stream, indent=2)
            stream.write('\n')
        return 0
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('REJECT ' + str(error))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
