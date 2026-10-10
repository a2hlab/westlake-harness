#!/usr/bin/env python3
"""Capture an already-installed reviewed Route B host by a real desktop click.
No provisioning, runtime change, direct aa start or process kill. Host UID
liveness is explicitly a proxy; Android Route B processes remain raw evidence.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_post_reboot as driver


def capture(round_dir):
    cfg = driver.read(round_dir / 'round.json')['special_slots']['toutiao']
    if not cfg.get('enabled') or cfg['host_package'] != 'org.westlake.imehost' or not cfg.get('identity_files'):
        raise ValueError('reviewed Route B files and exact host package must be pinned before enabling')
    batch = driver.module('foreground_batch', driver.MASTER / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
    root = round_dir / 'special-toutiao' / (time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]) / driver.SERIAL
    root.mkdir(parents=True)
    board = batch.Board(driver.SERIAL, 'hdc', str(driver.WS / 'westlake-inputs/tools/board_note.sh'), 'cx-t0', root / 'commands')
    board.ready()
    batch.preflight(board, root)
    batch.runtime_fingerprint(board, root)
    batch.boot_image_fingerprint(board, root)
    for path, digest in cfg['identity_files'].items():
        if not path.startswith(('/data/', '/system/')) or not __import__('re').fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('invalid Route B identity pin')
        _, actual = board.shell('sha256sum ' + shlex.quote(path))
        if actual.split()[0] != digest:
            raise ValueError('Route B installed artifact mismatch')
    key = 'toutiao'
    out = root / key
    out.mkdir()
    package = cfg['host_package']
    _, raw = board.shell('bm dump -n ' + package)
    (out / 'bundle.txt').write_text(raw)
    bundle = batch.parse_bundle(raw, package)
    if bundle.get('uid') is None or not bundle.get('desktop_activity'):
        raise ValueError('one queryable Route B host with desktop ability required')
    app = {'package': package, 'launch_activity': bundle['desktop_activity']}
    record = {'key': key, 'serial': driver.SERIAL, 'boot_id': board.boot, 'package': package,
              'embedded_android_package': 'com.ss.android.article.news', 'bms': bundle,
              'status': 'started', 'install': {'skipped': 'existing-reviewed-route-b'}, 'screenshots': [],
              'review': 'pending_review', 'launch_method': 'desktop', 'clicked': False,
              'liveness_attribution': 'HAP host UID proxy, not proof Android Route B child survived'}
    remote = '/data/local/tmp/demo-round-toutiao-' + uuid.uuid4().hex
    board.shell('mkdir ' + remote)
    before = batch.fault_files(board, out, 'before')
    try:
        batch.desktop_launch(board, app, remote, out, record)
        batch.timed_collection(board, bundle['uid'], out, remote, record, 20, [5, 20], False, 20, before)
    except batch.AppFailure as error:
        record.update(status='app_failed', error=str(error))
    finally:
        record['finished_at'] = time.time()
        batch.save(out / 'record.json', record)
        batch.save(root / 'summary.json', {'records': [record], 'review': 'pending_review'})
        batch.write_facts(root)
    # The special is not part of the 128 denominator and must not kill its watchdog/spawner.
    print((root / 'facts.txt').read_text(), end='')
    if record['status'] not in ('captured', 'foreground_unconfirmed'):
        raise RuntimeError('Route B foreground capture failed')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--round', type=Path, required=True)
    a = ap.parse_args()
    capture(a.round.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
