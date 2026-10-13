#!/usr/bin/env python3
"""Offline only: compile actual 5ea installed identity into the unchanged driver index shape."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid

SERIAL = '5ea34a4500000000000000001123012c'
MANIFEST_SHA = '7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933'
SHA = re.compile(r'[a-f0-9]{64}')
MARKER = re.compile(r'\n__(?:BMS_REMOTE_RC|EXACT_READ_RC)_[a-fA-F0-9]+__([0-9]+)\s*$')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def compile_index(request_path, out):
    request_path, out = Path(request_path).resolve(), Path(out).resolve()
    req = read(request_path)
    ws = Path(os.environ['WORKSPACES']).resolve()
    def path(text):
        p = Path(str(text).replace('$WORKSPACES', str(ws)))
        return p.resolve() if p.is_absolute() else (request_path.parent / p).resolve()
    def portable(p):
        p = Path(p).resolve()
        return '$WORKSPACES/' + str(p.relative_to(ws)) if p.is_relative_to(ws) else str(p)
    def pin(p):
        return {'path': portable(p), 'sha256': digest(p)}
    def checked(binding):
        need(set(binding) == {'path', 'sha256'} and SHA.fullmatch(binding['sha256']), 'invalid full pin')
        p = path(binding['path'])
        need(p.is_file() and digest(p) == binding['sha256'], 'input SHA drift: ' + binding['path'])
        return p
    evidence = []
    def reading(binding, command):
        receipt = read(checked(binding['receipt']))
        stdout = checked(binding['stdout']).read_text()
        stderr = checked(binding['stderr']).read_text()
        argv = receipt['argv']
        need(isinstance(argv, list) and argv.count('-t') == 1, 'missing exact transport serial')
        idx = argv.index('-t')
        need(argv[idx + 1:idx + 3] == [SERIAL, 'shell'], 'foreign serial/non-shell receipt')
        shell = ' '.join(argv[idx + 3:])
        need(command in shell, 'wrong evidence command: ' + command)
        need(receipt.get('rc', receipt.get('exit_code', receipt.get('transport_rc'))) == 0,
             'transport failure')
        need(receipt.get('remote_rc', 0) == 0, 'remote failure')
        need(not stderr.strip() and '[CODE:' not in stdout and 'Connect server failed' not in stdout,
             'transport/command error is not absence')
        marker = MARKER.search(stdout)
        if '__BMS_REMOTE_RC_' in shell or '__EXACT_READ_RC_' in shell:
            need(marker is not None and int(marker[1]) == 0, 'missing/failed remote rc marker')
        if marker:
            need(int(marker[1]) == 0, 'remote rc nonzero')
            stdout = stdout[:marker.start()]
        t = receipt.get('time', receipt.get('finished', receipt.get('finished_at')))
        need(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t), 'missing capture time')
        evidence.append({k: pin(checked(v)) for k, v in binding.items()})
        return stdout.strip(), t
    def boot(binding):
        text, t = reading(binding, 'cat /proc/sys/kernel/random/boot_id')
        need(text == req['boot_id'], 'boot mismatch')
        return t
    def bundles(binding):
        text, t = reading(binding, 'bm dump -a')
        lines = text.splitlines()
        need(lines and lines[0].strip() == 'ID: 100:', 'unexpected BMS bundle output')
        names = [line.strip() for line in lines[1:] if line.strip()]
        need(all(re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+', n) for n in names), 'malformed BMS output')
        need(len(names) == len(set(names)), 'duplicate BMS package')
        return set(names), t
    def identity(binding, apps, final=False):
        doc = read(checked(binding))
        need(doc['serial'] == SERIAL and doc['boot_id'] == req['boot_id'], 'identity serial/boot differs')
        rows = doc['rows']
        need(len(rows) == 128 and len({r['key'] for r in rows}) == 128, 'identity requires unique128')
        bykey = {r['key']: r for r in rows}
        need(set(bykey) == set(apps), 'identity membership differs')
        for key, app in apps.items():
            r = bykey[key]
            need(r['package'] == app['package'] and r['expected'] == app['apk_sha256'], 'identity manifest mismatch')
            if final:
                need(r['status'] == 'MATCH' and r['actual'] == app['apk_sha256'], 'final missing/drift/unknown: ' + key)
        return bykey

    need(req['schema'] == 'verified-installed-identity-request/v1' and req['serial'] == SERIAL, 'request scope')
    need(str(uuid.UUID(req['boot_id'])) == req['boot_id'], 'invalid boot UUID')
    need(not out.exists(), 'fresh output directory required')
    manifest = checked(req['manifest'])
    need(digest(manifest) == MANIFEST_SHA, 'canonical full128 manifest required')
    members = [a for a in read(manifest)['apps'] if a.get('install') is not False]
    apps = {a['key']: a for a in members}
    need(len(members) == len(apps) == 128 and len({a['package'] for a in members}) == 128, 'full128 membership required')
    initial = identity(req['initial']['identity'], apps)
    old_bundles, old_time = bundles(req['initial']['bundles'])
    final = req['final']
    final_rows = identity(final['identity'], apps, final=True)
    start, end = boot(final['boot_before']), boot(final['boot_after'])
    need(old_time < start <= end, 'final capture must follow initial preflight')
    registered, bundle_time = bundles(final['bundles'])
    need(start <= bundle_time <= end, 'BMS outside final sameboot capture')
    need({a['package'] for a in members} <= registered, 'BMS missing manifest package')
    actual = {}
    for b in final['apk_reads']:
        text, t = reading(b, 'sha256sum')
        need(start <= t <= end, 'APK evidence outside final capture')
        for line in text.splitlines():
            match = re.fullmatch(r'([a-f0-9]{64})\s+(/data/app/el1/bundle/public/[A-Za-z0-9_.]+/android/base\.apk)', line)
            need(match is not None, 'malformed/missing APK raw line')
            h, target = match.groups()
            need(target not in actual, 'duplicate APK evidence')
            actual[target] = h
    expected = {'/data/app/el1/bundle/public/' + a['package'] + '/android/base.apk': a['apk_sha256'] for a in members}
    need(actual == expected, 'final raw APK inventory differs from exact128')
    required = {k for k, a in apps.items() if initial[k]['status'] != 'MATCH' or initial[k]['actual'] != a['apk_sha256'] or a['package'] not in old_bundles}
    installations = req['installations']
    need(len({r['key'] for r in installations}) == len(installations), 'duplicate installation record')
    need({r['key'] for r in installations} == required, 'missing/extra changed-key installation record')
    installed = {}
    for item in installations:
        key = item['key']; app = apps[key]; record_path = checked(item['record']); r = read(record_path)
        need(r['serial'] == SERIAL and r['key'] == key and r['package'] == app['package'] and r['apk_sha256'] == app['apk_sha256'], 'foreign/stale installation identity')
        need(r.get('boot_id', req['boot_id']) == req['boot_id'], 'installation boot differs')
        need(r.get('status') == 'installed' and r.get('install_only') is True and r.get('bms', {}).get('queryable') is True, 'not a verified actual installed record')
        install = r['install']
        need(install.get('return_code') == 0 and install.get('success_text') is True and 'skipped' not in install, 'installation failed/skipped')
        first = boot(item['boot_before']); last = boot(item['boot_after'])
        text, when = reading(item['install_command'], 'bm install')
        output = checked(item['output'])
        need(path(install['output']) == output and output.read_text().strip() == text, 'install output does not match original record/command')
        need('install bundle successfully.' in text, 'actual install success text missing')
        need(old_time < first <= when <= last <= r['finished_at'] < start, 'install is not between preflight and final capture')
        installed[key] = {'record': pin(record_path), 'output': pin(output), 'boot_evidence': [item['boot_before'], item['boot_after']], 'install_command': item['install_command']}

    # Validation completes before any successful index or per-member evidence is written.
    out.mkdir(parents=True)
    (out / 'records').mkdir()
    index = {}
    request_pin = pin(request_path)
    for key, app in apps.items():
        basis = 'existing-installation-observed'
        if key in installed:
            basis = 'upgraded-installation' if initial[key]['status'] == 'DRIFT' else 'new-installation'
        doc = {'schema': 'verified-installed-identity/v1', 'key': key, 'package': app['package'], 'serial': SERIAL,
               'boot_id': req['boot_id'], 'apk_sha256': app['apk_sha256'], 'status': 'verified-installed-identity',
               'basis': basis, 'installation_performed': key in installed, 'request': request_pin,
               'manifest': req['manifest'], 'final_apk_identity': final['identity'],
               'actual_installation': installed.get(key), 'UI_verdict': 'not_checked'}
        p = out / 'records' / (key + '.json'); save(p, doc)
        index[key] = {'success': True, 'apk_sha256': app['apk_sha256'], 'record': portable(p),
                      'record_sha256': digest(p), 'status': 'verified-installed-identity', 'error': None,
                      'serial': SERIAL, 'boot_id': req['boot_id'], 'package': app['package'], 'basis': basis}
    save(out / 'install-index.json', index)
    save(out / 'receipt.json', {'schema': 'verified-installed-identity-compilation/v1', 'status': 'VERIFIED',
         'serial': SERIAL, 'boot_id': req['boot_id'], 'members': 128, 'existing_observed': 128-len(installed),
         'actual_installs_or_upgrades': len(installed), 'request': request_pin, 'compiler': pin(Path(__file__)),
         'index': pin(out / 'install-index.json'), 'evidence': evidence, 'device_calls': 0, 'UI_verdict': 'not_checked'})
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--request', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    try:
        result = compile_index(args.request, args.out)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'error': str(exc), 'device_calls': 0}))
        return 2
    print(json.dumps({'status': 'VERIFIED', 'members': len(result), 'device_calls': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
