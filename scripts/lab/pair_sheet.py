#!/usr/bin/env python3
"""Pair a window's per-key t20 with the same key's U9-signed t20, pre-screen each pair, and contact-sheet only the
pairs the outer still has to eyeball -- so a whole window is signed in one look instead of hand-pairing screenshots.

    pair_sheet.py --run <window board(s) run dir> [--reference <u9-reference dir or u9-ref-<board>.txt>]
                  [--signoff <u9 outer-signoff.json>] [--out <dir>] [--cols 6] [--threshold 0.86] [--no-sheet]
    pair_sheet.py --selftest     # known-answer test on window3 (76 same + trickytripper different); exit 0 iff reproduced

--run auto-walks <run>/**/runner/<shard>/<serial>/<key>/record.json (skips the 'smoke' shard). For each key it pairs
the window t20 with the same key's U9 t20 and PRE-SCREENS the pair (ffmpeg only, no Pillow): a 16x16 grey average-hash
similarity after cropping the status-bar time strip, giving an `auto` verdict:
  same       -- aHash similarity >= --threshold (default 0.86; window3 margin: lowest same 0.969 vs trickytripper 0.500)
  different  -- similarity below threshold (window rendered a different screen than U9)
  no-window  -- window t20 missing, OR near-uniform AND flatter than its U9 (lost content) / a blank white render
  no-ref     -- no U9 t20 to compare against
A flat-but-lit screen is NOT no-window: it matches an equally-flat U9 by similarity. Flaky-registry keys
(knowledge/gates/flaky-keys.json) also carry a `flaky_kn` k/n lit-rate (this window's auto + signed history), with
`regression`=true when the rule (>=3 obs, 0 lit) is met.

Output: two contact sheets -- `pair-sheet-suspects.jpeg` (only auto!=same or an undecided flaky key) and
`pair-sheet-full.jpeg` (every pair, for the record) -- plus `pair-sheet.json`. The JSON pre-fills `auto`, `similarity`
and `flaky_kn`, but per-key `window_verdict` is left BLANK on purpose: this tool never judges lit/white from a
screenshot; the outer fills the verdict, now only needing to look at the suspects sheet.

U9 side: a u9-ref-<board>.txt (benchmark/2026-10-02-u10-1-t8-rerun/u9-reference) gives the U9 verdict and t20 path;
otherwise the outer-signoff.json verdict + its `runs` locate the U9 t20. Every non-smoke key with a record is paired.
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
FLAKY_JSON = REPO / 'knowledge/gates/flaky-keys.json'
SERIAL_BOARD = {'5ea34a45': '5ea', '5cd1e3dd': '5cd', '61b06572': '61b'}
U9_REF_LINE = re.compile(r'^row \d+ col \d+\s+(\S+)\s+verdict=(\S+)\s+corpus=(\S+)\s+(.*)$')

# --- perceptual pre-screen (ffmpeg only; no Pillow/imagehash) -------------------------------------------------
# Calibrated on window3 (benchmark/2026-10-02-u10-1-t8-rerun/window3-signoff, 77 outer-signed pairs: 76 "same screen
# as U9" + cv2-de-koelle-christian-trickytripper "launcher at t20" = different). See --selftest.
HASH_SIZE = 16          # 16x16 grey -> 256-bit average hash
CROP_TOP = 0.06         # drop the top status-bar strip (clock/battery) before hashing, so the time never scores as diff
SAME_THRESHOLD = 0.86   # aHash similarity >= this => auto 'same'; below => 'different'
BLANK_FLAT = 2.0        # grey stddev below this => the window is near-uniform (a candidate blank)
BLANK_REL = 0.4         # ...and it is 'no-window' only if also < BLANK_REL * the U9 stddev (it LOST content the U9 drew);
BLANK_WHITE_MEAN = 235  # ...or, with no U9 to compare, only if near-uniform AND near-white (a blank white render)


def ff_gray(path, size=HASH_SIZE, crop_top=CROP_TOP):
    """size*size grey bytes of the image with the top status-bar strip cropped, or None if ffmpeg can't read it."""
    if not path or not Path(path).is_file():
        return None
    vf = f'crop=iw:ih*{1 - crop_top:.4f}:0:ih*{crop_top:.4f},scale={size}:{size},format=gray'
    try:
        r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path),
                            '-vf', vf, '-f', 'rawvideo', '-'], capture_output=True, timeout=30)
    except Exception:
        return None
    data = r.stdout
    return data if len(data) == size * size else None


