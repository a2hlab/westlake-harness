#!/usr/bin/env python3
"""U13 signing reference = U10.1T8 reference + the 5 U12 window-4 lit gains + itsdicey re-signed lit.

    build_reference.py [--out <dir>] [--no-sheet]

The U13 baseline is U12's 122-lit state: the U10.1T8 116-lit baseline, plus 5 keys that U12 window 4 signed lit
(fd-client + the 4 cv2 gains libresudoku/clipboardeditor/packlist/notepad, all dead on U10.1T8), plus
cv2-com-emmanuelmess-itsdicey, re-signed lit (cb7e105ffa; its correct idle screen is black by design,
DiceView.onDraw drawARGB(255,0,0,0) -- U10.1T8 had scored it alive-black-content). 116 + 5 + 1 = 122 lit.

This is an OVERLAY on the landed U10.1T8 reference (benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference): the grid
order and the 116 lit tiles are unchanged ("116 keys keep their original t20"); only the 6 changed keys move. The 5
gains take their t20 from the U12 window-4 run that signed them (benchmark/2026-10-02-u12-final-assembly/window4-signoff/
pair-sheet.json -> window_t20); itsdicey keeps its own U10.1T8 t20 (same screen, verdict only flips to lit). No t20 is
judged or substituted here -- each reference t20 is the real run t20 that carried the signed verdict.

Inputs (read-only): the U10.1T8 reference (u10-1-t8-ref-<board>.txt grid order + sources.json), and the U12 window-4
pair-sheet.json (the 5 gains' window-4 t20 + board + shard). Output: u13-ref-<board>.txt (same line format pair_sheet
parses) + u13-ref-<board>.jpeg (contact_sheet.sh --cols 7, unlabelled tiles) + sources.json (122-lit tallies +
per-key provenance). Verify with:
    scripts/lab/pair_sheet.py --run <U12 window-4 run> --reference benchmark/2026-10-03-u13-reference \
                              --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json
-> the 5 gains become auto=same (the reference t20 is that run's own t20), no-ref 0 (every discovered key resolves).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = HERE.parents[2]
# The U10.1T8 reference and the U12 assembly are landed on master; this lane's worktree branched before they landed,
# so read them from the shared master checkout (read-only).
MAIN = WS / 'westlake-harness'
U10 = MAIN / 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference'
W4PS = MAIN / 'benchmark/2026-10-02-u12-final-assembly/window4-signoff/pair-sheet.json'
W4_SIGNOFF = 'benchmark/2026-10-02-u12-final-assembly/window4-signoff/outer-signoff.json'
BOARDS = ('5ea', '5cd', '61b')
COLS = 7
REF_LINE = re.compile(r'^row \d+ col \d+\s+(\S+)\s+verdict=(\S+)\s+corpus=(\S+)\s+(.*)$')

# The 5 U12 window-4 gains (U10.1T8 dead -> U12 lit). t20 is taken from the window-4 pair-sheet.json, not hard-coded.
GAINS = ['fd-client', 'cv2-com-kaajjo-libresudoku', 'cv2-com-trianguloy-clipboardeditor',
         'cv2-com-nbossard-packlist', 'cv2-com-nononsenseapps-notepad']
ITSDICEY = 'cv2-com-emmanuelmess-itsdicey'


def ws(p):
    return str(p).replace(str(WS), '$WORKSPACES')


def expand(p):
    return p.replace('$WORKSPACES', str(WS))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def window4_gains():
    """key -> {t20 (abs), board, shard} for the 5 gains, from the U12 window-4 pair-sheet.json."""
    ps = json.loads(W4PS.read_text())
    out = {}
    for row in ps['pairs']:
        if row['key'] in GAINS:
            out[row['key']] = {'t20': row['window_t20'], 'board': row['board'], 'shard': row['shard']}
    missing = set(GAINS) - set(out)
    if missing:
        raise SystemExit(f'window-4 pair-sheet has no entry for {sorted(missing)}')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE)
    ap.add_argument('--no-sheet', action='store_true')
    a = ap.parse_args()

    base_src = json.loads((U10 / 'sources.json').read_text())['keys']
    gains = window4_gains()
    sources, tallies = {}, {}

    for board in BOARDS:
        txt = (U10 / f'u10-1-t8-ref-{board}.txt').read_text().splitlines()
        order = []                                   # (key, corpus) in grid order, from the U10.1T8 grid
        for line in txt:
            m = REF_LINE.match(line)
            if m:
                order.append((m.group(1), m.group(3)))
        header = [
            f'# U13 reference contact sheet — {board} (image: u13-ref-{board}.jpeg, cols={COLS}, {len(order)} tiles, '
            f'@MISSING@ missing). U13 baseline = U12 122-lit = U10.1T8 + 5 window-4 gains + itsdicey re-signed lit.',
            f'# Key order = U10.1T8 reference grid (= U12 plan-{board}.json shard concatenation); 116 lit tiles '
            f'unchanged. Changed on this board: see verdict=lit rows that were dead/alive-black-content on U10.1T8.',
            '# Each cell: grid row/col (matches the jpeg) + key + U13 baseline verdict + corpus + the real t20 of the '
            'run that signed it (116 keep their U10.1T8 t20; the 5 gains take their U12 window-4 t20).',
            '# Verdicts: U10.1T8 outer-signoff + U12 window-4 outer-signoff (gains) + cb7e105ffa (itsdicey). '
            'MISSING = that run has no t20; grey tile, not substituted.',
            '# pair_sheet: --reference <this dir> --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json',
        ]
        lines, imgs, missing, tally = list(header), [], 0, {}
        stage = a.out / f'.tiles-{board}'
        stage.mkdir(exist_ok=True)
        for f in stage.iterdir():
            f.unlink()

        for i, (key, corpus) in enumerate(order):
            base = base_src[key]
            if key in gains:
                g = gains[key]
                t20abs = expand(g['t20'])
                ent = {'board': board, 'plan_shard': base['plan_shard'], 'verdict': 'lit',
                       'windows': ['U12 stage-A window 4'],
                       'picked': f'U12 window-4 gain, outer-signed lit ({W4_SIGNOFF}); U10.1T8 was dead',
                       'run_board': g['board'], 'run_shard': g['shard'], 't20': ws(t20abs),
                       't20_sha256': sha(t20abs), 'source': 'u12-window4'}
            elif key == ITSDICEY:
                ent = dict(base)
                ent['verdict'] = 'lit'
                ent['picked'] = (base.get('picked', '') +
                                 ' | U13: re-signed lit (cb7e105ffa); correct idle screen is black by design '
                                 '(DiceView.onDraw drawARGB(255,0,0,0))')
                ent['source'] = 'u10-1-t8 re-sign (cb7e105ffa)'
            else:
                ent = dict(base)
                ent.setdefault('source', 'u10-1-t8')
            t20 = ent['t20']
            missing += t20 is None
            tally[ent['verdict']] = tally.get(ent['verdict'], 0) + 1
            lines.append(f'row {i // COLS + 1} col {i % COLS + 1}  {key}  verdict={ent["verdict"]}  corpus={corpus}  '
                         f'{t20 if t20 else "MISSING"}')
            sources[key] = ent
            link = stage / f'{i:03d}-{key}.jpeg'
            if t20:
                tgt = expand(t20)
                if os.path.exists(tgt):
                    link.symlink_to(tgt)
            imgs.append(str(link))

        lines[0] = lines[0].replace('@MISSING@', str(missing))
        (a.out / f'u13-ref-{board}.txt').write_text('\n'.join(lines) + '\n')
        tallies[board] = {'keys': len(order), 'lit': tally.get('lit', 0), 'missing': missing, 'verdicts': tally}
        if not a.no_sheet:
            r = subprocess.run(['bash', str(REPO / 'scripts/lab/contact_sheet.sh'),
                                str(a.out / f'u13-ref-{board}.jpeg'), '--cols', str(COLS), *imgs],
                               capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f'contact_sheet {board}: {r.stderr}')
        for f in stage.iterdir():
            f.unlink()
        stage.rmdir()

    total_lit = sum(t['lit'] for t in tallies.values())
    (a.out / 'sources.json').write_text(json.dumps({
        'baseline': 'U12 122-lit (U10.1T8 116 + 5 U12 window-4 gains + itsdicey re-signed lit)',
        'base_reference': 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference',
        'base_signoff': 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json',
        'gains_signoff': W4_SIGNOFF, 'itsdicey_resign_commit': 'cb7e105ffa',
        'gains': GAINS, 'itsdicey_relit': ITSDICEY, 'total_lit': total_lit,
        'tallies': tallies, 'keys': sources}, indent=1, ensure_ascii=False) + '\n')
    for b, t in tallies.items():
        print(b, t)
    print(f'{len(sources)} keys; lit {total_lit}; missing {sum(t["missing"] for t in tallies.values())}')
    if total_lit != 122:
        raise SystemExit(f'expected 122 lit, got {total_lit}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
