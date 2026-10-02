#!/usr/bin/env python3
"""Pair a window's per-key t20 with the same key's U9-signed t20, side by side, so the outer loop signs a whole
window in one look instead of hand-pairing screenshots.

    pair_sheet.py --run <window board(s) run dir> [--reference <u9-reference dir or u9-ref-<board>.txt>]
                  [--signoff <u9 outer-signoff.json>] [--out <dir>] [--cols 6] [--no-sheet]

--run auto-walks <run>/**/runner/<shard>/<serial>/<key>/record.json (skips the 'smoke' shard). For each key it
pairs the window t20 (left tile) with the U9 t20 (right tile), ordered, into ONE contact sheet (contact_sheet.sh,
--cols default 6 = 3 pairs per row; a missing image is a grey tile). It also prints one line per pair and writes a
JSON skeleton whose per-key `window_verdict` is left blank -- this tool never judges lit/white from a screenshot;
the outer fills the verdict reading the sheet.

U9 side: a u9-ref-<board>.txt (the format scripts produce in benchmark/2026-10-02-u10-1-t8-rerun/u9-reference) gives
the U9 verdict and the U9 t20 path directly; otherwise the outer-signoff.json verdict + its `runs` locate the U9 t20.
It does NOT exclude a key on how its window rendered (that is the outer's call) -- every non-smoke key with a record
is paired, camera/blocked keys included.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = HERE.parents[2]
CONTACT = HERE / 'contact_sheet.sh'
DEFAULT_REF = REPO / 'benchmark/2026-10-02-u10-1-t8-rerun/u9-reference'
DEFAULT_SIGNOFF = REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json'
SERIAL_BOARD = {'5ea34a45': '5ea', '5cd1e3dd': '5cd', '61b06572': '61b'}
U9_REF_LINE = re.compile(r'^row \d+ col \d+\s+(\S+)\s+verdict=(\S+)\s+corpus=(\S+)\s+(.*)$')


def expand(p):
    return os.path.expandvars(str(p).replace('$WORKSPACES', str(WORKSPACES)).replace('~', str(Path.home())))


def board_of(rel_parts, serial):
    """Board short name = the path part just before 'runner'; fall back to the serial prefix."""
    if 'runner' in rel_parts:
        i = rel_parts.index('runner')
        if i >= 1:
            return rel_parts[i - 1]
    return SERIAL_BOARD.get(serial[:8], serial[:8])


def discover(run):
    """Every non-smoke key that produced a record, as dicts {board, shard, serial, key, window_t20, status, phase}."""
    out = []
    for rec in sorted(run.rglob('record.json')):
        parts = rec.relative_to(run).parts
        if 'runner' not in parts:
            continue
        shard = parts[parts.index('runner') + 1] if parts.index('runner') + 1 < len(parts) else ''
        if shard == 'smoke':
            continue
        try:
            d = json.loads(rec.read_text())
        except Exception:
            continue
        key = d.get('key') or rec.parent.name
        serial = d.get('serial', '')
        if not serial or not key or rec.parent.name != key:
            continue  # a verification/probe record, not a key run
        t20 = rec.parent / 't20.jpeg'
        out.append({'board': board_of(parts, serial), 'shard': shard, 'serial': serial, 'key': key,
                    'window_t20': str(t20) if t20.is_file() else None,
                    'status': d.get('status'), 'phase': d.get('phase')})
    return out


def load_ref_board(reference, board):
    """key -> (u9_verdict, u9_t20_path or None) from a u9-ref-<board>.txt, if available."""
    ref = Path(reference)
    path = ref / f'u9-ref-{board}.txt' if ref.is_dir() else ref
    table = {}
    if not path.exists():
        return table
    for line in path.read_text().splitlines():
        m = U9_REF_LINE.match(line)
        if m:
            key, verdict, _corpus, p = m.groups()
            table[key] = (verdict, None if p.strip() == 'MISSING' else expand(p.strip()))
    return table


def load_signoff(signoff):
    path = Path(signoff)
    if not path.exists():
        return {}, {}
    d = json.loads(path.read_text())
    keys = d.get('keys', {})
    verd = {k: (v.get('verdict') if isinstance(v, dict) else v) for k, v in keys.items()} if isinstance(keys, dict) \
        else {e['key']: e.get('verdict') for e in keys}
    runs = {k: os.path.dirname(expand(v)) for k, v in d.get('runs', {}).items()}
    return verd, runs


def u9_t20_from_runs(runs, board, key):
    for label, rundir in runs.items():
        if label.startswith(board + ' '):
            cand = Path(rundir) / key / 't20.jpeg'
            if cand.is_file():
                return str(cand)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--reference', default=str(DEFAULT_REF))
    ap.add_argument('--signoff', default=str(DEFAULT_SIGNOFF))
    ap.add_argument('--out', type=Path)
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--no-sheet', action='store_true', help='listing + JSON only; skip the contact sheet (no ffmpeg)')
    a = ap.parse_args(argv)
    run = a.run.expanduser().resolve()
    if not run.is_dir():
        sys.exit(f'no such run dir: {run}')
    out = (a.out or run / 'pair-sheet').expanduser()
    out.mkdir(parents=True, exist_ok=True)

    pairs = discover(run)
    pairs.sort(key=lambda r: (r['board'], r['shard'], r['key']))
    ref_cache, (sign_verd, sign_runs) = {}, load_signoff(a.signoff)
    stage = out / 'tiles'
    for f in stage.glob('*') if stage.exists() else []:
        f.unlink()
    stage.mkdir(parents=True, exist_ok=True)

    imgs, rows = [], []
    for i, p in enumerate(pairs):
        board = p['board']
        if board not in ref_cache:
            ref_cache[board] = load_ref_board(a.reference, board)
        verdict, u9_t20 = ref_cache[board].get(p['key'], (None, None))
        if verdict is None:
            verdict = sign_verd.get(p['key'])
        if u9_t20 is None:
            u9_t20 = u9_t20_from_runs(sign_runs, board, p['key'])
        # staged symlinks so contact_sheet labels/stdout carry key+board+verdict; missing -> no link -> grey tile
        win_link = stage / f'{i:02d}a-{board}-{p["key"]}-WIN.jpeg'
        u9_link = stage / f'{i:02d}b-{board}-{p["key"]}-U9-{verdict or "none"}.jpeg'
        if p['window_t20']:
            win_link.symlink_to(p['window_t20'])
        if u9_t20:
            u9_link.symlink_to(u9_t20)
        imgs += [str(win_link), str(u9_link)]
        rows.append({'idx': i, 'board': board, 'shard': p['shard'], 'key': p['key'],
                     'u9_verdict': verdict, 'u9_t20': u9_t20, 'window_t20': p['window_t20'],
                     'window_status': p['status'], 'window_phase': p['phase'], 'window_verdict': ''})
        print(f'{i:3d}  {board:4} {p["shard"]:14} {p["key"]:34} U9={verdict or "?":18} '
              f'win_t20={"yes" if p["window_t20"] else "no":3} status={p["status"]}')
    print(f'{len(pairs)} pairs ({sum(1 for p in pairs if p["window_t20"])} with a window t20)')

    (out / 'pair-sheet.json').write_text(json.dumps(
        {'run': str(run), 'reference': str(a.reference), 'cols': a.cols,
         'note': 'window_verdict is blank on purpose; the outer fills it reading pair-sheet.jpeg (lit/white/...)',
         'pairs': rows}, indent=1, ensure_ascii=False))

    sheet = out / 'pair-sheet.jpeg'
    if a.no_sheet:
        print(f'--no-sheet: wrote {out / "pair-sheet.json"} (skipped the jpeg)')
        return 0
    r = subprocess.run(['bash', str(CONTACT), str(sheet), '--cols', str(a.cols), *imgs])
    print(f'sheet -> {sheet} (rc={r.returncode}); listing -> {out / "pair-sheet.json"}')
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
