#!/usr/bin/env python3
"""Assemble disabled t5 providers from explicit reviewed profiles and archives."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(__import__('os').environ.get('WORKSPACES', str(HERE.parents[2])))
MAIN = WS / 'westlake-harness'
ARCHIVE_INDEX = MAIN / 'benchmark/2026-10-12-toutiao-recovery-readonly/archive-1950/index.json'
APK_INVENTORY = MAIN / 'benchmark/2026-10-12-toutiao-recovery-readonly/package-inventory-1945/local-archives.json'
SCHEMA = 'demo-restore-deployment/v1'

# Real cross-board constraints observed in the pinned materials (data, not code):
CROSS_BOARD = {
    'archive_serial': '61b0657200000000000000000324012c',
    'provider_layers': ['u13', 'toutiao-route-b'],
    'constraints': [
        'sealed file corpus is byte-identical across the three boards per the 10-10 identity record, but the ARCHIVE itself was read from 61b; restoring on 5cd/5ea requires the outer loop to accept cross-board provenance explicitly',
        'U13 appspawn sandbox UIDs are per-board per-install (2001xxxx ranges in verified_apps); providers must never hardcode a UID — resolve at execute time from the deployment+seal',
        'Route B runs under the imehost HAP sandbox (org.westlake.imehost); its executor is a t0-owned parameter, not wired here',
        'rollback programs assume the same mount/label contract as install (relabel-before-bind); a board whose labels drift needs the sepolicy gate re-run first',
    ],
}


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def build_u13_candidate(seal_path: Path, route_b_executor=None, index_path=None, u13_profile=None):
    seal = json.loads(Path(seal_path).read_text())
    idx = json.loads(Path(index_path or ARCHIVE_INDEX).read_text())
    by_target = {f['target']: {'path': f['source'], 'sha256': f['sha256']} for f in idx['files']}
    profile = dict(u13_profile or {})
    apk_inventory = json.loads(APK_INVENTORY.read_text())
    archived_apks = {p['package']: p for p in apk_inventory}
    for pkg in seal['packages']:
        archive = archived_apks.get(pkg['package'])
        if archive and archive['sha256'] == pkg['apk_sha256']:
            by_target[pkg['apk_path']] = {'path': archive['source'], 'sha256': archive['sha256']}
    for row in profile.pop('additional_sources', []):
        by_target[row['target']] = row['source']
    expected = {}
    for members in seal['files'].values():
        expected.update(members)
    for pkg in seal['packages']:
        expected[pkg['apk_path']] = pkg['apk_sha256']
    missing = [t for t in expected if t not in by_target or by_target[t]['sha256'] != expected[t]]
    if missing:
        print(f'REFUSED archive does not cover the seal: {len(missing)} targets missing/SHA-drift: {missing[:3]}', file=sys.stderr)
        return None
    files = [{'target': t, 'mode': 'restore', 'source': dict(by_target[t])} for t in sorted(expected)]
    # target split per t5 semantics: overlay-group targets belong to the Route B
    # layer; the U13 layer owns the base corpus (runtime/boot/installation/APKs)
    route_b_targets = set(seal['files'].get('overlays', {}))
    if route_b_executor:
        route_b_targets.update(route_b_executor.get('targets', []))
    route_b_targets = sorted(route_b_targets)
    if not set(route_b_targets).issubset(expected):
        raise ValueError('Route B targets outside seal')
    u13_targets = sorted(set(expected) - set(route_b_targets))
    pending = []
    def local_pin(name):
        p = HERE / name
        return {'path': str(p), 'sha256': digest(p)}
    provider = dict(profile, layer='u13', interpreter='python3',
                    program=local_pin('u13_provider.py'), common=local_pin('provider_common.py'),
                    targets=u13_targets)
    apk = provider.get('apk_install')
    if isinstance(apk, dict):
        provider['apk_install'] = dict(apk, program=local_pin('apk_provider.py'), entry=local_pin('missing_apk_entry.py'),
                                       common=local_pin('provider_common.py'))
    for field in ('executor', 'rollback', 'boot_id', 'serial', 'transport', 'apk_install'):
        if not provider.get(field):
            pending.append('u13 reviewed profile missing ' + field)
    providers = [provider]
    if route_b_executor:
        rb = dict(route_b_executor)
        program = rb.pop('program', None)
        if program is None and rb.get('path'):
            program = {'path': rb.pop('path'), 'sha256': rb.pop('sha256')}
        if not rb.get('rollback'):
            pending.append('toutiao-route-b reviewed rollback pin missing')
        providers.append(dict(rb, layer='toutiao-route-b',
                              interpreter=rb.get('interpreter', 'python3'),
                              program=program, targets=route_b_targets))
    else:
        pending.append('toutiao-route-b executor (t0 parameter: path+sha256+rollback)')
    return {
        'schema': SCHEMA, 'execution_enabled': False,
        'synthetic': bool(seal.get('synthetic')),
        'files': files, 'providers': providers,
        'pending': pending,
        'cross_board_constraints': CROSS_BOARD['constraints'],
        'source_index': {'path': str(index_path or ARCHIVE_INDEX),
                         'sha256': digest(Path(index_path or ARCHIVE_INDEX)), 'files': len(idx['files']), 'bytes': idx['bytes'],
                         'serial': idx['serial']},
        'apk_inventory': {'path': 'benchmark/2026-10-12-toutiao-recovery-readonly/package-inventory-1945/local-archives.json',
                          'sha256': digest(APK_INVENTORY), 'apks': len(json.loads(APK_INVENTORY.read_text()))},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seal', type=Path, required=True)
    ap.add_argument('--route-b-executor', type=Path, help='JSON {path, sha256, interpreter?, rollback?} for the t0 Route B executor (parameter)')
    ap.add_argument('--u13-profile', type=Path, help='Reviewed unified-state profile: serial/boot/transport/executor/rollback/apk_install/additional_sources')
    ap.add_argument('--index', type=Path, default=ARCHIVE_INDEX, help='archive index (default: real archive-1950)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        print(f'ERROR output already exists, refusing to overwrite: {a.out}', file=sys.stderr)
        return 2
    def read_profile(path):
        def relocate(value):
            if isinstance(value, dict):
                out = {k: relocate(v) for k, v in value.items()}
                for key in ('path', 'input_root'):
                    v = out.get(key)
                    if isinstance(v, str) and not v.startswith('$WORKSPACES/') and not Path(v).is_absolute():
                        out[key] = str((path.parent / v).resolve())
                return out
            if isinstance(value, list):
                return [relocate(v) for v in value]
            return value
        return relocate(json.loads(path.read_text()))
    rb = None
    if a.route_b_executor:
        if not a.route_b_executor.is_file():
            print(f'ERROR route-b executor json not found: {a.route_b_executor}', file=sys.stderr)
            return 2
        rb = read_profile(a.route_b_executor)
    cand = build_u13_candidate(a.seal, rb, a.index, read_profile(a.u13_profile) if a.u13_profile else None)
    if cand is None:
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(cand, ensure_ascii=False, indent=1) + '\n')
    n = len(cand['files'])
    print(f'wrote {a.out}: {n} sealed targets from archive-1950, U13 Python provider (unified verify + APK delta), execution_enabled=false'
          + (', Route B parameter wired' if rb else ', Route B pending as parameter'))
    print('cross-board constraints:')
    for c in CROSS_BOARD['constraints']:
        print('  - ' + c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