def grey_std(data):
    m = sum(data) / len(data)
    return (sum((b - m) ** 2 for b in data) / len(data)) ** 0.5


def ahash_bits(data):
    m = sum(data) / len(data)
    return [1 if b > m else 0 for b in data]


def ahash_similarity(a, b):
    """1.0 == identical average-hash; 0.0 == every bit differs."""
    if a is None or b is None:
        return None
    ba, bb = ahash_bits(a), ahash_bits(b)
    return 1.0 - sum(x != y for x, y in zip(ba, bb)) / len(ba)


def prescreen(window_t20, u9_t20, threshold=SAME_THRESHOLD):
    """auto verdict + similarity for one pair, without judging lit/white (that stays the outer's call).
    no-window: window image absent, or near-uniform AND flatter than the U9 it should match (lost content) / blank white.
    A flat-but-lit screen (e.g. a plain settings page) is NOT no-window: it matches an equally-flat U9 by similarity."""
    wd = ff_gray(window_t20)
    if wd is None:
        return {'auto': 'no-window', 'similarity': None, 'window_std': None, 'reason': 'window t20 missing/unreadable'}
    wstd = round(grey_std(wd), 2)
    wmean = sum(wd) / len(wd)
    ud = ff_gray(u9_t20)
    ustd = round(grey_std(ud), 2) if ud is not None else None
    if wstd < BLANK_FLAT and ((ud is None and wmean > BLANK_WHITE_MEAN) or (ustd is not None and wstd < BLANK_REL * ustd)):
        return {'auto': 'no-window', 'similarity': None, 'window_std': wstd,
                'reason': f'near-uniform (std {wstd}, u9 std {ustd}) -- window lost content / blank'}
    if ud is None:
        return {'auto': 'no-ref', 'similarity': None, 'window_std': wstd, 'reason': 'no U9 t20 to compare'}
    sim = round(ahash_similarity(wd, ud), 3)
    return {'auto': 'same' if sim >= threshold else 'different', 'similarity': sim, 'window_std': wstd,
            'reason': f'aHash {sim} vs threshold {threshold} (u9 std {ustd})'}


def expand(p):
    return os.path.expandvars(str(p).replace('$WORKSPACES', str(WORKSPACES)).replace('~', str(Path.home())))


# --- flaky-key k/n (lit-rate prior so the outer does not recount every window) ---------------------------------
def load_flaky(flaky_json=None):
    """Set of keys the flaky registry says flip between runs (compare rates, do not trust one run)."""
    path = flaky_json or FLAKY_JSON
    try:
        j = json.loads(path.read_text())
    except Exception as e:
        print(f'flaky-keys.json unreadable: {path} ({e})', file=sys.stderr)
        sys.exit(2)
    return {e['key'] for e in j.get('keys', []) if isinstance(e, dict) and e.get('key')}


def _verdict_is_lit(v):
    v = (v or '').lower()
    return v.startswith('lit')  # lit / lit-webview-fallback


def signoff_history(key, extra_signoffs=()):
    """Signed verdicts for `key` across every window*-signoff/outer-signoff.json under the rerun dir (+ extras).
    Returns a list of 'lit'/'white'/'dead'/... strings. Reads the `u9` field when a window text is not a verdict."""
    seen, hist = set(), []
    roots = list(REPO.glob('benchmark/*/window*-signoff/outer-signoff.json'))
    roots += [Path(expand(s)) for s in extra_signoffs]
    for sp in roots:
        rp = str(Path(sp).resolve())
        if rp in seen or not Path(sp).is_file():
            continue
        seen.add(rp)
        try:
            keys = json.loads(Path(sp).read_text()).get('keys', {})
        except Exception:
            continue
        entry = keys.get(key) if isinstance(keys, dict) else next((e for e in keys if e.get('key') == key), None)
        if not isinstance(entry, dict):
            continue
        # a window signoff records the as-run outcome in `window`; fall back to the `verdict`/`u9` field
        w = str(entry.get('window', '')).lower()
        if 'same screen as u9' in w and _verdict_is_lit(entry.get('u9')):
            hist.append('lit')
        elif entry.get('verdict'):
            hist.append(str(entry['verdict']).lower())
        elif 'launcher' in w or 'sigsegv' in w or 'crash' in w or 'blank' in w or 'white' in w:
            hist.append('white')
    return hist


