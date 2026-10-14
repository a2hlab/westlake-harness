#!/usr/bin/env python3
"""Capture current launcher pages using the existing guarded BMS consumer."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
spec = importlib.util.spec_from_file_location('bms', ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
bms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bms)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--hdc', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    identity = json.loads(args.identity.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    commands = args.out / 'commands'
    commands.mkdir()
    board = bms.Board(identity['serial'], shlex.quote(args.hdc),
                      'bash ' + shlex.quote(str(ROOT / 'scripts/lab/board_note.sh')),
                      'outer(codex)', commands)
    board.ready()
    remote = '/data/local/tmp/demo-desktop-' + str(int(time.time()))
    board.shell('mkdir ' + shlex.quote(remote))
    board.shell('power-shell wakeup')
    board.shell('uitest uiInput keyEvent Home')
    time.sleep(1)
    result = {'serial': board.serial, 'boot': board.boot.strip(), 'pages': [], 'device_package_changes': 0}
    seen = set()
    # Home may retain the current page, so inspect both swipe directions.
    for direction in (-1, 1):
        repeated = 0
        direction_seen = set()
        for index in range(12):
            tag = f'page-{direction}-{index:02d}'
            tree = bms.layout(board, remote, args.out, tag)
            tiles = [a for a in bms.attributes(tree)
                     if str(a.get('id') or a.get('key') or '').startswith(bms.ICON_PREFIX)
                     and a.get('visible') in (True, 'true')]
            ids = tuple(sorted(str(a.get('id') or a.get('key')) for a in tiles))
            capture = bms.capture(board, remote + '/' + tag + '.jpeg', args.out / (tag + '.jpeg'))
            result['pages'].append({'tag': tag, 'visible_tiles': tiles, 'capture': capture})
            bms.save(args.out / 'progress.json', result)
            repeated = repeated + 1 if ids in direction_seen else 0
            direction_seen.add(ids)
            seen.add(ids)
            if repeated >= 2:
                break
            box = bms.panel(tree)
            if box is None or not ids:
                raise RuntimeError('No actionable desktop layout; retain evidence and stop')
            x1, y1, x2, y2 = box
            left, right, cy = x1 + (x2-x1)//5, x2-(x2-x1)//5, (y1+y2)//2
            start, end = (right, left) if direction == -1 else (left, right)
            board.shell(f'uitest uiInput swipe {start} {cy} {end} {cy}')
            time.sleep(0.8)
    board.shell('power-shell timeout -o 86400000', required=False)
    board.ready()
    result.update(status='CAPTURED_PENDING_VISUAL_REVIEW', unique_page_tile_sets=len(seen))
    bms.save(args.out / 'results.json', result)
    print(json.dumps({'pages': len(result['pages']), 'unique_page_tile_sets': len(seen)}))

if __name__ == '__main__':
    main()
