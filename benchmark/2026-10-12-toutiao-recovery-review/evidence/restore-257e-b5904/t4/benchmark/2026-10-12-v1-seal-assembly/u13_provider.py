#!/usr/bin/env python3
"""Standard t5 U13 provider: verify existing base, skip replay, dispatch APK delta.

No installer/reboot/replay path exists in this unified-state restoration profile.
The outer t5 driver owns authorization; execution_enabled is the dispatch gate.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import provider_common as c


def run(a):
    base, dep, seal, prov, cfg, exe = c.context(a, __file__)
    apk = prov.get('apk_install')
    if not isinstance(apk, dict):
        raise ValueError('apk_install must be a typed object')
    program = c.pinned(apk.get('program'), base, 'apk_install.program')
    for field in ('common', 'executor', 'entry', 'manifest'):
        c.pinned(apk.get(field), base, 'apk_install.' + field)
    if dep.get('execution_enabled') is not True:
        print('PREVIEW: verify unified U13 base; skip replay; invoke APK delta provider (no commands executed)')
        return 0
    out = Path(a.out)
    out.mkdir(parents=True)
    receipt = {'schema': 'u13-provider-receipt/v3', 'serial': a.serial,
               'replay_executed': False, 'installer_executed': False, 'status': 'failed'}
    try:
        _, board = c.board_for(exe, cfg, prov, a, out)
        sealed_files = {}
        for members in seal['files'].values():
            sealed_files.update(members)
        package_paths = {p['apk_path'] for p in seal['packages']}
        baseline_targets = set(prov['targets']) - package_paths
        if not baseline_targets or not baseline_targets.issubset(sealed_files):
            raise ValueError('u13 targets must be sealed base files plus owned APKs')
        expected = {p: sealed_files[p] for p in baseline_targets}
        observed = {p: c.path_hash(board, p) for p in sorted(expected)}
        receipt['base_hashes'] = observed
        if observed != expected:
            raise ValueError('base SHA drift: no replay or installer allowed in unified profile')
        controls = c.read(board, 'cat /data/westlake-demo/u13/receipt.env')
        fields = dict(line.split('=', 1) for line in controls.splitlines() if '=' in line)
        if fields.get('state') != 'READY' or fields.get('layers') != '56' or fields.get('boot_id') != prov['boot_id']:
            raise ValueError('persistent U13 receipt not current READY56')
        if c.read(board, 'if [ ! -e /data/westlake-demo/u13/DISABLED ] && [ ! -L /data/westlake-demo/u13/DISABLED ]; then echo ENABLED; else exit 42; fi') != 'ENABLED':
            raise ValueError('U13 DISABLED or unknown')
        table = c.read(board, 'cat /data/westlake-demo/u13/u13-recover-table.tsv')
        rows = [line.split('\t') for line in table.splitlines() if line.strip()]
        if len(rows) != 56 or any(len(row) not in (5, 6) for row in rows):
            raise ValueError('recover table must contain exactly 56 targets')
        targets = [row[3] for row in rows]
        if len(set(targets)) != 56:
            raise ValueError('duplicate recover target')
        mounts = c.read(board, 'cat /proc/mounts')
        mounted = {line.split()[1] for line in mounts.splitlines() if len(line.split()) == 6}
        missing = sorted(set(targets) - mounted)
        receipt['mount_targets'] = targets
        receipt['missing_mounts'] = missing
        if missing:
            raise ValueError('U13 target mounts missing: ' + ', '.join(missing))
        board.ready()
        receipt['base_status'] = 'verified-existing-skip'
        command = [sys.executable, str(program), '--seal', str(Path(a.seal).resolve()),
                   '--serial', a.serial, '--deployment', str(Path(a.deployment).resolve()),
                   '--out', str((out / 'apk').resolve())]
        r = subprocess.run(command, capture_output=True, text=True)
        (out / 'apk.stdout.txt').write_text(r.stdout)
        (out / 'apk.stderr.txt').write_text(r.stderr)
        receipt.update(command=command, apk_rc=r.returncode, status='completed' if r.returncode == 0 else 'failed')
        c.save(out / 'receipt.json', receipt)
        return r.returncode
    except Exception as e:
        receipt['error'] = str(e)
        c.save(out / 'receipt.json', receipt)
        raise


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
