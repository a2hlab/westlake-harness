#!/usr/bin/env python3
"""U14 signing reference = U13 122-lit reference + the 4 U13 stage-A lit gains + fd-seal t20 refresh.

    build_reference.py [--out <dir>] [--no-sheet]

U14 baseline = U13's 122-lit + 4 gains signed lit in U13 stage-A windows 1-2:
  fd-noice (5ea, 6/6 lottery), fd-uhabits (5ea, 6/6 lottery),
  noice (61b, 1/1), cv2-com-lcdcode-moodcairns (61b, 1/1).          122 + 4 = 126 lit.
fd-seal keeps verdict=lit but its t20 is refreshed from the window-4 seal-only run (the window
paints the Seal main UI behind the guide dialog; the old reference showed a blank background).

This is an OVERLAY on the landed U13 reference (benchmark/2026-10-03-u13-reference): grid order and
the untouched lit tiles are unchanged; only the 5 changed keys move. Each gain takes its t20 from the
stage-A pair-sheet that carried the signed verdict (the last lottery run for the 6/6 keys). No t20 is
judged or substituted here -- every reference t20 is the real run t20 that carried its verdict.

Inputs (read-only): the U13 reference on master (u13-ref-<board>.txt + sources.json), the stage-A
pair-sheets under $WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan/
(window1-signoff/pair-sheet.json, window2-signoff/pair-sheet-61b.json,
window4-signoff/pair-sheet-61b-seal.json). Output: u14-ref-<board>.txt + u14-ref-<board>.jpeg
(cols 7, unlabelled tiles) + sources.json (126-lit tallies + per-key provenance) + known-answers/.
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
MAIN = WS / 'westlake-harness'                       # landed U13 reference lives on master (read-only)
SA = WS / 'westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan'
U13 = MAIN / 'benchmark/2026-10-03-u13-reference'
BOARDS = ('5ea', '5cd', '61b')
COLS = 7
REF_LINE = re.compile(r'^row \d+ col \d+\s+(\S+)\s+verdict=(\S+)\s+corpus=(\S+)\s+(.*)$')

GAINS = ['fd-noice', 'fd-uhabits', 'noice', 'cv2-com-lcdcode-moodcairns']   # U13 non-lit -> U14 lit
SEAL = 'fd-seal'                                                             # lit stays, t20 refreshed


def ws(p):
    return str(p).replace(str(WS), '$WORKSPACES')


def expand(p):
    return p.replace('$WORKSPACES', str(WS))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def picks():
    """key -> {t20 (abs), board, shard, source} from the stage-A pair-sheets that carried the signed verdict."""
    w1 = json.loads((SA / 'window1-signoff/pair-sheet.json').read_text())
    w2 = json.loads((SA / 'window2-signoff/pair-sheet-61b.json').read_text())
    w4 = json.loads((SA / 'window4-signoff/pair-sheet-61b-seal.json').read_text())
    out = {}
    for key in ('fd-noice', 'fd-uhabits'):        # 6/6 lottery: the last run of the six
        rows = [r for r in w1['pairs'] if r['key'] == key]
        if not rows:
            raise SystemExit(f'window1 pair-sheet has no entry for {key}')
        r = rows[-1]
        out[key] = {'t20': r['window_t20'], 'board': r['board'], 'shard': r['shard'],
                    'source': 'U13 stage-A window 1 (6/6 lottery, last run)'}
    for key in ('noice', 'cv2-com-lcdcode-moodcairns'):
        r = next((r for r in w2['pairs'] if r['key'] == key), None)
        if not r:
            raise SystemExit(f'window2 61b pair-sheet has no entry for {key}')
        out[key] = {'t20': r['window_t20'], 'board': r['board'], 'shard': r['shard'],
                    'source': 'U13 stage-A window 2'}
    r = next((r for r in w4['pairs'] if r['key'] == SEAL), None)
    if not r:
        raise SystemExit('window4 seal pair-sheet has no fd-seal entry')
    out[SEAL] = {'t20': r['window_t20'], 'board': r['board'], 'shard': r['shard'],
                 'source': 'U13 stage-A window 4 (seal-only; paints main UI behind guide dialog)'}
    for k, v in out.items():
        if not Path(v['t20']).is_file():
            raise SystemExit(f"{k}: t20 missing: {v['t20']}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE)
    ap.add_argument('--no-sheet', action='store_true')
    a = ap.parse_args()

    base_src = json.loads((U13 / 'sources.json').read_text())['keys']
    picked = picks()
    sources, tallies = {}, {}

    for board in BOARDS:
        txt = (U13 / f'u13-ref-{board}.txt').read_text().splitlines()
        order = []                                    # (key, corpus) in grid order, from the U13 grid
        for line in txt:
            m = REF_LINE.match(line)
            if m:
                order.append((m.group(1), m.group(3)))
        header = [
            f'# U14 reference contact sheet — {board} (image: u14-ref-{board}.jpeg, cols={COLS}, {len(order)} tiles, '
            f'@MISSING@ missing). U14 baseline = U13 122-lit + 4 stage-A gains + fd-seal t20 refresh = 126 lit.',
            f'# Key order = U13 reference grid; unchanged tiles keep their U13 t20. Changed on this board: '
            f'verdict=lit rows marked *gain (stage-A signed) and fd-seal (t20 refreshed, verdict was already lit).',
            '# Each cell: grid row/col (matches the jpeg) + key + U14 baseline verdict + corpus + the real t20 of '
            'the run that signed it (untouched keys keep their U13 t20).',
            '# Verdicts: U13 baseline + U13 stage-A window signoffs (gains) + window-4 seal outer-signoff. '
            'MISSING = that run has no t20; grey tile, not substituted.',
        ]
        lines, imgs, missing, tally = list(header), [], 0, {}
        stage = a.out / f'.tiles-{board}'
        stage.mkdir(exist_ok=True)
        for f in stage.iterdir():
            f.unlink()

        for i, (key, corpus) in enumerate(order):
            base = base_src[key]
            if key in picked:
                p = picked[key]
                t20abs = p['t20']
                mark = ''
                if key in GAINS:
                    mark = ' *gain'
                    ent = dict(base)
                    ent.update({'verdict': 'lit', 'windows': [p['source']],
                                'picked': f'U13 stage-A gain, outer-signed lit; U13 was {base["verdict"]}',
                                'run_board': p['board'], 'run_shard': p['shard'], 't20': ws(t20abs),
                                't20_sha256': sha(t20abs), 'source': 'u13-stage-a'})
                else:                                   # fd-seal: verdict already lit, t20 refreshed
                    ent = dict(base)
                    ent.update({'windows': ent.get('windows', []) + [p['source']],
                                'picked': (base.get('picked', '') +
                                           f' | U14: t20 refreshed from {p["source"]}'),
                                'run_board': p['board'], 'run_shard': p['shard'], 't20': ws(t20abs),
                                't20_sha256': sha(t20abs), 'source': 'u13-stage-a-window4-seal'})
                    mark = ' *t20-refresh'
                t20 = ent['t20']
                missing += t20 is None
                tally[ent['verdict']] = tally.get(ent['verdict'], 0) + 1
                lines.append(f'row {i // COLS + 1} col {i % COLS + 1}  {key}  verdict={ent["verdict"]}  '
                             f'corpus={corpus}  {t20 if t20 else "MISSING"}{mark}')
                sources[key] = ent
                link = stage / f'{i:03d}-{key}.jpeg'
                if t20 and os.path.exists(expand(t20)):
                    link.symlink_to(expand(t20))
                imgs.append(str(link))
            else:
                ent = dict(base)
                ent.setdefault('source', 'u13')
                t20 = ent['t20']
                missing += t20 is None
                tally[ent['verdict']] = tally.get(ent['verdict'], 0) + 1
                lines.append(f'row {i // COLS + 1} col {i % COLS + 1}  {key}  verdict={ent["verdict"]}  '
                             f'corpus={corpus}  {t20 if t20 else "MISSING"}')
                sources[key] = ent
                link = stage / f'{i:03d}-{key}.jpeg'
                if t20 and os.path.exists(expand(t20)):
                    link.symlink_to(expand(t20))
                imgs.append(str(link))

        lines[0] = lines[0].replace('@MISSING@', str(missing))
        (a.out / f'u14-ref-{board}.txt').write_text('\n'.join(lines) + '\n')
        tallies[board] = {'keys': len(order), 'lit': tally.get('lit', 0), 'missing': missing, 'verdicts': tally}
        if not a.no_sheet:
            r = subprocess.run(['bash', str(REPO / 'scripts/lab/contact_sheet.sh'),
                                str(a.out / f'u14-ref-{board}.jpeg'), '--cols', str(COLS), *imgs],
                               capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f'contact_sheet {board}: {r.stderr}')
        for f in stage.iterdir():
            f.unlink()
        stage.rmdir()

    total_lit = sum(t['lit'] for t in tallies.values())
    src = {'baseline': 'U13 122-lit + 4 U13 stage-A gains (fd-noice/fd-uhabits/noice/moodcairns) + fd-seal t20 refresh',
           'base_reference': 'benchmark/2026-10-03-u13-reference',
           'gains': GAINS, 'seal_refresh': SEAL, 'total_lit': total_lit,
           'tallies': tallies, 'keys': sources}
    (a.out / 'sources.json').write_text(json.dumps(src, indent=1, ensure_ascii=False) + '\n')
    for b, t in tallies.items():
        print(b, t)
    print(f'{len(sources)} keys; lit {total_lit}; missing {sum(t["missing"] for t in tallies.values())}')
    if total_lit != 126:
        raise SystemExit(f'expected 126 lit, got {total_lit}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
