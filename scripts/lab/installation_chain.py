#!/usr/bin/env python3
"""Read-only installation identity: disk aliases plus actual service mappings.

collect(board, out) uses the existing lock/boot-guarded bms Board transport.
No service is started, restarted or installed. On-demand services absent from ps
are unknown, never reported as an observed matching loader.
"""
import json
import re
import shlex
from pathlib import Path

LIBRARIES = ('libbms.z.so', 'libapk_installer.so', 'libinstalls.z.so')
PATHS = tuple(f'{directory}/{name}' for directory in
              ('/system/lib64', '/system/lib64/platformsdk') for name in LIBRARIES)
ROLES = {'foundation', 'installs', 'installd', 'bms', 'bundlemgr'}


def hashes(text):
    return {m.group(2): m.group(1) for m in
            re.finditer(r'^([0-9a-f]{64})\s+(/\S+)$', text, re.M)}


def processes(text):
    result = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and all(p.isdigit() for p in parts[:3]) and parts[3] in ROLES:
            result.append({'pid': int(parts[0]), 'role': parts[3]})
    return result


def mappings(text):
    result = {}
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6 or not fields[4].isdigit():
            continue
        path = fields[5]
        deleted = path.endswith(' (deleted)')
        if deleted:
            path = path[:-10]
        if path.startswith('/system/') and Path(path).name in LIBRARIES:
            key = (path, int(fields[4]))
            result[key] = {'path': path, 'inode': int(fields[4]), 'deleted': deleted}
    return list(result.values())


def check_loaded(row, disk, view_hash, view_inode):
    """Check mapped inode as well as /proc/root content; current disk alone is insufficient."""
    reasons = []
    if row['deleted']:
        reasons.append('deleted mapping')
    if not row['inode'] or view_inode != row['inode']:
        reasons.append('mapped inode differs from process-root file')
    if view_hash is None or view_hash != disk.get(row['path']):
        reasons.append('process-root SHA absent or differs from disk identity')
    return {'matches': not reasons, 'reasons': reasons}



def compare_expected(expected, receipt):
    """Compare all six declared aliases; observed loaders remain a separate fact.

    Never collapse service versions to one short fingerprint or treat an absent
    on-demand loader as verified. This performs no device access.
    """
    if set(expected) != set(PATHS):
        raise ValueError('installation identity must declare exactly all six service aliases')
    if any(not re.fullmatch('[0-9a-f]{64}', str(value)) for value in expected.values()):
        raise ValueError('installation identity requires full SHA256 values')
    actual = receipt.get('disk_identities', {})
    rows = [{'path': path, 'expected': expected[path], 'actual': actual.get(path),
             'matches': actual.get(path) == expected[path]} for path in PATHS]
    diff = [row for row in rows if not row['matches']]
    mismatches = receipt.get('mismatches', [])
    unknown = receipt.get('unobserved_libraries', list(LIBRARIES))
    return {'schema': 'westlake-installation-assertion/v1', 'paths': rows,
            'diff': diff, 'loaded_mismatches': mismatches,
            'unobserved_libraries': unknown,
            'disk_assertion_passed': not diff,
            'loaded_verdict': 'mismatch' if mismatches else ('unknown' if unknown else 'verified'),
            'passed': not diff and not mismatches,
            'device_access': False}


def collect(board, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _, raw = board.shell('sha256sum ' + ' '.join(shlex.quote(p) for p in PATHS), required=False)
    disk = hashes(raw)
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    (out / 'processes.txt').write_text(ps)
    services = []
    for proc in processes(ps):
        pid = proc['pid']
        rc, text = board.shell(f'cat /proc/{pid}/maps', required=False)
        (out / f'{pid}-maps.txt').write_text(text)
        service = {**proc, 'mapped': [], 'observation': 'observed' if rc == 0 else 'unknown: process exited'}
        for row in mappings(text) if rc == 0 else []:
            path = f"/proc/{pid}/root{row['path']}"
            rc, value = board.shell('sha256sum ' + shlex.quote(path) + '; stat -c %i ' + shlex.quote(path), required=False)
            view = hashes(value).get(path)
            nums = [int(s) for s in value.splitlines() if s.isdigit()]
            inode = nums[-1] if rc == 0 and nums else None
            service['mapped'].append({**row, 'process_root_sha256': view,
                                      'process_root_inode': inode, **check_loaded(row, disk, view, inode)})
        services.append(service)
    missing = sorted(set(PATHS) - set(disk))
    mismatches = [dict(pid=p['pid'], role=p['role'], **m) for p in services
                  for m in p['mapped'] if not m['matches']]
    observed_names = {Path(m['path']).name for p in services for m in p['mapped']}
    result = {'schema': 'westlake-installation-chain/v1', 'disk_identities': disk,
              'missing_disk_paths': missing, 'services': services, 'mismatches': mismatches,
              'unobserved_libraries': sorted(set(LIBRARIES) - observed_names),
              'absent_roles': sorted(ROLES - {p['role'] for p in services}),
              'verdict': 'mismatch' if missing or mismatches else
                         ('unknown' if set(LIBRARIES) - observed_names else 'verified')}
    (out / 'installation-chain.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    import argparse
    import importlib.util
    import lab_paths
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', required=True, choices=sorted(lab_paths.boards('oh')))
    p.add_argument('--lane', required=True)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--hdc-cmd')
    p.add_argument('--expected', type=Path, help='JSON with services or six path->SHA entries')
    p.add_argument('--receipt', type=Path, help='offline exact assertion of an archived installation-chain.json')
    a = p.parse_args()
    if a.receipt:
        if not a.expected:
            p.error('--receipt requires --expected')
        expected = json.loads(a.expected.read_text())
        result = compare_expected(expected.get('services', expected), json.loads(a.receipt.read_text()))
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out/'installation-assertion.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
        return 0 if result['passed'] else 1
    if not a.hdc_cmd:
        p.error('on-board collect requires --hdc-cmd')
    source = Path(__file__).resolve().parents[2]/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
    spec = importlib.util.spec_from_file_location('installation_batch', source)
    batch = importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)
    board = batch.Board(a.serial, a.hdc_cmd, str(lab_paths.tools()/'board_note.sh'), a.lane, a.out/'commands')
    board.ready()
    result = collect(board, a.out)
    if a.expected:
        expected = json.loads(a.expected.read_text())
        assertion = compare_expected(expected.get('services', expected), result)
        (a.out/'installation-assertion.json').write_text(json.dumps(assertion, indent=2)+'\n')
        result['expected_assertion'] = assertion
        if not assertion['passed']:
            result['verdict'] = 'mismatch'
    print(json.dumps(result))
    return 1 if result['verdict'] == 'mismatch' else 0


if __name__ == '__main__':
    raise SystemExit(main())