def flaky_kn(key, this_auto, history, u9_verdict=None):
    """k lit / n observations for a flaky key.

    This window counts as lit ONLY when U9's own verdict for the key is lit AND this window's
    auto is 'same' (same screen as a lit U9). If U9 is not lit: same/no-window count as not-lit
    (n+1); 'different' is undecided -- not counted, kn_this='undecided' (always lands in the
    suspect sheet). regression (>=3 observations, 0 lit) only applies to U9=lit keys."""
    obs = list(history)
    kn_this = None
    if _verdict_is_lit(u9_verdict):
        obs.append('lit' if this_auto == 'same' else 'white')
        kn_this = 'lit' if this_auto == 'same' else 'not-lit'
    else:
        if this_auto == 'different':
            kn_this = 'undecided'
        else:
            obs.append('white')
            kn_this = 'not-lit'
    k = sum(1 for v in obs if _verdict_is_lit(v))
    n = len(obs)
    regression = _verdict_is_lit(u9_verdict) and n >= 3 and k == 0
    return {'k': k, 'n': n, 'rate': round(k / n, 2) if n else None,
            'regression': regression, 'observations': obs, 'kn_this': kn_this}


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


def build_rows(run, reference, signoff, threshold, flaky_json=None):
    """Discover pairs, resolve the U9 side, and pre-screen each pair (auto verdict + flaky k/n). Returns rows."""
    pairs = sorted(discover(run), key=lambda r: (r['board'], r['shard'], r['key']))
    ref_cache, (sign_verd, sign_runs) = {}, load_signoff(signoff)
    flaky = load_flaky(flaky_json)
    rows = []
    for i, p in enumerate(pairs):
        board = p['board']
        if board not in ref_cache:
            ref_cache[board] = load_ref_board(reference, board)
        verdict, u9_t20 = ref_cache[board].get(p['key'], (None, None))
        if verdict is None:
            verdict = sign_verd.get(p['key'])
        if u9_t20 is None:
            u9_t20 = u9_t20_from_runs(sign_runs, board, p['key'])
        scr = prescreen(p['window_t20'], u9_t20, threshold=threshold)
        row = {'idx': i, 'board': board, 'shard': p['shard'], 'key': p['key'],
               'u9_verdict': verdict, 'u9_t20': u9_t20, 'window_t20': p['window_t20'],
               'window_status': p['status'], 'window_phase': p['phase'],
               'auto': scr['auto'], 'similarity': scr['similarity'], 'window_std': scr['window_std'],
               'auto_reason': scr['reason'], 'flaky': p['key'] in flaky, 'flaky_kn': None,
               'window_verdict': ''}
        if p['key'] in flaky:
            row['flaky_kn'] = flaky_kn(p['key'], scr['auto'], signoff_history(p['key'], [signoff]), u9_verdict=verdict)
        rows.append(row)
    return rows


def is_suspect(row):
    """A pair the outer still has to eyeball: not a clean 'same', or a flaky key whose lit/white is undecided."""
    kn = row.get('flaky_kn') or {}
    return row['auto'] != 'same' or kn.get('kn_this') == 'undecided' or (row['flaky'] and not kn.get('regression') is True)


def stage_imgs(rows, stage, only=None):
    """Lay down labelled symlinks (WIN left, U9 right) for `rows` (or the `only` subset) -> contact_sheet inputs."""
    for f in stage.glob('*') if stage.exists() else []:
        f.unlink()
    stage.mkdir(parents=True, exist_ok=True)
    imgs = []
    for r in (rows if only is None else only):
        i, board, key = r['idx'], r['board'], r['key']
        tag = r['auto'] + (f"-k{r['flaky_kn']['k']}of{r['flaky_kn']['n']}" if r.get('flaky_kn') else '')
        win = stage / f'{i:03d}a-{board}-{key}-WIN-{tag}.jpeg'
        u9 = stage / f'{i:03d}b-{board}-{key}-U9-{r["u9_verdict"] or "none"}.jpeg'
        if r['window_t20']:
            win.symlink_to(r['window_t20'])
        if r['u9_t20']:
            u9.symlink_to(r['u9_t20'])
        imgs += [str(win), str(u9)]
    return imgs


