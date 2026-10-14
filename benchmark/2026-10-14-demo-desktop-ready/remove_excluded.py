#!/usr/bin/env python3
"""Execute the explicitly reviewed 13-package exclusion through the original BMS guard."""
import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
spec = importlib.util.spec_from_file_location('bms', ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
bms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bms)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--approved', required=True, type=Path)
    p.add_argument('--identities', required=True, type=Path)
    p.add_argument('--hdc', required=True)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    plan = json.loads(args.approved.read_text())
    verified = json.loads(args.identities.read_text())
    assert plan['execution_enabled'] is True and plan['approved_by'] == 'outer(codex)'
    removals = plan['remove']
    assert len(removals) == len({x['package'] for x in removals}) == 13
    protected = {x['package'] for k in ('keep', 'protect', 'unknown_no_action') for x in plan[k]}
    assert not {x['package'] for x in removals} & protected
    checked = {x['package']: x for x in verified['rows']}
    assert all(checked[x['package']]['equal'] for x in removals)
    args.out.mkdir(parents=True, exist_ok=False)
    commands = args.out / 'commands'
    commands.mkdir()
    board = bms.Board(plan['serial'], shlex.quote(args.hdc),
                      'bash ' + shlex.quote(str(ROOT / 'scripts/lab/board_note.sh')),
                      'outer(codex)', commands)
    board.ready()
    assert board.boot.strip() == plan['boot_id']
    result = {'serial': board.serial, 'boot': board.boot.strip(), 'removed': [], 'started_at': time.time()}
    deadline = time.monotonic() + 1200
    for row in removals:
        if time.monotonic() > deadline:
            raise RuntimeError('Window deadline reached')
        package = row['package']
        local = args.out / package
        local.mkdir()
        observed = checked[package]
        rc, text = board.shell('sha256sum ' + shlex.quote(observed['path']))
        assert rc == 0 and text.split()[0] == observed['expected']
        receipt = bms.uninstall_existing(board, row, local)
        result['removed'].append({'package': package, 'key': row['key'], 'receipt': receipt})
        bms.save(args.out / 'progress.json', result)
        print(package, receipt['success_text'], flush=True)
    rc, bundles = board.shell('bm dump -a')
    (args.out / 'bundles-after.txt').write_text(bundles)
    names = {x.strip() for x in bundles.splitlines()}
    assert not {x['package'] for x in removals} & names
    assert protected <= names
    result.update(status='EXCLUDED_13_REMOVED_PROTECTED_AND_KEEP_NAMES_RETAINED', finished_at=time.time())
    bms.save(args.out / 'results.json', result)

if __name__ == '__main__':
    main()
