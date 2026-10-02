#!/usr/bin/env python3
"""U12 per-key prediction: for each of the 166 signed U9 keys, its U9 first fatal (hilog file:line), whether it touches
any of the round's three JAR walls, and the upstream ledger control on the same wall.

    predict_u12.py [--out <dir>]

Inputs (all read, nothing typed by hand):
  U9 hilogs            run-index rows runtime_fp a8cb9a5a45a6 + approved-j10g (the same rows u9_first_wall.py reads)
  U9 first fatal       benchmark/2026-10-01-u9-sweep/u9-first-wall.json (text; located here to file:line)
  settings wall        AOSP's `Settings: Can't get key <name> from content://settings/<table>` (the NameValueCache
                       query fallback, logged only after the call path failed) and `OH_CPBridge: query: not connected,
                       authority=settings`, counted per hilog
  android.net wall     benchmark/2026-10-02-android-net-stub-members/predictions.csv
  own-provider wall    benchmark/2026-10-02-own-provider-local/predictions.csv
  upstream controls    benchmark/2026-10-02-upstream-copy-map/match.json (ledger rows joined by package)
Writes predictions.csv (one row per key) and evidence/settings-census.csv (per key: non-primed settings read, counts).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
U9_FP, U9_RUN = 'a8cb9a5a45a6', 'approved-j10g'
CANT = re.compile(r"Settings: Can't get key (\S+) from content://settings/(\w+)")
NC = 'OH_CPBridge: query: not connected, authority=settings'
# the upstream ledger rows that sit on this round's three walls (fixed_in / symptom); others are not the same wall
WALL_ROWS = {'settings': lambda r: 'ANDROID_ID' in (r.get('symptom') or '') or 'Settings' in (r.get('symptom') or ''),
             'net': lambda r: 'android.net' in (r.get('symptom') or '') or 'NetworkInfo' in (r.get('symptom') or ''),
             'own-provider': lambda r: 'own provider' in (r.get('symptom') or '').lower()}


def u9_hilogs(keys):
    out = {}
    for line in (WS / 'westlake-inputs/run-index/index.jsonl').read_text(errors='replace').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get('runtime_fp') != U9_FP or U9_RUN not in r.get('run', '') or r['key'] not in keys or r['key'] in out:
            continue
        p = Path(r['run'].replace('$WORKSPACES', str(WS))) / r['key'] / 'hilog.txt'
        if p.exists():
            out[r['key']] = p
    return out


def rel(p):
    return str(p).replace(str(WS), '$WORKSPACES')


def locate(lines, text):
    """1-based line of the first-fatal text in the hilog (the first 120 chars are the u9-first-wall prefix)."""
    if not text:
        return ''
    probe = text[:120]
    for i, l in enumerate(lines):
        if l.startswith(probe):
            return i + 1
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE))
    a = ap.parse_args()
    out = Path(a.out)
    signoff = json.loads((REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())['keys']
    fw = {e['key']: e for e in json.loads((REPO / 'benchmark/2026-10-01-u9-sweep/u9-first-wall.json').read_text())['entries']}
    net = {r['key']: r for r in csv.DictReader(open(REPO / 'benchmark/2026-10-02-android-net-stub-members/predictions.csv'))}
    own = {r['key']: r for r in csv.DictReader(open(REPO / 'benchmark/2026-10-02-own-provider-local/predictions.csv'))}
    match = {r['key']: r for r in json.loads((REPO / 'benchmark/2026-10-02-upstream-copy-map/match.json').read_text())['records']}
    logs = u9_hilogs(set(signoff))
    rows, census = [], []
    for k in sorted(signoff):
        v = signoff[k]['verdict']
        p = logs.get(k)
        lines = p.read_text(errors='replace').split('\n') if p else []
        reads, aid_line = set(), ''
        for i, l in enumerate(lines):
            m = CANT.search(l)
            if m:
                reads.add(f'{m.group(2)}/{m.group(1)}')
                if m.group(1) == 'android_id' and not aid_line:
                    aid_line = f'{i + 1}: {l.strip()[:160]}'
        n_nc = sum(1 for l in lines if NC in l)
        n_cant = sum(1 for l in lines if CANT.search(l))
        e = fw.get(k, {})
        ff = e.get('first_fatal') or ''
        ff_line = locate(lines, ff)
        u = (match.get(k) or {}).get('upstream') or {}
        ctrl = [f"{u['name']}: {r['symptom']} ({r.get('fixed_in')})" for r in u.get('ledger', [])
                for w, f in WALL_ROWS.items() if f(r)]
        touches = []
        if aid_line:
            touches.append('settings: reads secure/android_id (null on U9)')
        n = net.get(k, {})
        if n.get('observed_net_member_error', '').startswith(('U10', 'U9')):
            touches.append('android.net: ' + n['observed_net_member_error'][:120])
        o = own.get(k, {})
        if o and not o.get('u11j_predicted_effect', '').startswith('no change'):
            touches.append('own-provider: early own-authority lookup (PPMP)')
        moves = 'no'
        if v.startswith('lit'):
            why = 'lit on U9; no change expected'
        elif not touches:
            why = 'first fatal is on none of the three walls'
        else:
            why = {'x': 'android_id becomes 16 hex digits, but x reads it 2 s before its first fatal and survives the '
                        'null (U9 first fatal: TelephonyManager null cast) -> unchanged',
                   'toutiao': 'U9 first fatal is libflipped.so dlopen in attachBaseContext (wall 1, native, U10.1); '
                              'MainActivity NPE on enableGlobal follows from it -> unchanged by this JAR'}.get(k, 'see touches')
        rows.append({'key': k, 'u9_verdict': v, 'u9_first_fatal_family': e.get('family', ''),
                     'u9_hilog': rel(p) if p else '', 'u9_first_fatal_line': ff_line,
                     'u9_first_fatal': ff[:200], 'touches_u12_wall': ' | '.join(touches),
                     'android_id_read_line': aid_line, 'predicted_first_fatal_moves': moves, 'why': why,
                     'settings_cant_get_key_lines': n_cant, 'settings_not_connected_lines': n_nc,
                     'predicted_cant_get_key_lines': 0,
                     'upstream_same_wall_control': ' | '.join(ctrl)})
        census.append({'key': k, 'u9_verdict': v, 'non_primed_reads': ' '.join(sorted(reads)),
                       'cant_get_key_lines': n_cant, 'not_connected_lines': n_nc})
    with open(out / 'predictions.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out / 'evidence').mkdir(exist_ok=True)
    with open(out / 'evidence/settings-census.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(census[0]))
        w.writeheader()
        w.writerows(census)
    moved = [r['key'] for r in rows if r['predicted_first_fatal_moves'] != 'no']
    touched = [r['key'] for r in rows if r['touches_u12_wall']]
    print(f'keys {len(rows)} (hilogs {len(logs)}); touch a U12 wall: {touched}; first fatal predicted to move: {moved}; '
          f'keys with Cant-get-key lines {sum(1 for r in rows if r["settings_cant_get_key_lines"])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
