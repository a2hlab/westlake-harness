#!/usr/bin/env python3
"""U10.1T8 reference set for pair_sheet: per board, the U12 plan's key order, each key's signed U10.1T8 verdict and
the real t20 of the window run that signed it.

    build_reference.py [--out <dir>] [--no-sheet]

Inputs (read-only):
  - benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json: 166 keys, verdict + `windows` (the signing windows).
  - benchmark/2026-10-02-u12-assembly/plan-{5ea,5cd,61b}.json: board ownership and key order = the shards' keys_file
    concatenation in shard order (lit-original, lit-cv2, unlit-original, unlit-cv2); corpus from the shard name.
  - the real window runs, $WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/
    window (= window1), window2, window3, window4, window5 (gains, no_change and retests), walked with
    pair_sheet.discover (the same record.json walk pair_sheet uses on a window).

t20 rule (no judgment, no substitution):
  - the signing window is the LAST entry of `windows` (an earlier window that lacked a t20 or was outvoted by a retest
    is listed first: fd-reader, toutiao, wikipedia, trickytripper);
  - a signing window without a record of the key takes the window its signed text names ("same screen as U9 (window 2
    t20)": fd-binaryeye, signed in window4 from window2's t20); nothing else is substituted;
  - a window with several runs of the key (window5 retest-1/-2) takes the first attempt whose signed text equals the
    verdict (window5-signoff/outer-signoff-retests.json `attempts`, "w5 rN: <verdict>" -> shard *-retest-N);
  - that record's t20.jpeg; a record without one -> MISSING (grey tile), never another run's t20.
Output per board: u10-1-t8-ref-<board>.txt (`row R col C  <key>  verdict=<v>  corpus=<c>  <t20 or MISSING>`, the
u9-reference line format pair_sheet parses) + u10-1-t8-ref-<board>.jpeg (contact_sheet.sh --cols 7), and
sources.json (key -> window, board run, shard, record, t20 sha256).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402
import pair_sheet  # noqa: E402

WS = lab_paths.workspaces()
SIGNOFF = REPO / 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json'
PLANS = REPO / 'benchmark/2026-10-02-u12-assembly'
RERUN = WS / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun'
RETESTS = RERUN / 'window5-signoff/outer-signoff-retests.json'
WINDOW_DIR = {'window1': 'window', 'window2': 'window2', 'window3': 'window3', 'window4': 'window4', 'window5': 'window5'}
BOARDS = ('5ea', '5cd', '61b')
COLS = 7


def ws(p):
    return str(p).replace(str(WS), '$WORKSPACES')


def window_of(label):
    """'window5-gains(no_change)' / 'window5-retests' / 'window3' -> 'window5' / 'window3'."""
    m = re.match(r'(window\d)', label)
    if not m:
        raise SystemExit(f'unknown window label {label!r}')
    return m.group(1)


def plan_order(board):
    plan = json.loads((PLANS / f'plan-{board}.json').read_text())
    order = []
    for sh in plan['shards']:
        corpus = 'cv2' if sh['name'].endswith('cv2') else 'original'
        kf = Path(pair_sheet.expand(sh['keys_file']))
        local = PLANS / 'keys' / board / kf.name           # the landed copy; must be the same file the plan names
        if kf.is_file() and kf.read_bytes() != local.read_bytes():
            raise SystemExit(f'{kf} differs from {local}')
        for line in local.read_text().splitlines():
            k = line.strip()
            if k and not k.startswith('#'):
                order.append((k, corpus, sh['name']))
    return order


def pick(key, entry, runs, retests):
    """(record dict or None, why) for the run whose t20 the signed verdict was read from."""
    win = window_of(entry['windows'][-1])
    cands = [r for r in runs[win] if r['key'] == key]
    if not cands:
        text = signed_text(win, key)
        m = re.search(r'\(window (\d) t20\)', text)
        if not m:
            return None, f'no {win} record'
        named = f'window{m.group(1)}'
        cands = [r for r in runs[named] if r['key'] == key]
        if len(cands) != 1:
            return None, f'no {win} record; signed text names {named}, {len(cands)} record(s) there'
        return cands[0], f'{named} (signed in {win}: "{text}")'
    if len(cands) == 1:
        return cands[0], win
    attempts = retests.get(key, {}).get('attempts', [])
    for a in attempts:
        m = re.match(r'w5 r(\d+):\s*(\S+)', a)
        if m and m.group(2).lower() == str(entry['verdict']).lower():
            hit = [r for r in cands if r['shard'].endswith(f'retest-{m.group(1)}')]
            if len(hit) == 1:
                return hit[0], f'{win} {hit[0]["shard"]} ({a})'
    raise SystemExit(f'{key}: {len(cands)} {win} runs and no signed attempt picks one')


def signed_text(win, key):
    """The window text the outer signed for `key` in window1-4 (window5 signoffs never point at another window)."""
    f = RERUN / f'{win}-signoff/outer-signoff.json'
    if not f.is_file():
        return ''
    e = json.loads(f.read_text()).get('keys', {}).get(key) or {}
    return str(e.get('window', ''))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE)
    ap.add_argument('--no-sheet', action='store_true')
    a = ap.parse_args()
    keys = json.loads(SIGNOFF.read_text())['keys']
    retests = json.loads(RETESTS.read_text())['keys']
    runs = {w: pair_sheet.discover(RERUN / d) for w, d in WINDOW_DIR.items()}
    seen, sources, tallies = set(), {}, {}
    for board in BOARDS:
        order = plan_order(board)
        lines = [f'# U10.1T8 reference contact sheet — {board} (image: u10-1-t8-ref-{board}.jpeg, cols={COLS}, '
                 f'{len(order)} tiles, @MISSING@ missing)',
                 f'# Key order = U12 plan-{board}.json shard concatenation '
                 f'({", ".join(dict.fromkeys(s for _, _, s in order))}).',
                 '# Each cell: grid row/col (matches the jpeg) + key + its U10.1T8 outer-signed verdict + corpus + the '
                 'real t20 of the window run that signed it.',
                 '# Verdicts: benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json (windows field -> run). MISSING = '
                 'that run has no t20; grey tile, not substituted.',
                 '# pair_sheet: --reference <this dir> --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json']
        imgs, missing, tally = [], 0, {}
        stage = a.out / f'.tiles-{board}'
        stage.mkdir(exist_ok=True)
        for f in stage.iterdir():
            f.unlink()
        for i, (key, corpus, shard) in enumerate(order):
            if key in seen:
                raise SystemExit(f'{key} in two boards\' plans')
            seen.add(key)
            entry = keys[key]
            rec, why = pick(key, entry, runs, retests)
            t20 = rec['window_t20'] if rec else None
            missing += t20 is None
            tally[entry['verdict']] = tally.get(entry['verdict'], 0) + 1
            lines.append(f'row {i // COLS + 1} col {i % COLS + 1}  {key}  verdict={entry["verdict"]}  corpus={corpus}  '
                         f'{ws(t20) if t20 else "MISSING"}')
            sources[key] = {'board': board, 'plan_shard': shard, 'verdict': entry['verdict'], 'windows': entry['windows'],
                            'picked': why, 'run_board': rec['board'] if rec else None,
                            'run_shard': rec['shard'] if rec else None, 't20': ws(t20) if t20 else None,
                            't20_sha256': sha(t20) if t20 else None}
            link = stage / f'{i:03d}-{key}.jpeg'
            if t20:
                link.symlink_to(t20)
            imgs.append(str(link))
        lines[0] = lines[0].replace('@MISSING@', str(missing))
        (a.out / f'u10-1-t8-ref-{board}.txt').write_text('\n'.join(lines) + '\n')
        tallies[board] = {'keys': len(order), 'missing': missing, 'verdicts': tally}
        if not a.no_sheet:
            r = subprocess.run(['bash', str(REPO / 'scripts/lab/contact_sheet.sh'), str(a.out / f'u10-1-t8-ref-{board}.jpeg'),
                                '--cols', str(COLS), *imgs], capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f'contact_sheet {board}: {r.stderr}')
        for f in stage.iterdir():
            f.unlink()
        stage.rmdir()
    if seen != set(keys):
        raise SystemExit(f'plan keys != signoff keys: only plan {sorted(seen - set(keys))}, only signoff {sorted(set(keys) - seen)}')
    (a.out / 'sources.json').write_text(json.dumps({'signoff': 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json',
                                                     'signoff_sha256': sha(SIGNOFF), 'tallies': tallies,
                                                     'keys': sources}, indent=1, ensure_ascii=False) + '\n')
    for b, t in tallies.items():
        print(b, t)
    print(f'{len(seen)} keys; missing {sum(t["missing"] for t in tallies.values())}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
