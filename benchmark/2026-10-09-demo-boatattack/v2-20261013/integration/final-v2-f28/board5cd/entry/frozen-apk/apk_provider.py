#!/usr/bin/env python3
"""Standard t5 APK delta provider; pinned real install_one and BMS executor."""
import argparse
import json
from pathlib import Path
import re
import shlex
import sys
import provider_common as c


def package_equal(board, package):
    name = package['package']
    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_.]*', name):
        raise ValueError('invalid package name')
    # BMS may return rc=0 for absent bundles; require an explicit absence
    # diagnostic, never infer absence from a parsing/transport failure.
    rc, text = board.shell('bm dump -n ' + shlex.quote(name), required=False)
    if rc == 0 and text.strip().lower() in ('error: failed to get information of bundle', 'error: bundle not found',
                                'error: failed to get information and the parameters may be wrong.'):
        return None
    if rc:
        raise ValueError('BMS read failed rc=' + str(rc))
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[text.index('{'):])
    except ValueError as e:
        raise ValueError('unverified BMS identity: ' + name) from e
    if obj.get('name') != name or type(obj.get('versionCode')) is not int:
        raise ValueError('unverified BMS package/versionCode: ' + name)
    return str(obj['versionCode']) == str(package['version_code'])


def run(a):
    base, dep, seal, prov, cfg, exe = c.context(a, __file__, apk=True)
    entry = c.pinned(cfg.get('entry'), base, 'entry')
    manifest = c.pinned(cfg.get('manifest'), base, 'manifest')
    root = c.resolve(cfg.get('input_root', ''), base)
    if not cfg.get('input_root') or not root.is_dir():
        raise ValueError('input_root must exist')
    apps = json.loads(manifest.read_text())['apps']
    entries = {e['key']: e for e in apps}
    keys = cfg.get('keys')
    if isinstance(keys, str):
        keys = keys.split(',')
    if not isinstance(keys, list) or len(set(keys)) != len(keys) or any(k not in entries for k in keys):
        raise ValueError('keys must be unique pinned manifest keys')
    sealed = {p['package']: p for p in seal['packages']}
    selected = []
    for key in keys:
        if not re.fullmatch('[A-Za-z0-9_.-]+', key) or key in ('.', '..'):
            raise ValueError('invalid key')
        app = entries[key]
        package = sealed.get(app['package'])
        if not package or app.get('apk_sha256') != package['apk_sha256'] or package['apk_path'] not in prov['targets']:
            raise ValueError('manifest/targets differ from sealed APK: ' + key)
        selected.append((app, package))
    owned = {p['apk_path'] for p in seal['packages']} & set(prov['targets'])
    if {p['apk_path'] for _, p in selected} != owned:
        raise ValueError('APK keys must cover exactly owned sealed APKs')
    if dep.get('execution_enabled') is not True:
        print('PREVIEW: install_one for missing/drifted APKs only; no board commands')
        return 0
    out = Path(a.out)
    out.mkdir(parents=True)
    receipt = {'schema': 'apk-provider-receipt/v2', 'serial': a.serial, 'results': {}, 'status': 'failed'}
    try:
        b, board = c.board_for(exe, cfg, prov, a, out)
        mod = c.module(entry, 'pinned_install_entry')
        mod.b = b  # install_one must use the independently pinned executor.
        # Validate every local input before the first installation.
        for app, package in selected:
            resolved = b.resolve_input(root, app)
            if resolved['package'] != package['package'] or resolved['apk_sha256'] != package['apk_sha256'] or c.digest(resolved['apk']) != package['apk_sha256']:
                raise ValueError('local APK differs from sealed bytes: ' + app['key'])
        for app, package in selected:
            key = app['key']
            equal = package_equal(board, package)
            actual = c.path_hash(board, package['apk_path'])
            if equal is None and actual is not None:
                raise ValueError('BMS absence not corroborated by APK absence: ' + key)
            if equal and actual == package['apk_sha256']:
                receipt['results'][key] = {'status': 'already-equal', 'rc': 0}
                continue
            if equal is not None or actual is not None:
                raise ValueError('existing APK/package drift; missing-only policy refuses: ' + key)
            # install_one itself creates this directory; no mkdir here.
            result = mod.install_one(board, app, root, out / key, '/data/local/tmp/restore-' + key)
            actual_rc = (result.get('install') or {}).get('return_code')
            rc = actual_rc if isinstance(actual_rc, int) and actual_rc != 0 else (0 if result.get('status') == 'installed' else 1)
            receipt['results'][key] = {'rc': rc, 'install_return_code': actual_rc, 'record': result}
            if rc:
                c.save(out / 'receipt.json', receipt)
                return rc  # No later app writes after a failed install.
            if not package_equal(board, package) or c.path_hash(board, package['apk_path']) != package['apk_sha256']:
                raise ValueError('installed APK readback differs from seal: ' + key)
        board.ready()
        receipt['status'] = 'completed'
        c.save(out / 'receipt.json', receipt)
        return 0
    except Exception as e:
        receipt['error'] = str(e)
        c.save(out / 'receipt.json', receipt)
        raise  # BatchStop also aborts the batch; never continue after lost ownership.


def main():
    p = argparse.ArgumentParser()
    for key in ('seal', 'serial', 'deployment', 'out'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--lane')
    try:
        return run(p.parse_args())
    except Exception as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