def selftest():
    """Known-answer test against window3 (76 'same screen as U9' + trickytripper 'different'). Exit 0 iff reproduced."""
    u7 = WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun'
    run = u7 / 'window3'
    signoff = u7 / 'window3-signoff/outer-signoff.json'
    if not run.is_dir() or not signoff.is_file():
        print(f'SELFTEST SKIP: window3 inputs not present ({run})')
        return 0
    truth = json.loads(signoff.read_text()).get('keys', {})
    rows = build_rows(run.resolve(), str(DEFAULT_REF), str(DEFAULT_SIGNOFF), SAME_THRESHOLD)
    ok = bad = 0
    fails = []
    for r in rows:
        t = truth.get(r['key'])
        if not isinstance(t, dict):
            continue
        want = 'same' if 'same screen as u9' in str(t.get('window', '')).lower() else 'different'
        got = 'same' if r['auto'] == 'same' else 'different'  # no-window/no-ref count as not-same here
        if got == want:
            ok += 1
        else:
            bad += 1
            fails.append(f"{r['board']}/{r['key']}: want {want} got {r['auto']} (sim={r['similarity']})")
    print(f'SELFTEST window3: {ok} correct, {bad} wrong (threshold {SAME_THRESHOLD})')
    for f in fails:
        print('  MISS', f)
    return 0 if bad == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', type=Path)
    ap.add_argument('--reference', default=str(DEFAULT_REF))
    ap.add_argument('--signoff', default=str(DEFAULT_SIGNOFF))
    ap.add_argument('--out', type=Path)
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--threshold', type=float, default=SAME_THRESHOLD, help='aHash similarity >= => auto same')
    ap.add_argument('--no-sheet', action='store_true', help='listing + JSON only; skip the contact sheet (no ffmpeg)')
    ap.add_argument('--selftest', action='store_true', help='known-answer test on window3; ignores --run')
    ap.add_argument('--flaky-json', default=str(FLAKY_JSON), help='flaky-keys.json path (default: REPO/knowledge/gates/flaky-keys.json)')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.run:
        ap.error('--run is required (or use --selftest)')
    run = a.run.expanduser().resolve()
    if not run.is_dir():
        sys.exit(f'no such run dir: {run}')
    out = (a.out or run / 'pair-sheet').expanduser()
    out.mkdir(parents=True, exist_ok=True)

    rows = build_rows(run, a.reference, a.signoff, a.threshold, flaky_json=Path(a.flaky_json))
    suspects = [r for r in rows if is_suspect(r)]
    counts = {'same': 0, 'different': 0, 'no-window': 0, 'no-ref': 0}
    for r in rows:
        counts[r['auto']] = counts.get(r['auto'], 0) + 1
    for r in rows:
        kn = f" flaky k/n={r['flaky_kn']['k']}/{r['flaky_kn']['n']}{' REGRESSION' if r['flaky_kn']['regression'] else ''}" \
            if r.get('flaky_kn') else ''
        print(f'{r["idx"]:3d}  {r["board"]:4} {r["shard"]:14} {r["key"]:40} U9={r["u9_verdict"] or "?":10} '
              f'auto={r["auto"]:10} sim={r["similarity"]}{kn}')
    print(f'{len(rows)} pairs; auto {counts}; {len(suspects)} suspect(s) need an eyeball')

    (out / 'pair-sheet.json').write_text(json.dumps(
        {'run': str(run), 'reference': str(a.reference), 'threshold': a.threshold, 'cols': a.cols,
         'counts': counts, 'suspect_count': len(suspects),
         'note': 'auto/similarity/flaky_kn are a pre-screen; window_verdict is blank on purpose -- the outer fills '
                 'lit/white reading the sheet. Suspects (auto!=same or undecided flaky) are in pair-sheet-suspects.jpeg.',
         'pairs': rows}, indent=1, ensure_ascii=False))

    if a.no_sheet:
        print(f'--no-sheet: wrote {out / "pair-sheet.json"} (skipped the jpegs)')
        return 0
    rc = 0
    full_imgs = stage_imgs(rows, out / 'tiles-full')
    r1 = subprocess.run(['bash', str(CONTACT), str(out / 'pair-sheet-full.jpeg'), '--cols', str(a.cols), *full_imgs])
    rc |= r1.returncode
    if suspects:
        sus_imgs = stage_imgs(suspects, out / 'tiles-suspects')
        r2 = subprocess.run(['bash', str(CONTACT), str(out / 'pair-sheet-suspects.jpeg'), '--cols', str(a.cols), *sus_imgs])
        rc |= r2.returncode
        print(f'suspects sheet -> {out / "pair-sheet-suspects.jpeg"} ({len(suspects)} pairs)')
    else:
        print('no suspects -- every pair auto-matched U9; only the full sheet written')
    print(f'full sheet -> {out / "pair-sheet-full.jpeg"}; listing -> {out / "pair-sheet.json"} (rc={rc})')
    return rc


if __name__ == '__main__':
    sys.exit(main())
