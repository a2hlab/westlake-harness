#!/usr/bin/env python3
"""Outer-operated, exact-key game UI evidence; reuses the existing guarded UI path."""
import argparse
import importlib.util
import json
from pathlib import Path
import time
import uuid

REPO = Path(__file__).resolve().parents[2].parent / 'westlake-harness'
HERE = REPO / 'benchmark/2026-10-12-v1-seal-execution'
SERIAL = '61b0657200000000000000000324012c'
BOOT = '9f5af7c8-d359-4c25-99c6-63206b50cf0a'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['launch', 'tap', 'capture'])
    ap.add_argument('key')
    ap.add_argument('--x', type=int)
    ap.add_argument('--y', type=int)
    ap.add_argument('--control-text')
    ap.add_argument('--lane', choices=['outer(codex)','cx-t0'], default='outer(codex)')
    ap.add_argument('--fresh-launch', action='store_true')
    ap.add_argument('--wait', type=float, default=20)
    args = ap.parse_args()
    assert 0 <= args.wait <= 20
    assert not args.fresh_launch or args.action == 'launch'
    games = json.loads((REPO / 'benchmark/2026-10-12-v1-seal-assembly/game-tap-extraction/games.json').read_text())
    rows = games if isinstance(games, list) else games['games']
    row = next(r for r in rows if r['key'] == args.key)
    package = row['package']
    spec = importlib.util.spec_from_file_location('bms', REPO / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    root = HERE / 'game-interactions' / args.key
    out = root if args.action == 'launch' and not args.fresh_launch else root / (args.action + '-' + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    commands = out / 'commands'
    commands.mkdir()
    board = b.Board(SERIAL, '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc',
                    str(REPO / 'scripts/lab/board_note.sh'), args.lane, commands)
    board.ready()
    assert board.boot.strip() == BOOT
    remote = '/data/local/tmp/v1-game-' + uuid.uuid4().hex
    board.shell('mkdir ' + remote)
    rec = {'key': args.key, 'package': package, 'serial': SERIAL, 'boot_id': BOOT,
           'action': args.action, 'screenshots': [], 'review': 'pending_outer_visual_review',
           'automatic_consent': False, 'runtime_changes': False}
    try:
        if args.action == 'launch':
            _, raw = board.shell('bm dump -n ' + package)
            (out / 'bundle.txt').write_text(raw)
            bundle = b.parse_bundle(raw, package)
            assert bundle.get('uid') is not None and bundle.get('desktop_activity')
            rec['bms'] = bundle
            rec['launch_method'] = 'desktop'
            b.desktop_launch(board, {'package': package, 'launch_activity': bundle['desktop_activity']}, remote, out, rec)
            time.sleep(max(0, args.wait - (time.monotonic() - rec['click_monotonic'])))
        elif args.action == 'tap':
            assert args.x is not None and args.y is not None and args.control_text
            assert 0 <= args.x < 4096 and 0 <= args.y < 4096
            rec['control'] = {'text': args.control_text, 'x': args.x, 'y': args.y,
                              'basis': 'cx-t0 reviewed current screenshot under outer borrowed lock'}
            rec['screenshots'].append(b.capture(board, remote + '/before.jpeg', out / 'before.jpeg'))
            b.save(out / 'record.json', rec)
            board.shell(f'uitest uiInput click {args.x} {args.y}')
            time.sleep(2)
        rec['screenshots'].append(b.capture(board, remote + '/screen.jpeg', out / 'screen.jpeg'))
        rec['status'] = 'captured'
    finally:
        rec['finished_at'] = time.time()
        b.save(out / 'record.json', rec)
        print(out)


if __name__ == '__main__':
    main()
